"""RiskService — annualised return / volatility / Sharpe / max drawdown.

All daily-return statistics are derived from the same value series produced
by ``build_value_series`` (#61) — the FX pre-fetch + sampling logic is shared
with ``BenchmarkService`` (#62) to keep the daily grid consistent across all
performance endpoints.
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.performance import PerformancePeriod, ValuePoint
from app.exceptions import FxRateNotAvailableError
from app.repositories.portfolio_history import AllTxRow, PortfolioHistoryRepository
from app.schemas.risk import RiskMetricsResponse
from app.services.benchmark import _daily_grid
from app.services.fx_rate import FxRateService
from app.services.performance import (
    _compute_window,
    _ensure_utc,
    build_value_series,
)

logger = logging.getLogger(__name__)


_ONE = Decimal("1")
_ZERO = Decimal("0")
_TRADING_DAYS_PER_YEAR = 252


def _to_daily_returns(value_series: list[ValuePoint]) -> list[Decimal]:
    """Compute (v_i / v_{i-1}) - 1 for consecutive non-zero values.

    Drops samples where either side is zero (pre-baseline / pending).
    """
    returns: list[Decimal] = []
    prev: Decimal | None = None
    for vp in value_series:
        if prev is not None and prev > _ZERO and vp.value > _ZERO:
            returns.append((vp.value / prev) - _ONE)
        prev = vp.value
    return returns


def _stdev(values: list[Decimal]) -> Decimal | None:
    """Sample standard deviation (Bessel-corrected) — None if n < 2."""
    n = len(values)
    if n < 2:
        return None
    mean = sum(values, _ZERO) / Decimal(n)
    variance = sum(((v - mean) ** 2 for v in values), _ZERO) / Decimal(n - 1)
    if variance <= _ZERO:
        return _ZERO
    # sqrt via float — Decimal has no native sqrt for non-perfect-squares.
    return Decimal(str(math.sqrt(float(variance))))


def _annualized_volatility(
    daily_returns: list[Decimal],
    periods_per_year: int = _TRADING_DAYS_PER_YEAR,
) -> Decimal | None:
    """Daily-return stdev scaled by sqrt(periods_per_year)."""
    daily_vol = _stdev(daily_returns)
    if daily_vol is None:
        return None
    factor = Decimal(str(math.sqrt(periods_per_year)))
    return daily_vol * factor


def _annualized_return(
    start_value: Decimal,
    end_value: Decimal,
    days: float,
) -> Decimal | None:
    """(end/start)^(365/days) - 1 — None for non-positive inputs."""
    if start_value <= _ZERO or end_value <= _ZERO or days <= 0:
        return None
    ratio = float(end_value / start_value)
    exponent = 365.0 / days
    annualised = ratio**exponent - 1.0
    return Decimal(str(annualised))


def _max_drawdown(
    value_series: list[ValuePoint],
) -> tuple[Decimal | None, datetime | None]:
    """Maximum peak-to-trough drawdown over the series.

    Returns ``(mdd, trough_timestamp)``. ``mdd`` is a positive fraction
    (0.10 = 10% loss from peak); ``None`` if fewer than 2 non-zero samples.
    """
    peak: Decimal | None = None
    mdd: Decimal | None = None
    trough_at: datetime | None = None
    sample_count = 0

    for vp in value_series:
        if vp.value <= _ZERO:
            continue
        sample_count += 1
        if peak is None or vp.value > peak:
            peak = vp.value
            continue
        drawdown = (peak - vp.value) / peak
        if mdd is None or drawdown > mdd:
            mdd = drawdown
            trough_at = vp.timestamp

    if sample_count < 2:
        return None, None
    return (mdd or _ZERO), trough_at


class RiskService:
    """Composes value series → daily returns → vol/Sharpe/MDD."""

    def __init__(
        self,
        history_repo: PortfolioHistoryRepository,
        fx_service: FxRateService,
        risk_free_rate: Decimal = Decimal("0.03"),
    ) -> None:
        self._repo = history_repo
        self._fx = fx_service
        self._risk_free_rate = risk_free_rate

    async def get_risk_metrics(
        self,
        period: PerformancePeriod,
        currency: str,
    ) -> RiskMetricsResponse:
        warnings: list[str] = []
        end_dt = datetime.now(UTC)

        all_txs = await self._repo.list_all_transactions()
        start_dt, end_dt = _compute_window(period, end_dt, all_txs)
        timestamps = _daily_grid(start_dt, end_dt)

        if not all_txs:
            warnings.append("no_activity_in_period")
            return self._empty_response(period, currency, start_dt, end_dt, warnings)

        value_series = await self._build_value_series(all_txs, currency, timestamps, warnings)
        non_zero = [vp for vp in value_series if vp.value > _ZERO]
        if len(non_zero) < 2:
            warnings.append("insufficient_samples")
            return self._empty_response(period, currency, start_dt, end_dt, warnings)

        daily_returns = _to_daily_returns(value_series)
        ann_vol = _annualized_volatility(daily_returns)

        days = max((non_zero[-1].timestamp - non_zero[0].timestamp).days, 1)
        ann_return = _annualized_return(non_zero[0].value, non_zero[-1].value, float(days))

        sharpe: Decimal | None = None
        if ann_return is not None and ann_vol is not None and ann_vol > _ZERO:
            sharpe = (ann_return - self._risk_free_rate) / ann_vol
        elif ann_vol is not None and ann_vol == _ZERO:
            warnings.append("volatility_zero")

        mdd, trough_at = _max_drawdown(value_series)

        return RiskMetricsResponse(
            period=period,
            currency=currency,
            start_date=start_dt,
            end_date=end_dt,
            annualized_return=ann_return,
            annualized_volatility=ann_vol,
            sharpe_ratio=sharpe,
            max_drawdown=mdd,
            max_drawdown_at=trough_at,
            risk_free_rate=self._risk_free_rate,
            warnings=warnings,
        )

    def _empty_response(
        self,
        period: PerformancePeriod,
        currency: str,
        start_dt: datetime,
        end_dt: datetime,
        warnings: list[str],
    ) -> RiskMetricsResponse:
        return RiskMetricsResponse(
            period=period,
            currency=currency,
            start_date=start_dt,
            end_date=end_dt,
            annualized_return=None,
            annualized_volatility=None,
            sharpe_ratio=None,
            max_drawdown=None,
            max_drawdown_at=None,
            risk_free_rate=self._risk_free_rate,
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
