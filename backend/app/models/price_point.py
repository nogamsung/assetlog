"""PricePoint ORM model — historical price tick per asset symbol."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.asset_symbol import AssetSymbol


class PricePoint(Base):
    """One price snapshot recorded by the price-refresh scheduler.

    Rows are append-only — no updates. The composite index on
    ``(asset_symbol_id, fetched_at DESC)`` supports efficient latest-price
    queries without scanning the full table.
    """

    __tablename__ = "price_points"
    __table_args__ = (
        Index(
            "ix_price_points_symbol_fetched",
            "asset_symbol_id",
            "fetched_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_symbol_id: Mapped[int] = mapped_column(
        ForeignKey("asset_symbols.id", ondelete="CASCADE"),
        nullable=False,
        index=False,  # covered by composite index above
    )
    price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    asset_symbol: Mapped[AssetSymbol] = relationship(
        "AssetSymbol",
        back_populates="price_points",
        lazy="noload",
    )
