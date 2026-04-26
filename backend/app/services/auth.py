"""Auth service — business logic for authentication and token validation."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import decode_access_token, verify_password
from app.exceptions import OwnerPasswordNotConfiguredError, UnauthorizedError
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.login_rate_limiter import LoginRateLimiter

logger = logging.getLogger(__name__)

_OWNER_USER_ID = 1


class AuthService:
    """Handles single-owner auth lifecycle — no FastAPI/HTTP imports allowed."""

    def __init__(
        self,
        repository: UserRepository,
        rate_limiter: LoginRateLimiter,
        settings: Settings,
    ) -> None:
        self._repo = repository
        self._limiter = rate_limiter
        self._settings = settings

    async def authenticate(
        self, session: AsyncSession, password: str, client_ip: str
    ) -> User:  # MODIFIED
        """Verify the owner password and return the owner User.

        Args:
            session: Active async database session.
            password: Raw password string submitted by the client.
            client_ip: Client IP address for rate-limit tracking.

        Returns:
            Owner User ORM instance (id=1).

        Raises:
            OwnerPasswordNotConfiguredError: If APP_PASSWORD_HASH is not set.
            TooManyAttemptsError: If the IP is currently locked out.
            UnauthorizedError: If the password does not match.
        """
        pw_hash = self._settings.app_password_hash
        if not pw_hash:
            raise OwnerPasswordNotConfiguredError()

        await self._limiter.check(client_ip)

        if not verify_password(password, pw_hash):
            await self._limiter.record_failure(
                client_ip
            )  # MODIFIED — no 'when' arg (defaults to now)
            logger.warning("Failed login attempt from ip=%s", client_ip)
            raise UnauthorizedError("Invalid password")

        await self._limiter.record_success(client_ip)  # MODIFIED — no 'when' arg (defaults to now)

        user = await self._repo.get_by_id(_OWNER_USER_ID)
        if user is None:
            raise UnauthorizedError("Owner user not initialized")
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
