"""Unit tests for the KrStockAdapter — all external calls are mocked."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.adapters.kr_stock import KrStockAdapter, _fetch_price_sync
from app.domain.asset_type import AssetType
from app.domain.price_refresh import SymbolRef


def _make_ref(symbol: str = "005930") -> SymbolRef:
    return SymbolRef(
        asset_type=AssetType.KR_STOCK,
        symbol=symbol,
        exchange="KRX",
        asset_symbol_id=1,
    )


class TestFetchPriceSync:
    def test_returns_decimal_from_pykrx(self) -> None:
        import pandas as pd

        mock_df = pd.DataFrame({"종가": [75000]})

        with patch("pykrx.stock.get_market_ohlcv", return_value=mock_df):
            price = _fetch_price_sync("005930")

        assert price == Decimal("75000")

    def test_falls_back_to_fdr_when_pykrx_raises(self) -> None:
        import pandas as pd

        mock_fdr_df = pd.DataFrame({"Close": [74000]})

        with (
            patch("pykrx.stock.get_market_ohlcv", side_effect=RuntimeError("network error")),
            patch("FinanceDataReader.DataReader", return_value=mock_fdr_df),
        ):
            price = _fetch_price_sync("005930")

        assert price == Decimal("74000")

    def test_falls_back_to_fdr_when_pykrx_returns_empty(self) -> None:
        import pandas as pd

        empty_df = pd.DataFrame({"종가": []})
        mock_fdr_df = pd.DataFrame({"Close": [73000]})

        with (
            patch("pykrx.stock.get_market_ohlcv", return_value=empty_df),
            patch("FinanceDataReader.DataReader", return_value=mock_fdr_df),
        ):
            price = _fetch_price_sync("005930")

        assert price == Decimal("73000")

    def test_raises_value_error_when_both_fail(self) -> None:
        import pandas as pd

        empty_fdr = pd.DataFrame({"Close": []})

        with (
            patch("pykrx.stock.get_market_ohlcv", side_effect=RuntimeError("fail")),
            patch("FinanceDataReader.DataReader", return_value=empty_fdr),
        ):
            with pytest.raises(ValueError, match="Both pykrx and FinanceDataReader failed"):
                _fetch_price_sync("005930")

    def test_pykrx_uses_most_recent_row(self) -> None:
        import pandas as pd

        # Multiple rows — only the last row should be used
        mock_df = pd.DataFrame({"종가": [70000, 71000, 72000]})

        with patch("pykrx.stock.get_market_ohlcv", return_value=mock_df):
            price = _fetch_price_sync("005930")

        assert price == Decimal("72000")


class TestKrStockAdapterFetchBatch:
    @pytest.fixture()
    def adapter(self) -> KrStockAdapter:
        return KrStockAdapter()

    def test_asset_type_is_kr_stock(self, adapter: KrStockAdapter) -> None:
        assert adapter.asset_type == AssetType.KR_STOCK

    async def test_returns_success_quote(self, adapter: KrStockAdapter) -> None:
        import pandas as pd

        mock_df = pd.DataFrame({"종가": [75000]})
        refs = [_make_ref("005930")]

        with patch("pykrx.stock.get_market_ohlcv", return_value=mock_df):
            result = await adapter.fetch_batch(refs)

        assert len(result.successes) == 1
        assert len(result.failures) == 0
        quote = result.successes[0]
        assert quote.ref == refs[0]
        assert quote.price == Decimal("75000")
        assert quote.currency == "KRW"
        assert isinstance(quote.fetched_at, datetime)

    async def test_isolates_failure_per_symbol(self, adapter: KrStockAdapter) -> None:
        import pandas as pd

        mock_df = pd.DataFrame({"종가": [75000]})
        empty_fdr = pd.DataFrame({"Close": []})

        refs = [
            _make_ref("005930"),
            SymbolRef(
                asset_type=AssetType.KR_STOCK,
                symbol="999999",
                exchange="KRX",
                asset_symbol_id=2,
            ),
        ]

        call_count = 0

        def pykrx_side_effect(start: str, end: str, ticker: str) -> object:
            nonlocal call_count
            call_count += 1
            if ticker == "005930":
                return mock_df
            raise RuntimeError("unknown ticker")

        with (
            patch("pykrx.stock.get_market_ohlcv", side_effect=pykrx_side_effect),
            patch("FinanceDataReader.DataReader", return_value=empty_fdr),
        ):
            result = await adapter.fetch_batch(refs)

        assert len(result.successes) == 1
        assert len(result.failures) == 1
        assert result.failures[0].ref.symbol == "999999"

    async def test_empty_symbols_returns_empty_result(self, adapter: KrStockAdapter) -> None:
        result = await adapter.fetch_batch([])
        assert result.successes == []
        assert result.failures == []

    async def test_symbol_is_zero_padded_before_call(self, adapter: KrStockAdapter) -> None:
        import pandas as pd

        mock_df = pd.DataFrame({"종가": [75000]})
        refs = [
            SymbolRef(
                asset_type=AssetType.KR_STOCK,
                symbol="5930",  # not zero-padded
                exchange="KRX",
                asset_symbol_id=1,
            )
        ]

        called_with: list[str] = []

        def pykrx_side_effect(start: str, end: str, ticker: str) -> object:
            called_with.append(ticker)
            return mock_df

        with patch("pykrx.stock.get_market_ohlcv", side_effect=pykrx_side_effect):
            await adapter.fetch_batch(refs)

        assert called_with == ["005930"]

    async def test_recent_trading_day_price_returned(self, adapter: KrStockAdapter) -> None:
        """If market was closed today but had prices recently, return the last row."""
        import pandas as pd

        # Simulate multiple historical rows (last is the most recent)
        mock_df = pd.DataFrame({"종가": [70000, 71000, 72500]})
        refs = [_make_ref("005930")]

        with patch("pykrx.stock.get_market_ohlcv", return_value=mock_df):
            result = await adapter.fetch_batch(refs)

        assert result.successes[0].price == Decimal("72500")

    async def test_price_is_decimal_not_float(self, adapter: KrStockAdapter) -> None:
        import pandas as pd

        mock_df = pd.DataFrame({"종가": [75000.5]})
        refs = [_make_ref("005930")]

        with patch("pykrx.stock.get_market_ohlcv", return_value=mock_df):
            result = await adapter.fetch_batch(refs)

        price = result.successes[0].price
        assert isinstance(price, Decimal)

    async def test_fetched_at_is_utc_aware(self, adapter: KrStockAdapter) -> None:
        import pandas as pd

        mock_df = pd.DataFrame({"종가": [75000]})
        refs = [_make_ref("005930")]

        with patch("pykrx.stock.get_market_ohlcv", return_value=mock_df):
            result = await adapter.fetch_batch(refs)

        fetched_at = result.successes[0].fetched_at
        assert fetched_at.tzinfo is not None
        assert fetched_at.tzinfo == UTC

    async def test_failure_has_correct_error_class(self, adapter: KrStockAdapter) -> None:
        empty_fdr = MagicMock()
        empty_fdr.empty = True

        with (
            patch("pykrx.stock.get_market_ohlcv", side_effect=RuntimeError("down")),
            patch("FinanceDataReader.DataReader", return_value=empty_fdr),
        ):
            result = await adapter.fetch_batch([_make_ref("005930")])

        assert len(result.failures) == 1
        assert "ValueError" in result.failures[0].error_class
