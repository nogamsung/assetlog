"""PricePoint repository — append-only price history storage."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.price_refresh import PriceQuote
from app.models.price_point import PricePoint

logger = logging.getLogger("app.repositories.price_point")


class PricePointRepository:
    """Write-only repository for price snapshot records.

    All inserts are append-only — PricePoint rows are never updated or
    deleted by this repository.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_insert(self, quotes: Sequence[PriceQuote]) -> int:
        """Insert one PricePoint row per quote.

        Uses a single bulk INSERT for efficiency.

        Args:
            quotes: Successfully fetched price quotes to persist.

        Returns:
            Number of rows inserted.
        """
        if not quotes:
            return 0

        records = [
            {
                "asset_symbol_id": q.ref.asset_symbol_id,
                "price": q.price,
                "currency": q.currency,
                "fetched_at": q.fetched_at,
            }
            for q in quotes
        ]

        await self._session.execute(insert(PricePoint), records)
        logger.debug(
            "bulk_insert: inserted %d price_point rows",
            len(records),
            extra={"event": "price_point_bulk_insert", "count": len(records)},
        )
        return len(records)
