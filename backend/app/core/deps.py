"""FastAPI dependency providers — DI wiring for repositories, services, and auth."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db_session
from app.exceptions import UnauthorizedError
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.auth import AuthService

# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

# ---------------------------------------------------------------------------
# Repository factories
# ---------------------------------------------------------------------------


def get_user_repository(session: DbSession) -> UserRepository:
    """Inject a UserRepository bound to the current request session."""
    return UserRepository(session)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]

# ---------------------------------------------------------------------------
# Service factories
# ---------------------------------------------------------------------------


def get_auth_service(repo: UserRepositoryDep) -> AuthService:
    """Inject an AuthService bound to the current request session."""
    return AuthService(repo)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

# ---------------------------------------------------------------------------
# Current-user guard
# ---------------------------------------------------------------------------


async def get_current_user(
    request: Request,
    session: DbSession,
    auth_service: AuthServiceDep,
) -> User:
    """Resolve the authenticated user from cookie or Bearer header.

    Priority:
    1. ``access_token`` httpOnly cookie
    2. ``Authorization: Bearer <token>`` header

    Raises:
        UnauthorizedError: If no token is present or the token is invalid.
    """
    token: str | None = request.cookies.get("access_token")

    if token is None:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer ") :]

    if token is None:
        raise UnauthorizedError("No authentication token provided.")

    return await auth_service.get_user_from_token(session, token)


CurrentUser = Annotated[User, Depends(get_current_user)]
