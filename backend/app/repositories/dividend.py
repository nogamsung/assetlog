"""Dividend repository — append-only insert + filter queries."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.dividend import DividendQuote, DividendSource
from app.models.dividend import Dividend

logger = logging.getLogger(__name__)


class DividendRepository:
    """Async DB access for the dividends table.

    Insert is dedup-by-(asset_symbol_id, ex_date) — uses a pre-existence
    check rather than catching IntegrityError to keep transaction state
    clean across SQLite/MySQL (same approach as FxRateSnapshot).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_quotes(
        self,
        asset_symbol_id: int,
        quotes: list[DividendQuote],
        source: DividendSource,
    ) -> int:
        """Insert *quotes* for *asset_symbol_id*, skipping duplicates.

        Returns:
            Number of newly inserted rows.
        """
        if not quotes:
            return 0

        existing_stmt = select(Dividend.ex_date).where(
            Dividend.asset_symbol_id == asset_symbol_id,
        )
        existing_dates = set((await self._session.execute(existing_stmt)).scalars().all())

        inserted = 0
        for quote in quotes:
            if quote.ex_date in existing_dates:
                continue
            self._session.add(
                Dividend(
                    asset_symbol_id=asset_symbol_id,
                    ex_date=quote.ex_date,
                    amount=quote.amount,
                    currency=quote.currency,
                    source=source,
                )
            )
            existing_dates.add(quote.ex_date)
            inserted += 1

        if inserted > 0:
            await self._session.flush()
            logger.debug(
                "dividend_repo inserted",
                extra={
                    "event": "dividend_insert",
                    "asset_symbol_id": asset_symbol_id,
                    "count": inserted,
                },
            )
        return inserted

    async def list_filtered(
        self,
        *,
        asset_symbol_ids: list[int] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Dividend]:
        """Return dividends filtered by symbol and date range, newest first."""
        stmt = select(Dividend)
        if asset_symbol_ids is not None:
            if not asset_symbol_ids:
                return []
            stmt = stmt.where(Dividend.asset_symbol_id.in_(asset_symbol_ids))
        if date_from is not None:
            stmt = stmt.where(Dividend.ex_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Dividend.ex_date <= date_to)
        stmt = stmt.order_by(Dividend.ex_date.desc(), Dividend.id.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def sum_by_symbol(
        self,
        asset_symbol_ids: list[int] | None = None,
    ) -> dict[int, Decimal]:
        """Return cumulative dividend amount per asset_symbol_id."""
        stmt = select(
            Dividend.asset_symbol_id,
            func.sum(Dividend.amount).label("total"),
        ).group_by(Dividend.asset_symbol_id)
        if asset_symbol_ids is not None:
            if not asset_symbol_ids:
                return {}
            stmt = stmt.where(Dividend.asset_symbol_id.in_(asset_symbol_ids))
        rows = (await self._session.execute(stmt)).all()
        return {int(row[0]): Decimal(str(row[1])) for row in rows}
