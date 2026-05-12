"""Tests for the Toss Securities PDF/text parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.parsers.base import ParsedCashTx, ParsedDividend, ParsedTrade
from app.adapters.parsers.toss_securities import parse_text
from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "fixtures"
    / "parsers"
    / "toss_securities"
    / "sample_extracted.txt"
)


@pytest.fixture(scope="module")
def sample_text() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def parse_result(sample_text: str):  # type: ignore[no-untyped-def]
    return parse_text(sample_text)


class TestCounts:
    def test_trade_count(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """Should parse the expected number of BUY/SELL trades."""
        assert parse_result.trade_count >= 140

    def test_dividend_count(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """Should parse KRW + USD dividends."""
        assert parse_result.dividend_count >= 5

    def test_cash_tx_count(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """Should parse interest payments."""
        assert parse_result.cash_tx_count >= 4

    def test_skipped_non_zero(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """Many lines are unsupported and should be counted as skipped."""
        assert len(parse_result.skipped) >= 100


class TestDeterministicIds:
    def test_same_input_same_ids(self, sample_text: str) -> None:
        """Parsing the same text twice must produce identical external_ids."""
        result1 = parse_text(sample_text)
        result2 = parse_text(sample_text)
        ids1 = {r.external_id for r in result1.records}
        ids2 = {r.external_id for r in result2.records}
        assert ids1 == ids2

    def test_external_ids_are_32_hex(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        for rec in parse_result.records:
            assert len(rec.external_id) == 32
            assert all(c in "0123456789abcdef" for c in rec.external_id)


class TestKrStock:
    def test_kr_stock_trade_parsed(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """KR stock trade (코나아이 A052400) should be detected as KR_STOCK."""
        kr_trades = [
            r for r in parse_result.records if isinstance(r, ParsedTrade) and r.symbol == "052400"
        ]
        assert len(kr_trades) >= 1
        trade = kr_trades[0]
        assert trade.asset_type == AssetType.KR_STOCK
        assert trade.exchange == "KRX"
        assert trade.currency == "KRW"
        assert trade.side in {TransactionType.BUY, TransactionType.SELL}

    def test_kr_dividend_parsed(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """삼성전자 배당금 should be parsed as a Dividend."""
        kr_divs = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedDividend) and r.symbol == "005930"
        ]
        assert len(kr_divs) >= 1
        div = kr_divs[0]
        assert div.currency == "KRW"
        assert div.asset_type == AssetType.KR_STOCK


class TestUsStock:
    def test_us_stock_trade_parsed(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """AMD (US0079031078) trade should be detected as US_STOCK, price in USD."""
        amd_trades = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedTrade) and r.symbol == "US0079031078"
        ]
        assert len(amd_trades) >= 1
        trade = amd_trades[0]
        assert trade.asset_type == AssetType.US_STOCK
        assert trade.currency == "USD"
        # Price should be USD-denominated (well under KRW prices)
        assert trade.price < 1000

    def test_us_dividend_parsed(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """외화증권배당금입금 should produce a ParsedDividend with USD."""
        usd_divs = [
            r for r in parse_result.records if isinstance(r, ParsedDividend) and r.currency == "USD"
        ]
        assert len(usd_divs) >= 1


class TestInterest:
    def test_krw_interest_parsed(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """KRW 이자입금 should produce a ParsedCashTx with KRW."""
        krw_interest = [
            r for r in parse_result.records if isinstance(r, ParsedCashTx) and r.currency == "KRW"
        ]
        assert len(krw_interest) >= 1

    def test_usd_interest_parsed(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """외화이자입금 should produce a ParsedCashTx with USD."""
        usd_interest = [
            r for r in parse_result.records if isinstance(r, ParsedCashTx) and r.currency == "USD"
        ]
        assert len(usd_interest) >= 1


class TestTimezone:
    def test_traded_at_utc_aware(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """All traded_at timestamps must be UTC-aware."""

        for rec in parse_result.records:
            assert rec.traded_at.tzinfo is not None
            assert rec.traded_at.utcoffset().total_seconds() == 0  # type: ignore[union-attr]

    def test_kst_midnight_offset(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """KST midnight (00:00 KST = 15:00 UTC previous day)."""
        sample = next(
            r for r in parse_result.records if isinstance(r, ParsedTrade) and r.currency == "KRW"
        )
        # 00:00 KST = UTC-9h → hour should be 15 (previous day UTC)
        assert sample.traded_at.hour == 15


class TestLongName:
    def test_long_name_trade_parsed(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """Tickers that span two lines (name on line1, code on line2) must be parsed."""
        two_line_symbols = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedTrade) and r.symbol == "US25461A8412"
        ]
        assert len(two_line_symbols) >= 1
