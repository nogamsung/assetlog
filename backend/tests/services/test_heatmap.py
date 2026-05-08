"""Unit tests for HeatmapService — pure helpers + mocked I/O."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from app.domain.performance import ValuePoint
from app.domain.transaction_type import TransactionType
from app.repositories.portfolio_history import AllTxRow, PortfolioHistoryRepository
from app.schemas.heatmap import MonthlyReturn
from app.services.fx_rate import FxRateService
from app.services.heatmap import (
    HeatmapService,
    _month_end,
    _monthly_returns_from_series,
    _months_between,
    _yearly_compound,
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestMonthEnd:
    def test_정상_월말(self) -> None:
        assert _month_end(2026, 5) == datetime(2026, 5, 31, tzinfo=UTC)

    def test_2월_평년(self) -> None:
        assert _month_end(2026, 2) == datetime(2026, 2, 28, tzinfo=UTC)

    def test_2월_윤년(self) -> None:
        assert _month_end(2024, 2) == datetime(2024, 2, 29, tzinfo=UTC)


class TestMonthsBetween:
    def test_단일_월(self) -> None:
        start = datetime(2026, 5, 1, tzinfo=UTC)
        end = datetime(2026, 5, 31, tzinfo=UTC)
        assert _months_between(start, end) == [(2026, 5)]

    def test_연도_경계(self) -> None:
        start = datetime(2025, 11, 1, tzinfo=UTC)
        end = datetime(2026, 2, 1, tzinfo=UTC)
        result = _months_between(start, end)
        assert result == [(2025, 11), (2025, 12), (2026, 1), (2026, 2)]

    def test_역순_빈_리스트(self) -> None:
        start = datetime(2026, 5, 1, tzinfo=UTC)
        end = datetime(2026, 4, 1, tzinfo=UTC)
        assert _months_between(start, end) == []


class TestMonthlyReturnsFromSeries:
    def test_정상_월별_수익률(self) -> None:
        # 4 timestamps for 3 months (anchor + 3 month-ends)
        series = [
            ValuePoint(datetime(2025, 12, 31, tzinfo=UTC), Decimal("1000")),
            ValuePoint(datetime(2026, 1, 31, tzinfo=UTC), Decimal("1100")),
            ValuePoint(datetime(2026, 2, 28, tzinfo=UTC), Decimal("1050")),
            ValuePoint(datetime(2026, 3, 31, tzinfo=UTC), Decimal("1155")),
        ]
        months = [(2026, 1), (2026, 2), (2026, 3)]
        result = _monthly_returns_from_series(series, months)
        assert len(result) == 3
        assert result[0].return_pct == Decimal("0.1")  # 1100/1000 - 1
        assert result[1].return_pct is not None
        assert abs(float(result[1].return_pct) - (-50.0 / 1100.0)) < 1e-6
        assert result[2].return_pct is not None
        assert abs(float(result[2].return_pct) - 0.1) < 1e-6

    def test_0_월_샘플_None(self) -> None:
        series = [
            ValuePoint(datetime(2025, 12, 31, tzinfo=UTC), Decimal("0")),
            ValuePoint(datetime(2026, 1, 31, tzinfo=UTC), Decimal("1100")),
        ]
        months = [(2026, 1)]
        result = _monthly_returns_from_series(series, months)
        assert result[0].return_pct is None

    def test_샘플_불일치_모두_None(self) -> None:
        series = [ValuePoint(datetime(2025, 12, 31, tzinfo=UTC), Decimal("1000"))]
        months = [(2026, 1), (2026, 2)]
        result = _monthly_returns_from_series(series, months)
        assert all(r.return_pct is None for r in result)


class TestYearlyCompound:
    def test_복리_누적(self) -> None:
        # 1.10 × 1.10 = 1.21 → annual 0.21
        months = [
            MonthlyReturn(year=2026, month=1, return_pct=Decimal("0.1")),
            MonthlyReturn(year=2026, month=2, return_pct=Decimal("0.1")),
        ]
        result = _yearly_compound(months)
        assert 2026 in result
        assert result[2026] is not None
        assert abs(float(result[2026]) - 0.21) < 1e-9

    def test_None_있으면_연도_None(self) -> None:
        months = [
            MonthlyReturn(year=2026, month=1, return_pct=Decimal("0.1")),
            MonthlyReturn(year=2026, month=2, return_pct=None),
        ]
        result = _yearly_compound(months)
        assert result[2026] is None

    def test_연도별_분리(self) -> None:
        months = [
            MonthlyReturn(year=2025, month=12, return_pct=Decimal("0.05")),
            MonthlyReturn(year=2026, month=1, return_pct=Decimal("0.10")),
        ]
        result = _yearly_compound(months)
        assert result[2025] == Decimal("0.05")
        assert result[2026] == Decimal("0.10")


# ---------------------------------------------------------------------------
# Service-level integration
# ---------------------------------------------------------------------------


def _make_tx() -> AllTxRow:
    return AllTxRow(
        symbol_id=1,
        currency="KRW",
        traded_at=datetime(2024, 1, 1, tzinfo=UTC),
        quantity=Decimal("10"),
        price=Decimal("100"),
        tx_type=TransactionType.BUY,
    )


class TestHeatmapService:
    async def test_거래_없으면_no_activity(self) -> None:
        repo = AsyncMock(spec=PortfolioHistoryRepository)
        repo.list_all_transactions.return_value = []
        repo.list_price_points_for_symbols.return_value = {}
        fx = AsyncMock(spec=FxRateService)

        svc = HeatmapService(repo, fx)
        result = await svc.get_heatmap("KRW", years=2)
        assert "no_activity_in_period" in result.warnings
        assert result.months == []
        assert result.yearly_returns == {}

    async def test_정상_시나리오_월별_매트릭스(self) -> None:
        repo = AsyncMock(spec=PortfolioHistoryRepository)
        repo.list_all_transactions.return_value = [_make_tx()]
        repo.list_price_points_for_symbols.return_value = {
            1: [
                (datetime(2024, 1, 1, tzinfo=UTC), Decimal("100")),
                (datetime(2026, 5, 1, tzinfo=UTC), Decimal("200")),
            ]
        }
        fx = AsyncMock(spec=FxRateService)

        svc = HeatmapService(repo, fx)
        result = await svc.get_heatmap("KRW", years=1)
        assert result.currency == "KRW"
        assert len(result.months) > 0
        assert all(0 < m.month <= 12 for m in result.months)

    async def test_currency_그대로(self) -> None:
        repo = AsyncMock(spec=PortfolioHistoryRepository)
        repo.list_all_transactions.return_value = []
        repo.list_price_points_for_symbols.return_value = {}
        fx = AsyncMock(spec=FxRateService)

        svc = HeatmapService(repo, fx)
        result = await svc.get_heatmap("USD", years=1)
        assert result.currency == "USD"
