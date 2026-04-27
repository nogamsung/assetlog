"""Auth service — business logic for authentication and token validation."""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.core.principal import OWNER_ID, OwnerPrincipal
from app.core.security import decode_access_token, verify_password
from app.exceptions import OwnerPasswordNotConfiguredError, UnauthorizedError
from app.services.login_rate_limiter import LoginRateLimiter

logger = logging.getLogger(__name__)


class AuthService:
    """Handles single-owner auth lifecycle — no FastAPI/HTTP imports allowed."""

    def __init__(
        self,
        rate_limiter: LoginRateLimiter,
        settings: Settings,
    ) -> None:
        self._limiter = rate_limiter
        self._settings = settings

    async def authenticate(self, password: str, client_ip: str) -> OwnerPrincipal:
        """Verify the owner password and return the owner principal.

        Args:
            password: Raw password string submitted by the client.
            client_ip: Client IP address for rate-limit tracking.

        Returns:
            Static OwnerPrincipal — single-owner mode has no DB row.

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
            await self._limiter.record_failure(client_ip)
            logger.warning("Failed login attempt from ip=%s", client_ip)
            raise UnauthorizedError("Invalid password")

        await self._limiter.record_success(client_ip)
        return OwnerPrincipal()

    async def get_principal_from_token(self, token: str) -> OwnerPrincipal:
        """Decode a JWT and return the owner principal.

        Args:
            token: Raw JWT string (without Bearer prefix).

        Returns:
            Static OwnerPrincipal when the token is valid.

        Raises:
            UnauthorizedError: If the token is invalid, expired, or carries an unexpected subject.
        """
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if not sub:
            raise UnauthorizedError("Token payload is missing subject claim.")

        try:
            principal_id = int(sub)
        except (ValueError, TypeError) as exc:
            raise UnauthorizedError("Token subject is not a valid principal ID.") from exc

        if principal_id != OWNER_ID:
            raise UnauthorizedError("Token does not represent the owner principal.")

        return OwnerPrincipal()
