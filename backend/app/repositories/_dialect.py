"""Dialect detection helper for SQLAlchemy repository layer."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


def get_dialect_name(session: AsyncSession) -> str:
    """Return the dialect name for the given AsyncSession's bind.

    Args:
        session: Active AsyncSession.

    Returns:
        Dialect name string, e.g. "mysql", "sqlite", "postgresql".
    """
    bind = session.get_bind()
    if bind is None:
        return "sqlite"
    return bind.dialect.name
