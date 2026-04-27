"""UserAsset repository — pure data access, no business logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.asset_symbol import AssetSymbol
from app.models.user_asset import UserAsset


class UserAssetRepository:
    """Async CRUD operations for the UserAsset model.

    Single-owner mode: queries are not user-scoped.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_asset_id: int) -> UserAsset | None:
        """Return a UserAsset, eagerly loading AssetSymbol, or None."""
        stmt = (
            select(UserAsset)
            .options(selectinload(UserAsset.asset_symbol))
            .where(UserAsset.id == user_asset_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[UserAsset]:
        """Return all UserAsset rows, eagerly loading AssetSymbol."""
        stmt = (
            select(UserAsset)
            .options(selectinload(UserAsset.asset_symbol))
            .order_by(UserAsset.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_symbol(self, asset_symbol_id: int) -> UserAsset | None:
        """Return the UserAsset for a given asset symbol, or None."""
        stmt = select(UserAsset).where(UserAsset.asset_symbol_id == asset_symbol_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        asset_symbol_id: int,
        memo: str | None = None,
    ) -> UserAsset:
        """Persist a new UserAsset row and return the refreshed instance with AssetSymbol."""
        user_asset = UserAsset(
            asset_symbol_id=asset_symbol_id,
            memo=memo,
        )
        self._session.add(user_asset)
        await self._session.flush()

        loaded = await self.get_by_id(user_asset.id)
        assert loaded is not None  # just flushed — must exist
        return loaded

    async def delete_by_id(self, user_asset_id: int) -> bool:
        """Delete a UserAsset by id. Returns True if a row was deleted, False otherwise."""
        stmt = select(UserAsset).where(UserAsset.id == user_asset_id)
        result = await self._session.execute(stmt)
        user_asset = result.scalar_one_or_none()
        if user_asset is None:
            return False
        await self._session.delete(user_asset)
        await self._session.flush()
        return True

    async def get_asset_symbol(self, asset_symbol_id: int) -> AssetSymbol | None:
        """Return an AssetSymbol by PK — convenience for ownership checks."""
        stmt = select(AssetSymbol).where(AssetSymbol.id == asset_symbol_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
