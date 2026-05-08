"""Unit tests for BenchmarkAdapter — yfinance mocked."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import patch

import pandas as pd

from app.adapters.benchmark import (
    KNOWN_BENCHMARKS,
    BenchmarkAdapter,
    _fetch_history_sync,
)


def _df(closes: dict[datetime, float]) -> pd.DataFrame:
    """Build a yfinance-style single-ticker DataFrame indexed by Timestamp."""
    idx = pd.DatetimeIndex(list(closes.keys()))
    return pd.DataFrame({"Close": list(closes.values())}, index=idx)


class TestFetchHistorySync:
    def test_정상_close_매핑(self) -> None:
        df = _df({datetime(2026, 5, 1): 2500.0, datetime(2026, 5, 2): 2550.0})
        with patch("yfinance.download", return_value=df):
            out = _fetch_history_sync("^KS11", date(2026, 5, 1), date(2026, 5, 3))
        assert len(out) == 2
        assert out[0].close == Decimal("2500.0")
        assert out[1].close == Decimal("2550.0")
        assert all(c.symbol == "^KS11" for c in out)

    def test_빈_dataframe_빈_리스트(self) -> None:
        with patch("yfinance.download", return_value=pd.DataFrame()):
            assert _fetch_history_sync("^KS11", date(2026, 5, 1), date(2026, 5, 3)) == []

    def test_None_입력_무시(self) -> None:
        with patch("yfinance.download", return_value=None):
            assert _fetch_history_sync("^KS11", date(2026, 5, 1), date(2026, 5, 3)) == []

    def test_naive_index_utc_보강(self) -> None:
        df = _df({datetime(2026, 5, 1): 2500.0})
        with patch("yfinance.download", return_value=df):
            out = _fetch_history_sync("^KS11", date(2026, 5, 1), date(2026, 5, 2))
        assert out[0].at.tzinfo is UTC


class TestBenchmarkAdapter:
    async def test_fetch_history_to_thread(self) -> None:
        df = _df({datetime(2026, 5, 1): 2500.0})
        adapter = BenchmarkAdapter()
        with patch("yfinance.download", return_value=df):
            out = await adapter.fetch_history("^KS11", date(2026, 5, 1), date(2026, 5, 2))
        assert len(out) == 1

    async def test_예외_시_빈_리스트(self) -> None:
        adapter = BenchmarkAdapter()
        with patch("yfinance.download", side_effect=RuntimeError("boom")):
            out = await adapter.fetch_history("^KS11", date(2026, 5, 1), date(2026, 5, 2))
        assert out == []

    async def test_fetch_many_빈_입력(self) -> None:
        adapter = BenchmarkAdapter()
        out = await adapter.fetch_many([], date(2026, 5, 1), date(2026, 5, 2))
        assert out == {}

    async def test_fetch_many_병렬(self) -> None:
        df_ks = _df({datetime(2026, 5, 1): 2500.0})
        df_sp = _df({datetime(2026, 5, 1): 4500.0})

        def fake_download(ticker: str, **_: object) -> pd.DataFrame:
            return df_ks if ticker == "^KS11" else df_sp

        adapter = BenchmarkAdapter()
        with patch("yfinance.download", side_effect=fake_download):
            out = await adapter.fetch_many(["^KS11", "^GSPC"], date(2026, 5, 1), date(2026, 5, 2))
        assert "^KS11" in out
        assert "^GSPC" in out


class TestKnownBenchmarks:
    def test_default_3_종목(self) -> None:
        assert "^KS11" in KNOWN_BENCHMARKS
        assert "^GSPC" in KNOWN_BENCHMARKS
        assert "BTC-USD" in KNOWN_BENCHMARKS
