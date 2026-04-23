"""Auth service — business logic for registration, authentication, and token validation."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, hash_password, verify_password
from app.exceptions import ConflictError, UnauthorizedError
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import UserCreate, UserLogin

logger = logging.getLogger(__name__)


class AuthService:
    """Handles user auth lifecycle — no FastAPI/HTTP imports allowed."""

    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    async def register(self, session: AsyncSession, data: UserCreate) -> User:
        """Create a new user account.

        Args:
            session: Active async database session.
            data: Validated registration payload.

        Returns:
            Newly created User ORM instance.

        Raises:
            ConflictError: If the email address is already registered.
        """
        existing = await self._repo.get_by_email(data.email)
        if existing is not None:
            raise ConflictError("An account with this email address already exists.")

        pw_hash = hash_password(data.password)
        user = await self._repo.create(email=data.email, password_hash=pw_hash)
        logger.info("New user registered: id=%s", user.id)
        return user

    async def authenticate(self, session: AsyncSession, data: UserLogin) -> User:
        """Verify credentials and return the authenticated User.

        Args:
            session: Active async database session.
            data: Validated login payload.

        Returns:
            Authenticated User ORM instance.

        Raises:
            UnauthorizedError: If the email is not found or the password is wrong.
        """
        user = await self._repo.get_by_email(data.email)
        if user is None or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("Invalid email or password.")
        return user

    async def get_user_from_token(self, session: AsyncSession, token: str) -> User:
        """Decode a JWT and return the corresponding User.

        Args:
            session: Active async database session.
            token: Raw JWT string (without Bearer prefix).

        Returns:
            User matching the token subject.

        Raises:
            UnauthorizedError: If the token is invalid, expired, or the user no longer exists.
        """
        payload = decode_access_token(token)  # raises UnauthorizedError on bad token
        sub = payload.get("sub")
        if not sub:
            raise UnauthorizedError("Token payload is missing subject claim.")

        try:
            user_id = int(sub)
        except (ValueError, TypeError) as exc:
            raise UnauthorizedError("Token subject is not a valid user ID.") from exc

        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("User associated with this token no longer exists.")
        return user
