"""APScheduler job wrapper for the hourly price refresh."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters import AdapterRegistry
from app.domain.price_refresh import RefreshResult
from app.repositories.asset_symbol import AssetSymbolRepository
from app.repositories.price_point import PricePointRepository
from app.services.price_refresh import PriceRefreshService

logger = logging.getLogger("app.scheduler.price_refresh")


async def price_refresh_job(
    session_factory: async_sessionmaker[AsyncSession],
    adapters: AdapterRegistry,
) -> RefreshResult:
    """Entry point called by APScheduler on each cron tick.

    Creates a fresh DB session, runs PriceRefreshService, commits, then
    closes the session.  The session is NOT exposed to FastAPI's DI — it
    lives entirely within this function's scope.

    Args:
        session_factory: Factory used to create an async DB session.
        adapters: Pre-built adapter registry from lifespan.

    Returns:
        RefreshResult summarising the completed refresh run.
    """
    async with session_factory() as session:
        service = PriceRefreshService(
            asset_symbol_repo=AssetSymbolRepository(session),
            price_point_repo=PricePointRepository(session),
            adapters=adapters,
        )
        result = await service.refresh_all_prices()
        await session.commit()
        logger.info(
            "price_refresh_job committed",
            extra={
                "event": "price_refresh_job_done",
                "total": result.total,
                "success": result.success,
                "failed": result.failed,
                "elapsed_ms": result.elapsed_ms,
            },
        )
        return result
