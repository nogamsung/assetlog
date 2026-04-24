"""Pydantic v2 schemas for portfolio endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.domain.asset_type import AssetType
from app.domain.portfolio_history import HistoryBucket, HistoryPeriod


class SymbolEmbedded(BaseModel):
    """Minimal symbol data embedded inside HoldingResponse."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Asset symbol ID", examples=[7])
    asset_type: AssetType = Field(..., description="Asset category", examples=["us_stock"])
    symbol: str = Field(..., description="Ticker code", examples=["AAPL"])
    exchange: str = Field(..., description="Exchange identifier", examples=["NASDAQ"])
    name: str = Field(..., description="Human-readable name", examples=["Apple Inc."])
    currency: str = Field(..., description="Quote currency", examples=["USD"])


class HoldingResponse(BaseModel):
    """Per-holding row returned by GET /api/portfolio/holdings.

    Decimal monetary fields are serialised as strings to avoid floating-point
    precision loss when the frontend converts them with Number(...).
    """

    model_config = ConfigDict(from_attributes=True)

    user_asset_id: int = Field(..., description="UserAsset PK", examples=[12])
    asset_symbol: SymbolEmbedded = Field(..., description="Master symbol data")

    quantity: Decimal = Field(
        ..., description="Remaining held quantity (buy - sell)", examples=["10.0000000000"]
    )
    avg_cost: Decimal = Field(
        ..., description="Weighted-average buy price", examples=["170.500000"]
    )
    cost_basis: Decimal = Field(
        ...,
        description="Cost basis of remaining shares (remaining_qty × avg_cost)",
        examples=["1705.00"],
    )
    realized_pnl: Decimal = Field(  # ADDED
        default=Decimal("0"),
        description="Realized P&L from SELL transactions",
        examples=["50.00"],
    )

    latest_price: Decimal | None = Field(
        default=None,
        description="Last cached price (null = pending)",
        examples=["175.200000"],
    )
    latest_value: Decimal | None = Field(
        default=None,
        description="Current market value (null if pending)",
        examples=["1752.00"],
    )
    pnl_abs: Decimal | None = Field(
        default=None,
        description="Absolute P&L (null if pending)",
        examples=["47.00"],
    )
    pnl_pct: float | None = Field(
        default=None,
        description="P&L percentage (null if pending)",
        examples=[2.76],
    )
    weight_pct: float = Field(
        default=0.0,
        description="Portfolio weight % (0 if no valued holdings)",
        examples=[21.4],
    )

    last_price_refreshed_at: datetime | None = Field(
        default=None,
        description="When last_price was last updated (null = never)",
    )
    is_stale: bool = Field(
        default=False,
        description="True if last_price is older than 3 hours",
    )
    is_pending: bool = Field(
        default=False,
        description="True if latest_price is null",
    )

    @field_serializer("quantity", "avg_cost", "cost_basis", "realized_pnl")  # MODIFIED
    def _serialize_decimal_required(self, v: Decimal) -> str:
        return str(v)

    @field_serializer("latest_price", "latest_value", "pnl_abs")
    def _serialize_decimal_optional(self, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


class PnlEntry(BaseModel):
    """Absolute and percentage P&L for a single currency."""

    abs: Decimal = Field(
        ..., description="Absolute P&L (Decimal → string)", examples=["1500000.00"]
    )
    pct: float = Field(..., description="P&L percentage", examples=[13.64])

    @field_serializer("abs")
    def _serialize_abs(self, v: Decimal) -> str:
        return str(v)


class AllocationEntry(BaseModel):
    """Asset-class allocation entry in portfolio summary."""

    asset_type: AssetType = Field(..., description="Asset category", examples=["us_stock"])
    pct: float = Field(..., description="Portfolio weight 0–100", examples=[48.3])


class PortfolioSummaryResponse(BaseModel):
    """Aggregated portfolio summary returned by GET /api/portfolio/summary."""

    model_config = ConfigDict(from_attributes=True)

    total_value_by_currency: dict[str, str] = Field(
        default_factory=dict,
        description="Total market value per currency (Decimal → string)",
        examples=[{"KRW": "12500000.00", "USD": "8200.12"}],
    )
    total_cost_by_currency: dict[str, str] = Field(
        default_factory=dict,
        description="Total cost basis per currency (Decimal → string)",
        examples=[{"KRW": "11000000.00", "USD": "7500.00"}],
    )
    pnl_by_currency: dict[str, PnlEntry] = Field(
        default_factory=dict,
        description="Absolute and percentage P&L per currency",
    )
    realized_pnl_by_currency: dict[str, str] = Field(  # ADDED
        default_factory=dict,
        description="Realized P&L from SELL transactions per currency (Decimal → string)",
        examples=[{"KRW": "300000.00", "USD": "120.50"}],
    )
    allocation: list[AllocationEntry] = Field(
        default_factory=list,
        description="Asset-class breakdown by percentage",
    )
    last_price_refreshed_at: datetime | None = Field(
        default=None,
        description="Most recent price refresh across all holdings (null if all pending)",
    )
    pending_count: int = Field(
        default=0,
        description="Number of holdings with no cached price",
        examples=[1],
    )
    stale_count: int = Field(
        default=0,
        description="Number of holdings whose price is older than 3 hours",
        examples=[0],
    )

    # -----------------------------------------------------------------------
    # Currency conversion (optional — only populated when convert_to is given
    # and ALL required FX rates are available).
    # -----------------------------------------------------------------------

    converted_total_value: Decimal | None = Field(
        default=None,
        description=(
            "Total market value converted to display_currency "
            "(null if convert_to not provided or any FX rate is missing)"
        ),
        examples=["28000000.00"],
    )
    converted_total_cost: Decimal | None = Field(
        default=None,
        description="Total cost basis converted to display_currency (null if unavailable)",
        examples=["25000000.00"],
    )
    converted_pnl_abs: Decimal | None = Field(
        default=None,
        description="Absolute P&L in display_currency (null if unavailable)",
        examples=["3000000.00"],
    )
    converted_realized_pnl: Decimal | None = Field(
        default=None,
        description="Realized P&L in display_currency (null if unavailable)",
        examples=["500000.00"],
    )
    display_currency: str | None = Field(
        default=None,
        description="Target currency for conversion (null if unavailable)",
        examples=["KRW"],
    )

    @field_serializer(
        "converted_total_value",
        "converted_total_cost",
        "converted_pnl_abs",
        "converted_realized_pnl",
    )
    def _serialize_converted_decimal(self, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


# ---------------------------------------------------------------------------
# Portfolio history schemas
# ---------------------------------------------------------------------------


class HistoryPointResponse(BaseModel):
    """Single bucket snapshot in a portfolio value time series."""

    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime = Field(..., description="Bucket start timestamp (UTC)")
    value: Decimal = Field(..., description="Portfolio value at this bucket")
    cost_basis: Decimal = Field(..., description="Cost basis (sum of BUY tx up to T)")

    @field_serializer("value", "cost_basis")
    def _serialize_decimal(self, v: Decimal) -> str:
        return str(v)


class PortfolioHistoryResponse(BaseModel):
    """Portfolio value time series for a given period and currency."""

    model_config = ConfigDict(from_attributes=True)

    currency: str = Field(..., description="Quote currency", examples=["KRW"])
    period: HistoryPeriod = Field(..., description="Requested time window")
    bucket: HistoryBucket = Field(..., description="Aggregation granularity")
    points: list[HistoryPointResponse] = Field(..., description="Ordered list of value snapshots")
