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
    """Fetch all trades for every market the user has traded — sync."""
    import ccxt  # noqa: PLC0415  # lazy import for testability

    upbit = ccxt.upbit({"apiKey": access_key, "secret": secret_key, "enableRateLimit": True})
    balances = upbit.fetch_balance()
    # ccxt's standard `total` map is dict[str, float] keyed by currency.
    # We previously parsed `info` (the raw exchange payload), but Upbit's
    # /v1/accounts returns a list — caused 'list has no attribute items'.
    coins = sorted(
        asset
        for asset, val in (balances.get("total") or {}).items()
        if isinstance(val, int | float) and val > 0 and asset != "KRW"
    )
    markets: list[str] = [f"{coin}/KRW" for coin in coins if coin]

    trades: list[ExternalTrade] = []
    for market in markets:
        try:
            raw_trades = upbit.fetch_my_trades(symbol=market)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "upbit fetch_my_trades failed for %s: %s",
                market,
                exc,
                extra={"event": "upbit_trades_fail", "market": market},
            )
            continue
        for raw in raw_trades:
            mapped = _map_trade(raw)
            if mapped is not None:
                trades.append(mapped)
    return trades


def _map_trade(raw: dict[str, object]) -> ExternalTrade | None:
    """Convert a ccxt trade dict to an ExternalTrade — None if malformed."""
    external_id = raw.get("id")
    side = raw.get("side")
    symbol = raw.get("symbol")
    timestamp_ms = raw.get("timestamp")
    amount = raw.get("amount")
    price = raw.get("price")
    if (
        not isinstance(external_id, str)
        or not isinstance(side, str)
        or not isinstance(symbol, str)
        or not isinstance(timestamp_ms, int | float)
        or not isinstance(amount, int | float)
        or not isinstance(price, int | float)
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
