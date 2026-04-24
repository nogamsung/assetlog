"""US stock price adapter — yfinance."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from app.adapters.base import _wrap_failure
from app.adapters.normalize import normalize_us_exchange_code, normalize_us_stock_symbol  # MODIFIED
from app.domain.asset_type import AssetType
from app.domain.price_refresh import FetchBatchResult, FetchFailure, PriceQuote, SymbolRef
from app.domain.symbol_search import SymbolCandidate  # ADDED

logger = logging.getLogger("app.adapters.us_stock")

_MISSING = object()  # sentinel for negative cache entries


def _fetch_prices_sync(tickers: list[str]) -> dict[str, Decimal]:
    """Download the latest closing prices for *tickers* using yfinance (sync).

    Uses ``yf.download`` for bulk efficiency.  Falls back to individual
    ``Ticker.fast_info`` if bulk download returns no data.

    Args:
        tickers: List of upper-cased ticker symbols.

    Returns:
        Mapping from ticker symbol to latest closing price.

    Raises:
        ValueError: If a ticker could not be resolved.
    """
    import yfinance as yf  # noqa: PLC0415  # lazy import for testability

    prices: dict[str, Decimal] = {}

    if not tickers:
        return prices

    # Bulk download (period="5d") returns a MultiIndex DataFrame.
    raw = yf.download(tickers, period="5d", progress=False, auto_adjust=True)

    if raw is not None and not raw.empty:
        close = raw["Close"] if len(tickers) > 1 else raw[["Close"]]
        for ticker in tickers:
            try:
                col = ticker if ticker in close.columns else close.columns[0]
                series = close[col].dropna()
                if not series.empty:
                    prices[ticker] = Decimal(str(series.iloc[-1]))
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "yf.download column extraction failed for %s: %s",
                    ticker,
                    exc,
                )

    # For any ticker not resolved by bulk, try fast_info.
    missing = [t for t in tickers if t not in prices]
    for ticker in missing:
        try:
            info = yf.Ticker(ticker).fast_info
            last = getattr(info, "last_price", None)
            if last is not None:
                prices[ticker] = Decimal(str(last))
            else:
                raise ValueError(f"fast_info.last_price is None for {ticker}")
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"yfinance could not resolve {ticker}: {exc}") from exc

    return prices


def _fetch_info_sync(ticker: str) -> SymbolCandidate | None:  # ADDED
    """Fetch yfinance Ticker.info for *ticker* (sync, runs in thread pool).

    Args:
        ticker: Upper-cased, normalised US ticker symbol.

    Returns:
        SymbolCandidate if info is usable, None otherwise.
    """
    import yfinance as yf  # noqa: PLC0415

    raw_info = yf.Ticker(ticker).info
    info: dict[str, object] = raw_info if isinstance(raw_info, dict) else {}
    short_name = info.get("shortName") or info.get("longName")
    if not short_name:
        return None
    raw_exchange = str(info.get("exchange", "")) or "US"
    exchange = normalize_us_exchange_code(raw_exchange)
    currency = str(info.get("currency") or "USD")
    return SymbolCandidate(
        asset_type=AssetType.US_STOCK,
        symbol=ticker,
        name=str(short_name),
        exchange=exchange,
        currency=currency,
    )


class UsStockAdapter:
    """Fetch latest prices for US-listed equities and ETFs via yfinance.

    yfinance is a blocking library — fetches are offloaded to a thread
    pool via ``asyncio.to_thread``.
    """

    asset_type: AssetType = AssetType.US_STOCK

    def __init__(self) -> None:  # ADDED
        # Positive cache: ticker -> SymbolCandidate
        # Negative cache: ticker -> _MISSING  (avoids repeated failed lookups)
        self._info_cache: dict[str, SymbolCandidate | object] = {}

    async def fetch_batch(
        self,
        symbols: Sequence[SymbolRef],
    ) -> FetchBatchResult:
        """Fetch prices for all symbols in a single yfinance bulk call.

        Args:
            symbols: Sequence of SymbolRef with asset_type == US_STOCK.

        Returns:
            FetchBatchResult with successes and per-symbol failures.
        """
        successes: list[PriceQuote] = []
        failures: list[FetchFailure] = []
        fetched_at = datetime.now(tz=UTC)

        if not symbols:
            return FetchBatchResult(successes=successes, failures=failures)

        # Build normalised ticker → ref mapping (keep last if duplicates)
        ref_by_ticker: dict[str, SymbolRef] = {}
        for ref in symbols:
            norm = normalize_us_stock_symbol(ref.symbol)
            ref_by_ticker[norm] = ref

        tickers = list(ref_by_ticker.keys())

        try:
            price_map = await asyncio.to_thread(_fetch_prices_sync, tickers)
        except Exception as exc:  # noqa: BLE001
            # Catastrophic failure — mark all symbols as failed
            logger.error(
                "us_stock bulk fetch failed entirely: %s",
                exc,
                extra={"event": "us_stock_bulk_fail", "error_class": type(exc).__name__},
            )
            for ref in symbols:
                failures.append(_wrap_failure(ref, exc))
            return FetchBatchResult(successes=successes, failures=failures)

        for norm_ticker, ref in ref_by_ticker.items():
            if norm_ticker in price_map:
                price = price_map[norm_ticker]
                successes.append(
                    PriceQuote(
                        ref=ref,
                        price=price,
                        currency="USD",
                        fetched_at=fetched_at,
                    )
                )
                logger.debug(
                    "us_stock fetched",
                    extra={
                        "event": "us_stock_fetch_ok",
                        "symbol": norm_ticker,
                        "price": str(price),
                    },
                )
            else:
                exc_missing = ValueError(f"No price data returned for {norm_ticker}")
                failures.append(_wrap_failure(ref, exc_missing))
                logger.warning(
                    "us_stock no data for %s",
                    norm_ticker,
                    extra={"event": "us_stock_fetch_fail", "symbol": norm_ticker},
                )

        return FetchBatchResult(successes=successes, failures=failures)

    async def search_symbols(self, query: str, limit: int) -> list[SymbolCandidate]:  # ADDED
        """Search US stocks by exact-match info lookup via yfinance.

        Strategy: exact symbol match only (yfinance does not support fuzzy search).
        Result is cached per-ticker (positive + negative TTL handled by instance lifetime).

        Note: This method logs a ``us_stock_search_exact_only`` event since it
        can only return at most 1 candidate per query.

        Args:
            query: User query string (pre-stripped by caller).
            limit: Maximum number of results (only 1 ever returned).

        Returns:
            List with at most 1 SymbolCandidate.
        """
        norm = normalize_us_stock_symbol(query)
        logger.debug(
            "us_stock search (exact only)",
            extra={"event": "us_stock_search_exact_only", "ticker": norm},
        )

        cached = self._info_cache.get(norm)
        if cached is _MISSING:
            return []
        if isinstance(cached, SymbolCandidate):
            return [cached]

        # Not in cache — fetch from yfinance.
        try:
            candidate = await asyncio.to_thread(_fetch_info_sync, norm)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "us_stock info fetch failed for %s: %s",
                norm,
                exc,
                extra={"event": "us_stock_info_fetch_fail", "ticker": norm},
            )
            self._info_cache[norm] = _MISSING
            return []

        if candidate is None:
            self._info_cache[norm] = _MISSING
            return []

        self._info_cache[norm] = candidate
        return [candidate]
