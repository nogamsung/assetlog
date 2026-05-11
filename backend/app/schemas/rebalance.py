"""Pydantic v2 schemas for the rebalance-suggestion endpoint."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.domain.asset_type import AssetType

AllocationBucket = AssetType | Literal["cash"]


class RebalanceEntry(BaseModel):
    """Per-bucket rebalance recommendation in the report currency."""

    asset_type: AllocationBucket = Field(..., description="Bucket (asset_type or 'cash')")
    target_pct: Decimal = Field(
        ..., description="Configured target weight (fraction)", examples=["0.6000"]
    )
    current_pct: Decimal = Field(..., description="Current weight (fraction)", examples=["0.5234"])
    drift_pct: Decimal = Field(
        ...,
        description=(
            "Deviation from target = current_pct - target_pct (signed). "
            "Negative means under-allocated → buy; positive → sell."
        ),
        examples=["-0.0766"],
    )
    delta_amount: Decimal = Field(
        ...,
        description=(
            "Amount to add (positive) or trim (negative) in *currency* to "
            "reach target. delta = (target_pct - current_pct) × total_value"
        ),
        examples=["1000000.00"],
    )
    action: Literal["buy", "sell", "hold"] = Field(
        ...,
        description=(
            "Suggested action based on drift vs threshold — "
            "'buy' if drift_pct ≤ -threshold, 'sell' if drift_pct ≥ +threshold, "
            "else 'hold'"
        ),
        examples=["buy"],
    )

    @field_serializer("target_pct", "current_pct", "drift_pct", "delta_amount")
    def _serialize_decimal(self, v: Decimal) -> str:
        return str(v)


class RebalanceSuggestionResponse(BaseModel):
    """Suggested rebalance moves to align current allocation with target."""

    model_config = ConfigDict(from_attributes=True)

    currency: str = Field(..., description="Report currency for delta_amount values")
    total_value: Decimal = Field(
        ...,
        description="Total portfolio value (including cash) in report currency",
        examples=["25000000.00"],
    )
    threshold_pct: Decimal = Field(
        ...,
        description=(
            "Absolute drift threshold (fraction) — buckets within ±threshold are marked 'hold'."
        ),
        examples=["0.0500"],
    )
    entries: list[RebalanceEntry] = Field(
        default_factory=list,
        description="One entry per bucket (target ∪ current)",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Diagnostics: 'no_target_configured', 'no_portfolio_value', 'fx_rate_missing'"
        ),
    )

    @field_serializer("total_value", "threshold_pct")
    def _serialize_decimal(self, v: Decimal) -> str:
        return str(v)
