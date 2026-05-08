"""Unit tests for the pykrx-backed KR dividend adapter."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pandas as pd

from app.adapters import kr_dividends as mod
from app.adapters.kr_dividends import (
    KrDividendAdapter,
    _ex_date_for,
    _fetch_dividends_sync,
    _format_year_end,
)


class TestHelpers:
    def test_ex_date_for_year(self) -> None:
        assert _ex_date_for(2025) == date(2025, 12, 30)

    def test_format_year_end(self) -> None:
        assert _format_year_end(2025) == "20251230"


def _df_with(ticker: str, dps: float | str) -> pd.DataFrame:
    """Build a pykrx-shape DataFrame indexed by ticker."""
    return pd.DataFrame({"DPS": [dps]}, index=[ticker])


class TestFetchDividendsSync:
    def test_연도별_dps_quote_생성(self) -> None:
        ticker = "005930"

        def fake_dps(date_str: str, t: str) -> pd.DataFrame:
            year = int(date_str[:4])
            mapping = {2023: 1444.0, 2024: 1500.0, 2025: 0.0}
            return _df_with(t, mapping.get(year, 0.0))

        with (
            patch.object(mod, "_DEFAULT_LOOKBACK_YEARS", 3),
            patch("pykrx.stock.get_market_fundamental_by_ticker", side_effect=fake_dps),
            patch("app.adapters.kr_dividends.datetime") as fake_dt,
        ):
            fake_dt.now.return_value.date.return_value = date(2026, 5, 7)
            quotes = _fetch_dividends_sync(ticker, lookback_years=3)

        assert len(quotes) == 2
        assert quotes[0].ex_date == date(2023, 12, 30)
        assert quotes[0].amount == Decimal("1444.0")
        assert quotes[0].currency == "KRW"
        assert quotes[1].ex_date == date(2024, 12, 30)

    def test_빈_데이터프레임_무시(self) -> None:
        ticker = "005930"
        empty = pd.DataFrame()

        with (
            patch("pykrx.stock.get_market_fundamental_by_ticker", return_value=empty),
            patch("app.adapters.kr_dividends.datetime") as fake_dt,
        ):
            fake_dt.now.return_value.date.return_value = date(2026, 5, 7)
            quotes = _fetch_dividends_sync(ticker, lookback_years=3)
        assert quotes == []

    def test_dps_없는_컬럼_무시(self) -> None:
        ticker = "005930"
        df = pd.DataFrame({"BPS": [1000.0]}, index=[ticker])

        with (
            patch("pykrx.stock.get_market_fundamental_by_ticker", return_value=df),
            patch("app.adapters.kr_dividends.datetime") as fake_dt,
        ):
            fake_dt.now.return_value.date.return_value = date(2026, 5, 7)
            assert _fetch_dividends_sync(ticker, lookback_years=2) == []

    def test_pykrx_예외_무시_계속(self) -> None:
        ticker = "005930"

        def raise_then_ok(date_str: str, t: str) -> pd.DataFrame:
            year = int(date_str[:4])
            if year == 2024:
                raise RuntimeError("pykrx flaky")
            return _df_with(t, 1000.0)

        with (
            patch("pykrx.stock.get_market_fundamental_by_ticker", side_effect=raise_then_ok),
            patch("app.adapters.kr_dividends.datetime") as fake_dt,
        ):
            fake_dt.now.return_value.date.return_value = date(2026, 5, 7)
            quotes = _fetch_dividends_sync(ticker, lookback_years=3)

        ex_dates = [q.ex_date for q in quotes]
        assert date(2024, 12, 30) not in ex_dates
        assert len(quotes) == 2

    def test_dps_0_생략(self) -> None:
        ticker = "005930"

        with (
            patch(
                "pykrx.stock.get_market_fundamental_by_ticker",
                return_value=_df_with(ticker, 0.0),
            ),
            patch("app.adapters.kr_dividends.datetime") as fake_dt,
        ):
            fake_dt.now.return_value.date.return_value = date(2026, 5, 7)
            assert _fetch_dividends_sync(ticker, lookback_years=2) == []


class TestKrDividendAdapter:
    async def test_fetch_dividends_to_thread_위임(self) -> None:
        adapter = KrDividendAdapter(lookback_years=2)

        with (
            patch(
                "pykrx.stock.get_market_fundamental_by_ticker",
                return_value=_df_with("005930", 1500.0),
            ),
            patch("app.adapters.kr_dividends.datetime") as fake_dt,
        ):
            fake_dt.now.return_value.date.return_value = date(2026, 5, 7)
            quotes = await adapter.fetch_dividends("005930")

        assert all(q.currency == "KRW" for q in quotes)
        assert len(quotes) == 2

    async def test_fetch_치명적_예외시_빈_리스트(self) -> None:
        adapter = KrDividendAdapter(lookback_years=2)
        with patch(
            "app.adapters.kr_dividends._fetch_dividends_sync",
            side_effect=RuntimeError("boom"),
        ):
            assert await adapter.fetch_dividends("005930") == []
