"""KrNameCache ORM model — persistent Korean security-name → KRX code cache."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KrNameCache(Base):
    """Maps a Korean security name to its 6-digit KRX code (e.g. 삼성전자 → 005930).

    Source can be ``naver`` (Naver Finance autocomplete) or ``manual``. NULL
    ``code`` is allowed to remember a *negative* lookup so we don't re-hit the
    upstream API for an unrecognised name.
    """

    __tablename__ = "kr_name_cache"

    name: Mapped[str] = mapped_column(String(128), primary_key=True)
    code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="naver")
    looked_up_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
