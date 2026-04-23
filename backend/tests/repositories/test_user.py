"""Unit tests for UserRepository — uses SQLite in-memory via conftest."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user import UserRepository


class TestUserRepositoryCreate:
    async def test_사용자를_생성하면_id가_할당된다(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        user = await repo.create(email="test@example.com", password_hash="hashed")

        assert user.id is not None
        assert user.email == "test@example.com"

    async def test_사용자를_생성하면_email이_저장된다(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        user = await repo.create(email="store@example.com", password_hash="hashed")

        assert user.email == "store@example.com"


class TestUserRepositoryGetByEmail:
    async def test_존재하는_이메일로_조회하면_반환된다(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        created = await repo.create(email="lookup@example.com", password_hash="hashed")

        found = await repo.get_by_email("lookup@example.com")

        assert found is not None
        assert found.id == created.id

    async def test_없는_이메일로_조회하면_None이_반환된다(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)

        result = await repo.get_by_email("missing@example.com")

        assert result is None


class TestUserRepositoryGetById:
    async def test_존재하는_id로_조회하면_반환된다(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        created = await repo.create(email="byid@example.com", password_hash="hashed")

        found = await repo.get_by_id(created.id)

        assert found is not None
        assert found.email == "byid@example.com"

    async def test_없는_id로_조회하면_None이_반환된다(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)

        result = await repo.get_by_id(99999)

        assert result is None
