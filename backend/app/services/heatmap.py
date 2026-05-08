"""HeatmapService — month-over-month portfolio returns matrix.

Samples portfolio value at month-end timestamps (using ``build_value_series``
from #61), then computes month i's return as ``v[i] / v[i-1] - 1``. Calendar-
year aggregates compound the months in that year geometrically.
"""

from __future__ import annotations

import asyncio
import logging
from calendar import monthrange
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.performance import ValuePoint
from app.exceptions import FxRateNotAvailableError
from app.repositories.portfolio_history import AllTxRow, PortfolioHistoryRepository
from app.schemas.heatmap import HeatmapResponse, MonthlyReturn
from app.services.fx_rate import FxRateService
from app.services.performance import (
    _ensure_utc,
    build_value_series,
)

logger = logging.getLogger(__name__)


_ONE = Decimal("1")
_ZERO = Decimal("0")


def _month_end(year: int, month: int) -> datetime:
    """Return UTC midnight of the last calendar day of (year, month)."""
    last_day = monthrange(year, month)[1]
    return datetime(year, month, last_day, tzinfo=UTC)


def _months_between(start: datetime, end: datetime) -> list[tuple[int, int]]:
    """Return inclusive list of (year, month) pairs from start to end."""
    start_utc = _ensure_utc(start)
    end_utc = _ensure_utc(end)
    if end_utc < start_utc:
        return []

    pairs: list[tuple[int, int]] = []
    year, month = start_utc.year, start_utc.month
    while (year, month) <= (end_utc.year, end_utc.month):
        pairs.append((year, month))
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return pairs


def _monthly_returns_from_series(
    series: list[ValuePoint],
    months: list[tuple[int, int]],
) -> list[MonthlyReturn]:
    """Compute (v_i / v_{i-1}) - 1 for each month using sampled month-end values.

    The series is expected to align 1:1 with ``months`` (one extra anchor
    timestamp at the start of the window precedes the first month).
    """
    out: list[MonthlyReturn] = []
    if len(series) < 2 or len(series) != len(months) + 1:
        # No way to compute returns with mismatched sampling
        for year, month in months:
            out.append(MonthlyReturn(year=year, month=month, return_pct=None))
        return out

    for i, (year, month) in enumerate(months):
        prev = series[i].value
        cur = series[i + 1].value
        if prev > _ZERO and cur > _ZERO:
            ret = (cur / prev) - _ONE
        else:
            ret = None
        out.append(MonthlyReturn(year=year, month=month, return_pct=ret))
    return out


def _yearly_compound(months: list[MonthlyReturn]) -> dict[int, Decimal | None]:
    """Geometric compound of month returns within each calendar year.

    A year with any ``None`` month return → ``None`` for that year.
    """
    by_year: dict[int, list[Decimal]] = {}
    nulls_by_year: dict[int, bool] = {}
    for m in months:
        if m.return_pct is None:
            nulls_by_year[m.year] = True
            by_year.setdefault(m.year, [])
        else:
            by_year.setdefault(m.year, []).append(m.return_pct)

    result: dict[int, Decimal | None] = {}
    for year, returns in by_year.items():
        if nulls_by_year.get(year):
            result[year] = None
            continue
        compound: Decimal = _ONE
        for r in returns:
            compound = compound * (_ONE + r)
        result[year] = compound - _ONE
    return result


class HeatmapService:
    """Composes month-end value series → monthly returns → yearly compounds."""

    def __init__(
        self,
        history_repo: PortfolioHistoryRepository,
        fx_service: FxRateService,
    ) -> None:
        self._repo = history_repo
        self._fx = fx_service

    async def get_heatmap(
        self,
        currency: str,
        years: int = 5,
    ) -> HeatmapResponse:
        """Return monthly returns for the most recent *years* calendar years."""
        warnings: list[str] = []
        end_dt = datetime.now(UTC)
        start_dt = end_dt - timedelta(days=365 * max(years, 1))
        # Anchor start at first day of that month for clean alignment.
        start_dt = datetime(start_dt.year, start_dt.month, 1, tzinfo=UTC)

        all_txs = await self._repo.list_all_transactions()
        if not all_txs:
            warnings.append("no_activity_in_period")
            return HeatmapResponse(
                currency=currency,
                start_date=start_dt,
                end_date=end_dt,
                months=[],
                yearly_returns={},
                warnings=warnings,
            )

        months = _months_between(start_dt, end_dt)
        # Build sampling timestamps: start anchor + each month's end (clipped to today).
        anchor = (
            datetime(months[0][0], months[0][1], 1, tzinfo=UTC) - timedelta(days=1)
            if months
            else start_dt
        )
        timestamps: list[datetime] = [anchor]
        for year, month in months:
            month_end = _month_end(year, month)
            timestamps.append(min(month_end, end_dt))

        series = await self._build_value_series(all_txs, currency, timestamps, warnings)
        monthly = _monthly_returns_from_series(series, months)
        yearly = _yearly_compound(monthly)

        return HeatmapResponse(
            currency=currency,
            start_date=start_dt,
            end_date=end_dt,
            months=monthly,
            yearly_returns=yearly,
            warnings=warnings,
        )

    async def _build_value_series(
        self,
        all_txs: list[AllTxRow],
        currency: str,
        timestamps: list[datetime],
        warnings: list[str],
    ) -> list[ValuePoint]:
        symbol_ids = list({tx.symbol_id for tx in all_txs})
        price_index = await self._repo.list_price_points_for_symbols(
            symbol_ids,
            since=timestamps[0],
        )
        symbol_currency: dict[int, str] = {tx.symbol_id: tx.currency for tx in all_txs}

        fx_cache: dict[tuple[str, str, datetime], Decimal] = {}
        unique_pairs: set[tuple[str, datetime]] = set()
        for ts in timestamps:
            ts_hour = ts.replace(minute=0, second=0, microsecond=0)
            for sym_id in symbol_ids:
                sym_cur = symbol_currency.get(sym_id, currency)
                if sym_cur != currency:
                    unique_pairs.add((sym_cur, ts_hour))

        async def _fetch_one(
            from_cur: str, to_cur: str, at: datetime
        ) -> tuple[tuple[str, str, datetime], Decimal | None]:
            if from_cur == to_cur:
                return (from_cur, to_cur, at), _ONE
            try:
                rate = await self._fx.convert_at(Decimal("1"), from_cur, to_cur, at)
                return (from_cur, to_cur, at), rate
            except FxRateNotAvailableError:
                return (from_cur, to_cur, at), None

        results = await asyncio.gather(
            *(_fetch_one(from_cur, currency, at) for from_cur, at in unique_pairs)
        )
        fx_missing = False
        for key, rate in results:
            if rate is None:
                fx_missing = True
            else:
                fx_cache[key] = rate
        if fx_missing:
            warnings.append("fx_rate_missing")

        def fx_at_sync(amount: Decimal, from_cur: str, to_cur: str, at: datetime) -> Decimal:
            if from_cur == to_cur:
                return amount
            at_hour = _ensure_utc(at).replace(minute=0, second=0, microsecond=0)
            rate = fx_cache.get((from_cur, to_cur, at_hour))
            if rate is None:
                return _ZERO
            return amount * rate

        return build_value_series(
            txs=all_txs,
            price_index=price_index,
            symbol_currency=symbol_currency,
            fx_at=fx_at_sync,
            report_currency=currency,
            timestamps=timestamps,
        )
