"""Unit tests for UsStockAdapter — no real network calls."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.adapters.us_stock import UsStockAdapter, _fetch_prices_sync
from app.domain.asset_type import AssetType
from app.domain.price_refresh import SymbolRef


def _make_ref(symbol: str = "AAPL", asset_symbol_id: int = 1) -> SymbolRef:
    return SymbolRef(
        asset_type=AssetType.US_STOCK,
        symbol=symbol,
        exchange="NASDAQ",
        asset_symbol_id=asset_symbol_id,
    )


def _make_multi_col_df(data: dict[str, list[float]]) -> MagicMock:
    """Build a minimal mock mimicking yf.download multi-ticker output."""
    import pandas as pd

    close_df = pd.DataFrame(data)
    df_mock = MagicMock()
    df_mock.empty = False
    df_mock.__getitem__ = lambda self, key: close_df if key == "Close" else close_df
    df_mock.columns = close_df.columns
    return df_mock


def _make_single_df(close_values: list[float]) -> MagicMock:
    """Build a mock for single-ticker yf.download output."""
    import pandas as pd

    single_df = pd.DataFrame({"Close": close_values})
    df_mock = MagicMock()
    df_mock.empty = False
    df_mock.__getitem__ = lambda self, key: single_df if key == "Close" else single_df
    df_mock.columns = single_df.columns
    return df_mock


class TestFetchPricesSync:
    def test_returns_empty_dict_for_empty_tickers(self) -> None:
        result = _fetch_prices_sync([])
        assert result == {}

    def test_single_ticker_from_fast_info(self) -> None:
        empty_mock = MagicMock()
        empty_mock.empty = True
        fast_info_mock = MagicMock()
        fast_info_mock.last_price = 189.5

        with (
            patch("yfinance.download", return_value=empty_mock),
            patch("yfinance.Ticker") as mock_ticker_cls,
        ):
            mock_ticker_cls.return_value.fast_info = fast_info_mock
            result = _fetch_prices_sync(["AAPL"])

        assert result["AAPL"] == Decimal("189.5")

    def test_raises_value_error_when_fast_info_is_none(self) -> None:
        empty_mock = MagicMock()
        empty_mock.empty = True
        fast_info_mock = MagicMock()
        fast_info_mock.last_price = None

        with (
            patch("yfinance.download", return_value=empty_mock),
            patch("yfinance.Ticker") as mock_ticker_cls,
        ):
            mock_ticker_cls.return_value.fast_info = fast_info_mock
            with pytest.raises(ValueError, match="fast_info.last_price is None"):
                _fetch_prices_sync(["AAPL"])


class TestUsStockAdapterFetchBatch:
    @pytest.fixture()
    def adapter(self) -> UsStockAdapter:
        return UsStockAdapter()

    def test_asset_type_is_us_stock(self, adapter: UsStockAdapter) -> None:
        assert adapter.asset_type == AssetType.US_STOCK

    async def test_empty_symbols_returns_empty_result(self, adapter: UsStockAdapter) -> None:
        result = await adapter.fetch_batch([])
        assert result.successes == []
        assert result.failures == []

    async def test_successful_bulk_fetch(self, adapter: UsStockAdapter) -> None:
        import pandas as pd

        refs = [_make_ref("AAPL", 1), _make_ref("TSLA", 2)]

        close_df = pd.DataFrame({"AAPL": [189.5, 190.0], "TSLA": [250.0, 252.0]})
        mock_result = MagicMock()
        mock_result.empty = False
        mock_result.__getitem__ = lambda self, key: close_df if key == "Close" else close_df  # type: ignore[misc]
        mock_result.columns = close_df.columns

        with patch("yfinance.download", return_value=mock_result):
            result = await adapter.fetch_batch(refs)

        assert len(result.successes) == 2
        assert len(result.failures) == 0
        symbols = {q.ref.symbol for q in result.successes}
        assert symbols == {"AAPL", "TSLA"}

    async def test_missing_ticker_falls_back_to_fast_info(self, adapter: UsStockAdapter) -> None:

        refs = [_make_ref("AAPL")]
        # Simulate empty download (e.g. market closed)
        mock_empty = MagicMock()
        mock_empty.empty = True

        fast_info_mock = MagicMock()
        fast_info_mock.last_price = 191.0

        with (
            patch("yfinance.download", return_value=mock_empty),
            patch("yfinance.Ticker") as mock_ticker_cls,
        ):
            mock_ticker_cls.return_value.fast_info = fast_info_mock
            result = await adapter.fetch_batch(refs)

        assert len(result.successes) == 1
        assert result.successes[0].price == Decimal("191.0")

    async def test_failed_fetch_recorded_as_failure(self, adapter: UsStockAdapter) -> None:
        refs = [_make_ref("AAPL")]
        mock_empty = MagicMock()
        mock_empty.empty = True
        fast_info_mock = MagicMock()
        fast_info_mock.last_price = None

        with (
            patch("yfinance.download", return_value=mock_empty),
            patch("yfinance.Ticker") as mock_ticker_cls,
        ):
            mock_ticker_cls.return_value.fast_info = fast_info_mock
            result = await adapter.fetch_batch(refs)

        assert len(result.failures) == 1
        assert result.failures[0].ref.symbol == "AAPL"

    async def test_catastrophic_failure_marks_all_as_failed(self, adapter: UsStockAdapter) -> None:
        refs = [_make_ref("AAPL"), _make_ref("TSLA", 2)]

        with patch("yfinance.download", side_effect=OSError("network down")):
            result = await adapter.fetch_batch(refs)

        assert len(result.failures) == 2
        assert len(result.successes) == 0

    async def test_currency_is_usd(self, adapter: UsStockAdapter) -> None:
        import pandas as pd

        refs = [_make_ref("AAPL")]
        close_df = pd.DataFrame({"AAPL": [189.5]})
        mock_result = MagicMock()
        mock_result.empty = False
        mock_result.__getitem__ = lambda self, key: close_df if key == "Close" else close_df  # type: ignore[misc]
        mock_result.columns = close_df.columns

        with patch("yfinance.download", return_value=mock_result):
            result = await adapter.fetch_batch(refs)

        assert result.successes[0].currency == "USD"

    async def test_symbol_normalised_to_upper(self, adapter: UsStockAdapter) -> None:
        """Symbols should be uppercased before yfinance call."""
        import pandas as pd

        refs = [
            SymbolRef(
                asset_type=AssetType.US_STOCK,
                symbol=" aapl ",
                exchange="NASDAQ",
                asset_symbol_id=1,
            )
        ]
        close_df = pd.DataFrame({"AAPL": [189.5]})
        mock_result = MagicMock()
        mock_result.empty = False
        mock_result.__getitem__ = lambda self, key: close_df if key == "Close" else close_df  # type: ignore[misc]
        mock_result.columns = close_df.columns

        called_tickers: list[object] = []

        def capture_download(tickers: object, **kwargs: object) -> object:
            called_tickers.append(tickers)
            return mock_result

        with patch("yfinance.download", side_effect=capture_download):
            result = await adapter.fetch_batch(refs)

        assert len(result.successes) == 1
        assert "AAPL" in called_tickers[0]  # type: ignore[operator]

    async def test_price_is_decimal_not_float(self, adapter: UsStockAdapter) -> None:
        import pandas as pd

        refs = [_make_ref("AAPL")]
        close_df = pd.DataFrame({"AAPL": [189.5]})
        mock_result = MagicMock()
        mock_result.empty = False
        mock_result.__getitem__ = lambda self, key: close_df if key == "Close" else close_df  # type: ignore[misc]
        mock_result.columns = close_df.columns

        with patch("yfinance.download", return_value=mock_result):
            result = await adapter.fetch_batch(refs)

        assert isinstance(result.successes[0].price, Decimal)
