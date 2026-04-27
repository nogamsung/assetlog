"""UserAsset service — business logic for declared holding management."""

from __future__ import annotations

import logging

from app.exceptions import ConflictError, NotFoundError
from app.models.user_asset import UserAsset
from app.repositories.user_asset import UserAssetRepository
from app.schemas.asset import UserAssetCreate

logger = logging.getLogger(__name__)


class UserAssetService:
    """Handles UserAsset lifecycle — no FastAPI/HTTP imports."""

    def __init__(self, repository: UserAssetRepository) -> None:
        self._repo = repository

    async def list(self) -> list[UserAsset]:
        """Return all declared asset holdings with AssetSymbol eagerly loaded."""
        return await self._repo.list_all()

    async def add(self, data: UserAssetCreate) -> UserAsset:
        """Declare a new asset holding.

        Raises:
            NotFoundError: If asset_symbol_id does not exist.
            ConflictError: If the same symbol is already held.
        """
        symbol = await self._repo.get_asset_symbol(data.asset_symbol_id)
        if symbol is None:
            raise NotFoundError(f"AssetSymbol with id={data.asset_symbol_id} not found.")

        existing = await self._repo.get_by_symbol(asset_symbol_id=data.asset_symbol_id)
        if existing is not None:
            raise ConflictError("This asset symbol is already held.")

        user_asset = await self._repo.create(
            asset_symbol_id=data.asset_symbol_id,
            memo=data.memo,
        )
        logger.info(
            "UserAsset added: id=%s asset_symbol_id=%s",
            user_asset.id,
            data.asset_symbol_id,
        )
        return user_asset

    async def remove(self, user_asset_id: int) -> None:
        """Hard-delete a declared asset holding.

        Raises:
            NotFoundError: If the row does not exist.
        """
        deleted = await self._repo.delete_by_id(user_asset_id=user_asset_id)
        if not deleted:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found.")
        logger.info("UserAsset removed: id=%s", user_asset_id)
