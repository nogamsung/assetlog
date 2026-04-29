"""Pydantic v2 schemas for market index endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class IndexQuote(BaseModel):
    """Single market index quote."""

    model_config = ConfigDict(from_attributes=True)

    symbol: str = Field(..., description="Index ticker (e.g. ^GSPC)", examples=["^GSPC"])
    name: str = Field(..., description="Human-readable name", examples=["S&P 500"])
    currency: str = Field(..., description="Quote currency", examples=["USD"])
    price: Decimal = Field(..., description="Latest close", examples=["5123.41"])
    change: Decimal = Field(..., description="Absolute change vs previous close")
    change_pct: Decimal = Field(..., description="Percent change vs previous close")
    fetched_at: datetime = Field(..., description="UTC timestamp the quote was fetched")

    @field_serializer("price", "change", "change_pct")
    def _serialize_decimal(self, v: Decimal) -> str:
        return str(v)


class IndicesResponse(BaseModel):
    """Response for GET /api/market/indices."""

    model_config = ConfigDict(from_attributes=True)

    indices: list[IndexQuote] = Field(default_factory=list, description="Market index quotes")
