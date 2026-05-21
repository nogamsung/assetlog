"""Tests for the Shinhan Investment & Securities PDF/text parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.parsers.base import ParsedCashTx, ParsedDividend, ParsedTrade
from app.adapters.parsers.shinhan_securities import parse_text
from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "fixtures"
    / "parsers"
    / "shinhan_securities"
    / "sample_extracted.txt"
)


@pytest.fixture(scope="module")
def sample_text() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def parse_result(sample_text: str):  # type: ignore[no-untyped-def]
    return parse_text(sample_text)


class TestCounts:
    def test_trade_count_positive(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        assert parse_result.trade_count >= 5

    def test_dividend_count_positive(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        assert parse_result.dividend_count >= 3

    def test_cash_tx_count_positive(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """예탁금이용료 → KRW interest."""
        assert parse_result.cash_tx_count >= 1

    def test_cash_transfers_emit_cash_tx(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """``전자이체*`` events now become ParsedCashTx (deposit/withdraw)."""
        cash_kinds = [
            r.kind.value for r in parse_result.records if isinstance(r, ParsedCashTx)
        ]
        assert "deposit" in cash_kinds or "withdraw" in cash_kinds


class TestKrTrade:
    def test_kr_stock_trade_parsed(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """삼성전자 장내_매수 should produce a KRW KR_STOCK BUY trade."""
        samsung = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedTrade) and r.symbol == "삼성전자"
        ]
        assert samsung
        t = samsung[0]
        assert t.asset_type == AssetType.KR_STOCK
        assert t.currency == "KRW"
        assert t.exchange == "KRX"
        assert t.side in {TransactionType.BUY, TransactionType.SELL}
        assert t.quantity > 0
        assert t.price > 0
        assert t.name == "삼성전자"

    def test_etf_with_special_chars_in_name(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """종목명에 공백·영문·기호가 섞여도 토큰 분리가 정상 동작해야 함."""
        sp500 = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedTrade) and r.symbol == "TIGER 미국S&P500배당귀족"
        ]
        assert sp500
        assert all(t.quantity > 0 and t.price > 0 for t in sp500)

    def test_buy_fee_extracted_from_settle(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """수수료 가 비어있지 않은 BUY 는 ``fee = settle − gross`` 가 잡혀야 한다.

        Without this, cash_flow over-counts the Shinhan KRW balance by every
        broker deduction (≈ ₩651,874 on the user's 2-year history).
        """
        # 2024-08-16 TIGER 미국S&P500배당귀족 BUY 100 @ 11,700 — fee 2,210
        # (line1[1]=2,210, settle=1,172,210, gross=1,170,000)
        from decimal import Decimal  # noqa: PLC0415

        match = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedTrade)
            and r.symbol == "TIGER 미국S&P500배당귀족"
            and r.quantity == Decimal("100")
            and r.price == Decimal("11700")
            and r.side.value == "buy"
        ]
        assert match, "expected the 2024-08-16 TIGER 100@11,700 BUY in the fixture"
        assert match[0].fee == Decimal("2210")


class TestDividend:
    def test_etf_distribution_parsed(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """ETF분배금 should produce a ParsedDividend with KRW."""
        divs = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedDividend)
            and r.symbol == "TIGER 미국S&P500배당귀족"
        ]
        assert divs
        assert all(d.currency == "KRW" and d.gross_amount > 0 for d in divs)


class TestInterest:
    def test_interest_parsed(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """예탁금이용료 should produce a ParsedCashTx with KRW interest."""
        interest = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedCashTx) and r.currency == "KRW"
        ]
        assert interest
        assert all(c.amount > 0 for c in interest)


class TestDeterministicIds:
    def test_ids_are_stable(self, sample_text: str) -> None:
        r1 = parse_text(sample_text)
        r2 = parse_text(sample_text)
        ids1 = {r.external_id for r in r1.records}
        ids2 = {r.external_id for r in r2.records}
        assert ids1 == ids2

    def test_external_ids_are_32_hex(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        for rec in parse_result.records:
            assert len(rec.external_id) == 32
            assert all(c in "0123456789abcdef" for c in rec.external_id)


class TestTimezone:
    def test_traded_at_utc_aware_and_kst_midnight(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        sample = next(r for r in parse_result.records if isinstance(r, ParsedTrade))
        assert sample.traded_at.tzinfo is not None
        # 00:00 KST = 15:00 UTC (previous day)
        assert sample.traded_at.hour == 15
