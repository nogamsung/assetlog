"""UserAsset ORM model — links a user to an AssetSymbol they hold."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.asset_symbol import AssetSymbol


class UserAsset(Base):
    """Association between a user and an asset symbol they have declared holding.

    Actual P&L and quantity come from Transaction rows (future PR).
    The pair (user_id, asset_symbol_id) is unique — no duplicate holdings.
    """

    __tablename__ = "user_assets"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "asset_symbol_id",
            name="uq_user_asset_symbol",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
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

    # Relationship — loaded via selectinload in repositories to avoid N+1.
    asset_symbol: Mapped[AssetSymbol] = relationship(
        "AssetSymbol",
        lazy="raise",  # force explicit loading — never implicit lazy-load
    )
