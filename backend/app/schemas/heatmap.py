"""Pydantic v2 schemas for the monthly returns heatmap."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class MonthlyReturn(BaseModel):
    """Single (year, month) cell in the heatmap.

    ``return_pct`` is a fraction — ``0.05`` means +5% over that month.
    ``null`` indicates no usable data (zero portfolio value at month start
    or month end).
    """

    year: int = Field(..., description="4-digit year", examples=[2026])
    month: int = Field(..., ge=1, le=12, description="Calendar month 1–12", examples=[5])
    return_pct: Decimal | None = Field(
        default=None,
        description="Monthly return as a fraction (Decimal as string)",
        examples=["0.0512"],
    )

    @field_serializer("return_pct")
    def _serialize_pct(self, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


class HeatmapResponse(BaseModel):
    """Year × month return matrix for plotting a calendar heatmap."""

    model_config = ConfigDict(from_attributes=True)

    currency: str = Field(..., description="Report currency", examples=["KRW"])
    start_date: datetime = Field(..., description="Window start (UTC)")
    end_date: datetime = Field(..., description="Window end (UTC)")
    months: list[MonthlyReturn] = Field(
        default_factory=list,
        description="Per-month returns ordered chronologically (oldest first)",
    )
    yearly_returns: dict[int, Decimal | None] = Field(
        default_factory=dict,
        description=(
            "Calendar-year aggregated return per year — geometric compound of "
            "the year's monthly returns (Decimal as string per value)"
        ),
        examples=[{"2025": "0.1234"}],
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Diagnostics — 'no_activity_in_period', 'fx_rate_missing'",
    )

    @field_serializer("yearly_returns")
    def _serialize_yearly(self, v: dict[int, Decimal | None]) -> dict[str, str | None]:
        return {str(year): (str(ret) if ret is not None else None) for year, ret in v.items()}
