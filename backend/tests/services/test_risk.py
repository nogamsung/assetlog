"""Unit tests for RiskService — pure helpers + mocked I/O."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

from app.domain.performance import PerformancePeriod, ValuePoint
from app.domain.transaction_type import TransactionType
from app.repositories.portfolio_history import AllTxRow, PortfolioHistoryRepository
from app.services.fx_rate import FxRateService
from app.services.risk import (
    RiskService,
    _annualized_return,
    _annualized_volatility,
    _max_drawdown,
    _stdev,
    _to_daily_returns,
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _vp(day: int, value: str) -> ValuePoint:
    return ValuePoint(
        timestamp=datetime(2026, 5, day, tzinfo=UTC),
        value=Decimal(value),
    )


class TestToDailyReturns:
    def test_상승_시계열(self) -> None:
        series = [_vp(1, "100"), _vp(2, "110"), _vp(3, "121")]
        returns = _to_daily_returns(series)
        assert len(returns) == 2
        assert returns[0] == Decimal("0.1")
        assert returns[1] == Decimal("0.1")

    def test_baseline_0_skip(self) -> None:
        series = [_vp(1, "0"), _vp(2, "100"), _vp(3, "110")]
        returns = _to_daily_returns(series)
        assert len(returns) == 1
        assert returns[0] == Decimal("0.1")

    def test_단일_샘플_빈_리스트(self) -> None:
        assert _to_daily_returns([_vp(1, "100")]) == []

    def test_빈_입력(self) -> None:
        assert _to_daily_returns([]) == []


class TestStdev:
    def test_n_미만_2_None(self) -> None:
        assert _stdev([Decimal("1")]) is None
        assert _stdev([]) is None

    def test_동일값_0(self) -> None:
        assert _stdev([Decimal("0.05"), Decimal("0.05"), Decimal("0.05")]) == Decimal("0")

    def test_정상_표준편차(self) -> None:
        # values: 1, 2, 3 → mean 2, variance (1+0+1)/2 = 1, stdev = 1
        result = _stdev([Decimal("1"), Decimal("2"), Decimal("3")])
        assert result is not None
        assert abs(float(result) - 1.0) < 1e-6


class TestAnnualizedVolatility:
    def test_252_factor(self) -> None:
        # Bessel-corrected stdev of [0.01, -0.01, 0.01, -0.01]:
        # variance = 4 × 0.0001 / 3 ≈ 0.0001333; stdev ≈ 0.01155
        # annualised ≈ 0.01155 × sqrt(252) ≈ 0.1833
        result = _annualized_volatility(
            [Decimal("0.01"), Decimal("-0.01"), Decimal("0.01"), Decimal("-0.01")],
        )
        assert result is not None
        expected = math.sqrt(4 * 0.0001 / 3) * math.sqrt(252)
        assert abs(float(result) - expected) < 1e-3

    def test_샘플_부족_None(self) -> None:
        assert _annualized_volatility([]) is None
        assert _annualized_volatility([Decimal("0.01")]) is None


class TestAnnualizedReturn:
    def test_1년_20pct(self) -> None:
        result = _annualized_return(Decimal("1000"), Decimal("1200"), 365.0)
        assert result is not None
        assert abs(float(result) - 0.2) < 1e-6

    def test_반년_상승_연환산_복리(self) -> None:
        # 6m +20% → annualised ≈ (1.2)^2 - 1 = 0.44
        result = _annualized_return(Decimal("1000"), Decimal("1200"), 365.0 / 2)
        assert result is not None
        assert abs(float(result) - 0.44) < 1e-3

    def test_0_또는_음수_None(self) -> None:
        assert _annualized_return(Decimal("0"), Decimal("100"), 365.0) is None
        assert _annualized_return(Decimal("100"), Decimal("0"), 365.0) is None
        assert _annualized_return(Decimal("100"), Decimal("100"), 0.0) is None


class TestMaxDrawdown:
    def test_단조상승_drawdown_0(self) -> None:
        series = [_vp(1, "100"), _vp(2, "110"), _vp(3, "120")]
        mdd, trough = _max_drawdown(series)
        assert mdd == Decimal("0")
        assert trough is None

    def test_피크_후_30pct_하락(self) -> None:
        # peak 120 at d2, trough 84 at d3 → drawdown 0.30
        series = [_vp(1, "100"), _vp(2, "120"), _vp(3, "84"), _vp(4, "100")]
        mdd, trough = _max_drawdown(series)
        assert mdd is not None
        assert abs(float(mdd) - 0.30) < 1e-6
        assert trough == datetime(2026, 5, 3, tzinfo=UTC)

    def test_샘플_부족_None(self) -> None:
        mdd, trough = _max_drawdown([_vp(1, "100")])
        assert mdd is None
        assert trough is None

    def test_0_샘플_skip(self) -> None:
        # zeros excluded; only non-zero counted
        series = [_vp(1, "0"), _vp(2, "100"), _vp(3, "80")]
        mdd, trough = _max_drawdown(series)
        assert mdd is not None
        assert abs(float(mdd) - 0.20) < 1e-6


# ---------------------------------------------------------------------------
# Service-level integration
# ---------------------------------------------------------------------------


def _make_tx(symbol_id: int = 1, currency: str = "KRW") -> AllTxRow:
    return AllTxRow(
        symbol_id=symbol_id,
        currency=currency,
        traded_at=datetime(2026, 1, 1, tzinfo=UTC),
        quantity=Decimal("10"),
        price=Decimal("100"),
        tx_type=TransactionType.BUY,
    )


class TestRiskService:
    async def test_거래_없으면_no_activity(self) -> None:
        repo = AsyncMock(spec=PortfolioHistoryRepository)
        repo.list_all_transactions.return_value = []
        repo.list_price_points_for_symbols.return_value = {}
        fx = AsyncMock(spec=FxRateService)

        svc = RiskService(repo, fx)
        result = await svc.get_risk_metrics(PerformancePeriod.ONE_YEAR, "KRW")
        assert "no_activity_in_period" in result.warnings
        assert result.annualized_return is None
        assert result.annualized_volatility is None
        assert result.sharpe_ratio is None
        assert result.max_drawdown is None

    async def test_샘플_부족_warning(self) -> None:
        # All price points are zero → no non-zero samples
        repo = AsyncMock(spec=PortfolioHistoryRepository)
        repo.list_all_transactions.return_value = [_make_tx()]
        repo.list_price_points_for_symbols.return_value = {1: []}
        fx = AsyncMock(spec=FxRateService)

        svc = RiskService(repo, fx)
        result = await svc.get_risk_metrics(PerformancePeriod.ONE_WEEK, "KRW")
        assert "insufficient_samples" in result.warnings

    async def test_정상_시나리오_metrics_생성(self) -> None:
        # Single buy at d0 with prices climbing — verify all metrics produced
        repo = AsyncMock(spec=PortfolioHistoryRepository)
        repo.list_all_transactions.return_value = [_make_tx()]
        # Daily prices going up by ~0.5% then dropping at end
        end_dt = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        prices = []
        for d in range(8):
            day_ts = end_dt - timedelta(days=7 - d)
            prices.append((day_ts, Decimal("100") + Decimal(d)))
        repo.list_price_points_for_symbols.return_value = {1: prices}
        fx = AsyncMock(spec=FxRateService)

        svc = RiskService(repo, fx, risk_free_rate=Decimal("0.03"))
        result = await svc.get_risk_metrics(PerformancePeriod.ONE_WEEK, "KRW")

        assert result.annualized_return is not None
        assert result.annualized_volatility is not None
        assert result.max_drawdown is not None
        assert result.risk_free_rate == Decimal("0.03")

    async def test_currency_uppercase(self) -> None:
        repo = AsyncMock(spec=PortfolioHistoryRepository)
        repo.list_all_transactions.return_value = []
        repo.list_price_points_for_symbols.return_value = {}
        fx = AsyncMock(spec=FxRateService)

        svc = RiskService(repo, fx)
        result = await svc.get_risk_metrics(PerformancePeriod.ONE_YEAR, "USD")
        assert result.currency == "USD"
