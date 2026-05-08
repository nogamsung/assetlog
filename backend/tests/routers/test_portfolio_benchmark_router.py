"""Router tests for GET /api/portfolio/performance/benchmark."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_benchmark_service, get_current_user
from app.core.principal import OwnerPrincipal
from app.domain.performance import PerformancePeriod
from app.main import app
from app.schemas.benchmark import (
    BenchmarkComparisonResponse,
    BenchmarkSeries,
    ReturnPoint,
)
from app.services.benchmark import BenchmarkService


def _make_response() -> BenchmarkComparisonResponse:
    return BenchmarkComparisonResponse(
        period=PerformancePeriod.ONE_YEAR,
        currency="KRW",
        start_date=datetime(2025, 5, 1, tzinfo=UTC),
        end_date=datetime(2026, 5, 1, tzinfo=UTC),
        portfolio=BenchmarkSeries(
            symbol="PORTFOLIO",
            name="My portfolio",
            points=[
                ReturnPoint(
                    timestamp=datetime(2025, 5, 1, tzinfo=UTC),
                    cumulative_return_pct=Decimal("0"),
                ),
                ReturnPoint(
                    timestamp=datetime(2026, 5, 1, tzinfo=UTC),
                    cumulative_return_pct=Decimal("0.12"),
                ),
            ],
        ),
        benchmarks=[
            BenchmarkSeries(
                symbol="^KS11",
                name="KOSPI",
                points=[
                    ReturnPoint(
                        timestamp=datetime(2025, 5, 1, tzinfo=UTC),
                        cumulative_return_pct=Decimal("0"),
                    ),
                    ReturnPoint(
                        timestamp=datetime(2026, 5, 1, tzinfo=UTC),
                        cumulative_return_pct=Decimal("0.05"),
                    ),
                ],
            )
        ],
        alpha={"^KS11": Decimal("0.07")},
        warnings=[],
    )


class TestBenchmarkEndpoint:
    async def test_미인증_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/portfolio/performance/benchmark")
        assert response.status_code == 401

    async def test_정상_200_응답_구조(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=BenchmarkService)
        mock_svc.compare.return_value = _make_response()

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_benchmark_service] = lambda: mock_svc
        try:
            response = await async_client.get(
                "/api/portfolio/performance/benchmark?period=1Y&currency=krw&symbols=^KS11"
            )
            assert response.status_code == 200
            body = response.json()
            assert body["currency"] == "KRW"  # uppercase
            assert body["portfolio"]["symbol"] == "PORTFOLIO"
            assert body["benchmarks"][0]["symbol"] == "^KS11"
            assert body["alpha"]["^KS11"] == "0.07"
        finally:
            app.dependency_overrides.clear()

    async def test_symbols_파싱_passed(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=BenchmarkService)
        mock_svc.compare.return_value = _make_response()

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_benchmark_service] = lambda: mock_svc
        try:
            await async_client.get(
                "/api/portfolio/performance/benchmark?symbols=^KS11,^GSPC,BTC-USD"
            )
            mock_svc.compare.assert_awaited_once()
            call_args = mock_svc.compare.await_args
            assert call_args is not None
            assert call_args.args[2] == ["^KS11", "^GSPC", "BTC-USD"]
        finally:
            app.dependency_overrides.clear()

    async def test_잘못된_period_422(self, async_client: AsyncClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        try:
            response = await async_client.get("/api/portfolio/performance/benchmark?period=INVALID")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()
