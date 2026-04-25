"""Pydantic schemas for the sample seed endpoint."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SampleSeedResponse(BaseModel):
    """Response body returned by POST /api/sample/seed."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    seeded: bool = Field(
        ...,
        description="True when seed data was created; False when skipped.",
        examples=[True],
    )
    reason: str | None = Field(
        default=None,
        description="Populated only when seeded=False to explain why seed was skipped.",
        examples=["user_already_has_assets"],
    )
    user_assets_created: int = Field(
        default=0,
        description="Number of UserAsset rows created.",
        examples=[5],
    )
    transactions_created: int = Field(
        default=0,
        description="Total number of Transaction rows created across all seeded assets.",
        examples=[17],
    )
    symbols_created: int = Field(
        default=0,
        description="Number of new AssetSymbol rows inserted (vs. reused).",
        examples=[5],
    )
    symbols_reused: int = Field(
        default=0,
        description="Number of existing AssetSymbol rows reused without insertion.",
        examples=[0],
    )
