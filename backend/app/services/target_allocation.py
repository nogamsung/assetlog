"""TargetAllocationService — wraps repository with schema mapping."""

from __future__ import annotations

import logging

from app.models.target_allocation import TargetAllocation
from app.repositories.target_allocation import TargetAllocationRepository
from app.schemas.target_allocation import (
    TargetAllocationEntry,
    TargetAllocationListResponse,
    TargetAllocationUpsertRequest,
)

logger = logging.getLogger(__name__)


class TargetAllocationService:
    """Read / atomic-replace target asset-class allocations."""

    def __init__(self, repository: TargetAllocationRepository) -> None:
        self._repo = repository

    async def list_targets(self) -> TargetAllocationListResponse:
        """Return the current target allocation set."""
        rows = await self._repo.list_all()
        return TargetAllocationListResponse(
            entries=[self._to_entry(row) for row in rows],
        )

    async def replace(
        self,
        payload: TargetAllocationUpsertRequest,
    ) -> TargetAllocationListResponse:
        """Atomically replace the entire target allocation set."""
        pairs = [(str(e.asset_type), e.target_pct) for e in payload.entries]
        rows = await self._repo.replace_all(pairs)
        return TargetAllocationListResponse(
            entries=[self._to_entry(row) for row in rows],
        )

    @staticmethod
    def _to_entry(row: TargetAllocation) -> TargetAllocationEntry:
        return TargetAllocationEntry.model_validate(
            {"asset_type": row.asset_type, "target_pct": row.target_pct}
        )
