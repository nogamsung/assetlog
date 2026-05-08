"""BenchmarkService — compare portfolio cumulative return against indices.

Reuses ``build_value_series`` and ``_compute_window`` from #61's performance
module so the user portfolio time series is computed via the same pure
function used by TWR/IRR. The benchmark series is fetched independently
via the BenchmarkAdapter and aligned to the same daily grid.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.adapters.benchmark import KNOWN_BENCHMARKS, BenchmarkAdapter, HistoricalClose
from app.domain.performance import PerformancePeriod
from app.exceptions import FxRateNotAvailableError
from app.repositories.portfolio_history import PortfolioHistoryRepository
from app.schemas.benchmark import (
    BenchmarkComparisonResponse,
    BenchmarkSeries,
    ReturnPoint,
)
from app.services.fx_rate import FxRateService
from app.services.performance import (
    _compute_window,
    _ensure_utc,
    build_value_series,
)

logger = logging.getLogger(__name__)


_ONE = Decimal("1")
_ZERO = Decimal("0")


def _daily_grid(start: datetime, end: datetime) -> list[datetime]:
    """Return a list of daily UTC midnight timestamps spanning [start, end].

    Both endpoints are included. Sub-day windows fall back to start/end only.
    """
    start_utc = _ensure_utc(start).replace(hour=0, minute=0, second=0, microsecond=0)
    end_utc = _ensure_utc(end).replace(hour=0, minute=0, second=0, microsecond=0)
    if end_utc <= start_utc:
        return [start_utc, end_utc]

    out: list[datetime] = []
    cursor = start_utc
    while cursor <= end_utc:
        out.append(cursor)
        cursor = cursor + timedelta(days=1)
    if out[-1] != end_utc:
        out.append(end_utc)
    return out


def _to_cumulative_returns(
    samples: list[tuple[datetime, Decimal]],
) -> list[ReturnPoint]:
    """Convert a (timestamp, value) series into cumulative return %.

    The first non-zero value is treated as the baseline (return 0.0).
    Points before the first non-zero baseline carry return 0.0 to keep
    the series anchored at the window start.
    """
    if not samples:
        return []

    baseline: Decimal | None = None
    points: list[ReturnPoint] = []
    for ts, value in samples:
        if baseline is None:
            if value > _ZERO:
                baseline = value
                points.append(ReturnPoint(timestamp=ts, cumulative_return_pct=_ZERO))
            else:
                points.append(ReturnPoint(timestamp=ts, cumulative_return_pct=_ZERO))
            continue
        ret = (value / baseline) - _ONE
        points.append(ReturnPoint(timestamp=ts, cumulative_return_pct=ret))
    return points


def _benchmark_to_returns(
    history: list[HistoricalClose],
    timestamps: list[datetime],
) -> list[ReturnPoint]:
    """Sample *history* at *timestamps* and convert to cumulative returns.

    For each sample timestamp we pick the most recent close at or before
    that timestamp. Pre-baseline samples carry return 0.0 to keep the line
    anchored at the window start.
    """
    if not history or not timestamps:
        return []

    sorted_hist = sorted(history, key=lambda h: h.at)
    samples: list[tuple[datetime, Decimal]] = []
    cursor = 0
    last_close: Decimal | None = None
    for ts in timestamps:
        ts_utc = _ensure_utc(ts)
        while cursor < len(sorted_hist) and _ensure_utc(sorted_hist[cursor].at) <= ts_utc:
            last_close = sorted_hist[cursor].close
            cursor += 1
        samples.append((ts_utc, last_close if last_close is not None else _ZERO))
    return _to_cumulative_returns(samples)


class BenchmarkService:
    """Compose user portfolio + index cumulative-return series."""

    def __init__(
        self,
        history_repo: PortfolioHistoryRepository,
        fx_service: FxRateService,
        benchmark_adapter: BenchmarkAdapter,
    ) -> None:
        self._repo = history_repo
        self._fx = fx_service
        self._benchmark = benchmark_adapter

    async def compare(
        self,
        period: PerformancePeriod,
        currency: str,
        symbols: Sequence[str],
    ) -> BenchmarkComparisonResponse:
        warnings: list[str] = []
        end_dt = datetime.now(UTC)

        all_txs = await self._repo.list_all_transactions()
        start_dt, end_dt = _compute_window(period, end_dt, all_txs)
        timestamps = _daily_grid(start_dt, end_dt)

        portfolio_points = await self._build_portfolio_returns(
            all_txs, currency, timestamps, warnings
        )
        portfolio = BenchmarkSeries(
            symbol="PORTFOLIO",
            name="My portfolio",
            points=portfolio_points,
        )

        adapter_results = await self._benchmark.fetch_many(
            list(symbols), start_dt.date(), end_dt.date()
        )
        benchmarks: list[BenchmarkSeries] = []
        alpha: dict[str, Decimal] = {}
        for symbol in symbols:
            history = adapter_results.get(symbol, [])
            if not history:
                warnings.append(f"benchmark_fetch_failed:{symbol}")
                continue
            bm_points = _benchmark_to_returns(history, timestamps)
            benchmarks.append(
                BenchmarkSeries(
                    symbol=symbol,
                    name=KNOWN_BENCHMARKS.get(symbol, symbol),
                    points=bm_points,
                )
            )
            if portfolio_points and bm_points:
                alpha[symbol] = (
                    portfolio_points[-1].cumulative_return_pct - bm_points[-1].cumulative_return_pct
                )

        return BenchmarkComparisonResponse(
            period=period,
            currency=currency,
            start_date=start_dt,
            end_date=end_dt,
            portfolio=portfolio,
            benchmarks=benchmarks,
            alpha=alpha,
            warnings=warnings,
        )

    async def _build_portfolio_returns(
        self,
        all_txs: list,  # type: ignore[type-arg]  # forward-compat with #61 AllTxRow
        currency: str,
        timestamps: list[datetime],
        warnings: list[str],
    ) -> list[ReturnPoint]:
        """Build cumulative-return points for the user portfolio at *timestamps*."""
        if not all_txs:
            warnings.append("no_activity_in_period")
            return [ReturnPoint(timestamp=ts, cumulative_return_pct=_ZERO) for ts in timestamps]

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

        fetch_tasks = [_fetch_one(from_cur, currency, at) for from_cur, at in unique_pairs]
        fetch_results = await asyncio.gather(*fetch_tasks)
        fx_missing = False
        for key, rate in fetch_results:
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

        value_series = build_value_series(
            txs=all_txs,
            price_index=price_index,
            symbol_currency=symbol_currency,
            fx_at=fx_at_sync,
            report_currency=currency,
            timestamps=timestamps,
        )
        samples = [(vp.timestamp, vp.value) for vp in value_series]
        return _to_cumulative_returns(samples)
