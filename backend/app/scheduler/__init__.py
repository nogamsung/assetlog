"""Scheduler factory — builds an APScheduler AsyncIOScheduler for price refresh."""

from __future__ import annotations

from apscheduler.schedulers.asyncio import (
    AsyncIOScheduler,  # noqa: F401  # apscheduler has no stubs
)
from apscheduler.triggers.cron import CronTrigger  # noqa: F401  # apscheduler has no stubs
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters import AdapterRegistry
from app.scheduler.price_refresh_job import price_refresh_job


def build_scheduler(
    session_factory: async_sessionmaker[AsyncSession],
    adapters: AdapterRegistry,
) -> AsyncIOScheduler:
    """Create and configure an AsyncIOScheduler for the hourly price refresh.

    The scheduler is **not started** here — call ``.start()`` inside the
    FastAPI lifespan context manager.

    Args:
        session_factory: Async sessionmaker used inside the job.
        adapters: Pre-built adapter registry created at lifespan startup.

    Returns:
        Configured (but not yet started) AsyncIOScheduler.
    """
    scheduler: AsyncIOScheduler = AsyncIOScheduler(timezone="Asia/Seoul")
    scheduler.add_job(
        price_refresh_job,
        trigger=CronTrigger(minute=0),
        kwargs={"session_factory": session_factory, "adapters": adapters},
        id="price_refresh_hourly",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
        replace_existing=True,
    )
    return scheduler
