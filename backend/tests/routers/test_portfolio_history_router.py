"""Router tests for GET /api/portfolio/history."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_portfolio_history_service
from app.core.principal import OwnerPrincipal
from app.domain.portfolio_history import HistoryBucket, HistoryPeriod
from app.main import app
from app.schemas.portfolio import HistoryPointResponse, PortfolioHistoryResponse
from app.services.portfolio_history import PortfolioHistoryService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)


def _make_owner() -> OwnerPrincipal:
    return OwnerPrincipal()


def _make_history_response(
    period: HistoryPeriod = HistoryPeriod.ONE_MONTH,
    currency: str = "KRW",
    num_points: int = 3,
) -> PortfolioHistoryResponse:
    from datetime import timedelta

    points = [
        HistoryPointResponse(
            timestamp=NOW - timedelta(days=i),
            value=Decimal("1000000"),
            cost_basis=Decimal("900000"),
        )
        for i in range(num_points)
    ]
    return PortfolioHistoryResponse(
        currency=currency,
        period=period,
        bucket=HistoryBucket.DAY,
        points=points,
    )


# ---------------------------------------------------------------------------
# 401 — Unauthenticated
# ---------------------------------------------------------------------------


class TestPortfolioHistoryRouterUnauth:
    async def test_미인증_401_반환(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/portfolio/history", params={"currency": "KRW"})
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 200 — Happy path
# ---------------------------------------------------------------------------


class TestPortfolioHistoryRouterHappyPath:
    async def test_정상_200_반환(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=PortfolioHistoryService)
        mock_service.get_history.return_value = _make_history_response()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_history_service] = lambda: mock_service

        try:
            response = await async_client.get(
                "/api/portfolio/history",
                params={"currency": "KRW", "period": "1M"},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_history_service, None)

    async def test_응답_스키마_키_존재(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=PortfolioHistoryService)
        mock_service.get_history.return_value = _make_history_response()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_history_service] = lambda: mock_service

        try:
            response = await async_client.get(
                "/api/portfolio/history",
                params={"currency": "KRW"},
            )
            body = response.json()
            assert "currency" in body
            assert "period" in body
            assert "bucket" in body
            assert "points" in body
            assert isinstance(body["points"], list)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_history_service, None)

    async def test_points_항목_스키마(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=PortfolioHistoryService)
        mock_service.get_history.return_value = _make_history_response(num_points=1)

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_history_service] = lambda: mock_service

        try:
            response = await async_client.get(
                "/api/portfolio/history",
                params={"currency": "KRW"},
            )
            body = response.json()
            assert len(body["points"]) == 1
            pt = body["points"][0]
            assert "timestamp" in pt
            assert "value" in pt
            assert "cost_basis" in pt
            # Decimal fields must be serialised as strings
            assert isinstance(pt["value"], str)
            assert isinstance(pt["cost_basis"], str)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_history_service, None)

    async def test_빈_points_200_반환(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=PortfolioHistoryService)
        mock_service.get_history.return_value = PortfolioHistoryResponse(
            currency="KRW",
            period=HistoryPeriod.ONE_MONTH,
            bucket=HistoryBucket.DAY,
            points=[],
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_history_service] = lambda: mock_service

        try:
            response = await async_client.get(
                "/api/portfolio/history",
                params={"currency": "KRW"},
            )
            assert response.status_code == 200
            assert response.json()["points"] == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_history_service, None)

    async def test_service가_period와_currency로_호출됨(
        self, async_client: AsyncClient
    ) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=PortfolioHistoryService)
        mock_service.get_history.return_value = _make_history_response()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_history_service] = lambda: mock_service

        try:
            await async_client.get(
                "/api/portfolio/history",
                params={"currency": "usd", "period": "1Y"},
            )
            mock_service.get_history.assert_called_once_with(HistoryPeriod.ONE_YEAR, "USD")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_history_service, None)

    async def test_period_기본값_1M(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=PortfolioHistoryService)
        mock_service.get_history.return_value = _make_history_response()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_history_service] = lambda: mock_service

        try:
            await async_client.get(
                "/api/portfolio/history",
                params={"currency": "KRW"},
            )
            call_args = mock_service.get_history.call_args
            assert call_args[0][0] == HistoryPeriod.ONE_MONTH
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_history_service, None)


# ---------------------------------------------------------------------------
# 422 — Validation errors
# ---------------------------------------------------------------------------


class TestPortfolioHistoryRouterValidation:
    async def test_currency_누락_422(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=PortfolioHistoryService)

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_history_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/history")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_history_service, None)

    async def test_잘못된_period_422(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=PortfolioHistoryService)

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_history_service] = lambda: mock_service

        try:
            response = await async_client.get(
                "/api/portfolio/history",
                params={"currency": "KRW", "period": "INVALID"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_history_service, None)
