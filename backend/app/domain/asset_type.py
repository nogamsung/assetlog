"""AssetType domain enum — shared between ORM models and Pydantic schemas."""

from __future__ import annotations

import enum


class AssetType(enum.StrEnum):
    """Supported asset categories.

    Stored as plain strings (native_enum=False) to avoid ALTER TABLE when
    new values are added in the future.
    """

    CRYPTO = "crypto"
    KR_STOCK = "kr_stock"
    US_STOCK = "us_stock"
