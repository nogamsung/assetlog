"""Pydantic v2 schemas for the tag breakdown endpoint."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TagBreakdownEntry(BaseModel):
    """Flow metrics for a single tag (or null = untagged transactions).

    Decimal monetary values are pre-serialised as strings by the service layer
    before being placed in the dict fields.
    """

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    tag: str | None = Field(
        ...,
        description="Tag string, or null for transactions with no tag",
        examples=["DCA"],
    )
    transaction_count: int = Field(
        ...,
        ge=0,
        description="Total number of transactions for this tag",
        examples=[12],
    )
    buy_count: int = Field(
        ...,
        ge=0,
        description="Number of BUY transactions",
        examples=[10],
    )
    sell_count: int = Field(
        ...,
        ge=0,
        description="Number of SELL transactions",
        examples=[2],
    )
    total_bought_value_by_currency: dict[str, str] = Field(
        default_factory=dict,
        description="Σ(qty × price) of BUY transactions per currency (Decimal → string)",
        examples=[{"USD": "1500.00", "KRW": "5000000.00"}],
    )
    total_sold_value_by_currency: dict[str, str] = Field(
        default_factory=dict,
        description="Σ(qty × price) of SELL transactions per currency (Decimal → string)",
        examples=[{"USD": "100.00", "KRW": "0.00"}],
    )


class TagBreakdownResponse(BaseModel):
    """Response envelope for GET /api/portfolio/tags/breakdown."""

    model_config = ConfigDict(from_attributes=True)

    entries: list[TagBreakdownEntry] = Field(
        default_factory=list,
        description=(
            "Per-tag flow breakdown entries. "
            "Sorted by transaction_count DESC, then tag ASC. "
            "Untagged entries (tag=null) always appear last."
        ),
    )
