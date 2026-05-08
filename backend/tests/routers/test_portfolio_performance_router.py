"""Router tests for GET /api/portfolio/performance."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_performance_service
from app.core.principal import OwnerPrincipal
from app.domain.performance import PerformanceMethod, PerformancePeriod
from app.main import app
from app.schemas.performance import CashflowEntry, PerformanceResponse
from app.services.performance import PerformanceService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
START = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)


def _make_owner() -> OwnerPrincipal:
    return OwnerPrincipal()


def _make_performance_response(
    twr: Decimal | None = Decimal("0.20"),
    mwr: Decimal | None = Decimal("0.20"),
    warnings: list[str] | None = None,
) -> PerformanceResponse:
    return PerformanceResponse(
        period=PerformancePeriod.ONE_YEAR,
        method=PerformanceMethod.BOTH,
        currency="KRW",
        start_date=START,
        end_date=NOW,
        twr=twr,
        mwr=mwr,
        annualized_twr=twr,
        annualized_mwr=mwr,
        start_value=Decimal("1000000"),
        end_value=Decimal("1200000"),
        cashflows=[CashflowEntry(date=START, amount=Decimal("-1000000"), kind="buy")],
        warnings=warnings or [],
    )


# ---------------------------------------------------------------------------
# 401 — Unauthenticated
# ---------------------------------------------------------------------------


class TestPortfolioPerformanceRouterUnauth:
    async def test_미인증_401_반환(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/portfolio/performance")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 200 — Happy path
# ---------------------------------------------------------------------------


class TestPortfolioPerformanceRouterHappyPath:
    async def test_정상_200_반환(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=PerformanceService)
        mock_service.get_performance.return_value = _make_performance_response()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_performance_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/performance")
            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_performance_service, None)

    async def test_응답_스키마_키_존재(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=PerformanceService)
        mock_service.get_performance.return_value = _make_performance_response()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_performance_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/performance")
            body = response.json()
            assert "period" in body
            assert "method" in body
            assert "currency" in body
            assert "start_date" in body
            assert "end_date" in body
            assert "twr" in body
            assert "mwr" in body
            assert "cashflows" in body
            assert "warnings" in body
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_performance_service, None)

    async def test_decimal_필드가_문자열로_직렬화됨(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=PerformanceService)
        mock_service.get_performance.return_value = _make_performance_response()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_performance_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/performance")
            body = response.json()
            assert isinstance(body["twr"], str)
            assert isinstance(body["mwr"], str)
            # Cashflow amount should also be string
            if body["cashflows"]:
                assert isinstance(body["cashflows"][0]["amount"], str)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_performance_service, None)

    async def test_warnings_포함_응답_그대로_직렬화(self, async_client: AsyncClient) -> None:
        """mock이 warnings=['fx_rate_missing'] 응답 시 응답 본문에 그대로 직렬화."""
        user = _make_owner()
        mock_service = AsyncMock(spec=PerformanceService)
        mock_service.get_performance.return_value = _make_performance_response(
            twr=None,
            mwr=None,
            warnings=["fx_rate_missing"],
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_performance_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/performance")
            assert response.status_code == 200
            body = response.json()
            assert "fx_rate_missing" in body["warnings"]
            assert body["twr"] is None
            assert body["mwr"] is None
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_performance_service, None)

    async def test_service가_올바른_파라미터로_호출됨(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=PerformanceService)
        mock_service.get_performance.return_value = _make_performance_response()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_performance_service] = lambda: mock_service

        try:
            await async_client.get(
                "/api/portfolio/performance",
                params={"period": "1M", "method": "twr", "currency": "usd"},
            )
            mock_service.get_performance.assert_called_once_with(
                PerformancePeriod.ONE_MONTH,
                PerformanceMethod.TWR,
                "USD",
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_performance_service, None)

    async def test_기본값_파라미터_1Y_both_KRW(self, async_client: AsyncClient) -> None:
        """파라미터 없으면 기본값 period=1Y, method=both, currency=KRW."""
        user = _make_owner()
        mock_service = AsyncMock(spec=PerformanceService)
        mock_service.get_performance.return_value = _make_performance_response()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_performance_service] = lambda: mock_service

        try:
            await async_client.get("/api/portfolio/performance")
            mock_service.get_performance.assert_called_once_with(
                PerformancePeriod.ONE_YEAR,
                PerformanceMethod.BOTH,
                "KRW",
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_performance_service, None)


# ---------------------------------------------------------------------------
# 422 — Validation errors
# ---------------------------------------------------------------------------


class TestPortfolioPerformanceRouterValidation:
    async def test_잘못된_period_422(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=PerformanceService)

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_performance_service] = lambda: mock_service

        try:
            response = await async_client.get(
                "/api/portfolio/performance",
                params={"period": "INVALID"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_performance_service, None)

    async def test_잘못된_method_422(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=PerformanceService)

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_performance_service] = lambda: mock_service

        try:
            response = await async_client.get(
                "/api/portfolio/performance",
                params={"method": "foo"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_performance_service, None)
