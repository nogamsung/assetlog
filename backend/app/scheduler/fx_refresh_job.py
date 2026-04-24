"""APScheduler job wrapper for the hourly FX rate refresh."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.fx import FrankfurterAdapter
from app.repositories.fx_rate import FxRateRepository
from app.services.fx_rate import FxRateService

logger = logging.getLogger("app.scheduler.fx_refresh")


async def fx_refresh_job(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """Entry point called by APScheduler on each hourly cron tick.

    Creates a fresh DB session, runs FxRateService.refresh_all(), commits,
    then closes the session.  Failures are logged but do not propagate —
    APScheduler will retry on the next tick.

    Args:
        session_factory: Factory used to create an async DB session.

    Returns:
        Number of rate pairs upserted (0 on complete failure).
    """
    try:
        async with session_factory() as session:
            service = FxRateService(
                repo=FxRateRepository(session),
                adapter=FrankfurterAdapter(),
            )
            count = await service.refresh_all()
            await session.commit()
            logger.info(
                "fx_refresh_job committed",
                extra={"event": "fx_refresh_job_done", "upserted": count},
            )
            return count
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "fx_refresh_job failed: %s",
            exc,
            extra={"event": "fx_refresh_job_error", "error": str(exc)},
        )
        return 0
