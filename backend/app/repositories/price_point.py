"""PricePoint repository — one row per (asset_symbol_id, calendar day)."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.price_refresh import PriceQuote
from app.models.price_point import PricePoint
from app.repositories._dialect import get_dialect_name

logger = logging.getLogger("app.repositories.price_point")


class PricePointRepository:
    """Persist price snapshots — daily upsert keyed on (symbol, fetched_date).

    The 10-minute refresh scheduler calls into this repo every tick; the
    underlying UNIQUE index ``(asset_symbol_id, fetched_date)`` collapses
    those into a single per-symbol row per day so the table doesn't
    balloon. The latest tick of the day wins (``price`` + ``fetched_at``
    get overwritten on subsequent calls).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_insert(self, quotes: Sequence[PriceQuote]) -> int:
        """Upsert one PricePoint row per quote, keyed on (symbol, day).

        Args:
            quotes: Successfully fetched price quotes to persist.

        Returns:
            Number of rows the DB reports as written. MySQL reports 2 per
            updated row (1 delete + 1 insert), so this is an upper bound,
            not an exact count.
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

        dialect = get_dialect_name(self._session)
        if dialect == "mysql":
            # Daily upsert — matches the UNIQUE (asset_symbol_id, fetched_date)
            # index added by alembic a1c8b3e64d92.
            stmt = text(
                "INSERT INTO price_points "
                "(asset_symbol_id, price, currency, fetched_at) VALUES "
                "(:asset_symbol_id, :price, :currency, :fetched_at) "
                "ON DUPLICATE KEY UPDATE "
                "price = VALUES(price), fetched_at = VALUES(fetched_at)"
            )
            for r in records:
                await self._session.execute(stmt, r)
        else:
            # SQLite fallback (tests) — no generated column; the test
            # fixture rolls back the transaction so duplicates don't
            # leak between cases.
            await self._session.execute(insert(PricePoint), records)

        logger.debug(
            "bulk_insert: upserted %d price_point rows",
            len(records),
            extra={"event": "price_point_bulk_upsert", "count": len(records)},
        )
        return len(records)
