"""Pydantic schemas for AssetSymbol and UserAsset endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.asset_type import AssetType

# ---------------------------------------------------------------------------
# AssetSymbol schemas
# ---------------------------------------------------------------------------


class AssetSymbolCreate(BaseModel):
    """Payload for registering a new asset symbol in the master table."""

    model_config = ConfigDict(str_strip_whitespace=True)

    asset_type: AssetType = Field(
        ...,
        description="Asset category",
        examples=["crypto"],
    )
    symbol: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Ticker / symbol code",
        examples=["BTC"],
    )
    exchange: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Exchange or market identifier",
        examples=["upbit"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable asset name",
        examples=["Bitcoin"],
    )
    currency: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Quote currency",
        examples=["KRW"],
    )

    @field_validator("symbol", "exchange", "currency")
    @classmethod
    def no_whitespace_only(cls, v: str) -> str:
        """Reject strings that are only whitespace (after strip)."""
        if not v.strip():
            raise ValueError("Field must not be empty or whitespace-only.")
        return v


class AssetSymbolResponse(BaseModel):
    """Asset symbol data returned in API responses."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: int = Field(..., description="Asset symbol ID", examples=[1])
    asset_type: AssetType = Field(..., description="Asset category", examples=["crypto"])
    symbol: str = Field(..., description="Ticker / symbol code", examples=["BTC"])
    exchange: str = Field(..., description="Exchange identifier", examples=["upbit"])
    name: str = Field(..., description="Human-readable name", examples=["Bitcoin"])
    currency: str = Field(..., description="Quote currency", examples=["KRW"])
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last-updated timestamp")


class AssetSymbolQuery(BaseModel):
    """Query parameters for symbol search."""

    model_config = ConfigDict(str_strip_whitespace=True)

    q: str | None = Field(
        default=None,
        max_length=100,
        description="Partial text search on symbol or name",
        examples=["BTC"],
    )
    asset_type: AssetType | None = Field(
        default=None,
        description="Filter by asset category",
        examples=["crypto"],
    )
    exchange: str | None = Field(
        default=None,
        max_length=50,
        description="Filter by exchange",
        examples=["upbit"],
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results",
        examples=[20],
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset",
        examples=[0],
    )


# ---------------------------------------------------------------------------
# UserAsset schemas
# ---------------------------------------------------------------------------


class UserAssetCreate(BaseModel):
    """Payload for declaring a new asset holding."""

    model_config = ConfigDict(str_strip_whitespace=True)

    asset_symbol_id: int = Field(
        ...,
        ge=1,
        description="ID of the AssetSymbol master row",
        examples=[1],
    )
    memo: str | None = Field(
        default=None,
        max_length=255,
        description="Optional personal note about the holding",
        examples=["Long-term hold"],
    )


class UserAssetResponse(BaseModel):
    """User asset holding data returned in API responses."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: int = Field(..., description="User asset ID", examples=[1])
    user_id: int = Field(..., description="Owner user ID", examples=[1])
    asset_symbol: AssetSymbolResponse = Field(..., description="Master symbol data")
    memo: str | None = Field(default=None, description="Personal note", examples=["Long-term hold"])
    created_at: datetime = Field(..., description="Record creation timestamp")
