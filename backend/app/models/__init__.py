"""ORM models — imported here so Alembic autogenerate can detect all tables."""

from app.models.user import User

__all__ = ["User"]
