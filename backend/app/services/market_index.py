"""Market index service — fetch major indices via yfinance with TTL cache."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.schemas.market_index import IndexQuote

logger = logging.getLogger("app.services.market_index")


IndexSpec = tuple[str, str, str]  # (symbol, display_name, currency)


DEFAULT_INDICES: tuple[IndexSpec, ...] = (
    ("^GSPC", "S&P 500", "USD"),
    ("^IXIC", "NASDAQ", "USD"),
    ("^KS11", "KOSPI", "KRW"),
    ("^KQ11", "KOSDAQ", "KRW"),
    ("BTC-KRW", "BTC", "KRW"),
)


IndexFetcher = Callable[[Sequence[IndexSpec]], Awaitable[list[IndexQuote]]]


def _fetch_indices_sync(specs: Sequence[IndexSpec]) -> list[IndexQuote]:
    """Blocking yfinance fetcher — runs inside ``asyncio.to_thread``.

    Uses ``period='5d'`` so weekend/holiday gaps still leave at least two close
    points to compute change vs previous close.
    """
    import yfinance as yf  # noqa: PLC0415  # lazy import for testability

    tickers = [s[0] for s in specs]
    raw = yf.download(
        tickers,
        period="5d",
        progress=False,
        auto_adjust=False,
        group_by="ticker",
    )

    if raw is None or raw.empty:
        return []

    fetched_at = datetime.now(tz=UTC)
    quotes: list[IndexQuote] = []

    for symbol, name, currency in specs:
        try:
            if (symbol, "Close") in raw.columns:
                close = raw[(symbol, "Close")].dropna()
            elif "Close" in raw.columns:
                close = raw["Close"].dropna()
            else:
                continue

            if close.empty:
                continue

            price = Decimal(str(close.iloc[-1]))
            if len(close) >= 2:
                prev = Decimal(str(close.iloc[-2]))
                change = price - prev
                change_pct = (
                    (change / prev * Decimal("100")) if prev != 0 else Decimal("0")
                )
            else:
                change = Decimal("0")
                change_pct = Decimal("0")

            quotes.append(
                IndexQuote(
                    symbol=symbol,
                    name=name,
                    currency=currency,
                    price=price.quantize(Decimal("0.01")),
                    change=change.quantize(Decimal("0.01")),
                    change_pct=change_pct.quantize(Decimal("0.01")),
                    fetched_at=fetched_at,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "market_index fetch failed for %s: %s",
                symbol,
                exc,
                extra={"event": "market_index_fetch_fail", "symbol": symbol},
            )

    return quotes


async def yfinance_index_fetcher(specs: Sequence[IndexSpec]) -> list[IndexQuote]:
    """Async wrapper that offloads the blocking yfinance call to a thread."""
    return await asyncio.to_thread(_fetch_indices_sync, specs)


class MarketIndexService:
    """Return cached index quotes with a TTL.

    yfinance is rate-sensitive, and the dashboard renders these on every load —
    a small in-process cache (default 5 minutes) is enough.
    """

    def __init__(
        self,
        fetcher: IndexFetcher = yfinance_index_fetcher,
        specs: Sequence[IndexSpec] = DEFAULT_INDICES,
        ttl_seconds: int = 300,
    ) -> None:
        self._fetcher = fetcher
        self._specs = tuple(specs)
        self._ttl = timedelta(seconds=ttl_seconds)
        self._cache: tuple[list[IndexQuote], datetime] | None = None
        self._lock = asyncio.Lock()

    async def list_indices(self) -> list[IndexQuote]:
        """Return cached quotes if fresh, otherwise fetch and cache."""
        async with self._lock:
            now = datetime.now(tz=UTC)
            if self._cache is not None:
                quotes, fetched_at = self._cache
                if now - fetched_at < self._ttl:
                    return quotes

            try:
                quotes = await self._fetcher(self._specs)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "market_index batch fetch failed: %s",
                    exc,
                    extra={"event": "market_index_batch_fail"},
                )
                if self._cache is not None:
                    return self._cache[0]
                return []

            self._cache = (quotes, now)
            return quotes
