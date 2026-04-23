"""UserAsset repository — pure data access, no business logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.asset_symbol import AssetSymbol
from app.models.user_asset import UserAsset


class UserAssetRepository:
    """Async CRUD operations for the UserAsset model.

    All queries are scoped to a specific user_id to enforce data isolation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id_for_user(self, user_asset_id: int, user_id: int) -> UserAsset | None:
        """Return a UserAsset owned by the given user, or None.

        Uses selectinload to avoid N+1 when accessing asset_symbol.
        """
        stmt = (
            select(UserAsset)
            .options(selectinload(UserAsset.asset_symbol))
            .where(
                UserAsset.id == user_asset_id,
                UserAsset.user_id == user_id,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> list[UserAsset]:
        """Return all UserAsset rows for a user, eagerly loading AssetSymbol."""
        stmt = (
            select(UserAsset)
            .options(selectinload(UserAsset.asset_symbol))
            .where(UserAsset.user_id == user_id)
            .order_by(UserAsset.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user_and_symbol(
        self,
        user_id: int,
        asset_symbol_id: int,
    ) -> UserAsset | None:
        """Return the UserAsset for a specific (user, symbol) pair, or None."""
        stmt = select(UserAsset).where(
            UserAsset.user_id == user_id,
            UserAsset.asset_symbol_id == asset_symbol_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: int,
        asset_symbol_id: int,
        memo: str | None = None,
    ) -> UserAsset:
        """Persist a new UserAsset row and return the refreshed instance with AssetSymbol."""
        user_asset = UserAsset(
            user_id=user_id,
            asset_symbol_id=asset_symbol_id,
            memo=memo,
        )
        self._session.add(user_asset)
        await self._session.flush()

        # Reload with relationship so callers can access asset_symbol without N+1.
        loaded = await self.get_by_id_for_user(user_asset.id, user_id)
        assert loaded is not None  # just flushed — must exist
        return loaded

    async def delete_by_id_for_user(self, user_asset_id: int, user_id: int) -> bool:
        """Delete a UserAsset owned by the given user.

        Returns True if a row was deleted, False if not found.
        """
        stmt = select(UserAsset).where(
            UserAsset.id == user_asset_id,
            UserAsset.user_id == user_id,
        )
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
