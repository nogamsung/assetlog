"""Upbit private account adapter — read-only trade history via ccxt.

The user issues access/secret keys at https://upbit.com/mypage/open_api_management
and provides them via env vars (``UPBIT_ACCESS_KEY``, ``UPBIT_SECRET_KEY``).
The adapter only ever calls ``fetch_closed_orders`` / ``fetch_balance`` — it never
places orders.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.exchange_sync import ExternalTrade
from app.domain.transaction_type import TransactionType
from app.exceptions import ExternalIntegrationError

logger = logging.getLogger("app.adapters.upbit_account")

_FETCH_LIMIT = 200
_QUOTE_PREFERENCE = ("KRW", "BTC", "USDT")


def _trades_sync(access_key: str, secret_key: str) -> list[ExternalTrade]:
    """Fetch all closed orders for every market the user currently holds — sync.

    Steps:
      1. load_markets() so we know which trading pairs Upbit actually exposes.
      2. fetch_balance() for the user's positive holdings.
      3. For each held coin pick the first available quote (KRW > BTC > USDT)
         — Upbit lists some coins only on /BTC or /USDT.
      4. fetch_closed_orders(symbol, limit=200) per resolved market.

    We deliberately omit `since`: in production Upbit's /v1/orders/closed returned
    empty when called with start_time, but returns the latest 100 closed orders
    when called without it.
    """
    import ccxt  # noqa: PLC0415

    upbit = ccxt.upbit({"apiKey": access_key, "secret": secret_key, "enableRateLimit": True})
    upbit.load_markets()
    available_markets: set[str] = set(upbit.markets.keys() if upbit.markets else [])

    balances = upbit.fetch_balance()
    total_map = balances.get("total") or {}
    coins = sorted(
        asset
        for asset, val in total_map.items()
        if isinstance(val, int | float) and val > 0 and asset != "KRW"
    )

    markets: list[str] = []
    skipped_no_market: list[str] = []
    for coin in coins:
        chosen: str | None = None
        for quote in _QUOTE_PREFERENCE:
            symbol = f"{coin}/{quote}"
            if symbol in available_markets:
                chosen = symbol
                break
        if chosen is None:
            skipped_no_market.append(coin)
        else:
            markets.append(chosen)

    # WARNING level so it surfaces even when production log filters hide INFO.
    logger.warning(
        "upbit balance summary",
        extra={
            "event": "upbit_balance",
            "positive_coins": coins,
            "matched_markets": markets,
            "skipped_no_market": skipped_no_market,
        },
    )

    trades: list[ExternalTrade] = []
    for market in markets:
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
    return trades


def _map_trade(raw: dict[str, object]) -> ExternalTrade | None:
    """Convert a ccxt closed-order dict to an ExternalTrade — None if malformed.

    Closed-order rows carry the executed qty in `filled` and the executed price
    in `average`; older trade-shaped rows use `amount` / `price`. Both supported.
    """
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
        """Return every trade for every market the user has touched.

        Sorted ascending by traded_at. Empty list on transient errors so that
        callers can retry on the next scheduler tick.
        """
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
