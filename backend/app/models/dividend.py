"""Dividend ORM model — append-only ledger of cash dividend distributions."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.dividend import DividendSource


class Dividend(Base):
    """One row per (asset_symbol, ex_date) dividend distribution.

    The unique constraint prevents duplicate inserts for the same payout —
    adapters that re-fetch the full dividend history are safe to call repeatedly.
    Currency is stored explicitly because foreign-listed ADRs may distribute
    in their home currency rather than the symbol's quote currency.
    """

    __tablename__ = "dividends"
    __table_args__ = (
        UniqueConstraint(
            "asset_symbol_id",
            "ex_date",
            name="uq_dividend_symbol_ex_date",
        ),
        Index("ix_dividend_ex_date", "ex_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_symbol_id: Mapped[int] = mapped_column(
        ForeignKey("asset_symbols.id", ondelete="CASCADE"),
        nullable=False,
    )
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    source: Mapped[DividendSource] = mapped_column(
        String(16),
        nullable=False,
        default=DividendSource.YFINANCE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
