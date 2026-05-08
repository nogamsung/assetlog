"""Korean stock dividend adapter — pykrx fundamentals.

pykrx exposes only trailing-12-month DPS via ``get_market_fundamental_by_ticker``
(no event-level dividend feed). For a personal portfolio tracker this is a
useful approximation: we query DPS at calendar year-ends back N years and
emit one synthetic ``DividendQuote`` per non-zero year. The unique constraint
on ``(asset_symbol_id, ex_date)`` deduplicates repeat refreshes.

ex_date convention — Korean companies typically set the dividend record date
on the last trading day of the fiscal year (most are calendar-year), so we
use ``date(year, 12, 30)`` as the synthetic ex_date.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from decimal import Decimal

from app.domain.dividend import DividendQuote

logger = logging.getLogger("app.adapters.kr_dividends")


_DEFAULT_LOOKBACK_YEARS: int = 5


def _format_year_end(year: int) -> str:
    """Return pykrx-format date string for the last trading day candidate."""
    return f"{year}1230"


def _ex_date_for(year: int) -> date:
    """Synthetic record-date convention for fiscal year *year*."""
    return date(year, 12, 30)


def _fetch_dps_at(ticker: str, year: int) -> Decimal | None:
    """Return trailing-12m DPS for *ticker* as of *year* year-end, or None."""
    import pykrx.stock as pykrx  # noqa: PLC0415  # lazy import

    df = pykrx.get_market_fundamental_by_ticker(_format_year_end(year), ticker)
    if df is None or len(df) == 0:
        return None

    # pykrx returns a DataFrame indexed by ticker with a "DPS" column.
    if "DPS" not in df.columns:
        return None
    if ticker not in df.index:
        return None

    raw = df.loc[ticker, "DPS"]
    try:
        value = Decimal(str(float(raw)))
    except (ValueError, TypeError):
        return None
    if value <= Decimal("0"):
        return None
    return value


def _fetch_dividends_sync(
    ticker: str,
    *,
    lookback_years: int = _DEFAULT_LOOKBACK_YEARS,
) -> list[DividendQuote]:
    """Build DividendQuotes by sampling DPS at each year-end in window."""
    quotes: list[DividendQuote] = []
    today = datetime.now().date()
    # If we're past Dec 30, current calendar year's data is finalised; otherwise
    # the most recent reliable year is last calendar year.
    end_year = today.year if today.month == 12 and today.day >= 30 else today.year - 1
    start_year = end_year - lookback_years + 1
    for year in range(start_year, end_year + 1):
        try:
            dps = _fetch_dps_at(ticker, year)
        except Exception as exc:  # noqa: BLE001  # pykrx raises bare exceptions
            logger.warning(
                "kr_dividends DPS lookup failed for %s @%d: %s",
                ticker,
                year,
                exc,
                extra={
                    "event": "kr_div_fetch_fail",
                    "ticker": ticker,
                    "year": year,
                    "error": str(exc),
                },
            )
            continue
        if dps is None:
            continue
        quotes.append(
            DividendQuote(
                ex_date=_ex_date_for(year),
                amount=dps,
                currency="KRW",
            )
        )
    quotes.sort(key=lambda q: q.ex_date)
    return quotes


class KrDividendAdapter:
    """pykrx-backed dividend fetcher for Korean stocks.

    pykrx is sync only — calls are offloaded to a thread executor to avoid
    blocking the event loop.
    """

    def __init__(self, lookback_years: int = _DEFAULT_LOOKBACK_YEARS) -> None:
        self._lookback_years = lookback_years

    async def fetch_dividends(self, ticker: str) -> list[DividendQuote]:
        """Return synthetic per-year DividendQuotes for *ticker*."""
        try:
            return await asyncio.to_thread(
                _fetch_dividends_sync,
                ticker,
                lookback_years=self._lookback_years,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "kr_dividends fetch failed for %s: %s",
                ticker,
                exc,
                extra={
                    "event": "kr_div_fetch_fatal",
                    "ticker": ticker,
                    "error": str(exc),
                },
            )
            return []
