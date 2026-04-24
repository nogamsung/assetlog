"""Tests for AssetSymbolRepository.upsert_many — SQLite in-memory."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.asset_type import AssetType
from app.domain.symbol_search import SymbolCandidate
from app.repositories.asset_symbol import AssetSymbolRepository

_NOW = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)

_CANDIDATES = [
    SymbolCandidate(
        asset_type=AssetType.US_STOCK,
        symbol="AAPL",
        name="Apple Inc.",
        exchange="NASDAQ",
        currency="USD",
    ),
    SymbolCandidate(
        asset_type=AssetType.US_STOCK,
        symbol="TSLA",
        name="Tesla Inc.",
        exchange="NASDAQ",
        currency="USD",
    ),
]


@pytest.mark.asyncio
async def test_upsert_many_insert_new(db_session: AsyncSession) -> None:
    repo = AssetSymbolRepository(db_session)
    result = await repo.upsert_many(_CANDIDATES, now=_NOW)

    assert len(result) == 2
    symbols = {r.symbol for r in result}
    assert symbols == {"AAPL", "TSLA"}

    for row in result:
        # SQLite stores datetime without timezone; compare naive equivalent.
        assert row.last_synced_at is not None
        synced = row.last_synced_at
        if synced.tzinfo is not None:
            assert synced == _NOW
        else:
            assert synced == _NOW.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_upsert_many_update_existing(db_session: AsyncSession) -> None:
    repo = AssetSymbolRepository(db_session)

    # Insert initial row
    await repo.upsert_many([_CANDIDATES[0]], now=_NOW)

    # Update with new name
    updated = SymbolCandidate(
        asset_type=AssetType.US_STOCK,
        symbol="AAPL",
        name="Apple Inc. Updated",
        exchange="NASDAQ",
        currency="USD",
    )
    new_now = datetime(2026, 4, 25, 0, 0, 0, tzinfo=UTC)
    result = await repo.upsert_many([updated], now=new_now)

    assert len(result) == 1
    assert result[0].name == "Apple Inc. Updated"
    synced = result[0].last_synced_at
    assert synced is not None
    if synced.tzinfo is not None:
        assert synced == new_now
    else:
        assert synced == new_now.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_upsert_many_empty_input(db_session: AsyncSession) -> None:
    repo = AssetSymbolRepository(db_session)
    result = await repo.upsert_many([], now=_NOW)
    assert result == []


@pytest.mark.asyncio
async def test_upsert_many_preserves_input_order(db_session: AsyncSession) -> None:
    repo = AssetSymbolRepository(db_session)
    result = await repo.upsert_many(_CANDIDATES, now=_NOW)

    assert result[0].symbol == "AAPL"
    assert result[1].symbol == "TSLA"


@pytest.mark.asyncio
async def test_upsert_many_idempotent(db_session: AsyncSession) -> None:
    """Calling upsert_many twice with same data should not error."""
    repo = AssetSymbolRepository(db_session)
    r1 = await repo.upsert_many([_CANDIDATES[0]], now=_NOW)
    r2 = await repo.upsert_many([_CANDIDATES[0]], now=_NOW)

    assert r1[0].symbol == r2[0].symbol == "AAPL"
