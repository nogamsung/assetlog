"""TargetAllocation ORM model — single-owner desired asset-class weights."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TargetAllocation(Base):
    """One row per target asset_type bucket.

    Single-owner mode — no user FK. ``target_pct`` is a fraction (0–1)
    matching the existing ``AllocationEntry.pct`` semantics on the
    portfolio summary endpoint (0.60 = 60% target).

    ``asset_type`` mirrors ``app.domain.asset_type.AssetType`` values plus
    the synthetic ``"cash"`` bucket emitted by PortfolioService.
    """

    __tablename__ = "target_allocations"
    __table_args__ = (UniqueConstraint("asset_type", name="uq_target_allocation_asset_type"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
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
