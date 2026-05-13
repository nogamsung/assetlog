"""IsinTickerCache ORM model — persistent ISIN→ticker lookup cache."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IsinTickerCache(Base):
    """Maps an ISIN to its exchange ticker (e.g. US0079031078 → AMD).

    Source can be ``static`` (hand-curated map), ``openfigi``, or ``manual``.
    NULL ticker is allowed to remember a *negative* lookup result so we don't
    hit the upstream API repeatedly for unknown ISINs.
    """

    __tablename__ = "isin_ticker_cache"

    isin: Mapped[str] = mapped_column(String(12), primary_key=True)
    ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="openfigi")
    looked_up_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
