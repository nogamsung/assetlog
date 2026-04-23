"""Symbol service — business logic for AssetSymbol master management."""

from __future__ import annotations

import logging

from app.domain.asset_type import AssetType
from app.exceptions import ConflictError
from app.models.asset_symbol import AssetSymbol
from app.repositories.asset_symbol import AssetSymbolRepository
from app.schemas.asset import AssetSymbolCreate

logger = logging.getLogger(__name__)


class SymbolService:
    """Handles AssetSymbol registration and search — no FastAPI/HTTP imports."""

    def __init__(self, repository: AssetSymbolRepository) -> None:
        self._repo = repository

    async def search(
        self,
        q: str | None = None,
        asset_type: AssetType | None = None,
        exchange: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[AssetSymbol]:
        """Search AssetSymbol master table with optional text / filter criteria.

        Args:
            q: Partial text matched case-insensitively against symbol and name.
            asset_type: Optional filter to narrow by category.
            exchange: Optional exact-match filter on exchange identifier.
            limit: Maximum number of results (1–100).
            offset: Pagination offset.

        Returns:
            Ordered list of matching AssetSymbol instances.
        """
        return await self._repo.search(
            q=q,
            asset_type=asset_type,
            exchange=exchange,
            limit=limit,
            offset=offset,
        )

    async def register(self, data: AssetSymbolCreate) -> AssetSymbol:
        """Register a new asset symbol in the master table.

        Args:
            data: Validated creation payload.

        Returns:
            Newly created AssetSymbol ORM instance.

        Raises:
            ConflictError: If (asset_type, symbol, exchange) already exists.
        """
        existing = await self._repo.get_by_triple(
            asset_type=data.asset_type,
            symbol=data.symbol,
            exchange=data.exchange,
        )
        if existing is not None:
            raise ConflictError(f"Symbol '{data.symbol}' on '{data.exchange}' already registered.")

        asset = await self._repo.create(
            asset_type=data.asset_type,
            symbol=data.symbol,
            exchange=data.exchange,
            name=data.name,
            currency=data.currency,
        )
        logger.info(
            "AssetSymbol registered: id=%s symbol=%s exchange=%s",
            asset.id,
            asset.symbol,
            asset.exchange,
        )
        return asset
