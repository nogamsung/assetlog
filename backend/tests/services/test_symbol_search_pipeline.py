"""Tests for SymbolService.search pipeline — DB first, adapter fallback, graceful degrade."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.asset_type import AssetType
from app.domain.symbol_search import SymbolCandidate
from app.models.asset_symbol import AssetSymbol
from app.services.symbol import SymbolService

_NOW = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)


def _make_asset_symbol(symbol: str, asset_type: AssetType = AssetType.US_STOCK) -> AssetSymbol:
    row = MagicMock(spec=AssetSymbol)
    row.id = 1
    row.symbol = symbol
    row.asset_type = asset_type
    row.exchange = "NASDAQ"
    row.name = f"{symbol} Corp"
    row.currency = "USD"
    row.last_synced_at = None
    return row


def _make_candidate(symbol: str, asset_type: AssetType = AssetType.US_STOCK) -> SymbolCandidate:
    return SymbolCandidate(
        asset_type=asset_type,
        symbol=symbol,
        name=f"{symbol} Corp",
        exchange="NASDAQ",
        currency="USD",
    )


def _make_service(
    db_hits: list[AssetSymbol],
    adapter_candidates: list[SymbolCandidate] | None = None,
    adapter_raises: Exception | None = None,
    asset_type: AssetType = AssetType.US_STOCK,
) -> tuple[SymbolService, MagicMock, MagicMock]:
    repo = MagicMock()
    repo.search = AsyncMock(return_value=db_hits)
    repo.upsert_many = AsyncMock(return_value=[])

    adapter = MagicMock()
    if adapter_raises is not None:
        adapter.search_symbols = AsyncMock(side_effect=adapter_raises)
    else:
        adapter.search_symbols = AsyncMock(return_value=adapter_candidates or [])

    service = SymbolService(repository=repo, adapters={asset_type: adapter})
    return service, repo, adapter


@pytest.mark.asyncio
async def test_db_hits_sufficient_no_adapter_call() -> None:
    """When DB hits fill the limit, adapter must not be called."""
    db_hits = [_make_asset_symbol("AAPL"), _make_asset_symbol("TSLA")]
    service, repo, adapter = _make_service(db_hits=db_hits)

    result = await service.search(q="AAPL", asset_type=AssetType.US_STOCK, limit=2)

    adapter.search_symbols.assert_not_called()
    assert len(result) == 2


@pytest.mark.asyncio
async def test_db_hits_insufficient_adapter_called() -> None:
    """When DB hits < limit, adapter should be called."""
    db_hit = _make_asset_symbol("AAPL")
    candidate = _make_candidate("TSLA")

    persisted = _make_asset_symbol("TSLA")
    service, repo, adapter = _make_service(
        db_hits=[db_hit],
        adapter_candidates=[candidate],
    )
    repo.upsert_many = AsyncMock(return_value=[persisted])

    result = await service.search(q="A", asset_type=AssetType.US_STOCK, limit=3)

    adapter.search_symbols.assert_called_once()
    repo.upsert_many.assert_called_once()
    assert len(result) == 2


@pytest.mark.asyncio
async def test_empty_query_no_adapter_call() -> None:
    """Empty q must not trigger adapter fallback (US-S6)."""
    service, repo, adapter = _make_service(db_hits=[])

    await service.search(q="", asset_type=AssetType.US_STOCK, limit=20)

    adapter.search_symbols.assert_not_called()


@pytest.mark.asyncio
async def test_whitespace_query_no_adapter_call() -> None:
    service, repo, adapter = _make_service(db_hits=[])

    await service.search(q="   ", asset_type=AssetType.US_STOCK, limit=20)

    adapter.search_symbols.assert_not_called()


@pytest.mark.asyncio
async def test_no_asset_type_no_adapter_call() -> None:
    """asset_type=None must skip adapter fallback (US-S4)."""
    service, repo, adapter = _make_service(db_hits=[])

    await service.search(q="AAPL", asset_type=None, limit=20)

    adapter.search_symbols.assert_not_called()


@pytest.mark.asyncio
async def test_adapter_exception_graceful_degrade() -> None:
    """Adapter exception must not propagate — DB hits still returned (US-S5)."""
    db_hit = _make_asset_symbol("AAPL")
    service, repo, adapter = _make_service(
        db_hits=[db_hit],
        adapter_raises=RuntimeError("external down"),
    )

    result = await service.search(q="AAPL", asset_type=AssetType.US_STOCK, limit=10)

    # DB hits still returned
    assert len(result) == 1
    assert result[0].symbol == "AAPL"
    # No upsert when adapter fails
    repo.upsert_many.assert_not_called()


@pytest.mark.asyncio
async def test_deduplication_skips_db_duplicates() -> None:
    """Adapter candidates already in DB should not be upserted again."""
    db_hit = _make_asset_symbol("AAPL")
    # Candidate with same (asset_type, symbol, exchange) as the DB hit
    dup_candidate = SymbolCandidate(
        asset_type=AssetType.US_STOCK,
        symbol="AAPL",
        name="Apple Inc.",
        exchange="NASDAQ",
        currency="USD",
    )
    service, repo, adapter = _make_service(
        db_hits=[db_hit],
        adapter_candidates=[dup_candidate],
    )
    repo.upsert_many = AsyncMock(return_value=[])

    await service.search(q="AAPL", asset_type=AssetType.US_STOCK, limit=10)

    # No new candidates → upsert_many called with empty list
    call_args = repo.upsert_many.call_args
    candidates_arg = call_args[0][0] if call_args else []
    assert list(candidates_arg) == []


@pytest.mark.asyncio
async def test_no_adapter_for_asset_type_returns_db_only() -> None:
    """When no adapter is registered for the asset_type, return DB hits only."""
    db_hit = _make_asset_symbol("005930", AssetType.KR_STOCK)
    repo = MagicMock()
    repo.search = AsyncMock(return_value=[db_hit])
    repo.upsert_many = AsyncMock(return_value=[])

    # No adapters registered at all
    service = SymbolService(repository=repo, adapters={})

    result = await service.search(q="005930", asset_type=AssetType.KR_STOCK, limit=10)

    repo.upsert_many.assert_not_called()
    assert len(result) == 1
