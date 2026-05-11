"""Pydantic v2 schemas for Korean capital-gains-tax endpoint."""

from __future__ import annotations

from datetime import date, datetime
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


class DividendTaxEntry(BaseModel):
    """Per-dividend KRW-converted line item."""

    asset_symbol_id: int = Field(..., description="Asset symbol PK")
    symbol: str = Field(..., description="Ticker code")
    ex_date: date = Field(..., description="Ex-dividend date")
    amount_local: Decimal = Field(..., description="Per-share amount in *currency*")
    currency: str = Field(..., description="Distribution currency")
    amount_krw: Decimal = Field(..., description="amount_local × ex-date FX (KRW)")

    @field_serializer("amount_local", "amount_krw")
    def _serialize_decimal(self, v: Decimal) -> str:
        return str(v)


class DividendTaxResponse(BaseModel):
    """Korean dividend-income tax estimate for a single year.

    Korean residents owe 15.4% (14% income + 1.4% local) withheld at source
    on dividends. When total annual financial income (interest + dividend)
    exceeds 20,000,000 KRW, the surplus is subject to comprehensive income
    tax — this estimator only flags the threshold breach via
    ``comprehensive_threshold_breach`` and does not compute progressive
    bracket tax (depends on other income out of app's scope).
    """

    model_config = ConfigDict(from_attributes=True)

    year: int = Field(..., description="Tax year")
    entries: list[DividendTaxEntry] = Field(default_factory=list)
    total_dividend_krw: Decimal = Field(..., description="Σ amount_krw")
    withholding_rate: Decimal = Field(
        ...,
        description="Flat withholding rate (default 0.154 = 15.4%)",
        examples=["0.1540"],
    )
    withholding_tax_krw: Decimal = Field(..., description="total_dividend_krw × withholding_rate")
    comprehensive_threshold_krw: Decimal = Field(
        ...,
        description="Annual financial income threshold above which 종합과세 applies",
        examples=["20000000"],
    )
    comprehensive_threshold_breach: bool = Field(
        ...,
        description="True if total_dividend_krw exceeds comprehensive_threshold_krw",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Diagnostics: 'fx_rate_missing:<currency>:<date>'",
    )

    @field_serializer(
        "total_dividend_krw",
        "withholding_rate",
        "withholding_tax_krw",
        "comprehensive_threshold_krw",
    )
    def _serialize_decimal(self, v: Decimal) -> str:
        return str(v)
