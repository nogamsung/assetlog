"""Korean stock price adapter — pykrx primary, FinanceDataReader fallback."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.adapters._symbol_cache import SymbolListCache  # ADDED
from app.adapters.base import _wrap_failure
from app.adapters.normalize import normalize_kr_stock_symbol
from app.domain.asset_type import AssetType
from app.domain.price_refresh import FetchBatchResult, FetchFailure, PriceQuote, SymbolRef
from app.domain.symbol_search import SymbolCandidate  # ADDED

logger = logging.getLogger("app.adapters.kr_stock")

# Number of calendar days to look back when seeking the most recent trading day.
_LOOKBACK_DAYS = 10


def _fetch_price_sync(symbol: str) -> Decimal:
    """Fetch the latest closing price for *symbol* (sync, runs in a thread).

    Three-tier fallback so a single library outage doesn't black-hole KR
    prices:

      1. pykrx — official KRX data source
      2. FinanceDataReader — same data via a different scraper
      3. yfinance with ``.KS`` / ``.KQ`` suffix — last-resort external source

    Args:
        symbol: 6-digit zero-padded KRX ticker.

    Returns:
        Most recent closing price as Decimal.

    Raises:
        ValueError: If no price data could be obtained from any source.
    """
    today = datetime.now(tz=UTC).strftime("%Y%m%d")
    lookback_start = (datetime.now(tz=UTC) - timedelta(days=_LOOKBACK_DAYS)).strftime("%Y%m%d")

    # --- Primary: pykrx ---
    try:
        import pykrx.stock as pykrx  # noqa: PLC0415

        df = pykrx.get_market_ohlcv(lookback_start, today, symbol)
        if df is not None and not df.empty:
            close_price = df["종가"].iloc[-1]
            return Decimal(str(close_price))
    except Exception as primary_exc:  # noqa: BLE001
        logger.debug(
            "pykrx failed for %s: %s — trying FinanceDataReader",
            symbol,
            primary_exc,
            extra={"event": "kr_stock_pykrx_fallback", "symbol": symbol},
        )

    # --- Secondary: FinanceDataReader ---
    try:
        import FinanceDataReader as fdr  # noqa: PLC0415

        fdr_df = fdr.DataReader(symbol, lookback_start, today)
        if fdr_df is not None and not fdr_df.empty:
            close_price = fdr_df["Close"].iloc[-1]
            return Decimal(str(close_price))
    except Exception as fdr_exc:  # noqa: BLE001
        logger.debug(
            "FDR failed for %s: %s — trying yfinance .KS/.KQ",
            symbol,
            fdr_exc,
            extra={"event": "kr_stock_fdr_fallback", "symbol": symbol},
        )

    # --- Tertiary: yfinance with KOSPI (.KS) then KOSDAQ (.KQ) suffix ---
    try:
        import yfinance as yf  # noqa: PLC0415

        for suffix in (".KS", ".KQ"):
            try:
                fast = yf.Ticker(f"{symbol}{suffix}").fast_info
                last = fast.get("last_price")
                if last is not None and last > 0:
                    return Decimal(str(last))
            except Exception:  # noqa: BLE001  # try next suffix
                continue
    except Exception as yf_exc:  # noqa: BLE001
        raise ValueError(
            f"All KR price sources (pykrx/FDR/yfinance) failed for {symbol}: {yf_exc}"
        ) from yf_exc

    raise ValueError(f"No KR price data available for {symbol}")


def _load_symbol_list_sync() -> list[SymbolCandidate]:  # ADDED
    """Load the full KRX symbol list synchronously (for asyncio.to_thread).

    Primary: pykrx.stock.get_market_ticker_list / get_market_ticker_name.
    Fallback: FinanceDataReader StockListing("KRX").

    Returns:
        List of SymbolCandidate for all KRX-listed tickers.
    """
    try:
        import pykrx.stock as pykrx  # noqa: PLC0415

        tickers = pykrx.get_market_ticker_list(market="ALL")
        candidates: list[SymbolCandidate] = []
        for code in tickers:
            try:
                name = pykrx.get_market_ticker_name(code)
            except Exception:  # noqa: BLE001
                name = code
            candidates.append(
                SymbolCandidate(
                    asset_type=AssetType.KR_STOCK,
                    symbol=str(code).zfill(6),
                    name=name,
                    exchange="KRX",
                    currency="KRW",
                )
            )
        logger.debug(
            "kr_stock symbol list loaded via pykrx",
            extra={"event": "kr_stock_symbol_list_loaded", "count": len(candidates)},
        )
        return candidates
    except Exception as primary_exc:  # noqa: BLE001
        logger.warning(
            "pykrx symbol list failed (%s) — trying FinanceDataReader fallback",
            primary_exc,
            extra={"event": "kr_stock_symbol_list_pykrx_fail"},
        )

    try:
        import FinanceDataReader as fdr  # noqa: PLC0415

        df = fdr.StockListing("KRX")
        candidates = []
        for _, row in df.iterrows():
            code = str(row.get("Code", row.get("Symbol", ""))).zfill(6)
            name = str(row.get("Name", row.get("ShortName", code)))
            candidates.append(
                SymbolCandidate(
                    asset_type=AssetType.KR_STOCK,
                    symbol=code,
                    name=name,
                    exchange="KRX",
                    currency="KRW",
                )
            )
        logger.debug(
            "kr_stock symbol list loaded via FinanceDataReader",
            extra={"event": "kr_stock_symbol_list_fdr_loaded", "count": len(candidates)},
        )
        return candidates
    except Exception as fdr_exc:  # noqa: BLE001
        logger.error(
            "kr_stock symbol list load failed entirely: %s",
            fdr_exc,
            extra={"event": "kr_stock_symbol_list_fail"},
        )
        return []


class KrStockAdapter:
    """Fetch closing prices for KRX-listed stocks.

    pykrx is a blocking library — all calls are offloaded to a thread
    pool via ``asyncio.to_thread`` to avoid blocking the event loop.
    """

    asset_type: AssetType = AssetType.KR_STOCK

    def __init__(self, cache: SymbolListCache | None = None) -> None:  # ADDED
        self._symbol_cache: SymbolListCache = cache if cache is not None else SymbolListCache()

    async def fetch_batch(
        self,
        symbols: Sequence[SymbolRef],
    ) -> FetchBatchResult:
        """Fetch the latest closing price for each symbol individually.

        Each fetch is isolated — one failure does not affect others.

        Args:
            symbols: Sequence of SymbolRef with asset_type == KR_STOCK.

        Returns:
            FetchBatchResult with one entry per symbol.
        """
        successes: list[PriceQuote] = []
        failures: list[FetchFailure] = []
        fetched_at = datetime.now(tz=UTC)

        async def _fetch_one(ref: SymbolRef) -> None:
            norm_symbol = normalize_kr_stock_symbol(ref.symbol)
            try:
                price = await asyncio.to_thread(_fetch_price_sync, norm_symbol)
                successes.append(
                    PriceQuote(
                        ref=ref,
                        price=price,
                        currency="KRW",
                        fetched_at=fetched_at,
                    )
                )
                logger.debug(
                    "kr_stock fetched",
                    extra={
                        "event": "kr_stock_fetch_ok",
                        "symbol": norm_symbol,
                        "price": str(price),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                failures.append(_wrap_failure(ref, exc))
                logger.warning(
                    "kr_stock fetch failed for %s: %s",
                    norm_symbol,
                    exc,
                    extra={
                        "event": "kr_stock_fetch_fail",
                        "symbol": norm_symbol,
                        "error_class": type(exc).__name__,
                    },
                )

        await asyncio.gather(*(_fetch_one(ref) for ref in symbols))
        return FetchBatchResult(successes=successes, failures=failures)

    async def search_symbols(self, query: str, limit: int) -> list[SymbolCandidate]:  # ADDED
        """Search KRX-listed symbols matching *query*.

        Loads the full symbol list once (24h TTL), then filters in memory.
        Match priority: exact symbol > symbol prefix > name contains (case-insensitive).

        Args:
            query: User query string (pre-stripped by caller).
            limit: Maximum number of results.

        Returns:
            Up to *limit* SymbolCandidate items.
        """
        norm_symbol = normalize_kr_stock_symbol(query)
        query_lower = query.lower()

        async def _loader() -> list[SymbolCandidate]:
            return await asyncio.to_thread(_load_symbol_list_sync)

        all_symbols = await self._symbol_cache.get_or_load(_loader)

        exact: list[SymbolCandidate] = []
        prefix: list[SymbolCandidate] = []
        contains: list[SymbolCandidate] = []

        for candidate in all_symbols:
            if candidate.symbol == norm_symbol or candidate.symbol == query.strip():
                exact.append(candidate)
            elif candidate.symbol.startswith(norm_symbol) or candidate.symbol.startswith(
                query.strip()
            ):
                prefix.append(candidate)
            elif query_lower in candidate.name.lower() or query_lower in candidate.symbol.lower():
                contains.append(candidate)

        merged = exact + prefix + contains
        return merged[:limit]
