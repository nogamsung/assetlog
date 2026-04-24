"""Symbol service — business logic for AssetSymbol master management."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, datetime

from app.adapters.base import SymbolSearchAdapter  # ADDED
from app.domain.asset_type import AssetType
from app.domain.symbol_search import SymbolCandidate  # ADDED
from app.exceptions import ConflictError
from app.models.asset_symbol import AssetSymbol
from app.repositories.asset_symbol import AssetSymbolRepository
from app.schemas.asset import AssetSymbolCreate

logger = logging.getLogger(__name__)


class SymbolService:
    """Handles AssetSymbol registration and search — no FastAPI/HTTP imports."""

    def __init__(
        self,
        repository: AssetSymbolRepository,
        adapters: Mapping[AssetType, SymbolSearchAdapter] | None = None,  # ADDED
    ) -> None:
        self._repo = repository
        self._adapters: Mapping[AssetType, SymbolSearchAdapter] = adapters or {}  # ADDED

    async def search(
        self,
        q: str | None = None,
        asset_type: AssetType | None = None,
        exchange: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[AssetSymbol]:
        """Search AssetSymbol master table, with external adapter fallback.

        Pipeline (DB-first + external fallback + upsert):
        1. Query DB for matching symbols.
        2. If q is empty or asset_type is None: return DB hits only (US-S4/S6).
        3. If DB hits >= limit: return DB hits only.
        4. Call adapter.search_symbols for remaining quota.
        5. Deduplicate against DB hits by (asset_type, symbol, exchange).
        6. Upsert new candidates → last_synced_at refreshed.
        7. Merge and return up to limit rows.

        External adapter failures are caught and logged (US-S5) — DB hits
        are always returned regardless.

        Args:
            q: Partial text matched case-insensitively against symbol and name.
            asset_type: Optional filter to narrow by category.
            exchange: Optional exact-match filter on exchange identifier.
            limit: Maximum number of results (1–100).
            offset: Pagination offset.

        Returns:
            Ordered list of matching AssetSymbol instances (DB first).
        """
        db_hits = await self._repo.search(
            q=q,
            asset_type=asset_type,
            exchange=exchange,
            limit=limit,
            offset=offset,
        )

        # US-S4 / US-S6: no external fallback without both q and asset_type.
        if not q or not q.strip() or asset_type is None:
            return db_hits

        remaining = max(0, limit - len(db_hits))
        if remaining == 0:
            return db_hits

        adapter = self._adapters.get(asset_type)
        if adapter is None:
            return db_hits

        try:
            candidates: list[SymbolCandidate] = await adapter.search_symbols(
                q.strip(), limit=remaining * 2
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "adapter.search_symbols failed for asset_type=%s: %s",
                asset_type,
                exc,
                extra={
                    "event": "symbol_search_adapter_fail",
                    "asset_type": str(asset_type),
                    "error_class": type(exc).__name__,
                },
            )
            candidates = []

        if not candidates:
            return db_hits

        # Deduplicate: exclude candidates already present in DB hits.
        seen: set[tuple[str, str, str]] = {
            (str(h.asset_type), h.symbol, h.exchange) for h in db_hits
        }
        new_candidates = [
            c for c in candidates if (str(c.asset_type), c.symbol, c.exchange) not in seen
        ]

        if not new_candidates:
            return db_hits

        persisted = await self._repo.upsert_many(new_candidates, now=datetime.now(UTC))

        logger.info(
            "symbol search fallback: upserted %d new candidates",
            len(persisted),
            extra={
                "event": "symbol_search_upserted",
                "count": len(persisted),
                "asset_type": str(asset_type),
            },
        )

        # Merge: DB hits first, then new upserted rows (deduplicated).
        merged = list(db_hits)
        for row in persisted:
            key = (str(row.asset_type), row.symbol, row.exchange)
            if key not in seen:
                merged.append(row)
                seen.add(key)

        return merged[:limit]

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
