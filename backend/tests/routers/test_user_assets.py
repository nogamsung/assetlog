"""Integration tests for /api/user-assets router."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_user_asset_service
from app.core.principal import OwnerPrincipal
from app.domain.asset_type import AssetType
from app.exceptions import ConflictError, NotFoundError
from app.main import app
from app.models.asset_symbol import AssetSymbol
from app.models.user_asset import UserAsset
from app.services.user_asset import UserAssetService


def _make_user_asset(ua_id: int = 1) -> UserAsset:
    sym = AssetSymbol(
        asset_type=AssetType.CRYPTO,
        symbol="BTC",
        exchange="upbit",
        name="Bitcoin",
        currency="KRW",
    )
    sym.id = 1
    sym.created_at = datetime.now(UTC)
    sym.updated_at = datetime.now(UTC)

    ua = UserAsset(asset_symbol_id=sym.id)
    ua.id = ua_id
    ua.asset_symbol = sym  # type: ignore[assignment]  # mock relationship
    ua.memo = None
    ua.created_at = datetime.now(UTC)
    ua.updated_at = datetime.now(UTC)
    return ua


class TestListUserAssets:
    async def test_인증_없이_접근하면_401을_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/user-assets")
        assert response.status_code == 401

    async def test_인증_후_보유_목록을_반환한다(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        ua = _make_user_asset()
        mock_service = AsyncMock(spec=UserAssetService)
        mock_service.list.return_value = [ua]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_user_asset_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets")
            assert response.status_code == 200
            body = response.json()
            assert isinstance(body, list)
            assert body[0]["asset_symbol"]["symbol"] == "BTC"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_user_asset_service, None)

    async def test_빈_목록을_반환한다(self, async_client: AsyncClient) -> None:
        # Single owner, no assets
        user = OwnerPrincipal()
        mock_service = AsyncMock(spec=UserAssetService)
        mock_service.list.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_user_asset_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_user_asset_service, None)


class TestAddUserAsset:
    async def test_인증_없이_추가하면_401을_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/user-assets",
            json={"asset_symbol_id": 1},
        )
        assert response.status_code == 401

    async def test_보유_선언에_성공하면_201을_반환한다(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        ua = _make_user_asset()
        mock_service = AsyncMock(spec=UserAssetService)
        mock_service.add.return_value = ua

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_user_asset_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/user-assets",
                json={"asset_symbol_id": 1},
            )
            assert response.status_code == 201
            body = response.json()
            assert body["asset_symbol"]["symbol"] == "BTC"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_user_asset_service, None)

    async def test_존재하지_않는_심볼이면_404를_반환한다(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        mock_service = AsyncMock(spec=UserAssetService)
        mock_service.add.side_effect = NotFoundError("symbol not found")

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_user_asset_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/user-assets",
                json={"asset_symbol_id": 9999},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_user_asset_service, None)

    async def test_이미_보유_중이면_409를_반환한다(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        mock_service = AsyncMock(spec=UserAssetService)
        mock_service.add.side_effect = ConflictError("already held")

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_user_asset_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/user-assets",
                json={"asset_symbol_id": 1},
            )
            assert response.status_code == 409
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_user_asset_service, None)

    async def test_asset_symbol_id가_0이면_422를_반환한다(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.post(
                "/api/user-assets",
                json={"asset_symbol_id": 0},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestRemoveUserAsset:
    async def test_인증_없이_삭제하면_401을_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.delete("/api/user-assets/1")
        assert response.status_code == 401

    async def test_삭제에_성공하면_204를_반환한다(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        mock_service = AsyncMock(spec=UserAssetService)
        mock_service.remove.return_value = None

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_user_asset_service] = lambda: mock_service

        try:
            response = await async_client.delete("/api/user-assets/1")
            assert response.status_code == 204
            mock_service.remove.assert_called_once_with(1)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_user_asset_service, None)

    async def test_없는_자산_삭제하면_404를_반환한다(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        mock_service = AsyncMock(spec=UserAssetService)
        mock_service.remove.side_effect = NotFoundError("not found")

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_user_asset_service] = lambda: mock_service

        try:
            response = await async_client.delete("/api/user-assets/9999")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_user_asset_service, None)

    async def test_id가_0이면_422를_반환한다(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.delete("/api/user-assets/0")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)
