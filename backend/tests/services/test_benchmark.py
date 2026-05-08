"""Unit tests for BenchmarkService — pure helpers + mocked I/O."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

from app.adapters.benchmark import BenchmarkAdapter, HistoricalClose
from app.domain.performance import PerformancePeriod
from app.repositories.portfolio_history import AllTxRow, PortfolioHistoryRepository
from app.services.benchmark import (
    BenchmarkService,
    _benchmark_to_returns,
    _daily_grid,
    _to_cumulative_returns,
)
from app.services.fx_rate import FxRateService

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestDailyGrid:
    def test_단일_날짜_쌍(self) -> None:
        ts = datetime(2026, 5, 1, tzinfo=UTC)
        grid = _daily_grid(ts, ts)
        assert len(grid) == 2

    def test_3일_4_포인트(self) -> None:
        start = datetime(2026, 5, 1, tzinfo=UTC)
        end = datetime(2026, 5, 4, tzinfo=UTC)
        grid = _daily_grid(start, end)
        assert len(grid) == 4
        assert grid[0] == start
        assert grid[-1] == end

    def test_naive_datetime_utc_변환(self) -> None:
        start = datetime(2026, 5, 1, 12, 30)
        end = datetime(2026, 5, 2, 8, 15)
        grid = _daily_grid(start, end)
        assert all(g.tzinfo is UTC for g in grid)
        assert grid[0].hour == 0


class TestToCumulativeReturns:
    def test_baseline_0(self) -> None:
        samples = [
            (datetime(2026, 5, 1, tzinfo=UTC), Decimal("1000")),
            (datetime(2026, 5, 2, tzinfo=UTC), Decimal("1100")),
            (datetime(2026, 5, 3, tzinfo=UTC), Decimal("1200")),
        ]
        points = _to_cumulative_returns(samples)
        assert points[0].cumulative_return_pct == Decimal("0")
        assert points[1].cumulative_return_pct == Decimal("0.1")
        assert points[2].cumulative_return_pct == Decimal("0.2")

    def test_baseline_까지_0_유지(self) -> None:
        samples = [
            (datetime(2026, 5, 1, tzinfo=UTC), Decimal("0")),
            (datetime(2026, 5, 2, tzinfo=UTC), Decimal("1000")),
            (datetime(2026, 5, 3, tzinfo=UTC), Decimal("1100")),
        ]
        points = _to_cumulative_returns(samples)
        assert points[0].cumulative_return_pct == Decimal("0")
        assert points[1].cumulative_return_pct == Decimal("0")
        assert points[2].cumulative_return_pct == Decimal("0.1")

    def test_빈_입력_빈_출력(self) -> None:
        assert _to_cumulative_returns([]) == []

    def test_손실_음수_return(self) -> None:
        samples = [
            (datetime(2026, 5, 1, tzinfo=UTC), Decimal("1000")),
            (datetime(2026, 5, 2, tzinfo=UTC), Decimal("900")),
        ]
        points = _to_cumulative_returns(samples)
        assert points[1].cumulative_return_pct == Decimal("-0.1")


class TestBenchmarkToReturns:
    def test_타임스탬프_align(self) -> None:
        history = [
            HistoricalClose("^KS11", datetime(2026, 5, 1, tzinfo=UTC), Decimal("2500")),
            HistoricalClose("^KS11", datetime(2026, 5, 2, tzinfo=UTC), Decimal("2550")),
            HistoricalClose("^KS11", datetime(2026, 5, 3, tzinfo=UTC), Decimal("2600")),
        ]
        timestamps = [
            datetime(2026, 5, 1, tzinfo=UTC),
            datetime(2026, 5, 2, tzinfo=UTC),
            datetime(2026, 5, 3, tzinfo=UTC),
        ]
        points = _benchmark_to_returns(history, timestamps)
        assert points[0].cumulative_return_pct == Decimal("0")
        assert points[1].cumulative_return_pct == Decimal("0.02")
        assert points[2].cumulative_return_pct == Decimal("0.04")

    def test_가장_최근_과거_close_사용(self) -> None:
        history = [
            HistoricalClose("^KS11", datetime(2026, 5, 1, tzinfo=UTC), Decimal("2500")),
            HistoricalClose("^KS11", datetime(2026, 5, 4, tzinfo=UTC), Decimal("2600")),
        ]
        timestamps = [
            datetime(2026, 5, 1, tzinfo=UTC),
            datetime(2026, 5, 2, tzinfo=UTC),  # weekend — uses 5/1
            datetime(2026, 5, 4, tzinfo=UTC),
        ]
        points = _benchmark_to_returns(history, timestamps)
        assert points[1].cumulative_return_pct == Decimal("0")  # weekend → still baseline
        assert points[2].cumulative_return_pct == Decimal("0.04")

    def test_빈_history_빈_출력(self) -> None:
        timestamps = [datetime(2026, 5, 1, tzinfo=UTC)]
        assert _benchmark_to_returns([], timestamps) == []


# ---------------------------------------------------------------------------
# Service-level integration
# ---------------------------------------------------------------------------


class TestBenchmarkService:
    async def test_거래_없으면_no_activity_warning(self) -> None:
        repo = AsyncMock(spec=PortfolioHistoryRepository)
        repo.list_all_transactions.return_value = []
        repo.list_price_points_for_symbols.return_value = {}

        fx = AsyncMock(spec=FxRateService)
        adapter = AsyncMock(spec=BenchmarkAdapter)
        adapter.fetch_many.return_value = {}

        svc = BenchmarkService(repo, fx, adapter)
        result = await svc.compare(PerformancePeriod.ONE_YEAR, "KRW", [])

        assert "no_activity_in_period" in result.warnings
        assert result.portfolio.symbol == "PORTFOLIO"
        assert result.benchmarks == []
        assert result.alpha == {}

    async def test_benchmark_fetch_실패_warning(self) -> None:
        repo = AsyncMock(spec=PortfolioHistoryRepository)
        repo.list_all_transactions.return_value = []
        repo.list_price_points_for_symbols.return_value = {}

        fx = AsyncMock(spec=FxRateService)
        adapter = AsyncMock(spec=BenchmarkAdapter)
        adapter.fetch_many.return_value = {"^KS11": []}

        svc = BenchmarkService(repo, fx, adapter)
        result = await svc.compare(PerformancePeriod.ONE_YEAR, "KRW", ["^KS11"])
        assert "benchmark_fetch_failed:^KS11" in result.warnings
        assert result.alpha == {}

    async def test_alpha_계산(self) -> None:
        # No portfolio activity — portfolio returns stay 0
        # Benchmark gains 5% → alpha = 0 - 0.05 = -0.05
        repo = AsyncMock(spec=PortfolioHistoryRepository)
        repo.list_all_transactions.return_value = []
        repo.list_price_points_for_symbols.return_value = {}

        fx = AsyncMock(spec=FxRateService)

        end_dt = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        start_dt = end_dt - timedelta(days=2)
        bench_history = [
            HistoricalClose("^KS11", start_dt, Decimal("1000")),
            HistoricalClose("^KS11", end_dt, Decimal("1050")),
        ]
        adapter = AsyncMock(spec=BenchmarkAdapter)
        adapter.fetch_many.return_value = {"^KS11": bench_history}

        svc = BenchmarkService(repo, fx, adapter)
        result = await svc.compare(PerformancePeriod.ONE_WEEK, "KRW", ["^KS11"])
        # The portfolio has no activity so its final return is 0.
        # Benchmark cumulative return at last sample == 0.05
        assert "^KS11" in result.alpha
        assert result.alpha["^KS11"] == Decimal("-0.05")

    async def test_currency_uppercase_그대로(self) -> None:
        repo = AsyncMock(spec=PortfolioHistoryRepository)
        repo.list_all_transactions.return_value = []
        repo.list_price_points_for_symbols.return_value = {}

        fx = AsyncMock(spec=FxRateService)
        adapter = AsyncMock(spec=BenchmarkAdapter)
        adapter.fetch_many.return_value = {}

        svc = BenchmarkService(repo, fx, adapter)
        result = await svc.compare(PerformancePeriod.ONE_YEAR, "USD", [])
        assert result.currency == "USD"


def _make_tx(symbol_id: int = 1, currency: str = "KRW") -> AllTxRow:
    """Build a minimal AllTxRow (private dataclass from #97 repo)."""
    return AllTxRow(
        symbol_id=symbol_id,
        currency=currency,
        traded_at=datetime(2026, 1, 1, tzinfo=UTC),
        quantity=Decimal("10"),
        price=Decimal("100"),
        tx_type="buy",
    )


class TestPortfolioReturnsBuilder:
    async def test_거래_있으면_value_series_생성(self) -> None:
        repo = AsyncMock(spec=PortfolioHistoryRepository)
        repo.list_all_transactions.return_value = [_make_tx()]
        repo.list_price_points_for_symbols.return_value = {
            1: [
                (datetime(2026, 1, 1, tzinfo=UTC), Decimal("100")),
                (datetime(2026, 5, 1, tzinfo=UTC), Decimal("110")),
            ]
        }

        fx = AsyncMock(spec=FxRateService)
        adapter = AsyncMock(spec=BenchmarkAdapter)
        adapter.fetch_many.return_value = {}

        svc = BenchmarkService(repo, fx, adapter)
        result = await svc.compare(PerformancePeriod.ONE_YEAR, "KRW", [])
        assert "no_activity_in_period" not in result.warnings
        assert len(result.portfolio.points) > 0
