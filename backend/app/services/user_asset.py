"""UserAsset service — business logic for user holding management."""

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

    async def list(self, user_id: int) -> list[UserAsset]:
        """Return all asset holdings for a user.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            List of UserAsset rows with AssetSymbol eagerly loaded.
        """
        return await self._repo.list_for_user(user_id)

    async def add(self, user_id: int, data: UserAssetCreate) -> UserAsset:
        """Declare a new asset holding for a user.

        Args:
            user_id: The authenticated user's ID.
            data: Validated creation payload.

        Returns:
            Newly created UserAsset with AssetSymbol loaded.

        Raises:
            NotFoundError: If asset_symbol_id does not exist.
            ConflictError: If the user already holds the same symbol.
        """
        symbol = await self._repo.get_asset_symbol(data.asset_symbol_id)
        if symbol is None:
            raise NotFoundError(f"AssetSymbol with id={data.asset_symbol_id} not found.")

        existing = await self._repo.get_by_user_and_symbol(
            user_id=user_id,
            asset_symbol_id=data.asset_symbol_id,
        )
        if existing is not None:
            raise ConflictError("You already hold this asset symbol.")

        user_asset = await self._repo.create(
            user_id=user_id,
            asset_symbol_id=data.asset_symbol_id,
            memo=data.memo,
        )
        logger.info(
            "UserAsset added: id=%s user_id=%s asset_symbol_id=%s",
            user_asset.id,
            user_id,
            data.asset_symbol_id,
        )
        return user_asset

    async def remove(self, user_id: int, user_asset_id: int) -> None:
        """Hard-delete a user's asset holding.

        Args:
            user_id: The authenticated user's ID.
            user_asset_id: The UserAsset row to remove.

        Raises:
            NotFoundError: If the row does not exist or is not owned by user_id.
        """
        deleted = await self._repo.delete_by_id_for_user(
            user_asset_id=user_asset_id,
            user_id=user_id,
        )
        if not deleted:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found or not owned by you.")
        logger.info(
            "UserAsset removed: id=%s user_id=%s",
            user_asset_id,
            user_id,
        )
