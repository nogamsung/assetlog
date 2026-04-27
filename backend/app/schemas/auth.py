"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UserLogin(BaseModel):
    """Schema for single-owner password login."""

    model_config = ConfigDict(str_strip_whitespace=True)

    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Owner password",
        examples=["your-secret-password"],
    )


class UserResponse(BaseModel):
    """Schema for owner principal returned after authentication.

    Token is never included — it is set via httpOnly cookie only.
    Single-owner mode: no DB-backed user record, only the static principal id.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    id: int = Field(..., description="Owner principal ID", examples=[1])


class ErrorResponse(BaseModel):
    """Generic error response body."""

    detail: str = Field(..., examples=["Authentication credentials are missing or invalid."])
