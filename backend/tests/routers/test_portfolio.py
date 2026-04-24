"""Router tests for /api/portfolio — 401, 200, empty portfolio, contract."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_portfolio_service
from app.domain.asset_type import AssetType
from app.main import app
from app.models.user import User
from app.schemas.portfolio import (
    AllocationEntry,
    HoldingResponse,
    PnlEntry,
    PortfolioSummaryResponse,
    SymbolEmbedded,
)
from app.services.portfolio import PortfolioService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: int = 1) -> User:
    user = User(email="test@example.com", password_hash="x")
    user.id = user_id
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def _make_symbol_embedded() -> SymbolEmbedded:
    return SymbolEmbedded(
        id=7,
        asset_type=AssetType.US_STOCK,
        symbol="AAPL",
        exchange="NASDAQ",
        name="Apple Inc.",
        currency="USD",
    )


def _make_holding() -> HoldingResponse:
    return HoldingResponse(
        user_asset_id=12,
        asset_symbol=_make_symbol_embedded(),
        quantity=Decimal("10.0000000000"),
        avg_cost=Decimal("170.500000"),
        cost_basis=Decimal("1705.00"),
        latest_price=Decimal("175.200000"),
        latest_value=Decimal("1752.00"),
        pnl_abs=Decimal("47.00"),
        pnl_pct=2.76,
        weight_pct=21.4,
        last_price_refreshed_at=datetime(2026, 4, 24, 9, 0, 0, tzinfo=UTC),
        is_stale=False,
        is_pending=False,
    )


def _make_summary() -> PortfolioSummaryResponse:
    return PortfolioSummaryResponse(
        total_value_by_currency={"KRW": "12500000.00", "USD": "8200.12"},
        total_cost_by_currency={"KRW": "11000000.00", "USD": "7500.00"},
        pnl_by_currency={
            "KRW": PnlEntry(abs=Decimal("1500000.00"), pct=13.64),
            "USD": PnlEntry(abs=Decimal("700.12"), pct=9.34),
        },
        allocation=[
            AllocationEntry(asset_type=AssetType.US_STOCK, pct=48.3),
            AllocationEntry(asset_type=AssetType.CRYPTO, pct=51.7),
        ],
        last_price_refreshed_at=datetime(2026, 4, 24, 9, 0, 0, tzinfo=UTC),
        pending_count=1,
        stale_count=0,
    )


# ---------------------------------------------------------------------------
# GET /api/portfolio/summary
# ---------------------------------------------------------------------------


class TestGetPortfolioSummary:
    async def test_미인증_401_반환(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/portfolio/summary")
        assert response.status_code == 401

    async def test_정상_200_반환(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_summary.return_value = _make_summary()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/summary")
            assert response.status_code == 200
            body = response.json()
            assert "total_value_by_currency" in body
            assert "pnl_by_currency" in body
            assert "allocation" in body
            assert "pending_count" in body
            assert "stale_count" in body
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_빈_포트폴리오_summary_0값_구조(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_summary.return_value = PortfolioSummaryResponse()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/summary")
            assert response.status_code == 200
            body = response.json()
            assert body["total_value_by_currency"] == {}
            assert body["pending_count"] == 0
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_contract_응답_키_일치(self, async_client: AsyncClient) -> None:
        """Contract test: response keys must match the OpenAPI schema."""
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_summary.return_value = _make_summary()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/summary")
            body = response.json()
            required_keys = {
                "total_value_by_currency",
                "total_cost_by_currency",
                "pnl_by_currency",
                "allocation",
                "last_price_refreshed_at",
                "pending_count",
                "stale_count",
            }
            assert required_keys.issubset(set(body.keys()))
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_service가_user_id로_호출됨(self, async_client: AsyncClient) -> None:
        user = _make_user(user_id=42)
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_summary.return_value = PortfolioSummaryResponse()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            await async_client.get("/api/portfolio/summary")
            mock_service.get_summary.assert_called_once_with(42)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)


# ---------------------------------------------------------------------------
# GET /api/portfolio/holdings
# ---------------------------------------------------------------------------


class TestGetPortfolioHoldings:
    async def test_미인증_401_반환(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/portfolio/holdings")
        assert response.status_code == 401

    async def test_정상_200_반환(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_holdings.return_value = [_make_holding()]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/holdings")
            assert response.status_code == 200
            body = response.json()
            assert isinstance(body, list)
            assert len(body) == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_빈_포트폴리오_빈_배열_반환(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_holdings.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/holdings")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_contract_응답_키_일치(self, async_client: AsyncClient) -> None:
        """Contract test: holding row keys must match the OpenAPI HoldingResponse schema."""
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_holdings.return_value = [_make_holding()]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/holdings")
            item = response.json()[0]
            required_keys = {
                "user_asset_id",
                "asset_symbol",
                "quantity",
                "avg_cost",
                "cost_basis",
                "latest_price",
                "latest_value",
                "pnl_abs",
                "pnl_pct",
                "weight_pct",
                "last_price_refreshed_at",
                "is_stale",
                "is_pending",
            }
            assert required_keys.issubset(set(item.keys()))
            # Decimal fields must be strings
            assert isinstance(item["quantity"], str)
            assert isinstance(item["avg_cost"], str)
            assert isinstance(item["cost_basis"], str)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_asset_symbol_nested_키_존재(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_holdings.return_value = [_make_holding()]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/holdings")
            sym = response.json()[0]["asset_symbol"]
            assert "id" in sym
            assert "asset_type" in sym
            assert "symbol" in sym
            assert "exchange" in sym
            assert "name" in sym
            assert "currency" in sym
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_service가_user_id로_호출됨(self, async_client: AsyncClient) -> None:
        user = _make_user(user_id=7)
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_holdings.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            await async_client.get("/api/portfolio/holdings")
            mock_service.get_holdings.assert_called_once_with(7)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)
