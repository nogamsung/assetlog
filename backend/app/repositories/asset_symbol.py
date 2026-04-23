"""AssetSymbol repository — pure data access, no business logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.asset_type import AssetType
from app.models.asset_symbol import AssetSymbol


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
