"""Integration tests for /api/user-assets router."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_user_asset_service
from app.domain.asset_type import AssetType
from app.exceptions import ConflictError, NotFoundError
from app.main import app
from app.models.asset_symbol import AssetSymbol
from app.models.user import User
from app.models.user_asset import UserAsset
from app.services.user_asset import UserAssetService


def _make_user(user_id: int = 1, email: str = "test@example.com") -> User:
    user = User(email=email, password_hash="hashed")
    user.id = user_id
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def _make_user_asset(ua_id: int = 1, user_id: int = 1) -> UserAsset:
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

    ua = UserAsset(user_id=user_id, asset_symbol_id=sym.id)
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
        user = _make_user()
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

    async def test_사용자_A_자산이_사용자_B_목록에_없다(self, async_client: AsyncClient) -> None:
        # User B's service returns empty list — A's assets are not visible
        user_b = _make_user(user_id=2, email="b@example.com")
        mock_service = AsyncMock(spec=UserAssetService)
        mock_service.list.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user_b
        app.dependency_overrides[get_user_asset_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets")
            assert response.status_code == 200
            assert response.json() == []
            mock_service.list.assert_called_once_with(2)
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
        user = _make_user()
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
            assert body["user_id"] == 1
            assert body["asset_symbol"]["symbol"] == "BTC"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_user_asset_service, None)

    async def test_존재하지_않는_심볼이면_404를_반환한다(self, async_client: AsyncClient) -> None:
        user = _make_user()
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
        user = _make_user()
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
        user = _make_user()
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
        user = _make_user()
        mock_service = AsyncMock(spec=UserAssetService)
        mock_service.remove.return_value = None

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_user_asset_service] = lambda: mock_service

        try:
            response = await async_client.delete("/api/user-assets/1")
            assert response.status_code == 204
            mock_service.remove.assert_called_once_with(1, 1)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_user_asset_service, None)

    async def test_없는_자산_삭제하면_404를_반환한다(self, async_client: AsyncClient) -> None:
        user = _make_user()
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
        user = _make_user()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.delete("/api/user-assets/0")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestUserAssetIsolationIntegration:
    """Full integration test: user A's assets must not appear for user B."""

    async def test_사용자_격리_통합_테스트(
        self, async_client: AsyncClient, user_factory: Any
    ) -> None:
        from app.core.security import create_access_token
        from app.domain.asset_type import AssetType
        from app.repositories.asset_symbol import AssetSymbolRepository
        from app.repositories.user_asset import UserAssetRepository

        # Create two users
        user_a = await user_factory(email="isolation_a@example.com")
        user_b = await user_factory(email="isolation_b@example.com")

        # Create an asset symbol directly in DB
        from app.db.base import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            sym_repo = AssetSymbolRepository(session)
            sym = await sym_repo.create(
                asset_type=AssetType.CRYPTO,
                symbol="ISOLATE_COIN",
                exchange="test",
                name="Isolation Test Coin",
                currency="KRW",
            )
            await session.commit()
            sym_id = sym.id

        async with AsyncSessionLocal() as session:
            ua_repo = UserAssetRepository(session)
            await ua_repo.create(user_id=user_a.id, asset_symbol_id=sym_id)
            await session.commit()

        # User A sees the asset
        token_a = create_access_token(subject=user_a.id)
        resp_a = await async_client.get("/api/user-assets", cookies={"access_token": token_a})
        assert resp_a.status_code == 200
        a_symbols = [ua["asset_symbol"]["symbol"] for ua in resp_a.json()]
        assert "ISOLATE_COIN" in a_symbols

        # User B does NOT see the asset
        token_b = create_access_token(subject=user_b.id)
        resp_b = await async_client.get("/api/user-assets", cookies={"access_token": token_b})
        assert resp_b.status_code == 200
        b_symbols = [ua["asset_symbol"]["symbol"] for ua in resp_b.json()]
        assert "ISOLATE_COIN" not in b_symbols
