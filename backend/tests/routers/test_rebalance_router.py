"""Router tests for GET /api/rebalance/suggestion."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_rebalance_service
from app.core.principal import OwnerPrincipal
from app.main import app
from app.schemas.rebalance import RebalanceEntry, RebalanceSuggestionResponse
from app.services.rebalance import RebalanceService


def _make_response() -> RebalanceSuggestionResponse:
    return RebalanceSuggestionResponse(
        currency="KRW",
        total_value=Decimal("10000000"),
        threshold_pct=Decimal("0.05"),
        entries=[
            RebalanceEntry.model_validate(
                {
                    "asset_type": "us_stock",
                    "target_pct": Decimal("0.6"),
                    "current_pct": Decimal("0.5"),
                    "drift_pct": Decimal("-0.1"),
                    "delta_amount": Decimal("1000000"),
                    "action": "buy",
                }
            )
        ],
        warnings=[],
    )


class TestRebalanceEndpoint:
    async def test_미인증_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/rebalance/suggestion")
        assert response.status_code == 401

    async def test_정상_200(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=RebalanceService)
        mock_svc.suggest.return_value = _make_response()

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_rebalance_service] = lambda: mock_svc
        try:
            response = await async_client.get(
                "/api/rebalance/suggestion?currency=krw&threshold_pct=0.05"
            )
            assert response.status_code == 200
            body = response.json()
            assert body["currency"] == "KRW"
            assert body["entries"][0]["action"] == "buy"
            assert body["entries"][0]["delta_amount"] == "1000000"
        finally:
            app.dependency_overrides.clear()

    async def test_threshold_범위_초과_422(self, async_client: AsyncClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        try:
            response = await async_client.get("/api/rebalance/suggestion?threshold_pct=1.5")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_default_threshold(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=RebalanceService)
        mock_svc.suggest.return_value = _make_response()

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_rebalance_service] = lambda: mock_svc
        try:
            response = await async_client.get("/api/rebalance/suggestion")
            assert response.status_code == 200
            mock_svc.suggest.assert_awaited_once()
            args = mock_svc.suggest.await_args
            assert args is not None
            assert args.args[0] == "KRW"
            assert args.args[1] == Decimal("0.05")
        finally:
            app.dependency_overrides.clear()
