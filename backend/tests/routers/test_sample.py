"""Integration tests for /api/sample/seed router."""

from __future__ import annotations

from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_sample_seed_service
from app.main import app
from app.models.user import User
from app.schemas.sample_seed import SampleSeedResponse
from app.services.sample_seed import SampleSeedService


def _make_user(user_id: int = 1, email: str = "test@example.com") -> User:
    """Local copy — avoids cross-module import of a non-fixture helper."""
    from datetime import UTC, datetime

    user = User(email=email, password_hash="hashed")
    user.id = user_id
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


class TestSeedEndpointUnauthorized:
    async def test_미인증_요청은_401을_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.post("/api/sample/seed")
        assert response.status_code == 401


class TestSeedEndpointSuccess:
    async def test_신규_사용자_200_seeded_true를_반환한다(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=SampleSeedService)
        mock_service.seed_for_user.return_value = SampleSeedResponse(
            seeded=True,
            user_assets_created=5,
            transactions_created=17,
            symbols_created=5,
            symbols_reused=0,
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_sample_seed_service] = lambda: mock_service

        try:
            response = await async_client.post("/api/sample/seed")
            assert response.status_code == 200
            body = response.json()
            assert body["seeded"] is True
            assert body["user_assets_created"] == 5
            assert body["transactions_created"] == 17
            assert body["symbols_created"] == 5
            assert body["symbols_reused"] == 0
            assert body["reason"] is None
            mock_service.seed_for_user.assert_called_once_with(user.id)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_sample_seed_service, None)

    async def test_이미_자산이_있는_사용자는_200_seeded_false를_반환한다(
        self, async_client: AsyncClient
    ) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=SampleSeedService)
        mock_service.seed_for_user.return_value = SampleSeedResponse(
            seeded=False,
            reason="user_already_has_assets",
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_sample_seed_service] = lambda: mock_service

        try:
            response = await async_client.post("/api/sample/seed")
            assert response.status_code == 200
            body = response.json()
            assert body["seeded"] is False
            assert body["reason"] == "user_already_has_assets"
            assert body["user_assets_created"] == 0
            assert body["transactions_created"] == 0
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_sample_seed_service, None)

    async def test_seed_false_시_심볼_카운트도_0이다(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=SampleSeedService)
        mock_service.seed_for_user.return_value = SampleSeedResponse(
            seeded=False,
            reason="user_already_has_assets",
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_sample_seed_service] = lambda: mock_service

        try:
            response = await async_client.post("/api/sample/seed")
            body = response.json()
            assert body["symbols_created"] == 0
            assert body["symbols_reused"] == 0
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_sample_seed_service, None)

    async def test_기존_심볼_재사용_시_symbols_reused가_채워진다(
        self, async_client: AsyncClient
    ) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=SampleSeedService)
        mock_service.seed_for_user.return_value = SampleSeedResponse(
            seeded=True,
            user_assets_created=5,
            transactions_created=14,
            symbols_created=0,
            symbols_reused=5,
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_sample_seed_service] = lambda: mock_service

        try:
            response = await async_client.post("/api/sample/seed")
            body = response.json()
            assert body["symbols_reused"] == 5
            assert body["symbols_created"] == 0
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_sample_seed_service, None)
