"""Router tests for GET /api/market/indices."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_market_index_service
from app.core.principal import OwnerPrincipal
from app.main import app
from app.schemas.market_index import IndexQuote
from app.services.market_index import MarketIndexService


def _make_owner() -> OwnerPrincipal:
    return OwnerPrincipal()


def _make_quote(symbol: str = "^GSPC", name: str = "S&P 500") -> IndexQuote:
    return IndexQuote(
        symbol=symbol,
        name=name,
        currency="USD",
        price=Decimal("5123.41"),
        change=Decimal("12.34"),
        change_pct=Decimal("0.24"),
        fetched_at=datetime(2026, 4, 24, 9, 0, 0, tzinfo=UTC),
    )


class TestGetMarketIndices:
    async def test_미인증_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/market/indices")
        assert response.status_code == 401

    async def test_정상_200_반환(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_svc = AsyncMock(spec=MarketIndexService)
        mock_svc.list_indices.return_value = [
            _make_quote("^GSPC", "S&P 500"),
            _make_quote("BTC-KRW", "BTC"),
        ]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_market_index_service] = lambda: mock_svc

        try:
            response = await async_client.get("/api/market/indices")
            assert response.status_code == 200
            body = response.json()
            assert len(body["indices"]) == 2
            entry = body["indices"][0]
            required_keys = {
                "symbol",
                "name",
                "currency",
                "price",
                "change",
                "change_pct",
                "fetched_at",
            }
            assert required_keys.issubset(set(entry.keys()))
            # Decimal must serialize as string per schema config.
            assert isinstance(entry["price"], str)
            assert isinstance(entry["change_pct"], str)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_market_index_service, None)

    async def test_빈_indices_빈_배열(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_svc = AsyncMock(spec=MarketIndexService)
        mock_svc.list_indices.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_market_index_service] = lambda: mock_svc

        try:
            response = await async_client.get("/api/market/indices")
            assert response.status_code == 200
            assert response.json()["indices"] == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_market_index_service, None)
