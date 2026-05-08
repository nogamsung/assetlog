"""Benchmark history adapter — yfinance OHLCV downloads for major indices.

Returns daily close prices over an explicit window so the service can
align them with the user's portfolio time series. Each fetch is offloaded
to a thread because yfinance is sync.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

logger = logging.getLogger("app.adapters.benchmark")


# Default symbol → human-readable label.
KNOWN_BENCHMARKS: dict[str, str] = {
    "^KS11": "KOSPI",
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ",
    "^KQ11": "KOSDAQ",
    "BTC-USD": "BTC (USD)",
    "BTC-KRW": "BTC (KRW)",
}


@dataclass(frozen=True)
class HistoricalClose:
    """A single daily close price for a benchmark symbol."""

    symbol: str
    at: datetime  # tz-aware UTC midnight of the trading day
    close: Decimal


def _fetch_history_sync(symbol: str, start: date, end: date) -> list[HistoricalClose]:
    """Synchronously fetch daily closes for *symbol* over [start, end]."""
    import yfinance as yf  # noqa: PLC0415  # lazy import for testability

    raw = yf.download(
        symbol,
        start=start.isoformat(),
        end=end.isoformat(),
        progress=False,
        auto_adjust=False,
    )
    if raw is None or raw.empty:
        return []

    # ``yf.download`` for a single ticker returns a DataFrame with a single-level
    # columns index containing "Close"; for multi-ticker it would be MultiIndex.
    closes = raw["Close"] if "Close" in raw.columns else raw.get(("Close", symbol))
    if closes is None or closes.empty:
        return []

    out: list[HistoricalClose] = []
    for idx, value in closes.items():
        to_py = getattr(idx, "to_pydatetime", None)
        if to_py is None:
            continue
        ts = to_py()
        if not isinstance(ts, datetime):
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        try:
            close_value = Decimal(str(float(value)))
        except (ValueError, TypeError):
            continue
        out.append(HistoricalClose(symbol=symbol, at=ts, close=close_value))
    out.sort(key=lambda c: c.at)
    return out


class BenchmarkAdapter:
    """yfinance-backed historical close fetcher.

    On any error returns an empty list — callers translate that into a
    ``benchmark_fetch_failed:<symbol>`` warning rather than aborting the
    whole comparison response.
    """

    async def fetch_history(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> list[HistoricalClose]:
        try:
            return await asyncio.to_thread(_fetch_history_sync, symbol, start, end)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "benchmark history fetch failed for %s: %s",
                symbol,
                exc,
                extra={
                    "event": "benchmark_history_fail",
                    "symbol": symbol,
                    "error": str(exc),
                },
            )
            return []

    async def fetch_many(
        self,
        symbols: Sequence[str],
        start: date,
        end: date,
    ) -> dict[str, list[HistoricalClose]]:
        """Fetch all *symbols* in parallel."""
        if not symbols:
            return {}
        results = await asyncio.gather(*(self.fetch_history(s, start, end) for s in symbols))
        return dict(zip(symbols, results, strict=True))
