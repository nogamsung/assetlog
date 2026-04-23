"""User repository — pure data access, no business logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Async CRUD operations for the User model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        """Return the User with the given email, or None if not found."""
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        """Return the User with the given primary key, or None if not found."""
        stmt = select(User).where(User.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, email: str, password_hash: str) -> User:
        """Persist a new User row and return the refreshed instance."""
        user = User(email=email, password_hash=password_hash)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user
