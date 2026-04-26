"""Integration tests for auth router — password-only single-owner login."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_auth_service, get_current_user
from app.exceptions import OwnerPasswordNotConfiguredError, TooManyAttemptsError, UnauthorizedError
from app.main import app
from app.models.user import User
from app.services.auth import AuthService


def _make_user(
    *,
    user_id: int = 1,
    email: str = "owner+local-1@assetlog.local",
) -> User:
    now = datetime.now(UTC)
    user = User(email=email, password_hash="!disabled")
    user.id = user_id
    user.created_at = now
    user.updated_at = now
    return user


# ---------------------------------------------------------------------------
# POST /api/auth/signup — removed; must return 404 or 405
# ---------------------------------------------------------------------------


class TestSignupRemoved:
    async def test_signup_엔드포인트는_존재하지_않는다(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/auth/signup",
            json={"email": "user@example.com", "password": "TestPass1"},
        )
        assert response.status_code in (404, 405)


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


class TestLogin:
    async def test_올바른_비밀번호이면_200과_쿠키를_반환한다(
        self, async_client: AsyncClient
    ) -> None:
        owner = _make_user(user_id=1)
        mock_service = AsyncMock(spec=AuthService)
        mock_service.authenticate.return_value = owner
        app.dependency_overrides[get_auth_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/auth/login",
                json={"password": "correct-password"},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["id"] == 1
            assert "access_token" in response.cookies
        finally:
            app.dependency_overrides.pop(get_auth_service, None)

    async def test_잘못된_비밀번호이면_401을_반환한다(self, async_client: AsyncClient) -> None:
        mock_service = AsyncMock(spec=AuthService)
        mock_service.authenticate.side_effect = UnauthorizedError("Invalid password")
        app.dependency_overrides[get_auth_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/auth/login",
                json={"password": "wrong"},
            )
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid password"
        finally:
            app.dependency_overrides.pop(get_auth_service, None)

    async def test_rate_limit_초과이면_429와_Retry_After_헤더를_반환한다(
        self, async_client: AsyncClient
    ) -> None:
        mock_service = AsyncMock(spec=AuthService)
        mock_service.authenticate.side_effect = TooManyAttemptsError(300)
        app.dependency_overrides[get_auth_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/auth/login",
                json={"password": "anything"},
            )
            assert response.status_code == 429
            assert "Retry-After" in response.headers
            assert response.headers["Retry-After"] == "300"
            assert "300 seconds" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_auth_service, None)

    async def test_비밀번호_미설정이면_503을_반환한다(self, async_client: AsyncClient) -> None:
        mock_service = AsyncMock(spec=AuthService)
        mock_service.authenticate.side_effect = OwnerPasswordNotConfiguredError()
        app.dependency_overrides[get_auth_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/auth/login",
                json={"password": "anything"},
            )
            assert response.status_code == 503
            assert "not configured" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_auth_service, None)

    async def test_글로벌_rate_limit_초과이면_429를_반환한다(  # ADDED
        self, async_client: AsyncClient
    ) -> None:
        """Global IP-rotation defense also returns 429 with Retry-After."""
        mock_service = AsyncMock(spec=AuthService)
        mock_service.authenticate.side_effect = TooManyAttemptsError(60)
        app.dependency_overrides[get_auth_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/auth/login",
                json={"password": "anything"},
            )
            assert response.status_code == 429
            assert "Retry-After" in response.headers
            assert response.headers["Retry-After"] == "60"
        finally:
            app.dependency_overrides.pop(get_auth_service, None)

    async def test_비밀번호_빈_문자열이면_422를_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/auth/login",
            json={"password": ""},
        )
        assert response.status_code == 422

    async def test_email_필드를_보내면_무시된다(self, async_client: AsyncClient) -> None:
        """Extra fields are ignored — Pydantic extra='ignore' default."""
        owner = _make_user(user_id=1)
        mock_service = AsyncMock(spec=AuthService)
        mock_service.authenticate.return_value = owner
        app.dependency_overrides[get_auth_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/auth/login",
                json={"email": "ignored@example.com", "password": "correct-password"},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_auth_service, None)


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------


class TestLogout:
    async def test_로그아웃하면_204와_쿠키_삭제를_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.post("/api/auth/logout")

        assert response.status_code == 204
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token" in set_cookie


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------


class TestMe:
    async def test_쿠키로_인증하면_사용자_정보를_반환한다(self, async_client: AsyncClient) -> None:
        user = _make_user(user_id=1)
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.get("/api/auth/me")
            assert response.status_code == 200
            body = response.json()
            assert body["id"] == 1
            assert body["email"] == "owner+local-1@assetlog.local"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_인증_없이_접근하면_401을_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/auth/me")
        assert response.status_code == 401
