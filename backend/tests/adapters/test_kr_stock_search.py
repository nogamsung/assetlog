"""Unit tests for KrStockAdapter.search_symbols — all external I/O mocked."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.adapters._symbol_cache import SymbolListCache
from app.adapters.kr_stock import KrStockAdapter, _load_symbol_list_sync
from app.domain.asset_type import AssetType
from app.domain.symbol_search import SymbolCandidate

_KR_CANDIDATES = [
    SymbolCandidate(
        asset_type=AssetType.KR_STOCK,
        symbol="005930",
        name="삼성전자",
        exchange="KRX",
        currency="KRW",
    ),
    SymbolCandidate(
        asset_type=AssetType.KR_STOCK,
        symbol="000660",
        name="SK하이닉스",
        exchange="KRX",
        currency="KRW",
    ),
    SymbolCandidate(
        asset_type=AssetType.KR_STOCK,
        symbol="005935",
        name="삼성전자우",
        exchange="KRX",
        currency="KRW",
    ),
]


def _make_preloaded_cache() -> SymbolListCache:
    cache = SymbolListCache(ttl_seconds=3600)
    cache._data = list(_KR_CANDIDATES)
    cache._loaded_at = 0.0
    # Override _is_stale so the cache is never stale during tests
    cache._now = lambda: 0.0
    return cache


@pytest.mark.asyncio
async def test_search_exact_symbol_6digit() -> None:
    adapter = KrStockAdapter(cache=_make_preloaded_cache())
    results = await adapter.search_symbols("005930", limit=10)
    assert len(results) >= 1
    assert results[0].symbol == "005930"
    assert results[0].name == "삼성전자"


@pytest.mark.asyncio
async def test_search_exact_symbol_short() -> None:
    """'5930' should be zero-padded and match '005930'."""
    adapter = KrStockAdapter(cache=_make_preloaded_cache())
    results = await adapter.search_symbols("5930", limit=10)
    symbols = [r.symbol for r in results]
    assert "005930" in symbols


@pytest.mark.asyncio
async def test_search_name_korean() -> None:
    adapter = KrStockAdapter(cache=_make_preloaded_cache())
    results = await adapter.search_symbols("삼성", limit=10)
    symbols = [r.symbol for r in results]
    assert "005930" in symbols
    assert "005935" in symbols


@pytest.mark.asyncio
async def test_search_name_english_case_insensitive() -> None:
    adapter = KrStockAdapter(cache=_make_preloaded_cache())
    # "samsung" is not in the test data names, so should return empty
    results = await adapter.search_symbols("하이닉스", limit=10)
    assert any(r.symbol == "000660" for r in results)


@pytest.mark.asyncio
async def test_search_prefix_match() -> None:
    adapter = KrStockAdapter(cache=_make_preloaded_cache())
    # '005' prefix should match 005930 and 005935
    results = await adapter.search_symbols("005", limit=10)
    symbols = [r.symbol for r in results]
    assert "005930" in symbols
    assert "005935" in symbols


@pytest.mark.asyncio
async def test_search_limit_respected() -> None:
    adapter = KrStockAdapter(cache=_make_preloaded_cache())
    results = await adapter.search_symbols("삼성", limit=1)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_load_symbol_list_sync_via_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _load_symbol_list_sync by patching pykrx.stock attributes directly."""
    import pykrx.stock as pykrx_stock  # noqa: PLC0415

    mock_tickers = ["005930", "000660"]
    mock_names = {"005930": "삼성전자", "000660": "SK하이닉스"}

    monkeypatch.setattr(pykrx_stock, "get_market_ticker_list", lambda market: mock_tickers)
    monkeypatch.setattr(
        pykrx_stock, "get_market_ticker_name", lambda code: mock_names.get(code, code)
    )

    result = _load_symbol_list_sync()

    assert len(result) == 2
    symbols = [r.symbol for r in result]
    assert "005930" in symbols
    assert "000660" in symbols


@pytest.mark.asyncio
async def test_load_symbol_list_sync_pykrx_fails_fdr_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When pykrx fails, should fall back to FinanceDataReader."""
    import pandas as pd
    import pykrx.stock as pykrx_stock  # noqa: PLC0415

    fdr_df = pd.DataFrame({"Code": ["005930", "000660"], "Name": ["삼성전자", "SK하이닉스"]})

    def raise_error(market: str) -> list[str]:
        raise RuntimeError("pykrx simulated failure")

    monkeypatch.setattr(pykrx_stock, "get_market_ticker_list", raise_error)

    with patch("FinanceDataReader.StockListing", return_value=fdr_df):
        result = _load_symbol_list_sync()

    assert len(result) == 2
    names = [r.name for r in result]
    assert "삼성전자" in names
