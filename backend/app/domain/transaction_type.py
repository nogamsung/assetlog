"""TransactionType domain enum — shared between ORM models and Pydantic schemas."""

from __future__ import annotations

import enum


class TransactionType(enum.StrEnum):
    """Supported transaction categories.

    Stored as plain strings (native_enum=False) to avoid ALTER TABLE when
    new values are added in future PRs (SELL, DIVIDEND, etc.).
    """

    BUY = "buy"
    # SELL = "sell"       # future PR
    # DIVIDEND = "div"    # future PR
