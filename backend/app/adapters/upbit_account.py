"""Upbit private account adapter — read-only trade history via ccxt.

The user issues access/secret keys at https://upbit.com/mypage/open_api_management
and provides them via env vars (``UPBIT_ACCESS_KEY``, ``UPBIT_SECRET_KEY``).
The adapter only ever reads — it never places orders.

Strategy
--------
Phase 0 (primary): call Upbit's /v1/orders/closed *without a market filter*
    via ccxt's implicit method (``private_get_orders_closed``). This returns
    every closed order across every market, paginated by ``start_time``/
    ``end_time``. We walk back in time until the page is short or empty,
    capturing the user's full trade history — including coins the user no
    longer holds.

Phase 1+ (fallback): if Phase 0 yields nothing (e.g. API rejects the
    no-symbol form on a future Upbit change), iterate per-market with
    ``fetch_closed_orders(symbol=...)`` over the user's currently held coins.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.domain.exchange_sync import ExternalTrade
from app.domain.transaction_type import TransactionType
from app.exceptions import ExternalIntegrationError

logger = logging.getLogger("app.adapters.upbit_account")

_FETCH_LIMIT = 100  # Upbit /v1/orders/closed default; max 1000 but 100 is safer
_QUOTE_PREFERENCE = ("KRW", "BTC", "USDT")
_MAX_PAGES = 200  # safety: 200 × 100 = 20,000 orders cap
_PAGE_PROGRESS_REQUIRED = True  # break if oldest_at doesn't move


def _trades_sync(access_key: str, secret_key: str) -> list[ExternalTrade]:
    """Fetch the user's Upbit holdings AND closed-order history — sync.

    Returns a combined list of:
      - ExternalTrades from /v1/orders/closed (real history, when available)
      - Synthetic BUY trades from current holdings (qty=balance, price=avg_buy_price)
        for any held coin that wasn't represented in the history fetch.

    Synthetic trades carry a stable external_id (`upbit:holding:<COIN>`) so a
    re-sync dedupes them (they don't double-count balance).
    """
    import ccxt  # noqa: PLC0415

    upbit = ccxt.upbit({"apiKey": access_key, "secret": secret_key, "enableRateLimit": True})
    upbit.load_markets()

    # Step 1: pull every closed order across all markets (real trade history).
    history = _fetch_all_closed_orders(upbit)
    if not history:
        # Fallback per-market in case the no-symbol form ever stops working.
        logger.warning(
            "upbit primary all-orders fetch returned nothing; falling back to per-market",
            extra={"event": "upbit_phase0_empty"},
        )
        history = _fetch_history_per_held_market(upbit)

    covered_symbols: set[str] = {t.symbol for t in history}

    # Step 2: synthesize BUY trades from holdings the history didn't cover.
    balances = upbit.fetch_balance()
    synthetic = _balance_to_synthetic_trades(balances, exclude_symbols=covered_symbols)

    return history + synthetic


def _fetch_history_per_held_market(upbit: Any) -> list[ExternalTrade]:
    """Per-market fallback when no-symbol /orders/closed returns nothing."""
    available_markets: set[str] = set(upbit.markets.keys() if upbit.markets else [])
    balances = upbit.fetch_balance()
    total_map = balances.get("total") or {}
    coins = sorted(
        asset
        for asset, val in total_map.items()
        if isinstance(val, int | float) and val > 0 and asset != "KRW"
    )
    primary_markets: list[str] = []
    for coin in coins:
        for quote in _QUOTE_PREFERENCE:
            symbol = f"{coin}/{quote}"
            if symbol in available_markets:
                primary_markets.append(symbol)
                break
    fallback_trades, _ = _fetch_orders_for_markets(upbit, primary_markets)
    return fallback_trades


def _balance_to_synthetic_trades(
    balances: dict[str, Any], exclude_symbols: set[str]
) -> list[ExternalTrade]:
    """Build placeholder BUY trades from current holdings.

    Uses Upbit's raw `info` list (each row has currency / balance / avg_buy_price)
    so the user's "보유 자산" view is populated even when the trade history is
    empty (deposit-only assets or trades pre-dating the order log).

    Skipped:
      - KRW (cash)
      - balance <= 0
      - avg_buy_price <= 0 (deposit-only without a recorded cost basis)
      - currencies already covered by real trade history
    """
    info = balances.get("info")
    if not isinstance(info, list):
        return []
    out: list[ExternalTrade] = []
    skipped_no_avg: list[str] = []
    skipped_covered: list[str] = []
    now = datetime.now(UTC)
    for row in info:
        if not isinstance(row, dict):
            continue
        currency = row.get("currency")
        if not isinstance(currency, str) or currency.upper() == "KRW":
            continue
        symbol_upper = currency.upper()
        if symbol_upper in exclude_symbols:
            skipped_covered.append(currency)
            continue
        balance = _to_decimal(row.get("balance"))
        avg_buy = _to_decimal(row.get("avg_buy_price"))
        if balance is None or balance <= 0:
            continue
        if avg_buy is None or avg_buy <= 0:
            skipped_no_avg.append(currency)
            continue
        out.append(
            ExternalTrade(
                external_id=f"upbit:holding:{symbol_upper}",
                symbol=symbol_upper,
                quote_currency="KRW",
                side=TransactionType.BUY,
                quantity=balance,
                price=avg_buy,
                traded_at=now,
            )
        )
    logger.warning(
        "upbit synthetic holdings",
        extra={
            "event": "upbit_synthetic_holdings",
            "synthesized": [t.symbol for t in out],
            "skipped_no_avg": skipped_no_avg,
            "skipped_covered_by_history": skipped_covered,
        },
    )
    return out


def _fetch_all_closed_orders(upbit: Any) -> list[ExternalTrade]:
    """Page through Upbit /v1/orders/closed without a market filter.

    Upbit returns up to ``_FETCH_LIMIT`` orders sorted desc by created_at.
    For the next page we set ``end_time`` to just before the oldest order's
    timestamp, so each page strictly precedes the previous one.
    """
    trades: list[ExternalTrade] = []
    seen_uuids: set[str] = set()
    end_time: str | None = None  # ISO8601 with TZ; None = "now"

    for page in range(_MAX_PAGES):
        params: dict[str, Any] = {
            "state": "done",
            "limit": _FETCH_LIMIT,
            "order_by": "desc",
        }
        if end_time is not None:
            params["end_time"] = end_time

        try:
            raw_page = upbit.private_get_orders_closed(params)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "upbit private_get_orders_closed page %d failed: %s",
                page,
                exc,
                extra={"event": "upbit_all_orders_fail", "page": page, "error": str(exc)},
            )
            break

        if not isinstance(raw_page, list) or not raw_page:
            logger.warning(
                "upbit private_get_orders_closed page %d empty",
                page,
                extra={"event": "upbit_all_orders_done", "page": page, "total": len(trades)},
            )
            break

        new_in_page = 0
        oldest_iso: str | None = None
        for raw in raw_page:
            uuid = raw.get("uuid") if isinstance(raw, dict) else None
            if not isinstance(uuid, str) or uuid in seen_uuids:
                continue
            seen_uuids.add(uuid)
            mapped = _map_native_order(raw)
            if mapped is not None:
                trades.append(mapped)
                new_in_page += 1
            created_at = raw.get("created_at") if isinstance(raw, dict) else None
            if isinstance(created_at, str) and (oldest_iso is None or created_at < oldest_iso):
                oldest_iso = created_at

        logger.warning(
            "upbit all-orders page",
            extra={
                "event": "upbit_all_orders_page",
                "page": page,
                "raw_count": len(raw_page),
                "mapped_in_page": new_in_page,
                "running_total": len(trades),
                "oldest_iso": oldest_iso,
            },
        )

        if len(raw_page) < _FETCH_LIMIT:
            break  # last page
        if oldest_iso is None:
            break  # nothing to use as cursor
        if _PAGE_PROGRESS_REQUIRED and oldest_iso == end_time:
            break  # cursor stuck — defensive
        end_time = oldest_iso

    return trades


def _map_native_order(raw: dict[str, Any]) -> ExternalTrade | None:
    """Map an Upbit-native /v1/orders/closed row to ExternalTrade.

    Upbit shape (selected fields)::

        {
          "uuid": "9bf...c5",
          "side": "bid" | "ask",
          "market": "KRW-BTC",
          "state": "done",
          "price": "50000000.0",          # limit price (None for market orders)
          "avg_price": "50100000.0",      # actual executed avg (use this)
          "executed_volume": "0.001",
          "volume": "0.001",
          "created_at": "2024-09-15T10:30:00+09:00",
          ...
        }
    """
    uuid = raw.get("uuid")
    side = raw.get("side")
    market = raw.get("market")
    state = raw.get("state")
    if not (
        isinstance(uuid, str)
        and isinstance(side, str)
        and isinstance(market, str)
        and isinstance(state, str)
    ):
        return None
    if state != "done":
        return None
    if side not in {"bid", "ask"}:
        return None
    if "-" not in market:
        return None
    quote_raw, _, base_raw = market.partition("-")  # Upbit: QUOTE-BASE
    if not quote_raw or not base_raw:
        return None

    qty = _to_decimal(raw.get("executed_volume"))
    price = _to_decimal(raw.get("avg_price")) or _to_decimal(raw.get("price"))
    created_at = raw.get("created_at")
    if qty is None or price is None or qty <= 0 or price <= 0:
        return None
    if not isinstance(created_at, str):
        return None
    try:
        traded_at = datetime.fromisoformat(created_at).astimezone(UTC)
    except ValueError:
        return None

    return ExternalTrade(
        external_id=uuid,
        symbol=base_raw.upper(),
        quote_currency=quote_raw.upper(),
        side=TransactionType.BUY if side == "bid" else TransactionType.SELL,
        quantity=qty,
        price=price,
        traded_at=traded_at,
    )


def _to_decimal(v: object) -> Decimal | None:
    """Tolerant Decimal conversion — Upbit returns numerics as strings."""
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (ArithmeticError, ValueError):
        return None


def _fetch_orders_for_markets(
    upbit: Any, markets: list[str]
) -> tuple[list[ExternalTrade], set[str]]:
    """Fallback: per-market closed orders via ccxt's standard helper."""
    trades: list[ExternalTrade] = []
    attempted: set[str] = set()
    for market in markets:
        attempted.add(market)
        try:
            raw_orders = upbit.fetch_closed_orders(symbol=market, limit=_FETCH_LIMIT)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "upbit fetch_closed_orders failed for %s: %s",
                market,
                exc,
                extra={"event": "upbit_orders_fail", "market": market},
            )
            continue
        mapped_count = 0
        for raw in raw_orders:
            mapped = _map_trade(raw)
            if mapped is not None:
                trades.append(mapped)
                mapped_count += 1
        logger.warning(
            "upbit market trades",
            extra={
                "event": "upbit_market_trades",
                "market": market,
                "raw_count": len(raw_orders),
                "mapped_count": mapped_count,
            },
        )
    return trades, attempted


def _map_trade(raw: dict[str, object]) -> ExternalTrade | None:
    """Convert a ccxt closed-order dict to ExternalTrade — None if malformed."""
    external_id = raw.get("id")
    side = raw.get("side")
    symbol = raw.get("symbol")
    timestamp_ms = raw.get("timestamp")
    amount = raw.get("filled")
    if not isinstance(amount, int | float):
        amount = raw.get("amount")
    price = raw.get("average")
    if not isinstance(price, int | float):
        price = raw.get("price")
    if (
        not isinstance(external_id, str)
        or not isinstance(side, str)
        or not isinstance(symbol, str)
        or not isinstance(timestamp_ms, int | float)
        or not isinstance(amount, int | float)
        or not isinstance(price, int | float)
        or amount <= 0
        or price <= 0
    ):
        return None

    base, _, quote = symbol.partition("/")
    if not base or not quote:
        return None
    if side not in {"buy", "sell"}:
        return None

    return ExternalTrade(
        external_id=str(external_id),
        symbol=base.upper(),
        quote_currency=quote.upper(),
        side=TransactionType.BUY if side == "buy" else TransactionType.SELL,
        quantity=Decimal(str(amount)),
        price=Decimal(str(price)),
        traded_at=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC),
    )


class UpbitAccountAdapter:
    """Async wrapper around the synchronous ccxt client."""

    def __init__(self, access_key: str, secret_key: str) -> None:
        if not access_key or not secret_key:
            raise ExternalIntegrationError("Upbit API keys are not configured.")
        self._access_key = access_key
        self._secret_key = secret_key

    async def fetch_trades(self) -> list[ExternalTrade]:
        """Return every closed trade for the account, sorted ascending by traded_at."""
        try:
            trades = await asyncio.to_thread(_trades_sync, self._access_key, self._secret_key)
        except Exception as exc:
            logger.error(
                "upbit fetch_trades failed: %s",
                exc,
                extra={"event": "upbit_fetch_fail", "error": str(exc)},
            )
            raise ExternalIntegrationError(f"Upbit fetch failed: {exc}") from exc
        trades.sort(key=lambda t: t.traded_at)
        return trades
