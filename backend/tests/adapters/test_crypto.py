"""Unit tests for the CryptoAdapter — all ccxt calls are mocked."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.crypto import CryptoAdapter
from app.domain.asset_type import AssetType
from app.domain.price_refresh import SymbolRef


def _make_ref(
    symbol: str = "BTC/USDT",
    exchange: str = "upbit",
    asset_symbol_id: int = 1,
) -> SymbolRef:
    return SymbolRef(
        asset_type=AssetType.CRYPTO,
        symbol=symbol,
        exchange=exchange,
        asset_symbol_id=asset_symbol_id,
    )


def _ccxt_exchange_mock(tickers: dict[str, dict[str, float | None]]) -> MagicMock:
    """Create a mock ccxt async exchange that returns *tickers* from fetch_tickers."""
    mock = MagicMock()
    mock.fetch_tickers = AsyncMock(return_value=tickers)
    mock.close = AsyncMock()
    return mock


class TestCryptoAdapterFetchBatch:
    @pytest.fixture()
    def adapter(self) -> CryptoAdapter:
        return CryptoAdapter()

    def test_asset_type_is_crypto(self, adapter: CryptoAdapter) -> None:
        assert adapter.asset_type == AssetType.CRYPTO

    async def test_empty_symbols_returns_empty_result(self, adapter: CryptoAdapter) -> None:
        result = await adapter.fetch_batch([])
        assert result.successes == []
        assert result.failures == []

    async def test_successful_upbit_fetch(self, adapter: CryptoAdapter) -> None:
        refs = [_make_ref("BTC/KRW", "upbit")]

        upbit_mock = _ccxt_exchange_mock({"BTC/KRW": {"last": 90000000.0}})

        with patch("ccxt.async_support.upbit", return_value=upbit_mock):
            result = await adapter.fetch_batch(refs)

        assert len(result.successes) == 1
        assert len(result.failures) == 0
        assert result.successes[0].price == Decimal("90000000.0")
        assert result.successes[0].currency == "KRW"

    async def test_binance_fallback_when_upbit_misses(self, adapter: CryptoAdapter) -> None:
        """Symbol not in Upbit response should try Binance."""
        refs = [_make_ref("BTC/USDT", "binance")]

        upbit_mock = _ccxt_exchange_mock({})  # no data for BTC/USDT
        binance_mock = _ccxt_exchange_mock({"BTC/USDT": {"last": 65000.0}})

        with (
            patch("ccxt.async_support.upbit", return_value=upbit_mock),
            patch("ccxt.async_support.binance", return_value=binance_mock),
        ):
            result = await adapter.fetch_batch(refs)

        assert len(result.successes) == 1
        assert result.successes[0].price == Decimal("65000.0")
        assert result.successes[0].currency == "USDT"

    async def test_failure_when_both_exchanges_miss(self, adapter: CryptoAdapter) -> None:
        refs = [_make_ref("UNKNOWN/USDT", "binance")]

        upbit_mock = _ccxt_exchange_mock({})
        binance_mock = _ccxt_exchange_mock({})

        with (
            patch("ccxt.async_support.upbit", return_value=upbit_mock),
            patch("ccxt.async_support.binance", return_value=binance_mock),
        ):
            result = await adapter.fetch_batch(refs)

        assert len(result.failures) == 1
        assert result.failures[0].ref.symbol == "UNKNOWN/USDT"

    async def test_upbit_bulk_failure_fallback_to_binance(self, adapter: CryptoAdapter) -> None:
        """If Upbit's fetch_tickers raises, all symbols should try Binance."""
        refs = [_make_ref("BTC/USDT", "binance")]

        upbit_mock = MagicMock()
        upbit_mock.fetch_tickers = AsyncMock(side_effect=RuntimeError("Upbit down"))
        upbit_mock.close = AsyncMock()

        binance_mock = _ccxt_exchange_mock({"BTC/USDT": {"last": 65000.0}})

        with (
            patch("ccxt.async_support.upbit", return_value=upbit_mock),
            patch("ccxt.async_support.binance", return_value=binance_mock),
        ):
            result = await adapter.fetch_batch(refs)

        assert len(result.successes) == 1

    async def test_price_is_decimal(self, adapter: CryptoAdapter) -> None:
        refs = [_make_ref("ETH/KRW", "upbit")]
        upbit_mock = _ccxt_exchange_mock({"ETH/KRW": {"last": 4500000.0}})

        with patch("ccxt.async_support.upbit", return_value=upbit_mock):
            result = await adapter.fetch_batch(refs)

        assert isinstance(result.successes[0].price, Decimal)

    async def test_upbit_legacy_symbol_normalised(self, adapter: CryptoAdapter) -> None:
        """KRW-BTC input should be normalised to BTC/KRW before query."""
        refs = [_make_ref("KRW-BTC", "upbit")]  # legacy format

        upbit_mock = _ccxt_exchange_mock({"BTC/KRW": {"last": 90000000.0}})

        called_with: list[list[str]] = []

        async def capture_fetch_tickers(pairs: list[str]) -> dict[str, dict[str, float | None]]:
            called_with.append(pairs)
            return {"BTC/KRW": {"last": 90000000.0}}

        upbit_mock.fetch_tickers = capture_fetch_tickers

        with patch("ccxt.async_support.upbit", return_value=upbit_mock):
            await adapter.fetch_batch(refs)

        # The pair passed to upbit should be normalised ccxt format
        assert any("BTC/KRW" in batch for batch in called_with)

    async def test_rate_limit_enabled(self, adapter: CryptoAdapter) -> None:
        """enableRateLimit must be passed when constructing the exchange."""
        refs = [_make_ref("BTC/KRW", "upbit")]

        created_with: list[dict[str, object]] = []

        def upbit_cls(config: dict[str, object]) -> MagicMock:
            created_with.append(config)
            m = _ccxt_exchange_mock({"BTC/KRW": {"last": 90000000.0}})
            return m

        with patch("ccxt.async_support.upbit", side_effect=upbit_cls):
            await adapter.fetch_batch(refs)

        assert len(created_with) == 1
        assert created_with[0].get("enableRateLimit") is True

    async def test_multiple_symbols_upbit(self, adapter: CryptoAdapter) -> None:
        refs = [
            _make_ref("BTC/KRW", "upbit", 1),
            _make_ref("ETH/KRW", "upbit", 2),
        ]
        upbit_mock = _ccxt_exchange_mock(
            {
                "BTC/KRW": {"last": 90000000.0},
                "ETH/KRW": {"last": 4500000.0},
            }
        )

        with patch("ccxt.async_support.upbit", return_value=upbit_mock):
            result = await adapter.fetch_batch(refs)

        assert len(result.successes) == 2
        assert len(result.failures) == 0
