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
    interest_rate_annual: Decimal | None = Field(
        default=None,
        ge=0,
        le=1,
        max_digits=6,
        decimal_places=4,
        description=(
            "Optional annualised interest rate as a fraction (0.035 = 3.5%). "
            "Display-only — accrual is not auto-applied to balance."
        ),
        examples=["0.0350"],
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
    interest_rate_annual: Decimal | None = Field(
        default=None,
        ge=0,
        le=1,
        max_digits=6,
        decimal_places=4,
        description=(
            "Annualised interest rate as a fraction (0.035 = 3.5%). "
            "Omit to keep existing; explicit null clears it via extra='forbid' is not allowed — "
            "use a separate clear endpoint if needed."
        ),
        examples=["0.0350"],
    )

    @model_validator(mode="after")
    def at_least_one_field(self) -> CashAccountUpdate:
        """Require at least one field to be provided."""
        if (
            self.label is None
            and self.balance is None
            and self.interest_rate_annual is None
        ):
            raise ValueError(
                "at least one field must be provided (label, balance, or interest_rate_annual)"
            )
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
    interest_rate_annual: Decimal | None = Field(
        default=None,
        description="Optional annualised interest rate (Decimal as string) — null if not set",
        examples=["0.0350"],
    )
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")

    @field_serializer("balance")
    def _serialize_balance(self, v: Decimal) -> str:
        return str(v)

    @field_serializer("interest_rate_annual")
    def _serialize_interest(self, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None
