"""TargetAllocation repository — single-owner async access."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.target_allocation import TargetAllocation

logger = logging.getLogger(__name__)


class TargetAllocationRepository:
    """Async CRUD operations for the TargetAllocation model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> Sequence[TargetAllocation]:
        """Return all target allocation rows ordered by asset_type."""
        stmt = select(TargetAllocation).order_by(TargetAllocation.asset_type)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def replace_all(
        self,
        entries: list[tuple[str, Decimal]],
    ) -> Sequence[TargetAllocation]:
        """Atomically replace the entire target allocation set.

        Deletes all existing rows then inserts the provided ``entries``.
        Commit is handled by the caller via Depends(get_db_session).
        """
        await self._session.execute(delete(TargetAllocation))
        for asset_type, target_pct in entries:
            self._session.add(TargetAllocation(asset_type=asset_type, target_pct=target_pct))
        await self._session.flush()
        logger.info(
            "target_allocations replaced",
            extra={"event": "target_alloc_replace", "count": len(entries)},
        )
        return await self.list_all()
