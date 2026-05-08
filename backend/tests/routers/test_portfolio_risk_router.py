"""Router tests for GET /api/portfolio/performance/risk."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_risk_service
from app.core.principal import OwnerPrincipal
from app.domain.performance import PerformancePeriod
from app.main import app
from app.schemas.risk import RiskMetricsResponse
from app.services.risk import RiskService


def _make_response() -> RiskMetricsResponse:
    return RiskMetricsResponse(
        period=PerformancePeriod.ONE_YEAR,
        currency="KRW",
        start_date=datetime(2025, 5, 8, tzinfo=UTC),
        end_date=datetime(2026, 5, 8, tzinfo=UTC),
        annualized_return=Decimal("0.1234"),
        annualized_volatility=Decimal("0.1850"),
        sharpe_ratio=Decimal("0.50"),
        max_drawdown=Decimal("0.0823"),
        max_drawdown_at=datetime(2025, 11, 2, tzinfo=UTC),
        risk_free_rate=Decimal("0.03"),
        warnings=[],
    )


class TestRiskEndpoint:
    async def test_미인증_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/portfolio/performance/risk")
        assert response.status_code == 401

    async def test_정상_200(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=RiskService)
        mock_svc.get_risk_metrics.return_value = _make_response()

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_risk_service] = lambda: mock_svc
        try:
            response = await async_client.get(
                "/api/portfolio/performance/risk?period=1Y&currency=krw"
            )
            assert response.status_code == 200
            body = response.json()
            assert body["currency"] == "KRW"
            assert body["annualized_return"] == "0.1234"
            assert body["sharpe_ratio"] == "0.50"
            assert body["max_drawdown"] == "0.0823"
            assert body["risk_free_rate"] == "0.03"
        finally:
            app.dependency_overrides.clear()

    async def test_잘못된_period_422(self, async_client: AsyncClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        try:
            response = await async_client.get("/api/portfolio/performance/risk?period=INVALID")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()
