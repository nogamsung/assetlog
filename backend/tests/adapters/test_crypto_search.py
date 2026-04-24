"""Unit tests for CryptoAdapter.search_symbols — ccxt mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters._symbol_cache import SymbolListCache
from app.adapters.crypto import CryptoAdapter, _load_markets_async
from app.domain.asset_type import AssetType
from app.domain.symbol_search import SymbolCandidate

_BINANCE_MARKETS = {
    "BTC/USDT": {
        "active": True,
        "base": "BTC",
        "quote": "USDT",
        "baseName": "Bitcoin",
    },
    "BTC/BUSD": {
        "active": True,
        "base": "BTC",
        "quote": "BUSD",
        "baseName": "Bitcoin",
    },
    "ETH/USDT": {
        "active": True,
        "base": "ETH",
        "quote": "USDT",
        "baseName": "Ethereum",
    },
}

_PRELOADED_CANDIDATES = [
    SymbolCandidate(
        asset_type=AssetType.CRYPTO,
        symbol="BTC/USDT",
        name="Bitcoin",
        exchange="binance",
        currency="USDT",
    ),
    SymbolCandidate(
        asset_type=AssetType.CRYPTO,
        symbol="BTC/BUSD",
        name="Bitcoin",
        exchange="binance",
        currency="BUSD",
    ),
    SymbolCandidate(
        asset_type=AssetType.CRYPTO,
        symbol="ETH/USDT",
        name="Ethereum",
        exchange="binance",
        currency="USDT",
    ),
]


def _make_preloaded_cache() -> SymbolListCache:
    cache = SymbolListCache(ttl_seconds=3600)
    cache._data = list(_PRELOADED_CANDIDATES)
    cache._loaded_at = 0.0
    cache._now = lambda: 0.0
    return cache


@pytest.mark.asyncio
async def test_search_base_prefix_btc() -> None:
    adapter = CryptoAdapter(cache=_make_preloaded_cache())
    results = await adapter.search_symbols("BTC", limit=10)
    symbols = [r.symbol for r in results]
    assert "BTC/USDT" in symbols
    assert "BTC/BUSD" in symbols
    assert "ETH/USDT" not in symbols


@pytest.mark.asyncio
async def test_search_exact_pair_btc_usdt() -> None:
    adapter = CryptoAdapter(cache=_make_preloaded_cache())
    results = await adapter.search_symbols("BTC/USDT", limit=10)
    assert len(results) >= 1
    assert results[0].symbol == "BTC/USDT"


@pytest.mark.asyncio
async def test_search_exact_match_prioritised_over_prefix() -> None:
    """Exact match should appear before prefix matches."""
    adapter = CryptoAdapter(cache=_make_preloaded_cache())
    results = await adapter.search_symbols("BTC/USDT", limit=10)
    # exact comes first
    assert results[0].symbol == "BTC/USDT"


@pytest.mark.asyncio
async def test_search_limit_respected() -> None:
    adapter = CryptoAdapter(cache=_make_preloaded_cache())
    results = await adapter.search_symbols("BTC", limit=1)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_search_no_match_returns_empty() -> None:
    adapter = CryptoAdapter(cache=_make_preloaded_cache())
    results = await adapter.search_symbols("XYZ", limit=10)
    assert results == []


@pytest.mark.asyncio
async def test_search_exchange_exception_returns_empty() -> None:
    """When market load fails, search_symbols returns empty list gracefully."""
    failing_cache = SymbolListCache(ttl_seconds=3600)

    async def _failing_loader() -> list[SymbolCandidate]:
        raise RuntimeError("ccxt down")

    # Patch get_or_load to raise
    async def _raise(_: object) -> list[SymbolCandidate]:
        raise RuntimeError("ccxt down")

    adapter = CryptoAdapter(cache=failing_cache)
    # Override the loader to force failure
    with patch.object(failing_cache, "get_or_load", side_effect=RuntimeError("ccxt down")):
        results = await adapter.search_symbols("BTC", limit=10)

    assert results == []


@pytest.mark.asyncio
async def test_load_markets_async_success() -> None:
    """Test _load_markets_async with mocked ccxt exchange."""
    mock_exchange = AsyncMock()
    mock_exchange.load_markets = AsyncMock(return_value=_BINANCE_MARKETS)
    mock_exchange.close = AsyncMock()

    mock_cls = MagicMock(return_value=mock_exchange)

    import ccxt.async_support as ccxt_mod  # noqa: PLC0415

    with patch.object(ccxt_mod, "binance", mock_cls):
        result = await _load_markets_async("binance")

    assert len(result) == 3
    symbols = [r.symbol for r in result]
    assert "BTC/USDT" in symbols
    assert "ETH/USDT" in symbols


@pytest.mark.asyncio
async def test_load_markets_async_inactive_filtered() -> None:
    """Inactive markets should be excluded."""
    markets: dict[str, object] = {
        "BTC/USDT": {"active": True, "base": "BTC", "quote": "USDT"},
        "DEAD/USDT": {"active": False, "base": "DEAD", "quote": "USDT"},
    }
    mock_exchange = AsyncMock()
    mock_exchange.load_markets = AsyncMock(return_value=markets)
    mock_exchange.close = AsyncMock()

    mock_cls = MagicMock(return_value=mock_exchange)

    import ccxt.async_support as ccxt_mod  # noqa: PLC0415

    with patch.object(ccxt_mod, "binance", mock_cls):
        result = await _load_markets_async("binance")

    symbols = [r.symbol for r in result]
    assert "BTC/USDT" in symbols
    assert "DEAD/USDT" not in symbols
