"""AssetSymbol ORM model — global master table for tradeable assets."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.asset_type import AssetType


class AssetSymbol(Base):
    """Global master row for a tradeable asset on a specific exchange.

    Multiple users may reference the same AssetSymbol via UserAsset.
    The triple (asset_type, symbol, exchange) is unique.
    """

    __tablename__ = "asset_symbols"
    __table_args__ = (
        UniqueConstraint(
            "asset_type",
            "symbol",
            "exchange",
            name="uq_asset_type_symbol_exchange",
        ),
        Index("ix_asset_symbols_symbol", "symbol"),
        Index("ix_asset_symbols_type_exchange", "asset_type", "exchange"),
        Index("ix_asset_symbols_last_refreshed", "last_price_refreshed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_type: Mapped[AssetType] = mapped_column(
        SqlEnum(AssetType, native_enum=False, length=16),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    last_price_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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
