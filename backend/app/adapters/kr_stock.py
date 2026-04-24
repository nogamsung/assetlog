"""Korean stock price adapter — pykrx primary, FinanceDataReader fallback."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.adapters.base import _wrap_failure
from app.adapters.normalize import normalize_kr_stock_symbol
from app.domain.asset_type import AssetType
from app.domain.price_refresh import FetchBatchResult, FetchFailure, PriceQuote, SymbolRef

logger = logging.getLogger("app.adapters.kr_stock")

# Number of calendar days to look back when seeking the most recent trading day.
_LOOKBACK_DAYS = 10


def _fetch_price_sync(symbol: str) -> Decimal:
    """Fetch the latest closing price for *symbol* using pykrx (sync).

    Falls back to FinanceDataReader if pykrx raises or returns empty data.

    Args:
        symbol: 6-digit zero-padded KRX ticker.

    Returns:
        Most recent closing price as Decimal.

    Raises:
        ValueError: If no price data could be obtained from either source.
    """
    import pykrx.stock as pykrx  # noqa: PLC0415  # lazy import for testability

    today = datetime.now(tz=UTC).strftime("%Y%m%d")
    lookback_start = (datetime.now(tz=UTC) - timedelta(days=_LOOKBACK_DAYS)).strftime("%Y%m%d")

    try:
        df = pykrx.get_market_ohlcv(lookback_start, today, symbol)
        if df is not None and not df.empty:
            close_price = df["종가"].iloc[-1]
            return Decimal(str(close_price))
        # Empty frame → pykrx found nothing (holiday / ticker mismatch)
        raise ValueError(f"pykrx returned empty DataFrame for {symbol}")
    except Exception as primary_exc:  # noqa: BLE001
        logger.debug(
            "pykrx failed for %s (%s: %s) — trying FinanceDataReader fallback",
            symbol,
            type(primary_exc).__name__,
            primary_exc,
            extra={"event": "kr_stock_pykrx_fallback", "symbol": symbol},
        )

    # --- FinanceDataReader fallback ---
    try:
        import FinanceDataReader as fdr  # noqa: PLC0415  # lazy import for testability

        fdr_df = fdr.DataReader(symbol, lookback_start, today)
        if fdr_df is not None and not fdr_df.empty:
            close_price = fdr_df["Close"].iloc[-1]
            return Decimal(str(close_price))
        raise ValueError(f"FinanceDataReader returned empty DataFrame for {symbol}")
    except Exception as fallback_exc:  # noqa: BLE001
        raise ValueError(
            f"Both pykrx and FinanceDataReader failed for {symbol}: {fallback_exc}"
        ) from fallback_exc


class KrStockAdapter:
    """Fetch closing prices for KRX-listed stocks.

    pykrx is a blocking library — all calls are offloaded to a thread
    pool via ``asyncio.to_thread`` to avoid blocking the event loop.
    """

    asset_type: AssetType = AssetType.KR_STOCK

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
