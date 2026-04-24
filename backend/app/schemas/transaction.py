"""Pydantic schemas for Transaction endpoints and UserAsset summary."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.transaction_type import TransactionType

# ---------------------------------------------------------------------------
# Transaction schemas
# ---------------------------------------------------------------------------

# Tolerance for "future" check: allow up to 60 s of clock skew.
_FUTURE_TOLERANCE_SECONDS = 60


class _TransactionBase(BaseModel):  # ADDED — shared validator base for Create & Update
    """Common fields and validators for transaction write schemas."""

    model_config = ConfigDict(str_strip_whitespace=True)

    type: TransactionType = Field(
        default=TransactionType.BUY,
        description="Transaction type (BUY for MVP)",
        examples=["buy"],
    )
    quantity: Decimal = Field(
        ...,
        gt=Decimal("0"),
        max_digits=28,
        decimal_places=10,
        description="Number of units purchased / sold",
        examples=["1.5000000000"],
    )
    price: Decimal = Field(
        ...,
        gt=Decimal("0"),
        max_digits=20,
        decimal_places=6,
        description="Price per unit at time of trade",
        examples=["50000.000000"],
    )
    traded_at: datetime = Field(
        ...,
        description="UTC datetime of the trade (timezone-aware required)",
        examples=["2026-04-23T10:00:00+00:00"],
    )
    memo: str | None = Field(
        default=None,
        max_length=255,
        description="Optional personal note about this trade",
        examples=["DCA buy"],
    )

    @field_validator("traded_at")
    @classmethod
    def must_be_aware_and_not_future(cls, v: datetime) -> datetime:
        """Reject naive datetimes and timestamps too far in the future."""
        if v.tzinfo is None:
            raise ValueError("traded_at must be timezone-aware (include UTC offset).")
        now_utc = datetime.now(tz=UTC)
        if v > now_utc + timedelta(seconds=_FUTURE_TOLERANCE_SECONDS):
            raise ValueError("traded_at must not be in the future.")
        return v


class TransactionCreate(_TransactionBase):  # MODIFIED — now extends _TransactionBase
    """Payload for recording a new transaction."""


class TransactionUpdate(_TransactionBase):  # ADDED — full replace (PUT semantics)
    """Payload for replacing an existing transaction (all fields required)."""


class TransactionResponse(BaseModel):
    """Transaction data returned in API responses."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: int = Field(..., description="Transaction ID", examples=[1])
    user_asset_id: int = Field(..., description="Parent UserAsset ID", examples=[1])
    type: TransactionType = Field(..., description="Transaction type", examples=["buy"])
    quantity: Decimal = Field(..., description="Number of units", examples=["1.5000000000"])
    price: Decimal = Field(
        ..., description="Price per unit at trade time", examples=["50000.000000"]
    )
    traded_at: datetime = Field(..., description="UTC datetime of the trade")
    memo: str | None = Field(default=None, description="Personal note", examples=["DCA buy"])
    created_at: datetime = Field(..., description="Record creation timestamp")


# ---------------------------------------------------------------------------
# UserAsset summary schema
# ---------------------------------------------------------------------------


class UserAssetSummaryResponse(BaseModel):  # MODIFIED — SELL 지원 + realized P&L 추가
    """Aggregated BUY/SELL summary with realized P&L for a single UserAsset."""

    model_config = ConfigDict(from_attributes=True)

    user_asset_id: int = Field(..., description="UserAsset ID", examples=[1])
    total_bought_quantity: Decimal = Field(  # ADDED (replaces total_quantity)
        ...,
        description="Sum of all BUY quantities",
        examples=["5.0000000000"],
    )
    total_sold_quantity: Decimal = Field(  # ADDED
        ...,
        description="Sum of all SELL quantities",
        examples=["2.0000000000"],
    )
    remaining_quantity: Decimal = Field(  # ADDED
        ...,
        description="bought_qty - sold_qty (current holding)",
        examples=["3.0000000000"],
    )
    avg_buy_price: Decimal = Field(
        ...,
        description="Weighted average buy price across all BUYs (0 when no BUY)",
        examples=["48500.000000"],
    )
    total_invested: Decimal = Field(
        ...,
        description="Sum of (quantity × price) for all BUY transactions",
        examples=["242500.000000"],
    )
    total_sold_value: Decimal = Field(  # ADDED
        ...,
        description="Sum of (quantity × price) for all SELL transactions",
        examples=["100000.000000"],
    )
    realized_pnl: Decimal = Field(  # ADDED
        ...,
        description="Realized P&L = total_sold_value - sold_qty × avg_buy_price",
        examples=["3000.000000"],
    )
    transaction_count: int = Field(
        ...,
        description="Total number of BUY + SELL transactions recorded",
        examples=[3],
    )
    currency: str = Field(
        ...,
        description="Quote currency from the linked AssetSymbol",
        examples=["KRW"],
    )
