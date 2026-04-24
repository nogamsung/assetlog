"""FxRate ORM model — latest cached exchange rate per currency pair."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FxRate(Base):
    """One cached exchange rate row per (base_currency, quote_currency) pair.

    The unique constraint on (base_currency, quote_currency) enforces a single
    row per pair — upsert updates rate and fetched_at in place rather than
    appending new rows.

    Example: base=USD, quote=KRW, rate=1380.25000000 means
    1 USD = 1380.25 KRW as of fetched_at.
    """

    __tablename__ = "fx_rates"
    __table_args__ = (
        UniqueConstraint(
            "base_currency",
            "quote_currency",
            name="uq_fx_base_quote",
        ),
        Index("ix_fx_fetched_at", "fetched_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    base_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
