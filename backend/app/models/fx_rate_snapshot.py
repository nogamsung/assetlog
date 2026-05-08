"""FxRateSnapshot ORM model — append-only time-series of exchange rates."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FxRateSnapshot(Base):
    """One snapshot row per (base_currency, quote_currency, recorded_at) triple.

    Unlike ``FxRate`` which keeps only the latest cached row per pair, this
    table is append-only — each scheduler tick inserts a new row.  The unique
    constraint prevents duplicate inserts for the same tick timestamp.

    Example: base=USD, quote=KRW, rate=1380.25000000, recorded_at=2026-05-07T10:00:00Z
    means 1 USD = 1380.25 KRW as of that timestamp.
    """

    __tablename__ = "fx_rate_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "base_currency",
            "quote_currency",
            "recorded_at",
            name="uq_fx_snap_base_quote_recorded",
        ),
        Index(
            "ix_fx_snap_pair_recorded",
            "base_currency",
            "quote_currency",
            "recorded_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    base_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
