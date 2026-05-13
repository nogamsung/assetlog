"""Schemas for external integration endpoints (Upbit, brokerage OpenAPIs, file import)."""

from __future__ import annotations

from typing import Any

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


class ImportFileResponse(BaseModel):
    """Result of a file-based import (Toss Securities, etc.)."""

    model_config = ConfigDict(from_attributes=True)

    inserted_trades: int = Field(..., description="New Transaction rows inserted", examples=[159])
    inserted_dividends: int = Field(..., description="New Dividend rows inserted", examples=[7])
    inserted_cash_txs: int = Field(
        ..., description="New CashAccountTransaction rows inserted", examples=[10]
    )
    skipped_duplicate: int = Field(
        ...,
        description="Records skipped because (source, external_id) already exists",
        examples=[0],
    )
    skipped_unsupported: int = Field(
        ...,
        description="Records skipped because the transaction type is not yet supported",
        examples=[196],
    )
    skipped_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Per-kind count of skipped records (e.g. {'대차거래 대여출고': 73, "
            "'환전외화입금': 9}). Useful for understanding what was skipped — most "
            "entries are intentional (cash transfers, FX, securities lending)."
        ),
        examples=[{"대차거래 대여출고": 73, "환전외화입금": 9, "이체입금": 18}],
    )
    dry_run: bool = Field(
        default=False,
        description="When True no DB writes were performed — counts reflect what would be inserted",
    )
    preview: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Up to 20 sample records (dry_run only)",
    )
