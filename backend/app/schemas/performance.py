"""Pydantic v2 schemas for portfolio performance endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.domain.performance import PerformanceMethod, PerformancePeriod


class CashflowEntry(BaseModel):
    """Single signed cashflow entry for the performance response."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    date: datetime = Field(
        ..., description="Cashflow date (UTC)", examples=["2024-01-15T09:30:00Z"]
    )
    amount: Decimal = Field(
        ...,
        description="Signed cashflow amount (negative=BUY, positive=SELL)",
        examples=["-1000000.00"],
    )
    kind: Literal["buy", "sell"] = Field(..., description="Transaction kind", examples=["buy"])

    @field_serializer("amount")
    def _serialize_amount(self, v: Decimal) -> str:
        return str(v)


class PerformanceResponse(BaseModel):
    """Portfolio TWR / MWR performance over a period.

    All Decimal monetary fields are serialised as strings to preserve precision
    when the frontend converts them (consistent with the rest of the codebase).
    """

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    period: PerformancePeriod = Field(..., description="Requested time window", examples=["1Y"])
    method: PerformanceMethod = Field(
        ..., description="Calculation method requested", examples=["both"]
    )
    currency: str = Field(..., description="Report currency", examples=["KRW"])

    start_date: datetime = Field(
        ..., description="Window start datetime (UTC)", examples=["2023-01-01T00:00:00Z"]
    )
    end_date: datetime = Field(
        ..., description="Window end datetime (UTC)", examples=["2024-01-01T00:00:00Z"]
    )

    twr: Decimal | None = Field(
        default=None,
        description="Time-weighted return (null if not requested or unsolvable)",
        examples=["0.20"],
    )
    mwr: Decimal | None = Field(
        default=None,
        description="Money-weighted return / IRR (null if not requested or unsolvable)",
        examples=["0.20"],
    )
    annualized_twr: Decimal | None = Field(
        default=None,
        description="Annualized TWR using CAGR formula (null if twr is null or period < 1 day)",
        examples=["0.20"],
    )
    annualized_mwr: Decimal | None = Field(
        default=None,
        description="Annualized MWR (same as mwr — IRR is already annualized)",
        examples=["0.20"],
    )

    start_value: Decimal | None = Field(
        default=None,
        description="Portfolio value at window start (null if no data)",
        examples=["1000000.00"],
    )
    end_value: Decimal | None = Field(
        default=None,
        description="Portfolio value at window end (null if no data)",
        examples=["1200000.00"],
    )

    cashflows: list[CashflowEntry] = Field(
        default_factory=list,
        description="Signed cashflows within the window",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Non-fatal warnings: 'no_activity_in_period', 'fx_rate_missing', 'mwr_unsolvable'"
        ),
        examples=[["fx_rate_missing"]],
    )

    @field_serializer("twr", "mwr", "annualized_twr", "annualized_mwr")
    def _serialize_rate(self, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None

    @field_serializer("start_value", "end_value")
    def _serialize_value(self, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None
