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
from app.core.principal import OWNER_ID
from app.core.security import create_access_token
from app.db.base import Base, get_db_session
from app.main import app
from app.models.asset_symbol import AssetSymbol
from app.models.user_asset import UserAsset

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")  # type: ignore[misc]
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


@pytest_asyncio.fixture  # type: ignore[misc]
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


@pytest_asyncio.fixture  # type: ignore[misc]
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

    original_session_local = db_base.AsyncSessionLocal
    test_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    db_base.AsyncSessionLocal = test_session_factory  # type: ignore[assignment]

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_settings] = override_get_settings

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    db_base.AsyncSessionLocal = original_session_local  # type: ignore[assignment]


@pytest_asyncio.fixture  # type: ignore[misc]
async def authenticated_client(
    db_session: AsyncSession,
    test_engine: AsyncEngine,
) -> AsyncGenerator[Any, None]:
    """Factory fixture that returns an AsyncClient already authenticated as the owner.

    Usage::

        async def test_something(authenticated_client):
            client = await authenticated_client()
            response = await client.get("/api/user-assets")
    """

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    def override_get_settings() -> Settings:
        return Settings(
            database_url=TEST_DATABASE_URL,
            jwt_secret_key="test-secret",
        )

    original_session_local = db_base.AsyncSessionLocal
    test_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    db_base.AsyncSessionLocal = test_session_factory  # type: ignore[assignment]

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_settings] = override_get_settings

    transport = ASGITransport(app=app)  # type: ignore[arg-type]

    async def _make_client() -> AsyncClient:
        token = create_access_token(subject=OWNER_ID)
        client = AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies={"access_token": token},
        )
        await client.__aenter__()
        return client

    yield _make_client

    app.dependency_overrides.clear()
    db_base.AsyncSessionLocal = original_session_local  # type: ignore[assignment]


@pytest_asyncio.fixture  # type: ignore[misc]
async def asset_symbol_factory(
    db_session: AsyncSession,
) -> AsyncGenerator[Any, None]:
    """Factory fixture that creates AssetSymbol rows in the test DB.

    Usage::

        async def test_something(asset_symbol_factory):
            sym = await asset_symbol_factory(symbol="BTC", asset_type=AssetType.CRYPTO)
    """

    async def _make(
        symbol: str = "BTC",
        exchange: str = "upbit",
        name: str = "Bitcoin",
        currency: str = "KRW",
        asset_type: Any = None,
    ) -> AssetSymbol:
        from app.domain.asset_type import AssetType
        from app.repositories.asset_symbol import AssetSymbolRepository

        resolved_type = asset_type if asset_type is not None else AssetType.CRYPTO
        repo = AssetSymbolRepository(db_session)
        return await repo.create(
            asset_type=resolved_type,
            symbol=symbol,
            exchange=exchange,
            name=name,
            currency=currency,
        )

    yield _make


@pytest_asyncio.fixture  # type: ignore[misc]
async def user_asset_factory(
    db_session: AsyncSession,
) -> AsyncGenerator[Any, None]:
    """Factory fixture that creates UserAsset rows in the test DB.

    Usage::

        async def test_something(user_asset_factory, asset_symbol_factory):
            sym = await asset_symbol_factory()
            ua = await user_asset_factory(asset_symbol=sym)
    """

    async def _make(
        asset_symbol: AssetSymbol,
        memo: str | None = None,
    ) -> UserAsset:
        from app.repositories.user_asset import UserAssetRepository

        repo = UserAssetRepository(db_session)
        return await repo.create(
            asset_symbol_id=asset_symbol.id,
            memo=memo,
        )

    yield _make


def pytest_configure(config: Any) -> None:
    """Register custom markers."""
