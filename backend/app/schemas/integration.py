"""Schemas for external integration endpoints (Upbit, brokerage OpenAPIs)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SyncResultResponse(BaseModel):
    """Counters for a sync operation."""

    model_config = ConfigDict(from_attributes=True)

    fetched: int = Field(..., description="Total external trades fetched", examples=[42])
    inserted: int = Field(..., description="New transactions persisted", examples=[40])
    skipped_duplicate: int = Field(
        ...,
        description="Trades skipped because (source, external_id) already exists",
        examples=[2],
    )
    skipped_no_symbol: int = Field(
        ...,
        description="Trades skipped because the symbol could not be resolved",
        examples=[0],
    )
