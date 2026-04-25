"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserLogin(BaseModel):
    """Schema for single-owner password login."""  # MODIFIED

    model_config = ConfigDict(str_strip_whitespace=True)

    password: str = Field(  # MODIFIED — email removed
        ...,
        min_length=1,
        max_length=128,
        description="Owner password",
        examples=["your-secret-password"],
    )


class UserResponse(BaseModel):
    """Schema for user data returned in API responses.

    Token is never included — it is set via httpOnly cookie only.
    """

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: int = Field(..., description="User ID", examples=[1])
    email: str = Field(..., description="User email address", examples=["owner@assetlog.local"])
    created_at: datetime = Field(..., description="Account creation timestamp")


class ErrorResponse(BaseModel):
    """Generic error response body."""

    detail: str = Field(..., examples=["Authentication credentials are missing or invalid."])
