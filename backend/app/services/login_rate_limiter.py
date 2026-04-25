"""In-memory per-IP login rate limiter.

Single-instance, no Redis dependency. Safe for FastAPI single-process async context.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.exceptions import TooManyAttemptsError

logger = logging.getLogger(__name__)

_INACTIVE_TTL_SECONDS = 1800  # evict entries idle for 30 min


@dataclass
class _IpState:
    failure_count: int = 0
    locked_until: datetime | None = None
    last_seen: datetime = field(default_factory=lambda: datetime.now(UTC))


class LoginRateLimiter:
    """Per-IP login attempt counter with lockout on max failures.

    Args:
        max_attempts: Number of consecutive failures before lockout.
        lockout_seconds: Seconds to lock out the IP after max_attempts failures.
    """

    def __init__(self, max_attempts: int, lockout_seconds: int) -> None:
        self._max_attempts = max_attempts
        self._lockout_seconds = lockout_seconds
        self._states: dict[str, _IpState] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def check(self, ip: str) -> None:
        """Raise TooManyAttemptsError if the IP is currently locked out.

        Args:
            ip: Client IP address string.

        Raises:
            TooManyAttemptsError: If the IP is within its lockout window.
        """
        async with self._lock:
            self._evict_expired()
            state = self._states.get(ip)
            if state is None:
                return
            now = datetime.now(UTC)
            if state.locked_until is not None and now < state.locked_until:
                retry_after = int((state.locked_until - now).total_seconds()) + 1
                raise TooManyAttemptsError(retry_after)

    async def record_failure(self, ip: str) -> None:
        """Increment the failure counter for an IP, locking it out if threshold is reached.

        Args:
            ip: Client IP address string.
        """
        async with self._lock:
            self._evict_expired()
            now = datetime.now(UTC)
            state = self._states.setdefault(ip, _IpState())
            state.failure_count += 1
            state.last_seen = now
            if state.failure_count >= self._max_attempts:
                from datetime import timedelta

                state.locked_until = now + timedelta(seconds=self._lockout_seconds)
                logger.warning(
                    "IP locked out after %d failures: ip=%s locked_until=%s",
                    state.failure_count,
                    ip,
                    state.locked_until.isoformat(),
                )

    async def record_success(self, ip: str) -> None:
        """Reset the failure counter on successful login.

        Args:
            ip: Client IP address string.
        """
        async with self._lock:
            self._states.pop(ip, None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict_expired(self) -> None:
        """Remove stale entries: expired lockouts idle longer than _INACTIVE_TTL_SECONDS."""
        now = datetime.now(UTC)
        from datetime import timedelta

        cutoff = now - timedelta(seconds=_INACTIVE_TTL_SECONDS)
        stale = [
            ip
            for ip, state in self._states.items()
            if state.last_seen < cutoff
            or (state.locked_until is not None and state.locked_until <= now)
        ]
        for ip in stale:
            del self._states[ip]
