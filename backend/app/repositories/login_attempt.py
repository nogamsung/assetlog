"""LoginAttempt repository — persist and query login audit records."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.login_attempt import LoginAttempt

logger = logging.getLogger(__name__)


class LoginAttemptRepository:
    """Async data access for LoginAttempt records.

    All datetimes are stored as UTC-naive (MySQL DATETIME without timezone).
    Callers must pass UTC-naive datetimes consistently.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, ip: str, success: bool, attempted_at: datetime) -> None:
        """Persist a login attempt record.

        Args:
            ip: Client IP address (up to 45 chars, IPv6-compatible).
            success: True for successful login, False for failure.
            attempted_at: UTC-naive timestamp of the attempt.
        """
        attempt = LoginAttempt(ip=ip, success=success, attempted_at=attempted_at)
        self._session.add(attempt)
        await self._session.flush()

    async def count_failures_since(self, ip: str | None, since: datetime) -> int:
        """Count failure records (success=False) within a lookback window.

        Args:
            ip: Client IP to filter on.  Pass ``None`` for a global count
                (all IPs combined — used for global rate limiting).
            since: UTC-naive lower bound (exclusive) for ``attempted_at``.

        Returns:
            Number of failure rows matching the criteria.
        """
        stmt = (
            select(func.count())
            .select_from(LoginAttempt)
            .where(
                LoginAttempt.success.is_(False),
                LoginAttempt.attempted_at >= since,
            )
        )
        if ip is not None:
            stmt = stmt.where(LoginAttempt.ip == ip)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_last_failure(self, ip: str | None, since: datetime) -> datetime | None:
        """Return the ``attempted_at`` of the most recent failure in the window.

        Args:
            ip: Client IP to filter on.  Pass ``None`` for a global query.
            since: UTC-naive lower bound for the query window.

        Returns:
            Most recent failure timestamp, or ``None`` if no failures found.
        """
        stmt = (
            select(LoginAttempt.attempted_at)
            .where(
                LoginAttempt.success.is_(False),
                LoginAttempt.attempted_at >= since,
            )
            .order_by(LoginAttempt.attempted_at.desc())
            .limit(1)
        )
        if ip is not None:
            stmt = stmt.where(LoginAttempt.ip == ip)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def purge_older_than(self, cutoff: datetime) -> int:
        """Delete all records with ``attempted_at`` older than ``cutoff``.

        Intended to be called by the cleanup scheduler job to prevent
        unbounded table growth.

        Args:
            cutoff: UTC-naive datetime; rows strictly older than this are deleted.

        Returns:
            Number of rows deleted.
        """
        stmt = delete(LoginAttempt).where(LoginAttempt.attempted_at < cutoff)
        cursor: CursorResult[tuple[()]] = await self._session.execute(stmt)  # type: ignore[assignment]  # mypy infers Result[Any]
        deleted: int = int(cursor.rowcount)
        logger.info(
            "login_attempts purged",
            extra={"event": "login_attempts_purge", "deleted": deleted},
        )
        return deleted
