"""Transaction ORM model — individual buy/sell records linked to a UserAsset."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.transaction_type import TransactionType


class Transaction(Base):
    """A single trade event (BUY/SELL) recorded by the user or imported externally.

    Quantity and average-buy-price shown in UserAsset summaries are derived
    by aggregating Transaction rows — they are not stored on UserAsset itself.

    ``external_source`` + ``external_id`` let integrations (Upbit, broker
    OpenAPIs, file imports) dedupe re-syncs by carrying the upstream trade
    identifier. Both nullable for manually entered rows.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_asset_traded_at", "user_asset_id", "traded_at"),
        UniqueConstraint(
            "external_source",
            "external_id",
            name="uq_tx_external_source_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_asset_id: Mapped[int] = mapped_column(
        ForeignKey("user_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[TransactionType] = mapped_column(
        SqlEnum(TransactionType, native_enum=False, length=16),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    traded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    memo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tag: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
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
