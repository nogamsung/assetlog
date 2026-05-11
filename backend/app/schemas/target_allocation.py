"""Pydantic v2 schemas for target asset-allocation endpoints."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from app.domain.asset_type import AssetType


AllocationBucket = AssetType | Literal["cash"]


class TargetAllocationEntry(BaseModel):
    """Single target allocation row."""

    asset_type: AllocationBucket = Field(
        ...,
        description=(
            "Bucket — any AssetType (us_stock / kr_stock / crypto / ...) "
            "or the synthetic 'cash' bucket"
        ),
        examples=["us_stock"],
    )
    target_pct: Decimal = Field(
        ...,
        ge=0,
        le=1,
        max_digits=6,
        decimal_places=4,
        description="Target weight as a fraction (0–1; 0.60 = 60%)",
        examples=["0.6000"],
    )

    @field_serializer("target_pct")
    def _serialize_pct(self, v: Decimal) -> str:
        return str(v)


class TargetAllocationListResponse(BaseModel):
    """Response for GET /api/target-allocation."""

    model_config = ConfigDict(from_attributes=True)

    entries: list[TargetAllocationEntry] = Field(default_factory=list)


class TargetAllocationUpsertRequest(BaseModel):
    """Atomic upsert payload for PUT /api/target-allocation.

    The full target allocation set must sum to ≤ 1.0 (100%). An explicit
    empty list clears the configuration.
    """

    entries: list[TargetAllocationEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_sum_and_unique(self) -> TargetAllocationUpsertRequest:
        seen: set[str] = set()
        total = Decimal("0")
        for e in self.entries:
            key = str(e.asset_type)
            if key in seen:
                raise ValueError(f"duplicate asset_type: {key}")
            seen.add(key)
            total += e.target_pct
        if total > Decimal("1"):
            raise ValueError(f"sum of target_pct must be ≤ 1.0 (got {total})")
        return self
