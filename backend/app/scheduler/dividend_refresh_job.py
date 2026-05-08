"""APScheduler job wrapper for the daily dividend refresh (US + KR)."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.kr_dividends import KrDividendAdapter
from app.adapters.us_dividends import UsDividendAdapter
from app.repositories.asset_symbol import AssetSymbolRepository
from app.repositories.dividend import DividendRepository
from app.services.dividend import DividendService

logger = logging.getLogger("app.scheduler.dividend_refresh")


async def dividend_refresh_job(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """Entry point called by APScheduler on each daily cron tick.

    Creates a fresh DB session, runs both US and KR dividend refreshes,
    commits, then closes the session. Failures are logged but do not
    propagate — APScheduler will retry on the next tick.

    Args:
        session_factory: Factory used to create an async DB session.

    Returns:
        Total number of new dividend rows inserted (US + KR; 0 on complete failure).
    """
    try:
        async with session_factory() as session:
            service = DividendService(
                repo=DividendRepository(session),
                symbol_repo=AssetSymbolRepository(session),
                us_adapter=UsDividendAdapter(),
                kr_adapter=KrDividendAdapter(),
            )
            us_count = await service.refresh_us_dividends()
            kr_count = await service.refresh_kr_dividends()
            await session.commit()
            total = us_count + kr_count
            logger.info(
                "dividend_refresh_job committed",
                extra={
                    "event": "dividend_refresh_job_done",
                    "inserted_us": us_count,
                    "inserted_kr": kr_count,
                    "inserted_total": total,
                },
            )
            return total
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "dividend_refresh_job failed: %s",
            exc,
            extra={"event": "dividend_refresh_job_error", "error": str(exc)},
        )
        return 0
