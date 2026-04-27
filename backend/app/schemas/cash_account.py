"""Pydantic v2 schemas for cash account endpoints."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


class CashAccountCreate(BaseModel):
    """Request schema for creating a cash account."""

    model_config = ConfigDict(str_strip_whitespace=True)

    label: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable label for this cash account",
        examples=["KRW Savings Account"],
    )
    currency: str = Field(
        ...,
        description="ISO 4217 currency code (3–4 uppercase letters, e.g. KRW, USD, USDT)",
        examples=["KRW"],
    )
    balance: Decimal = Field(
        ...,
        ge=0,
        max_digits=20,
        decimal_places=4,
        description="Current cash balance (non-negative)",
        examples=["1500000.0000"],
    )

    @field_validator("currency", mode="before")
    @classmethod
    def validate_currency(cls, v: object) -> str:
        """Strip, uppercase, and validate currency code format."""
        if not isinstance(v, str):
            raise ValueError("currency must be a string")
        normalised = v.strip().upper()
        if not re.match(r"^[A-Z]{3,4}$", normalised):
            raise ValueError("currency must be 3–4 uppercase letters (e.g. KRW, USD, USDT)")
        return normalised


class CashAccountUpdate(BaseModel):
    """Request schema for partially updating a cash account.

    currency is intentionally excluded — it cannot be changed after creation.
    extra='forbid' ensures 422 if the client sends 'currency'.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    label: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="New label (omit to keep existing)",
        examples=["My Euro Account"],
    )
    balance: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=20,
        decimal_places=4,
        description="New balance value (omit to keep existing)",
        examples=["2000000.0000"],
    )

    @model_validator(mode="after")
    def at_least_one_field(self) -> CashAccountUpdate:
        """Require at least one field to be provided."""
        if self.label is None and self.balance is None:
            raise ValueError("at least one field must be provided (label or balance)")
        return self


class CashAccountResponse(BaseModel):
    """Response schema for a cash account."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Cash account primary key", examples=[1])
    label: str = Field(..., description="Human-readable label", examples=["KRW Savings Account"])
    currency: str = Field(..., description="ISO 4217 currency code", examples=["KRW"])
    balance: Decimal = Field(
        ..., description="Current balance (serialised as string)", examples=["1500000.0000"]
    )
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")

    @field_serializer("balance")
    def _serialize_balance(self, v: Decimal) -> str:
        return str(v)
