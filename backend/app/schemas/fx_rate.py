"""Pydantic v2 schemas for FX rate endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class FxRateEntry(BaseModel):
    """Single exchange rate entry in the GET /api/fx/rates response."""

    model_config = ConfigDict(from_attributes=True)

    base: str = Field(..., description="Base currency code", examples=["USD"])
    quote: str = Field(..., description="Quote currency code", examples=["KRW"])
    rate: Decimal = Field(
        ...,
        description="Exchange rate: 1 base = rate quote",
        examples=["1380.25000000"],
    )
    fetched_at: datetime = Field(
        ..., description="Timestamp when this rate was last fetched from Frankfurter"
    )

    @field_serializer("rate")
    def _serialize_rate(self, v: Decimal) -> str:
        return str(v)


class FxRatesResponse(BaseModel):
    """Response for GET /api/fx/rates — all cached exchange rate pairs."""

    model_config = ConfigDict(from_attributes=True)

    rates: list[FxRateEntry] = Field(
        default_factory=list,
        description="All cached exchange rate pairs",
    )
