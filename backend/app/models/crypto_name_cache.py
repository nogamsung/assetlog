"""CryptoNameCache ORM model — base ticker → Korean display name (Upbit)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CryptoNameCache(Base):
    """Maps a crypto base ticker (BTC) to its Korean display name (비트코인).

    Source is ``upbit`` for entries from the Upbit market-meta API. NULL name
    keeps a *negative* lookup so we don't keep hitting the API for tickers
    Upbit doesn't list.
    """

    __tablename__ = "crypto_name_cache"

    base: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="upbit")
    looked_up_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
