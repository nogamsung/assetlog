"""Unit tests for SymbolListCache — TTL, single-flight, invalidate."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import pytest

from app.adapters._symbol_cache import SymbolListCache
from app.domain.asset_type import AssetType
from app.domain.symbol_search import SymbolCandidate

_SAMPLE = SymbolCandidate(
    asset_type=AssetType.US_STOCK,
    symbol="AAPL",
    name="Apple Inc.",
    exchange="NASDAQ",
    currency="USD",
)


async def _make_loader(
    items: list[SymbolCandidate], call_count: list[int]
) -> Callable[[], Awaitable[list[SymbolCandidate]]]:
    async def _loader() -> list[SymbolCandidate]:
        call_count.append(1)
        return items

    return _loader


@pytest.mark.asyncio
async def test_first_call_loads_data() -> None:
    cache = SymbolListCache(ttl_seconds=60)
    calls: list[int] = []
    loader = await _make_loader([_SAMPLE], calls)

    result = await cache.get_or_load(loader)
    assert result == [_SAMPLE]
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_second_call_uses_cache() -> None:
    cache = SymbolListCache(ttl_seconds=60)
    calls: list[int] = []
    loader = await _make_loader([_SAMPLE], calls)

    await cache.get_or_load(loader)
    await cache.get_or_load(loader)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_ttl_expiry_triggers_reload() -> None:
    """Using injected now function to simulate TTL expiry without sleeping."""
    clock = [0.0]

    def fake_now() -> float:
        return clock[0]

    cache = SymbolListCache(ttl_seconds=1.0, now=fake_now)
    calls: list[int] = []
    loader = await _make_loader([_SAMPLE], calls)

    await cache.get_or_load(loader)
    assert len(calls) == 1

    # Advance clock past TTL
    clock[0] = 2.0
    await cache.get_or_load(loader)
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_invalidate_forces_reload() -> None:
    cache = SymbolListCache(ttl_seconds=3600)
    calls: list[int] = []
    loader = await _make_loader([_SAMPLE], calls)

    await cache.get_or_load(loader)
    cache.invalidate()
    assert not cache.is_loaded()

    await cache.get_or_load(loader)
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_single_flight_under_concurrency() -> None:
    """Concurrent callers should only trigger one loader invocation."""
    cache = SymbolListCache(ttl_seconds=60)
    calls: list[int] = []

    async def slow_loader() -> list[SymbolCandidate]:
        calls.append(1)
        await asyncio.sleep(0)
        return [_SAMPLE]

    results = await asyncio.gather(
        cache.get_or_load(slow_loader),
        cache.get_or_load(slow_loader),
        cache.get_or_load(slow_loader),
    )
    assert all(r == [_SAMPLE] for r in results)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_is_loaded_false_before_first_call() -> None:
    cache = SymbolListCache()
    assert not cache.is_loaded()


@pytest.mark.asyncio
async def test_is_loaded_true_after_first_call() -> None:
    cache = SymbolListCache()
    calls: list[int] = []
    loader = await _make_loader([_SAMPLE], calls)
    await cache.get_or_load(loader)
    assert cache.is_loaded()
