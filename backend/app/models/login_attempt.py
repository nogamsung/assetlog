"""LoginAttempt ORM model — persists login audit records for brute-force detection."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LoginAttempt(Base):
    """Audit record for every login attempt — persisted for rate limiting and forensics.

    success=True rows represent successful logins; False rows represent failures.
    The rate limiter queries only success=False rows when enforcing per-IP and global limits.
    """

    __tablename__ = "login_attempts"
    __table_args__ = (
        Index("ix_login_attempts_ip_attempted", "ip", "attempted_at"),
        Index("ix_login_attempts_attempted", "attempted_at"),
        Index("ix_login_attempts_success_attempted", "success", "attempted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)  # IPv6-compatible
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(  # ADDED
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
