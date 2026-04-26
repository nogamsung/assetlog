"""Scheduler factory — builds an AsyncIOScheduler for price refresh, FX refresh, and cleanup."""

from __future__ import annotations

from apscheduler.schedulers.asyncio import (
    AsyncIOScheduler,  # noqa: F401  # apscheduler has no stubs
)
from apscheduler.triggers.cron import CronTrigger  # noqa: F401  # apscheduler has no stubs
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters import AdapterRegistry
from app.scheduler.fx_refresh_job import fx_refresh_job
from app.scheduler.login_attempt_cleanup_job import login_attempt_cleanup_job  # ADDED
from app.scheduler.price_refresh_job import price_refresh_job


def build_scheduler(
    session_factory: async_sessionmaker[AsyncSession],
    adapters: AdapterRegistry,
    login_attempt_retention_days: int = 90,  # ADDED
) -> AsyncIOScheduler:
    """Create and configure an AsyncIOScheduler for hourly price/FX refresh and daily cleanup.

    Registers three jobs:
    - ``price_refresh_hourly``: fetches asset prices via adapter registry.
    - ``fx_refresh_hourly``: fetches ECB reference rates via Frankfurter API.
    - ``login_attempt_cleanup_daily``: purges login_attempts older than retention_days.

    Price/FX jobs fire at minute=0 every hour (Asia/Seoul timezone).
    Cleanup fires daily at 03:00 Asia/Seoul.
    The scheduler is **not started** here — call ``.start()`` inside the
    FastAPI lifespan context manager.

    Args:
        session_factory: Async sessionmaker used inside each job.
        adapters: Pre-built adapter registry created at lifespan startup.
        login_attempt_retention_days: Rows older than this many days are deleted (default 90).

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
    scheduler.add_job(
        fx_refresh_job,
        trigger=CronTrigger(minute=0),
        kwargs={"session_factory": session_factory},
        id="fx_refresh_hourly",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
        replace_existing=True,
    )
    scheduler.add_job(  # ADDED
        login_attempt_cleanup_job,
        trigger=CronTrigger(hour=3, minute=0),
        kwargs={
            "session_factory": session_factory,
            "retention_days": login_attempt_retention_days,
        },
        id="login_attempt_cleanup_daily",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
        replace_existing=True,
    )
    return scheduler
