"""Pydantic v2 schemas for the benchmark comparison endpoint."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.domain.performance import PerformancePeriod


class ReturnPoint(BaseModel):
    """Single point in a cumulative-return time series.

    ``cumulative_return_pct`` is expressed as a fraction — ``0.10`` means +10%.
    The first point of every series is anchored at ``0`` (baseline).
    """

    timestamp: datetime = Field(..., description="Sample timestamp (UTC)")
    cumulative_return_pct: Decimal = Field(
        ...,
        description="Cumulative return at this timestamp (Decimal as string)",
        examples=["0.1234"],
    )

    @field_serializer("cumulative_return_pct")
    def _serialize_pct(self, v: Decimal) -> str:
        return str(v)


class BenchmarkSeries(BaseModel):
    """Named cumulative-return series for a single subject (portfolio or index)."""

    symbol: str = Field(
        ...,
        description="Identifier — 'PORTFOLIO' or a yfinance ticker",
        examples=["^KS11"],
    )
    name: str = Field(..., description="Human-readable label", examples=["KOSPI"])
    points: list[ReturnPoint] = Field(
        default_factory=list,
        description="Ordered cumulative-return samples (first point == 0)",
    )


class BenchmarkComparisonResponse(BaseModel):
    """Side-by-side cumulative-return comparison for plotting and alpha computation."""

    model_config = ConfigDict(from_attributes=True)

    period: PerformancePeriod = Field(..., description="Requested time window")
    currency: str = Field(..., description="Report currency for the portfolio series")
    start_date: datetime = Field(..., description="Window start (UTC)")
    end_date: datetime = Field(..., description="Window end (UTC)")
    portfolio: BenchmarkSeries = Field(..., description="User portfolio series")
    benchmarks: list[BenchmarkSeries] = Field(
        default_factory=list,
        description="One series per requested benchmark symbol",
    )
    alpha: dict[str, Decimal] = Field(
        default_factory=dict,
        description=(
            "Final portfolio return minus final benchmark return per symbol (Decimal as string)"
        ),
        examples=[{"^KS11": "0.0234"}],
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=("Diagnostics — e.g. 'no_activity_in_period', 'benchmark_fetch_failed:^KS11'"),
    )

    @field_serializer("alpha")
    def _serialize_alpha(self, v: dict[str, Decimal]) -> dict[str, str]:
        return {k: str(d) for k, d in v.items()}
