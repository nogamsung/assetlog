"""Pydantic schemas for bulk multi-symbol transaction import."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.transaction import CsvImportError, TransactionResponse, _TransactionBase


class BulkTransactionRow(_TransactionBase):
    """A single row in a bulk transaction import request.

    Extends _TransactionBase with symbol and exchange fields so the service
    can resolve (symbol, exchange) → user_asset_id without a prior path param.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Ticker symbol (e.g. 'BTC', 'AAPL')",
        examples=["BTC"],
    )
    exchange: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Exchange identifier (e.g. 'UPBIT', 'NASDAQ')",
        examples=["UPBIT"],
    )


class BulkTransactionRequest(BaseModel):
    """Request body for the bulk import endpoint (JSON mode)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    rows: list[BulkTransactionRow] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Transaction rows to import (1–500 rows)",
    )


class BulkTransactionResponse(BaseModel):
    """Response body for the bulk import endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True)

    imported_count: int = Field(
        ...,
        description="Total number of transactions successfully imported",
        examples=[2],
    )
    preview: list[TransactionResponse] = Field(
        ...,
        description="First 10 imported transactions ordered by traded_at ASC",
    )


class BulkValidationErrorResponse(BaseModel):
    """422 response body returned when bulk validation fails."""

    model_config = ConfigDict(str_strip_whitespace=True)

    detail: str = Field(
        ...,
        description="High-level error message",
        examples=["Bulk validation failed"],
    )
    errors: list[CsvImportError] = Field(
        ...,
        description="Per-row validation errors",
    )
