"""DB-backed per-IP and global login rate limiter with progressive backoff.

Replaces the previous in-memory dict implementation.  All state is persisted
in the ``login_attempts`` table so that limits survive server restarts and
work correctly across multiple application instances.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.exceptions import TooManyAttemptsError
from app.repositories.login_attempt import LoginAttemptRepository

logger = logging.getLogger(__name__)


def _utc_now_naive() -> datetime:
    """Return the current UTC time as a naive datetime (no tzinfo).

    The ``login_attempts.attempted_at`` column uses DATETIME (without timezone)
    so all comparisons must use naive UTC datetimes.
    """
    return datetime.now(UTC).replace(tzinfo=None)


class LoginRateLimiter:
    """Per-IP and global login attempt rate limiter backed by the DB.

    Two independent limits are enforced on every ``check()`` call:

    **Per-IP limit** — within ``per_ip_window_seconds``, if a single IP has
    ``>= per_ip_max`` failures the request is blocked.  The block duration
    grows exponentially (progressive backoff) as additional failures accumulate
    beyond the threshold.

    **Global limit** — within ``global_window_seconds``, if the total failure
    count across ALL IPs reaches ``>= global_max`` the request is blocked for
    ``global_window_seconds``.  This defends against distributed IP-rotation
    attacks where no single IP hits its per-IP threshold.

    Args:
        repo: Repository used to record and query login attempts.
        per_ip_max: Max failures per IP before lockout (default 5).
        global_max: Max total failures across all IPs before global lockout (default 50).
        per_ip_window_seconds: Lookback window for per-IP failures (default 600).
        global_window_seconds: Lookback window for global failures (default 60).
    """

    def __init__(
        self,
        repo: LoginAttemptRepository,
        per_ip_max: int = 5,
        global_max: int = 50,
        per_ip_window_seconds: int = 600,
        global_window_seconds: int = 60,
    ) -> None:
        self._repo = repo
        self._per_ip_max = per_ip_max
        self._global_max = global_max
        self._per_ip_window = per_ip_window_seconds
        self._global_window = global_window_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def check(self, ip: str) -> None:
        """Raise TooManyAttemptsError if any rate limit is exceeded.

        Checks are ordered: per-IP first (with backoff), then global.

        Args:
            ip: Client IP address string.

        Raises:
            TooManyAttemptsError: If either the per-IP or global limit is exceeded.
                The ``retry_after_seconds`` attribute indicates how long to wait.
        """
        now = _utc_now_naive()

        # --- Per-IP check ---------------------------------------------------
        per_ip_since = now - timedelta(seconds=self._per_ip_window)
        failures = await self._repo.count_failures_since(ip, per_ip_since)
        if failures >= self._per_ip_max:
            excess = failures - self._per_ip_max
            # Progressive backoff: double the base window for every 5 excess failures
            # cap at 64× (per_ip_window × 64) or 1 hour, whichever is smaller.
            multiplier = min(2 ** (excess // 5), 64)
            retry_after = min(self._per_ip_window * multiplier, 3600)
            logger.warning(
                "Per-IP rate limit exceeded: ip=%s failures=%d retry_after=%d",
                ip,
                failures,
                retry_after,
            )
            raise TooManyAttemptsError(retry_after)

        # --- Global check ---------------------------------------------------
        global_since = now - timedelta(seconds=self._global_window)
        global_failures = await self._repo.count_failures_since(None, global_since)
        if global_failures >= self._global_max:
            logger.warning(
                "Global rate limit exceeded: total_failures=%d retry_after=%d",
                global_failures,
                self._global_window,
            )
            raise TooManyAttemptsError(self._global_window)

    async def record_failure(self, ip: str, when: datetime | None = None) -> None:  # MODIFIED
        """Record a failed login attempt for the given IP.

        Args:
            ip: Client IP address string.
            when: UTC-naive timestamp of the attempt (defaults to now).
        """
        ts = when.replace(tzinfo=None) if when is not None else _utc_now_naive()
        await self._repo.record(ip=ip, success=False, attempted_at=ts)

    async def record_success(self, ip: str, when: datetime | None = None) -> None:  # MODIFIED
        """Record a successful login for the given IP.

        The success record is stored for audit purposes but does not affect
        failure counts — ``count_failures_since`` only counts ``success=False``
        rows, so the per-IP lockout window expires naturally once all failure
        rows fall outside the window.

        Args:
            ip: Client IP address string.
            when: UTC-naive timestamp of the attempt (defaults to now).
        """
        ts = when.replace(tzinfo=None) if when is not None else _utc_now_naive()
        await self._repo.record(ip=ip, success=True, attempted_at=ts)
