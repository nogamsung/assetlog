"""Unit tests for UsStockAdapter.search_symbols — yfinance mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.adapters.normalize import normalize_us_exchange_code
from app.adapters.us_stock import UsStockAdapter, _fetch_info_sync


def _mock_yf_ticker(info: dict[str, object]) -> MagicMock:
    mock = MagicMock()
    mock.info = info
    return mock


@pytest.mark.asyncio
async def test_search_exact_match() -> None:
    adapter = UsStockAdapter()
    apple_info: dict[str, object] = {
        "shortName": "Apple Inc.",
        "exchange": "NMS",
        "currency": "USD",
    }

    with patch("yfinance.Ticker", return_value=_mock_yf_ticker(apple_info)):
        results = await adapter.search_symbols("AAPL", limit=5)

    assert len(results) == 1
    assert results[0].symbol == "AAPL"
    assert results[0].name == "Apple Inc."
    assert results[0].exchange == "NASDAQ"
    assert results[0].currency == "USD"


@pytest.mark.asyncio
async def test_search_lowercase_normalised() -> None:
    """Lowercase query should be normalised to uppercase before lookup."""
    adapter = UsStockAdapter()
    info: dict[str, object] = {"shortName": "Apple Inc.", "exchange": "NMS", "currency": "USD"}

    with patch("yfinance.Ticker", return_value=_mock_yf_ticker(info)):
        results = await adapter.search_symbols("aapl", limit=5)

    assert len(results) == 1
    assert results[0].symbol == "AAPL"


@pytest.mark.asyncio
async def test_search_no_shortname_returns_empty() -> None:
    """If info has no shortName or longName, return empty list."""
    adapter = UsStockAdapter()
    info: dict[str, object] = {"exchange": "NMS"}  # no name fields

    with patch("yfinance.Ticker", return_value=_mock_yf_ticker(info)):
        results = await adapter.search_symbols("UNKNOWN", limit=5)

    assert results == []


@pytest.mark.asyncio
async def test_search_exception_returns_empty() -> None:
    """Exception from yfinance should be swallowed and empty list returned."""
    adapter = UsStockAdapter()

    with patch("yfinance.Ticker", side_effect=RuntimeError("yf down")):
        results = await adapter.search_symbols("AAPL", limit=5)

    assert results == []


@pytest.mark.asyncio
async def test_search_cached_on_second_call() -> None:
    """Second call for same ticker should not call yfinance again."""
    adapter = UsStockAdapter()
    info: dict[str, object] = {"shortName": "Apple Inc.", "exchange": "NMS", "currency": "USD"}

    with patch("yfinance.Ticker", return_value=_mock_yf_ticker(info)) as mock_ticker:
        await adapter.search_symbols("AAPL", limit=5)
        await adapter.search_symbols("AAPL", limit=5)

    # yfinance.Ticker called only once (second call hits instance cache)
    assert mock_ticker.call_count == 1


@pytest.mark.asyncio
async def test_search_negative_cache() -> None:
    """Negative cache: failed lookup should not be retried."""
    adapter = UsStockAdapter()
    info: dict[str, object] = {}  # no name → None result

    with patch("yfinance.Ticker", return_value=_mock_yf_ticker(info)) as mock_ticker:
        r1 = await adapter.search_symbols("BADTICKER", limit=5)
        r2 = await adapter.search_symbols("BADTICKER", limit=5)

    assert r1 == []
    assert r2 == []
    assert mock_ticker.call_count == 1


def test_normalize_us_exchange_code_nms() -> None:
    assert normalize_us_exchange_code("NMS") == "NASDAQ"


def test_normalize_us_exchange_code_nyq() -> None:
    assert normalize_us_exchange_code("NYQ") == "NYSE"


def test_normalize_us_exchange_code_unknown_passthrough() -> None:
    assert normalize_us_exchange_code("XYZ") == "XYZ"


def test_fetch_info_sync_success() -> None:
    info: dict[str, object] = {"shortName": "Tesla Inc.", "exchange": "NMS", "currency": "USD"}
    with patch("yfinance.Ticker", return_value=_mock_yf_ticker(info)):
        result = _fetch_info_sync("TSLA")
    assert result is not None
    assert result.symbol == "TSLA"
    assert result.exchange == "NASDAQ"


def test_fetch_info_sync_no_name_returns_none() -> None:
    info: dict[str, object] = {}
    with patch("yfinance.Ticker", return_value=_mock_yf_ticker(info)):
        result = _fetch_info_sync("UNKNOWN")
    assert result is None
