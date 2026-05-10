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


class DividendCalendarEntry(BaseModel):
    """Display-friendly upcoming/past dividend row for the calendar UI."""

    model_config = ConfigDict(from_attributes=True)

    asset_symbol_id: int = Field(..., description="Asset symbol PK")
    symbol: str = Field(..., description="Ticker code", examples=["AAPL"])
    name: str = Field(..., description="Human-readable asset name", examples=["Apple Inc."])
    ex_date: date = Field(..., description="Ex-dividend date")
    amount: Decimal = Field(..., description="Per-share dividend amount (Decimal as string)")
    currency: str = Field(..., description="Distribution currency", examples=["USD"])

    @field_serializer("amount")
    def _serialize_amount(self, v: Decimal) -> str:
        return str(v)


class DividendCalendarResponse(BaseModel):
    """Chronological dividend calendar — past & upcoming rows joined with symbol/name."""

    model_config = ConfigDict(from_attributes=True)

    entries: list[DividendCalendarEntry] = Field(default_factory=list)


class YieldOnCostEntry(BaseModel):
    """Per-holding cumulative-dividend yield-on-cost computation."""

    model_config = ConfigDict(from_attributes=True)

    asset_symbol_id: int = Field(..., description="Asset symbol PK")
    symbol: str = Field(..., description="Ticker code", examples=["AAPL"])
    name: str = Field(..., description="Human-readable asset name")
    currency: str = Field(..., description="Quote / dividend currency", examples=["USD"])
    cost_basis: Decimal = Field(
        ...,
        description="Remaining-share cost basis in *currency* (Decimal as string)",
        examples=["1705.00"],
    )
    total_dividend: Decimal = Field(
        ...,
        description="Cumulative dividend received in *currency* (Decimal as string)",
        examples=["49.20"],
    )
    yield_on_cost_pct: Decimal | None = Field(
        default=None,
        description=(
            "Cumulative dividend / cost basis (Decimal as string). "
            "Null when cost basis is 0 (fully sold or never held)."
        ),
        examples=["0.0289"],
    )

    @field_serializer("cost_basis", "total_dividend")
    def _serialize_required(self, v: Decimal) -> str:
        return str(v)

    @field_serializer("yield_on_cost_pct")
    def _serialize_optional(self, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


class YieldOnCostResponse(BaseModel):
    """Aggregate response for GET /api/dividends/yield-on-cost."""

    model_config = ConfigDict(from_attributes=True)

    entries: list[YieldOnCostEntry] = Field(default_factory=list)
