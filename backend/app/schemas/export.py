"""Pydantic schemas for data export endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType


class ExportAssetSymbol(BaseModel):
    """Snapshot of an AssetSymbol at export time."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: int = Field(..., description="AssetSymbol ID", examples=[7])
    asset_type: AssetType = Field(..., description="Asset category", examples=["crypto"])
    symbol: str = Field(..., description="Ticker / symbol code", examples=["BTC"])
    exchange: str = Field(..., description="Exchange identifier", examples=["upbit"])
    name: str = Field(..., description="Human-readable name", examples=["Bitcoin"])
    currency: str = Field(..., description="Quote currency", examples=["KRW"])
    last_price: Decimal | None = Field(
        default=None,
        description="Last known price (snapshot at export time — subject to change)",
        examples=["50000.000000"],
    )


class ExportUserAsset(BaseModel):
    """UserAsset row with nested AssetSymbol for JSON export."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: int = Field(..., description="UserAsset ID", examples=[1])
    asset_symbol_id: int = Field(..., description="AssetSymbol foreign key", examples=[7])
    memo: str | None = Field(default=None, description="Personal note", examples=["Long-term hold"])
    created_at: datetime = Field(..., description="Record creation timestamp")
    asset_symbol: ExportAssetSymbol = Field(..., description="Master symbol snapshot")


class ExportTransaction(BaseModel):
    """Transaction row for JSON export."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: int = Field(..., description="Transaction ID", examples=[1])
    user_asset_id: int = Field(..., description="Parent UserAsset ID", examples=[1])
    type: TransactionType = Field(..., description="Transaction type", examples=["buy"])
    quantity: Decimal = Field(..., description="Number of units", examples=["1.5000000000"])
    price: Decimal = Field(
        ..., description="Price per unit at trade time", examples=["50000.000000"]
    )
    traded_at: datetime = Field(..., description="Timezone-aware datetime of the trade")
    memo: str | None = Field(default=None, description="Personal note", examples=["DCA buy"])
    tag: str | None = Field(default=None, description="User-defined tag", examples=["DCA"])
    created_at: datetime = Field(..., description="Record creation timestamp")


class ExportEnvelope(BaseModel):
    """Top-level JSON export envelope."""

    model_config = ConfigDict(str_strip_whitespace=True)

    exported_at: datetime = Field(
        ...,
        description="UTC timestamp when the export was generated",
        examples=["2026-04-25T10:00:00Z"],
    )
    user_assets: list[ExportUserAsset] = Field(
        ...,
        description="All asset holdings with their master symbol snapshot",
    )
    transactions: list[ExportTransaction] = Field(
        ...,
        description="All transactions across all asset holdings",
    )
