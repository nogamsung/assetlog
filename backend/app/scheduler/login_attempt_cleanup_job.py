"""APScheduler job — purge login_attempts rows older than the retention period."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("app.scheduler.login_attempt_cleanup")


async def login_attempt_cleanup_job(
    session_factory: async_sessionmaker[AsyncSession],
    retention_days: int,
) -> int:
    """Delete login_attempt records older than ``retention_days`` days.

    Runs inside a fresh DB session, commits, then closes.  Failures are
    logged and do not propagate — APScheduler retries on the next tick.

    Args:
        session_factory: Factory used to create an async DB session.
        retention_days: Rows older than this many days are deleted.

    Returns:
        Number of rows deleted (0 on complete failure).
    """
    try:
        from app.repositories.login_attempt import (  # noqa: PLC0415  # lazy import avoids circular deps
            LoginAttemptRepository,
        )

        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=retention_days)
        async with session_factory() as session:
            repo = LoginAttemptRepository(session)
            deleted = await repo.purge_older_than(cutoff)
            await session.commit()
            logger.info(
                "login_attempt_cleanup_job committed",
                extra={
                    "event": "login_attempt_cleanup_done",
                    "deleted": deleted,
                    "cutoff": cutoff.isoformat(),
                },
            )
            return deleted
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "login_attempt_cleanup_job failed: %s",
            exc,
            extra={"event": "login_attempt_cleanup_error", "error": str(exc)},
        )
        return 0
