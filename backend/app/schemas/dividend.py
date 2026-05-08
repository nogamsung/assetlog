"""Pydantic v2 schemas for dividend endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.domain.dividend import DividendSource


class DividendResponse(BaseModel):
    """Single dividend distribution row returned by GET /api/dividends."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Dividend row PK", examples=[42])
    asset_symbol_id: int = Field(..., description="Asset symbol PK", examples=[7])
    ex_date: date = Field(..., description="Ex-dividend date", examples=["2026-02-07"])
    amount: Decimal = Field(
        ...,
        description="Per-share dividend amount in *currency* (Decimal as string)",
        examples=["0.24"],
    )
    currency: str = Field(..., description="Distribution currency", examples=["USD"])
    source: DividendSource = Field(..., description="Origin adapter", examples=["yfinance"])
    created_at: datetime = Field(..., description="When this row was first stored")

    @field_serializer("amount")
    def _serialize_amount(self, v: Decimal) -> str:
        return str(v)


class DividendSummaryEntry(BaseModel):
    """Cumulative dividend total for a single asset symbol."""

    asset_symbol_id: int = Field(..., description="Asset symbol PK")
    total_amount: Decimal = Field(..., description="Cumulative dividend (Decimal as string)")
    currency: str = Field(..., description="Distribution currency")

    @field_serializer("total_amount")
    def _serialize_total(self, v: Decimal) -> str:
        return str(v)


class DividendListResponse(BaseModel):
    """List response for GET /api/dividends."""

    model_config = ConfigDict(from_attributes=True)

    items: list[DividendResponse] = Field(default_factory=list)
    summary_by_symbol: list[DividendSummaryEntry] = Field(default_factory=list)
