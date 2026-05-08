"""Pydantic v2 schemas for portfolio risk metrics."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.domain.performance import PerformancePeriod


class RiskMetricsResponse(BaseModel):
    """Risk-adjusted performance summary for a portfolio over *period*.

    All Decimal fractions are encoded as strings to preserve precision —
    ``0.1234`` means +12.34% (returns/volatility) or 12.34% drawdown.
    """

    model_config = ConfigDict(from_attributes=True)

    period: PerformancePeriod = Field(..., description="Requested time window")
    currency: str = Field(..., description="Report currency", examples=["KRW"])
    start_date: datetime = Field(..., description="Window start (UTC)")
    end_date: datetime = Field(..., description="Window end (UTC)")

    annualized_return: Decimal | None = Field(
        default=None,
        description=(
            "Annualised return = (end_value / start_value)^(365/days) - 1. "
            "Null when fewer than 2 non-zero value samples exist."
        ),
        examples=["0.1234"],
    )
    annualized_volatility: Decimal | None = Field(
        default=None,
        description=(
            "Annualised volatility = stdev(daily_returns) × sqrt(252). "
            "Null when fewer than 2 daily return samples exist."
        ),
        examples=["0.1850"],
    )
    sharpe_ratio: Decimal | None = Field(
        default=None,
        description=(
            "Sharpe ratio = (annualized_return - risk_free_rate) / "
            "annualized_volatility. Null when volatility is 0 or unavailable."
        ),
        examples=["0.62"],
    )
    max_drawdown: Decimal | None = Field(
        default=None,
        description=(
            "Maximum peak-to-trough drawdown over the window — fraction (0.10 = 10%). "
            "Null when fewer than 2 non-zero value samples exist."
        ),
        examples=["0.0823"],
    )
    max_drawdown_at: datetime | None = Field(
        default=None,
        description="Timestamp of the worst drawdown (the trough)",
    )
    risk_free_rate: Decimal = Field(
        ...,
        description="Annualised risk-free rate used for the Sharpe calculation",
        examples=["0.03"],
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Diagnostics — e.g. 'no_activity_in_period', 'fx_rate_missing', "
            "'insufficient_samples', 'volatility_zero'"
        ),
    )

    @field_serializer(
        "annualized_return",
        "annualized_volatility",
        "sharpe_ratio",
        "max_drawdown",
    )
    def _serialize_optional(self, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None

    @field_serializer("risk_free_rate")
    def _serialize_required(self, v: Decimal) -> str:
        return str(v)
