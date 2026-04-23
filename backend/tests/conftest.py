"""Pytest fixtures for async tests.

Tests use SQLite in-memory via aiosqlite — decoupled from production MySQL.
"""

from collections.abc import AsyncGenerator
from typing import Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import app.db.base as db_base
from app.core.config import Settings, get_settings
from app.db.base import Base, get_db_session
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")  # type: ignore[misc]  # pytest-asyncio fixture typing
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a shared in-memory SQLite engine for the test session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture  # type: ignore[misc]  # pytest-asyncio fixture typing
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional AsyncSession per test — rolls back after each test."""
    session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture  # type: ignore[misc]  # pytest-asyncio fixture typing
async def async_client(
    db_session: AsyncSession,
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with DB overrides pointing to in-memory SQLite.

    Also patches app.db.base.AsyncSessionLocal so that /health (which imports
    it at call time) also uses the test SQLite engine.
    """

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    def override_get_settings() -> Settings:
        return Settings(
            database_url=TEST_DATABASE_URL,
            jwt_secret_key="test-secret",
        )

    # Patch the module-level AsyncSessionLocal used by /health endpoint
    original_session_local = db_base.AsyncSessionLocal
    test_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    db_base.AsyncSessionLocal = test_session_factory  # type: ignore[assignment]  # module-level patch

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_settings] = override_get_settings

    transport = ASGITransport(app=app)  # type: ignore[arg-type]  # httpx/starlette type mismatch
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    db_base.AsyncSessionLocal = original_session_local  # type: ignore[assignment]  # restoring original


def pytest_configure(config: Any) -> None:
    """Register custom markers."""
