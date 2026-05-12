"""CashAccountTransaction ORM model — cash flow events (interest, transfers, etc.)."""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CashTxKind(enum.StrEnum):
    """Kind of cash account transaction."""

    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    INTEREST = "interest"
    INTEREST_TAX = "interest_tax"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


class CashAccountTransaction(Base):
    """One row per cash-flow event linked to (optionally) a CashAccount.

    ``external_source`` + ``external_id`` allow file-import deduplication.
    ``cash_account_id`` is nullable — balance mapping to a specific account
    is deferred to a follow-up PR.
    """

    __tablename__ = "cash_account_transactions"
    __table_args__ = (
        Index("ix_cash_tx_traded_at", "traded_at"),
        UniqueConstraint(
            "external_source",
            "external_id",
            name="uq_cash_tx_external",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cash_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("cash_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    kind: Mapped[CashTxKind] = mapped_column(
        SqlEnum(CashTxKind, native_enum=False, length=32),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    traded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    external_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
