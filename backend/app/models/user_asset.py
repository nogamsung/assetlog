"""UserAsset ORM model — single-owner declared holding for an AssetSymbol."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.asset_symbol import AssetSymbol


class UserAsset(Base):
    """Declared holding for an asset symbol in single-owner mode.

    Actual P&L and quantity come from Transaction rows.
    Only one row per asset_symbol_id — duplicate holdings are rejected.
    """

    __tablename__ = "user_assets"
    __table_args__ = (
        UniqueConstraint(
            "asset_symbol_id",
            name="uq_user_asset_symbol",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_symbol_id: Mapped[int] = mapped_column(
        ForeignKey("asset_symbols.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    memo: Mapped[str | None] = mapped_column(String(255), nullable=True)
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

    asset_symbol: Mapped[AssetSymbol] = relationship(
        "AssetSymbol",
        lazy="raise",  # force explicit loading — never implicit lazy-load
    )
