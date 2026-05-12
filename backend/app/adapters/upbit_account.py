"""Upbit private account adapter — read-only trade history via ccxt.

The user issues access/secret keys at https://upbit.com/mypage/open_api_management
and provides them via env vars (``UPBIT_ACCESS_KEY``, ``UPBIT_SECRET_KEY``).
The adapter only ever calls ``fetch_my_trades`` / ``fetch_balance`` — it never
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


def _trades_sync(access_key: str, secret_key: str) -> list[ExternalTrade]:
    """Fetch all trades for every market the user has traded — sync.

    Upbit's /v1/orders/closed (which ccxt's fetch_my_trades calls under the hood)
    paginates by 100 by default and only returns recent orders unless `start_time`
    is provided. We loop through coins the user currently holds and pull up to
    `_FETCH_LIMIT` orders per market, going back `_LOOKBACK_DAYS`.
    """
    import time  # noqa: PLC0415

    import ccxt  # noqa: PLC0415

    upbit = ccxt.upbit({"apiKey": access_key, "secret": secret_key, "enableRateLimit": True})
    balances = upbit.fetch_balance()

    total_map = balances.get("total") or {}
    coins = sorted(
        asset
        for asset, val in total_map.items()
        if isinstance(val, int | float) and val > 0 and asset != "KRW"
    )
    logger.info(
        "upbit balance summary",
        extra={
            "event": "upbit_balance",
            "total_keys": sorted(total_map.keys()),
            "positive_coins": coins,
            "info_type": type(balances.get("info")).__name__,
        },
    )
    markets: list[str] = [f"{coin}/KRW" for coin in coins if coin]

    since_ms = int((time.time() - _LOOKBACK_DAYS * 86400) * 1000)
    trades: list[ExternalTrade] = []
    for market in markets:
        # ccxt's Upbit class does not implement fetch_my_trades — use
        # fetch_closed_orders (maps to Upbit /v1/orders/closed). For market/limit
        # orders the closed-order row carries the executed qty + average price,
        # so 1 order ≈ 1 trade for our import purposes.
        try:
            raw_orders = upbit.fetch_closed_orders(
                symbol=market, since=since_ms, limit=_FETCH_LIMIT
            )
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
        logger.info(
            "upbit market trades",
            extra={
                "event": "upbit_market_trades",
                "market": market,
                "raw_count": len(raw_orders),
                "mapped_count": mapped_count,
            },
        )
    return trades


_LOOKBACK_DAYS = 365 * 3
_FETCH_LIMIT = 200


def _map_trade(raw: dict[str, object]) -> ExternalTrade | None:
    """Convert a ccxt order/trade dict to an ExternalTrade — None if malformed.

    Accepts either:
      - a trade row (raw['amount'], raw['price'])  — fetch_my_trades shape
      - a closed-order row (raw['filled'], raw['average']) — fetch_closed_orders shape
    """
    external_id = raw.get("id")
    side = raw.get("side")
    symbol = raw.get("symbol")
    timestamp_ms = raw.get("timestamp")
    # Prefer order-shaped fields (filled/average) since fetch_my_trades is unsupported on Upbit.
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
