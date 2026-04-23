"""Unit tests for AuthService — uses AsyncMock to isolate from DB."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.exceptions import ConflictError, UnauthorizedError
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import UserCreate, UserLogin
from app.services.auth import AuthService


def _make_user(
    *,
    user_id: int = 1,
    email: str = "test@example.com",
    password: str = "Secur3Pass",
) -> User:
    """Build a transient User ORM instance for testing without a real DB session."""
    now = datetime.now(UTC)
    user = User(email=email, password_hash=hash_password(password))
    user.id = user_id
    user.created_at = now
    user.updated_at = now
    return user


def _make_service(repo: UserRepository) -> AuthService:
    return AuthService(repo)


class TestAuthServiceRegister:
    async def test_신규_이메일이면_사용자를_생성한다(self) -> None:
        mock_session = AsyncMock(spec=AsyncSession)
        repo = AsyncMock(spec=UserRepository)
        repo.get_by_email.return_value = None
        new_user = _make_user(user_id=1, email="new@example.com")
        repo.create.return_value = new_user

        service = _make_service(repo)
        data = UserCreate(email="new@example.com", password="Secur3Pass")
        result = await service.register(mock_session, data)

        assert result.email == "new@example.com"
        repo.get_by_email.assert_awaited_once_with("new@example.com")
        repo.create.assert_awaited_once()

    async def test_이미_등록된_이메일이면_ConflictError를_던진다(self) -> None:
        mock_session = AsyncMock(spec=AsyncSession)
        repo = AsyncMock(spec=UserRepository)
        repo.get_by_email.return_value = _make_user(email="dup@example.com")

        service = _make_service(repo)
        data = UserCreate(email="dup@example.com", password="Secur3Pass")

        with pytest.raises(ConflictError):
            await service.register(mock_session, data)

        repo.create.assert_not_awaited()

    async def test_비밀번호는_해시되어_저장된다(self) -> None:
        mock_session = AsyncMock(spec=AsyncSession)
        repo = AsyncMock(spec=UserRepository)
        repo.get_by_email.return_value = None
        captured_hash: list[str] = []

        async def capture_create(email: str, password_hash: str) -> User:
            captured_hash.append(password_hash)
            return _make_user(email=email, password="Secur3Pass")

        repo.create.side_effect = capture_create

        service = _make_service(repo)
        data = UserCreate(email="hash@example.com", password="Secur3Pass")
        await service.register(mock_session, data)

        assert len(captured_hash) == 1
        assert captured_hash[0] != "Secur3Pass"  # plain text must NOT be stored


class TestAuthServiceAuthenticate:
    async def test_올바른_자격증명이면_사용자를_반환한다(self) -> None:
        mock_session = AsyncMock(spec=AsyncSession)
        repo = AsyncMock(spec=UserRepository)
        user = _make_user(email="auth@example.com", password="Secur3Pass")
        repo.get_by_email.return_value = user

        service = _make_service(repo)
        data = UserLogin(email="auth@example.com", password="Secur3Pass")
        result = await service.authenticate(mock_session, data)

        assert result.email == "auth@example.com"

    async def test_이메일이_없으면_UnauthorizedError를_던진다(self) -> None:
        mock_session = AsyncMock(spec=AsyncSession)
        repo = AsyncMock(spec=UserRepository)
        repo.get_by_email.return_value = None

        service = _make_service(repo)
        data = UserLogin(email="ghost@example.com", password="Secur3Pass")

        with pytest.raises(UnauthorizedError):
            await service.authenticate(mock_session, data)

    async def test_비밀번호가_틀리면_UnauthorizedError를_던진다(self) -> None:
        mock_session = AsyncMock(spec=AsyncSession)
        repo = AsyncMock(spec=UserRepository)
        user = _make_user(email="pw@example.com", password="Secur3Pass")
        repo.get_by_email.return_value = user

        service = _make_service(repo)
        data = UserLogin(email="pw@example.com", password="WrongPass1")

        with pytest.raises(UnauthorizedError):
            await service.authenticate(mock_session, data)


class TestAuthServiceGetUserFromToken:
    async def test_유효한_토큰이면_사용자를_반환한다(self) -> None:
        mock_session = AsyncMock(spec=AsyncSession)
        repo = AsyncMock(spec=UserRepository)
        user = _make_user(user_id=42, email="token@example.com")
        repo.get_by_id.return_value = user

        service = _make_service(repo)
        token = create_access_token(subject=42)
        result = await service.get_user_from_token(mock_session, token)

        assert result.id == 42
        repo.get_by_id.assert_awaited_once_with(42)

    async def test_잘못된_토큰이면_UnauthorizedError를_던진다(self) -> None:
        mock_session = AsyncMock(spec=AsyncSession)
        repo = AsyncMock(spec=UserRepository)

        service = _make_service(repo)

        with pytest.raises(UnauthorizedError):
            await service.get_user_from_token(mock_session, "not.a.valid.jwt")

    async def test_토큰의_사용자가_없으면_UnauthorizedError를_던진다(self) -> None:
        mock_session = AsyncMock(spec=AsyncSession)
        repo = AsyncMock(spec=UserRepository)
        repo.get_by_id.return_value = None

        service = _make_service(repo)
        token = create_access_token(subject=999)

        with pytest.raises(UnauthorizedError):
            await service.get_user_from_token(mock_session, token)
