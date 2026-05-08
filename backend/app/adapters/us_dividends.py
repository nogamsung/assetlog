"""US dividend adapter — yfinance.

Pulls full dividend history per ticker via ``Ticker.dividends`` (a pandas
Series whose index is timezone-aware ex-dates and values are USD amounts).
The full history is fetched on every call — repository deduplicates by
(asset_symbol_id, ex_date), so duplicate inserts are silently skipped.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from decimal import Decimal

from app.domain.dividend import DividendQuote

logger = logging.getLogger("app.adapters.us_dividends")


def _fetch_dividends_sync(ticker: str) -> list[DividendQuote]:
    """Download full dividend history for *ticker* via yfinance (sync)."""
    import yfinance as yf  # noqa: PLC0415  # lazy import for testability

    series = yf.Ticker(ticker).dividends  # pandas.Series
    if series is None or len(series) == 0:
        logger.debug(
            "us_dividends empty",
            extra={"event": "us_div_empty", "ticker": ticker},
        )
        return []

    quotes: list[DividendQuote] = []
    for raw_idx, raw_amount in series.items():
        ex_date_dt = raw_idx if isinstance(raw_idx, datetime) else None
        if ex_date_dt is None:
            try:
                ex_date_dt = raw_idx.to_pydatetime()  # pandas.Timestamp
            except AttributeError:
                logger.warning(
                    "us_dividends invalid index type",
                    extra={
                        "event": "us_div_bad_index",
                        "ticker": ticker,
                        "type": type(raw_idx).__name__,
                    },
                )
                continue
        ex_date_only: date = ex_date_dt.date()
        try:
            amount = Decimal(str(float(raw_amount)))
        except (ValueError, TypeError):
            continue
        quotes.append(
            DividendQuote(
                ex_date=ex_date_only,
                amount=amount,
                currency="USD",
            )
        )
    return quotes


class UsDividendAdapter:
    """yfinance-backed dividend fetcher.

    All public methods are async — the synchronous yfinance call is offloaded
    to a thread executor to avoid blocking the event loop.
    """

    async def fetch_dividends(self, ticker: str) -> list[DividendQuote]:
        """Return the full dividend history for *ticker*.

        Args:
            ticker: Upper-cased US ticker symbol (e.g. "AAPL").

        Returns:
            List of DividendQuote sorted ascending by ex_date — empty if
            yfinance returns no data or only invalid rows.
        """
        try:
            quotes = await asyncio.to_thread(_fetch_dividends_sync, ticker)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "us_dividends fetch failed for %s: %s",
                ticker,
                exc,
                extra={
                    "event": "us_div_fetch_fail",
                    "ticker": ticker,
                    "error": str(exc),
                },
            )
            return []
        quotes.sort(key=lambda q: q.ex_date)
        return quotes
