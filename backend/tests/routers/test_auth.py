"""Integration tests for auth router — uses in-memory SQLite via conftest fixtures."""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient

from app.core.deps import get_auth_service, get_current_user
from app.core.security import create_access_token
from app.exceptions import ConflictError, UnauthorizedError
from app.main import app
from app.models.user import User
from app.services.auth import AuthService


def _make_user(
    *,
    user_id: int = 1,
    email: str = "test@example.com",
) -> User:
    now = datetime.now(UTC)
    user = User(email=email, password_hash="hashed")
    user.id = user_id
    user.created_at = now
    user.updated_at = now
    return user


# ---------------------------------------------------------------------------
# POST /api/auth/signup
# ---------------------------------------------------------------------------


class TestSignup:
    async def test_신규_가입이면_201과_쿠키를_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/auth/signup",
            json={"email": "newuser@example.com", "password": "Secur3Pass"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "newuser@example.com"
        assert "id" in body
        assert "access_token" in response.cookies

    async def test_이미_등록된_이메일이면_409를_반환한다(self, async_client: AsyncClient) -> None:
        from unittest.mock import AsyncMock

        mock_service = AsyncMock(spec=AuthService)
        mock_service.register.side_effect = ConflictError("already exists")
        app.dependency_overrides[get_auth_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/auth/signup",
                json={"email": "dup@example.com", "password": "Secur3Pass"},
            )
            assert response.status_code == 409
        finally:
            app.dependency_overrides.pop(get_auth_service, None)

    async def test_짧은_비밀번호이면_422를_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/auth/signup",
            json={"email": "short@example.com", "password": "abc1"},
        )
        assert response.status_code == 422

    async def test_숫자없는_비밀번호이면_422를_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/auth/signup",
            json={"email": "nodigit@example.com", "password": "abcdefghij"},
        )
        assert response.status_code == 422

    async def test_문자없는_비밀번호이면_422를_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/auth/signup",
            json={"email": "noletter@example.com", "password": "12345678"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


class TestLogin:
    async def test_올바른_자격증명이면_200과_쿠키를_반환한다(
        self, async_client: AsyncClient
    ) -> None:
        # First register the user
        await async_client.post(
            "/api/auth/signup",
            json={"email": "loginuser@example.com", "password": "Secur3Pass"},
        )

        response = await async_client.post(
            "/api/auth/login",
            json={"email": "loginuser@example.com", "password": "Secur3Pass"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "loginuser@example.com"
        assert "access_token" in response.cookies

    async def test_잘못된_비밀번호이면_401을_반환한다(self, async_client: AsyncClient) -> None:
        from unittest.mock import AsyncMock

        mock_service = AsyncMock(spec=AuthService)
        mock_service.authenticate.side_effect = UnauthorizedError("Invalid credentials")
        app.dependency_overrides[get_auth_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/auth/login",
                json={"email": "someone@example.com", "password": "WrongPass1"},
            )
            assert response.status_code == 401
        finally:
            app.dependency_overrides.pop(get_auth_service, None)


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------


class TestLogout:
    async def test_로그아웃하면_204와_쿠키_삭제를_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.post("/api/auth/logout")

        assert response.status_code == 204
        # The Set-Cookie header should clear the cookie
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token" in set_cookie


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------


class TestMe:
    async def test_쿠키로_인증하면_사용자_정보를_반환한다(self, async_client: AsyncClient) -> None:
        user = _make_user(user_id=10, email="me@example.com")
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.get("/api/auth/me")
            assert response.status_code == 200
            body = response.json()
            assert body["id"] == 10
            assert body["email"] == "me@example.com"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_인증_없이_접근하면_401을_반환한다(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/auth/me")
        assert response.status_code == 401

    async def test_Bearer_헤더_fallback으로_인증된다(self, async_client: AsyncClient) -> None:
        """Verify Authorization: Bearer header works as a token fallback."""
        # Register a user first to get a real user in the DB
        signup_resp = await async_client.post(
            "/api/auth/signup",
            json={"email": "bearer@example.com", "password": "Secur3Pass"},
        )
        assert signup_resp.status_code == 201
        user_id = signup_resp.json()["id"]

        token = create_access_token(subject=user_id)

        # Call /me with Bearer header (no cookie)
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            cookies={},
        )

        assert response.status_code == 200
        assert response.json()["id"] == user_id
