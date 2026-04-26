"""Tests for SecurityHeadersMiddleware — verifies response headers are injected."""

from __future__ import annotations

from unittest.mock import patch

from httpx import AsyncClient

from app.core.config import Settings, get_settings


class TestSecurityHeadersPresent:
    """All security headers except HSTS must appear on every response."""

    async def test_x_content_type_options_헤더가_있다(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/health")
        assert response.headers.get("x-content-type-options") == "nosniff"

    async def test_x_frame_options_헤더가_있다(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/health")
        assert response.headers.get("x-frame-options") == "DENY"

    async def test_referrer_policy_헤더가_있다(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/health")
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    async def test_permissions_policy_헤더가_있다(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/health")
        assert (
            response.headers.get("permissions-policy") == "camera=(), microphone=(), geolocation=()"
        )

    async def test_POST_엔드포인트에도_보안_헤더가_있다(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/auth/login",
            json={"password": "anything"},
        )
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"


class TestHSTSHeader:
    """HSTS is only added when cookie_secure=True."""

    async def test_cookie_secure_False이면_HSTS_헤더_없음(self, async_client: AsyncClient) -> None:
        """Default test config has cookie_secure=False — HSTS must be absent."""
        response = await async_client.get("/health")
        assert "strict-transport-security" not in response.headers

    async def test_cookie_secure_True이면_HSTS_헤더_있음(self, async_client: AsyncClient) -> None:
        """When cookie_secure=True, HSTS must be present."""
        from app.main import app  # noqa: PLC0415

        def _secure_settings() -> Settings:
            return Settings(
                database_url="sqlite+aiosqlite:///:memory:",
                jwt_secret_key="test-secret",
                cookie_secure=True,
            )

        app.dependency_overrides[get_settings] = _secure_settings

        # Also patch the module-level settings reference used by the middleware
        secure_settings = _secure_settings()
        try:
            with patch("app.main.settings", secure_settings):
                response = await async_client.get("/health")
            assert response.headers.get("strict-transport-security") == (
                "max-age=31536000; includeSubDomains"
            )
        finally:
            app.dependency_overrides.pop(get_settings, None)
