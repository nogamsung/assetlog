"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Schema for user registration."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(..., description="User email address", examples=["user@example.com"])
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 chars, must contain at least one letter and one digit)",
        examples=["Secur3Pass"],
    )

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        """Require at least one letter and one digit."""
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not has_letter or not has_digit:
            raise ValueError("Password must contain at least one letter and one digit.")
        return v


class UserLogin(BaseModel):
    """Schema for user login."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(..., description="User email address", examples=["user@example.com"])
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="User password",
        examples=["Secur3Pass"],
    )


class UserResponse(BaseModel):
    """Schema for user data returned in API responses.

    Token is never included — it is set via httpOnly cookie only.
    """

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: int = Field(..., description="User ID", examples=[1])
    email: str = Field(..., description="User email address", examples=["user@example.com"])
    created_at: datetime = Field(..., description="Account creation timestamp")


class ErrorResponse(BaseModel):
    """Generic error response body."""

    detail: str = Field(..., examples=["Authentication credentials are missing or invalid."])
