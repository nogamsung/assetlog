"""AssetSymbol repository — pure data access, no business logic."""

from __future__ import annotations

import logging  # ADDED
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, tuple_, update  # MODIFIED
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.asset_type import AssetType
from app.domain.price_refresh import SymbolRef
from app.domain.symbol_search import SymbolCandidate  # ADDED
from app.models.asset_symbol import AssetSymbol
from app.repositories._dialect import get_dialect_name  # ADDED

logger = logging.getLogger(__name__)  # ADDED


class AssetSymbolRepository:
    """Async CRUD operations for the AssetSymbol model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, asset_symbol_id: int) -> AssetSymbol | None:
        """Return an AssetSymbol by primary key, or None."""
        stmt = select(AssetSymbol).where(AssetSymbol.id == asset_symbol_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_triple(
        self,
        asset_type: AssetType,
        symbol: str,
        exchange: str,
    ) -> AssetSymbol | None:
        """Return an AssetSymbol matching the unique (asset_type, symbol, exchange), or None."""
        stmt = select(AssetSymbol).where(
            AssetSymbol.asset_type == asset_type,
            AssetSymbol.symbol == symbol,
            AssetSymbol.exchange == exchange,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        q: str | None = None,
        asset_type: AssetType | None = None,
        exchange: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[AssetSymbol]:
        """Search asset symbols with optional text / filter criteria.

        Text search uses case-insensitive LIKE on symbol and name.
        SQLite uses LIKE (case-insensitive for ASCII by default);
        MySQL/MariaDB uses LIKE (case-insensitive for utf8mb4_general_ci).
        """
        stmt = select(AssetSymbol)

        if q is not None and q.strip():
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(AssetSymbol.symbol.ilike(pattern) | AssetSymbol.name.ilike(pattern))

        if asset_type is not None:
            stmt = stmt.where(AssetSymbol.asset_type == asset_type)

        if exchange is not None and exchange.strip():
            stmt = stmt.where(AssetSymbol.exchange == exchange.strip())

        stmt = stmt.order_by(AssetSymbol.symbol).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self) -> list[AssetSymbol]:
        """Return all AssetSymbol rows ordered by symbol."""
        stmt = select(AssetSymbol).order_by(AssetSymbol.symbol)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        asset_type: AssetType,
        symbol: str,
        exchange: str,
        name: str,
        currency: str,
    ) -> AssetSymbol:
        """Persist a new AssetSymbol row and return the refreshed instance."""
        asset = AssetSymbol(
            asset_type=asset_type,
            symbol=symbol,
            exchange=exchange,
            name=name,
            currency=currency,
        )
        self._session.add(asset)
        await self._session.flush()
        await self._session.refresh(asset)
        return asset

    async def list_distinct_refresh_targets(self) -> list[SymbolRef]:
        """Return all distinct (asset_type, exchange, symbol, id) for scheduling.

        Returns every AssetSymbol row as a SymbolRef.  The scheduler fetches
        prices for all known symbols regardless of whether any user currently
        holds them — this keeps the cache warm for instant portfolio reads.

        Returns:
            List of SymbolRef, one per AssetSymbol row.
        """
        stmt = select(
            AssetSymbol.id,
            AssetSymbol.asset_type,
            AssetSymbol.symbol,
            AssetSymbol.exchange,
        ).distinct()
        rows = (await self._session.execute(stmt)).all()
        return [
            SymbolRef(
                asset_symbol_id=row.id,
                asset_type=row.asset_type,
                symbol=row.symbol,
                exchange=row.exchange,
            )
            for row in rows
        ]

    async def upsert_many(  # ADDED
        self,
        candidates: Sequence[SymbolCandidate],
        *,
        now: datetime,
    ) -> list[AssetSymbol]:
        """Insert or update-on-conflict (asset_type, symbol, exchange).

        On match: UPDATE name, currency, last_synced_at.
        On insert: set last_synced_at = now.

        Dialect-aware: MySQL uses ON DUPLICATE KEY UPDATE,
        SQLite uses ON CONFLICT DO UPDATE.

        Args:
            candidates: Symbol candidates to persist.
            now: Timestamp to write into last_synced_at.

        Returns:
            Persisted rows in input order.
        """
        if not candidates:
            return []

        dialect = get_dialect_name(self._session)

        if dialect == "mysql":
            from sqlalchemy.dialects.mysql import insert as mysql_insert  # noqa: PLC0415

            stmt = mysql_insert(AssetSymbol).values(
                [
                    {
                        "asset_type": c.asset_type,
                        "symbol": c.symbol,
                        "exchange": c.exchange,
                        "name": c.name,
                        "currency": c.currency,
                        "last_synced_at": now,
                    }
                    for c in candidates
                ]
            )
            stmt = stmt.on_duplicate_key_update(
                name=stmt.inserted.name,
                currency=stmt.inserted.currency,
                last_synced_at=stmt.inserted.last_synced_at,
            )
            await self._session.execute(stmt)
        else:
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert  # noqa: PLC0415

            stmt_sqlite = sqlite_insert(AssetSymbol).values(
                [
                    {
                        "asset_type": c.asset_type,
                        "symbol": c.symbol,
                        "exchange": c.exchange,
                        "name": c.name,
                        "currency": c.currency,
                        "last_synced_at": now,
                    }
                    for c in candidates
                ]
            )
            stmt_sqlite = stmt_sqlite.on_conflict_do_update(
                index_elements=["asset_type", "symbol", "exchange"],
                set_={
                    "name": stmt_sqlite.excluded.name,
                    "currency": stmt_sqlite.excluded.currency,
                    "last_synced_at": stmt_sqlite.excluded.last_synced_at,
                },
            )
            await self._session.execute(stmt_sqlite)

        await self._session.flush()

        # Refetch in input order to return ORM instances.
        triples = [(c.asset_type, c.symbol, c.exchange) for c in candidates]
        refetch_stmt = select(AssetSymbol).where(
            tuple_(
                AssetSymbol.asset_type,
                AssetSymbol.symbol,
                AssetSymbol.exchange,
            ).in_(triples)
        )
        rows = list((await self._session.execute(refetch_stmt)).scalars().all())

        row_map = {(r.asset_type, r.symbol, r.exchange): r for r in rows}
        result = [row_map[t] for t in triples if t in row_map]

        logger.info(
            "upsert_many: persisted %d symbols",
            len(result),
            extra={"event": "asset_symbol_upsert_many", "count": len(result)},
        )
        return result

    async def bulk_update_cache(
        self,
        rows: Sequence[tuple[int, Decimal, datetime]],
    ) -> int:
        """Update last_price and last_price_refreshed_at for multiple symbols.

        Issues one UPDATE statement per row to keep the ORM expression
        layer free from raw SQL.

        Args:
            rows: Sequence of (asset_symbol_id, last_price, refreshed_at).

        Returns:
            Number of rows updated.
        """
        updated = 0
        for asset_symbol_id, price, refreshed_at in rows:
            stmt = (
                update(AssetSymbol)
                .where(AssetSymbol.id == asset_symbol_id)
                .values(last_price=price, last_price_refreshed_at=refreshed_at)
            )
            result = await self._session.execute(stmt)
            updated += result.rowcount  # type: ignore[attr-defined]  # SQLAlchemy CursorResult
        return updated
