"""Integration tests for /api/symbols router."""

from __future__ import annotations

from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_symbol_service
from app.core.principal import OwnerPrincipal
from app.domain.asset_type import AssetType
from app.exceptions import ConflictError
from app.main import app
from app.models.asset_symbol import AssetSymbol
from app.services.symbol import SymbolService


def _make_owner() -> OwnerPrincipal:
    return OwnerPrincipal()


def _make_asset(
    asset_id: int = 1,
    symbol: str = "BTC",
    exchange: str = "upbit",
) -> AssetSymbol:
    from datetime import UTC, datetime

    asset = AssetSymbol(
        asset_type=AssetType.CRYPTO,
        symbol=symbol,
        exchange=exchange,
        name="Bitcoin",
        currency="KRW",
    )
    asset.id = asset_id
    asset.created_at = datetime.now(UTC)
    asset.updated_at = datetime.now(UTC)
    return asset


class TestSearchSymbols:
    async def test_인증_없이_접근하면_401을_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/symbols")
        assert response.status_code == 401

    async def test_인증_후_검색하면_200과_목록을_반환한다(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        asset = _make_asset()
        mock_service = AsyncMock(spec=SymbolService)
        mock_service.search.return_value = [asset]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_symbol_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/symbols?q=BTC")
            assert response.status_code == 200
            body = response.json()
            assert isinstance(body, list)
            assert body[0]["symbol"] == "BTC"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_symbol_service, None)

    async def test_빈_검색_결과면_빈_배열을_반환한다(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=SymbolService)
        mock_service.search.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_symbol_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/symbols?q=UNKNOWN999")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_symbol_service, None)

    async def test_asset_type_필터를_전달한다(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=SymbolService)
        mock_service.search.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_symbol_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/symbols?asset_type=crypto")
            assert response.status_code == 200
            mock_service.search.assert_called_once()
            call_kwargs = mock_service.search.call_args.kwargs
            assert call_kwargs["asset_type"] == AssetType.CRYPTO
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_symbol_service, None)


class TestRegisterSymbol:
    async def test_인증_없이_등록하면_401을_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/symbols",
            json={
                "asset_type": "crypto",
                "symbol": "BTC",
                "exchange": "upbit",
                "name": "Bitcoin",
                "currency": "KRW",
            },
        )
        assert response.status_code == 401

    async def test_신규_심볼_등록하면_201과_응답을_반환한다(
        self, async_client: AsyncClient
    ) -> None:
        user = _make_owner()
        asset = _make_asset()
        mock_service = AsyncMock(spec=SymbolService)
        mock_service.register.return_value = asset

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_symbol_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/symbols",
                json={
                    "asset_type": "crypto",
                    "symbol": "BTC",
                    "exchange": "upbit",
                    "name": "Bitcoin",
                    "currency": "KRW",
                },
            )
            assert response.status_code == 201
            body = response.json()
            assert body["symbol"] == "BTC"
            assert body["exchange"] == "upbit"
            assert "id" in body
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_symbol_service, None)

    async def test_중복_심볼이면_409를_반환한다(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=SymbolService)
        mock_service.register.side_effect = ConflictError("already registered")

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_symbol_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/symbols",
                json={
                    "asset_type": "crypto",
                    "symbol": "BTC",
                    "exchange": "upbit",
                    "name": "Bitcoin",
                    "currency": "KRW",
                },
            )
            assert response.status_code == 409
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_symbol_service, None)

    async def test_잘못된_asset_type이면_422를_반환한다(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.post(
                "/api/symbols",
                json={
                    "asset_type": "invalid_type",
                    "symbol": "BTC",
                    "exchange": "upbit",
                    "name": "Bitcoin",
                    "currency": "KRW",
                },
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_symbol이_빈_문자열이면_422를_반환한다(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.post(
                "/api/symbols",
                json={
                    "asset_type": "crypto",
                    "symbol": "   ",
                    "exchange": "upbit",
                    "name": "Bitcoin",
                    "currency": "KRW",
                },
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestSymbolIntegration:
    """Full integration test using real SQLite DB (no mocks)."""

    async def test_등록_후_검색하면_결과에_나타난다(
        self, async_client: AsyncClient
    ) -> None:
        from app.core.principal import OWNER_ID
        from app.core.security import create_access_token

        token = create_access_token(subject=OWNER_ID)

        reg_resp = await async_client.post(
            "/api/symbols",
            json={
                "asset_type": "us_stock",
                "symbol": "MSFT",
                "exchange": "NASDAQ",
                "name": "Microsoft Corporation",
                "currency": "USD",
            },
            cookies={"access_token": token},
        )
        assert reg_resp.status_code == 201

        search_resp = await async_client.get(
            "/api/symbols?q=MSFT",
            cookies={"access_token": token},
        )
        assert search_resp.status_code == 200
        symbols = search_resp.json()
        assert any(s["symbol"] == "MSFT" for s in symbols)
