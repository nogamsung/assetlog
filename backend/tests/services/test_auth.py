"""Unit tests for AuthService — single-owner password-only auth."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.core.principal import OwnerPrincipal
from app.core.security import create_access_token, hash_password
from app.exceptions import OwnerPasswordNotConfiguredError, TooManyAttemptsError, UnauthorizedError
from app.repositories.login_attempt import LoginAttemptRepository
from app.services.auth import AuthService
from app.services.login_rate_limiter import LoginRateLimiter


def _make_principal(user_id: int = 1) -> OwnerPrincipal:
    """Build an OwnerPrincipal instance for testing."""
    return OwnerPrincipal(id=user_id)


def _make_settings(pw_hash: str | None = None) -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        jwt_secret_key="test-secret",
        app_password_hash=pw_hash,
        login_max_attempts=5,
        login_lockout_seconds=600,
        login_global_max_attempts=50,  # ADDED
        login_global_window_seconds=60,  # ADDED
    )


def _make_limiter_with_mock_repo(
    *,
    ip_failures: int = 0,
    global_failures: int = 0,
    per_ip_max: int = 5,
    global_max: int = 50,
    per_ip_window: int = 600,
    global_window: int = 60,
) -> LoginRateLimiter:
    """Build a LoginRateLimiter backed by a mocked repo with preset failure counts."""
    repo = AsyncMock(spec=LoginAttemptRepository)

    async def _count(ip: str | None, since: datetime) -> int:  # type: ignore[misc]
        return global_failures if ip is None else ip_failures

    repo.count_failures_since.side_effect = _count
    return LoginRateLimiter(
        repo=repo,
        per_ip_max=per_ip_max,
        global_max=global_max,
        per_ip_window_seconds=per_ip_window,
        global_window_seconds=global_window,
    )


def _make_service(
    *,
    pw: str | None = "TestPass1",
    limiter: LoginRateLimiter | None = None,
) -> AuthService:
    pw_hash = hash_password(pw) if pw else None
    settings = _make_settings(pw_hash=pw_hash)
    if limiter is None:
        limiter = _make_limiter_with_mock_repo()  # DB-backed mock
    return AuthService(rate_limiter=limiter, settings=settings)


class TestAuthServiceAuthenticate:
    async def test_올바른_비밀번호이면_owner_principal를_반환한다(self) -> None:
        service = _make_service(pw="TestPass1")
        result = await service.authenticate("TestPass1", "1.2.3.4")

        assert result.id == 1
        assert isinstance(result, OwnerPrincipal)

    async def test_잘못된_비밀번호이면_UnauthorizedError를_던진다(self) -> None:
        service = _make_service(pw="TestPass1")

        with pytest.raises(UnauthorizedError) as exc_info:
            await service.authenticate("WrongPass", "1.2.3.4")

        assert "Invalid password" in str(exc_info.value)

    async def test_비밀번호_미설정이면_OwnerPasswordNotConfiguredError를_던진다(self) -> None:
        settings = _make_settings(pw_hash=None)
        limiter = _make_limiter_with_mock_repo()
        service = AuthService(rate_limiter=limiter, settings=settings)

        with pytest.raises(OwnerPasswordNotConfiguredError):
            await service.authenticate("anything", "1.2.3.4")

    async def test_빈_문자열_해시이면_OwnerPasswordNotConfiguredError를_던진다(self) -> None:
        settings = _make_settings(pw_hash="")
        limiter = _make_limiter_with_mock_repo()
        service = AuthService(rate_limiter=limiter, settings=settings)

        with pytest.raises(OwnerPasswordNotConfiguredError):
            await service.authenticate("anything", "1.2.3.4")

    async def test_5회_실패_후_TooManyAttemptsError를_던진다(self) -> None:
        # After 5 failures the limiter returns 5 as failure count → blocks
        limiter = _make_limiter_with_mock_repo(ip_failures=5, per_ip_max=5)
        service = _make_service(pw="TestPass1", limiter=limiter)

        with pytest.raises(TooManyAttemptsError):
            await service.authenticate("WrongPass", "9.9.9.9")

    async def test_rate_limit_check가_먼저_호출된다(self) -> None:
        """Verify check() is called before password verification."""
        mock_limiter = AsyncMock(spec=LoginRateLimiter)
        mock_limiter.check.side_effect = TooManyAttemptsError(300)

        settings = _make_settings(pw_hash=hash_password("TestPass1"))
        service = AuthService(rate_limiter=mock_limiter, settings=settings)

        with pytest.raises(TooManyAttemptsError):
            await service.authenticate("TestPass1", "blocked-ip")

        mock_limiter.check.assert_awaited_once_with("blocked-ip")

    async def test_성공_시_record_success가_호출된다(self) -> None:
        mock_limiter = AsyncMock(spec=LoginRateLimiter)
        settings = _make_settings(pw_hash=hash_password("TestPass1"))
        service = AuthService(rate_limiter=mock_limiter, settings=settings)

        await service.authenticate("TestPass1", "5.5.5.5")

        mock_limiter.record_success.assert_awaited_once_with("5.5.5.5")

    async def test_실패_시_record_failure가_호출된다(self) -> None:
        mock_limiter = AsyncMock(spec=LoginRateLimiter)
        settings = _make_settings(pw_hash=hash_password("TestPass1"))
        service = AuthService(rate_limiter=mock_limiter, settings=settings)

        with pytest.raises(UnauthorizedError):
            await service.authenticate("WrongPass", "6.6.6.6")

        mock_limiter.record_failure.assert_awaited_once_with("6.6.6.6")

    async def test_올바른_비밀번호_및_owner_principal이_반환된다(self) -> None:
        service = _make_service(pw="TestPass1")
        result = await service.authenticate("TestPass1", "1.2.3.4")

        assert result.id == 1
        assert isinstance(result, OwnerPrincipal)


class TestAuthServiceGetPrincipalFromToken:
    async def test_유효한_토큰이면_principal을_반환한다(self) -> None:
        service = _make_service()
        token = create_access_token(subject=1)
        result = await service.get_principal_from_token(token)

        assert result.id == 1
        assert isinstance(result, OwnerPrincipal)

    async def test_잘못된_토큰이면_UnauthorizedError를_던진다(self) -> None:
        service = _make_service()

        with pytest.raises(UnauthorizedError):
            await service.get_principal_from_token("not.a.valid.jwt")

    async def test_token_subject가_1이_아니면_UnauthorizedError를_던진다(self) -> None:
        service = _make_service()
        token = create_access_token(subject=999)

        with pytest.raises(UnauthorizedError):
            await service.get_principal_from_token(token)
