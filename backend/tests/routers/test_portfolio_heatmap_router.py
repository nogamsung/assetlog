"""Router tests for GET /api/portfolio/performance/heatmap."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_heatmap_service
from app.core.principal import OwnerPrincipal
from app.main import app
from app.schemas.heatmap import HeatmapResponse, MonthlyReturn
from app.services.heatmap import HeatmapService


def _make_response() -> HeatmapResponse:
    return HeatmapResponse(
        currency="KRW",
        start_date=datetime(2025, 1, 1, tzinfo=UTC),
        end_date=datetime(2026, 5, 8, tzinfo=UTC),
        months=[
            MonthlyReturn(year=2025, month=12, return_pct=Decimal("0.05")),
            MonthlyReturn(year=2026, month=1, return_pct=Decimal("0.03")),
            MonthlyReturn(year=2026, month=2, return_pct=None),
        ],
        yearly_returns={2025: Decimal("0.05"), 2026: None},
        warnings=[],
    )


class TestHeatmapEndpoint:
    async def test_미인증_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/portfolio/performance/heatmap")
        assert response.status_code == 401

    async def test_정상_200_응답구조(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=HeatmapService)
        mock_svc.get_heatmap.return_value = _make_response()

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_heatmap_service] = lambda: mock_svc
        try:
            response = await async_client.get(
                "/api/portfolio/performance/heatmap?currency=krw&years=2"
            )
            assert response.status_code == 200
            body = response.json()
            assert body["currency"] == "KRW"
            assert body["months"][0]["year"] == 2025
            assert body["months"][0]["return_pct"] == "0.05"
            assert body["months"][2]["return_pct"] is None
            assert body["yearly_returns"]["2025"] == "0.05"
            assert body["yearly_returns"]["2026"] is None
        finally:
            app.dependency_overrides.clear()

    async def test_years_검증_상한(self, async_client: AsyncClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        try:
            response = await async_client.get("/api/portfolio/performance/heatmap?years=21")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_years_검증_하한(self, async_client: AsyncClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        try:
            response = await async_client.get("/api/portfolio/performance/heatmap?years=0")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()
