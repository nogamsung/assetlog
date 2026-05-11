"""Pydantic v2 schemas for Korean capital-gains-tax endpoint."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

CostMethod = Literal["fifo", "average"]


class TaxableSaleEntry(BaseModel):
    """Per-sale realised P&L breakdown (KRW)."""

    sold_at: datetime = Field(..., description="SELL timestamp (UTC)")
    asset_symbol_id: int = Field(..., description="Asset symbol PK")
    symbol: str = Field(..., description="Ticker code")
    quantity: Decimal = Field(..., description="Quantity sold")
    sell_value_krw: Decimal = Field(..., description="Sell proceeds × sell-date FX (KRW)")
    cost_basis_krw: Decimal = Field(..., description="Matched cost × buy-date FX(es) (KRW)")
    realized_gain_krw: Decimal = Field(..., description="sell_value_krw - cost_basis_krw (signed)")

    @field_serializer(
        "quantity",
        "sell_value_krw",
        "cost_basis_krw",
        "realized_gain_krw",
    )
    def _serialize_decimal(self, v: Decimal) -> str:
        return str(v)


class CapitalGainsTaxResponse(BaseModel):
    """Korean foreign-stock capital gains tax estimate for a single year."""

    model_config = ConfigDict(from_attributes=True)

    year: int = Field(..., description="Tax year")
    method: CostMethod = Field(..., description="Cost-basis matching method")
    sales: list[TaxableSaleEntry] = Field(default_factory=list)
    gross_gain_krw: Decimal = Field(
        ..., description="Σ realized_gain_krw across all SELLs in *year*"
    )
    deduction_krw: Decimal = Field(
        ...,
        description="Annual deduction applied (default 2,500,000 KRW)",
        examples=["2500000"],
    )
    taxable_gain_krw: Decimal = Field(
        ...,
        description="max(0, gross_gain_krw - deduction_krw)",
    )
    tax_rate: Decimal = Field(
        ...,
        description="Flat capital-gains rate applied (default 0.22 = 22%)",
        examples=["0.2200"],
    )
    estimated_tax_krw: Decimal = Field(..., description="taxable_gain_krw × tax_rate")
    warnings: list[str] = Field(
        default_factory=list,
        description=("Diagnostics: 'fx_rate_missing:<currency>:<date>', 'oversold'"),
    )

    @field_serializer(
        "gross_gain_krw",
        "deduction_krw",
        "taxable_gain_krw",
        "tax_rate",
        "estimated_tax_krw",
    )
    def _serialize_decimal(self, v: Decimal) -> str:
        return str(v)
