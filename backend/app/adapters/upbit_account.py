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
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.domain.exchange_sync import ExternalTrade
from app.domain.transaction_type import TransactionType
from app.exceptions import ExternalIntegrationError

logger = logging.getLogger("app.adapters.upbit_account")

_FETCH_LIMIT = 100  # Upbit /v1/orders/closed default; max 1000 but 100 is safer
_QUOTE_PREFERENCE = ("KRW", "BTC", "USDT")
_MAX_PAGES = 200  # safety: 200 × 100 = 20,000 orders cap
_PAGE_PROGRESS_REQUIRED = True  # break if oldest_at doesn't move

# Match transactions table column precision (Numeric(20,6) for price,
# Numeric(28,10) for quantity) so MySQL doesn't truncate inserts.
_PRICE_QUANTUM = Decimal("0.000001")
_QTY_QUANTUM = Decimal("0.0000000001")


def _trades_sync(access_key: str, secret_key: str) -> list[ExternalTrade]:
    """Fetch the user's Upbit holdings AND closed-order history — sync.

    Strategy:
      1. Fetch all closed orders → real trade history.
      2. Fetch current balances. For EVERY held coin compute:
            history_qty = sum(BUY) − sum(SELL) of trades from step 1
            actual_qty  = current balance from Upbit
            diff        = actual_qty − history_qty
         If |diff| > 0 emit a synthetic BUY/SELL adjustment so the system
         holding matches the real Upbit balance (covers airdrops, deposits
         from external wallets, history gaps, etc).
      3. Coins held with no history at all also fall through this path (history
         contributes 0 → diff = full balance → synthetic BUY).

    All synthetic adjustments share a stable external_id (`upbit:adjust:<COIN>`)
    so the upstream replace-then-insert path keeps holdings exact on every sync.
    """
    import ccxt  # noqa: PLC0415

    upbit = ccxt.upbit({"apiKey": access_key, "secret": secret_key, "enableRateLimit": True})
    upbit.load_markets()

    # Step 1: pull every closed order across all markets (real trade history).
    history = _fetch_all_closed_orders(upbit)
    if not history:
        logger.warning(
            "upbit primary all-orders fetch returned nothing; falling back to per-market",
            extra={"event": "upbit_phase0_empty"},
        )
        history = _fetch_history_per_held_market(upbit)

    # Step 2: balance-based adjustment so system holdings match Upbit exactly.
    balances = upbit.fetch_balance()
    adjustments = _balance_adjustments(balances, history)
    return history + adjustments


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


def _balance_adjustments(
    balances: dict[str, Any], history: list[ExternalTrade]
) -> list[ExternalTrade]:
    """Emit BUY/SELL adjustments to make system holdings == Upbit balance.

    For each held coin (Upbit `info` row): compute system_qty from history,
    compare with actual balance, emit a single BUY (positive diff) or SELL
    (negative diff) trade with stable external_id `upbit:adjust:<COIN>` —
    the replace path keeps it idempotent.
    """
    info = balances.get("info")
    if not isinstance(info, list):
        return []

    history_qty: dict[str, Decimal] = {}
    for t in history:
        delta = t.quantity if t.side == TransactionType.BUY else -t.quantity
        history_qty[t.symbol] = history_qty.get(t.symbol, Decimal(0)) + delta

    out: list[ExternalTrade] = []
    skipped_zero_avg: list[str] = []
    matched: list[str] = []
    now = datetime.now(UTC)
    for row in info:
        if not isinstance(row, dict):
            continue
        currency = row.get("currency")
        if not isinstance(currency, str) or currency.upper() == "KRW":
            continue
        symbol = currency.upper()
        actual = _to_decimal(row.get("balance"))
        avg_buy = _to_decimal(row.get("avg_buy_price"))
        if actual is None or actual < 0:
            continue
        sys_qty = history_qty.get(symbol, Decimal(0))
        diff = actual - sys_qty
        if abs(diff) < _QTY_QUANTUM:
            matched.append(symbol)
            continue
        if avg_buy is None or avg_buy <= 0:
            # Deposit-only with no cost basis — use 1.0 as harmless placeholder
            # so quantity still shows in holdings (PnL is the user's problem).
            avg_buy = Decimal("1")
            skipped_zero_avg.append(symbol)
        side = TransactionType.BUY if diff > 0 else TransactionType.SELL
        qty = abs(diff)
        out.append(
            ExternalTrade(
                external_id=f"upbit:adjust:{symbol}",
                symbol=symbol,
                quote_currency="KRW",
                side=side,
                quantity=_q(qty, _QTY_QUANTUM),
                price=_q(avg_buy, _PRICE_QUANTUM),
                traded_at=now,
            )
        )
    logger.warning(
        "upbit balance adjustments",
        extra={
            "event": "upbit_balance_adjust",
            "adjusted": [(t.symbol, str(t.side.value), str(t.quantity)) for t in out],
            "matched": matched,
            "no_avg_buy_used_placeholder": skipped_zero_avg,
        },
    )
    return out


def _q(value: Decimal, quantum: Decimal) -> Decimal:
    """Quantize to MySQL column precision; falls back to value on overflow."""
    try:
        return value.quantize(quantum, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return value


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
        quantity=_q(qty, _QTY_QUANTUM),
        price=_q(price, _PRICE_QUANTUM),
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
        quantity=_q(Decimal(str(amount)), _QTY_QUANTUM),
        price=_q(Decimal(str(price)), _PRICE_QUANTUM),
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

    async def fetch_cash_flow(self) -> list[dict[str, Any]]:
        """Return every KRW deposit + withdrawal as a normalised dict.

        Each row: ``{"external_id", "kind", "amount", "currency", "traded_at"}``.
        ``kind`` is one of ``"deposit"`` / ``"withdraw"``. Used by sync flows to
        push into ``cash_account_transactions`` so the per-broker balance lines
        up with what the user sees on the Upbit app.
        """
        try:
            rows = await asyncio.to_thread(
                _cash_flow_sync, self._access_key, self._secret_key
            )
        except Exception as exc:
            logger.warning(
                "upbit fetch_cash_flow failed: %s",
                exc,
                extra={"event": "upbit_cashflow_fail", "error": str(exc)},
            )
            return []
        return rows

    async def fetch_balance_krw(self) -> Decimal | None:
        """Return the user's available KRW balance on Upbit (or ``None`` on error)."""
        try:
            return await asyncio.to_thread(
                _balance_krw_sync, self._access_key, self._secret_key
            )
        except Exception as exc:
            logger.warning(
                "upbit fetch_balance_krw failed: %s",
                exc,
                extra={"event": "upbit_balance_fail", "error": str(exc)},
            )
            return None


def _balance_krw_sync(access_key: str, secret_key: str) -> Decimal | None:
    """Return the spot KRW balance reported by Upbit, or None if missing."""
    import ccxt  # noqa: PLC0415

    upbit = ccxt.upbit({"apiKey": access_key, "secret": secret_key, "enableRateLimit": True})
    raw = upbit.fetch_balance()
    info = raw.get("info") if isinstance(raw, dict) else None
    rows = info if isinstance(info, list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("currency") == "KRW":
            try:
                return Decimal(str(row.get("balance", "0")))
            except (TypeError, ValueError):
                return None
    return None


def _cash_flow_sync(access_key: str, secret_key: str) -> list[dict[str, Any]]:
    """Hit Upbit's native /v1/deposits and /v1/withdraws endpoints for KRW."""
    import ccxt  # noqa: PLC0415

    upbit = ccxt.upbit({"apiKey": access_key, "secret": secret_key, "enableRateLimit": True})
    out: list[dict[str, Any]] = []

    def _norm_iso(s: object) -> datetime | None:
        if not isinstance(s, str):
            return None
        try:
            # Upbit returns RFC3339; treat naïve strings as KST
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.astimezone(UTC)
        except ValueError:
            return None

    # Deposits — only KRW. Crypto deposits are inventory transfers, not cash.
    try:
        deposits = upbit.private_get_deposits({"currency": "KRW", "limit": 100})
    except Exception:  # noqa: BLE001
        deposits = []
    if isinstance(deposits, list):
        for d in deposits:
            if not isinstance(d, dict):
                continue
            uuid = d.get("uuid")
            amount = d.get("amount")
            done_at = _norm_iso(d.get("done_at") or d.get("created_at"))
            if not uuid or amount is None or done_at is None:
                continue
            try:
                amount_dec = Decimal(str(amount))
            except (TypeError, ValueError):
                continue
            if amount_dec <= 0:
                continue
            out.append({
                "external_id": f"upbit-dep-{uuid}",
                "kind": "deposit",
                "amount": amount_dec,
                "currency": "KRW",
                "traded_at": done_at,
            })

    # Withdrawals — only KRW.
    try:
        withdraws = upbit.private_get_withdraws({"currency": "KRW", "limit": 100})
    except Exception:  # noqa: BLE001
        withdraws = []
    if isinstance(withdraws, list):
        for w in withdraws:
            if not isinstance(w, dict):
                continue
            uuid = w.get("uuid")
            amount = w.get("amount")
            done_at = _norm_iso(w.get("done_at") or w.get("created_at"))
            if not uuid or amount is None or done_at is None:
                continue
            try:
                amount_dec = Decimal(str(amount))
            except (TypeError, ValueError):
                continue
            if amount_dec <= 0:
                continue
            out.append({
                "external_id": f"upbit-wd-{uuid}",
                "kind": "withdraw",
                "amount": amount_dec,
                "currency": "KRW",
                "traded_at": done_at,
            })

    return out
