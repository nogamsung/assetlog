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
    """The parser intentionally emits the raw ISIN as ``symbol``.

    Translating ISIN → exchange ticker is the job of ``IsinResolver`` during
    ``import_records``, not the parser. These tests therefore assert the
    *raw parsed shape* (ISIN, name, quantity), not the eventual ticker.
    """

    def test_us_stock_trade_parsed(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """AMD (US0079031078) is parsed as a USD US_STOCK trade."""
        from decimal import Decimal

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
        # Quantity must be the share count, NOT the FX rate (~1,300–1,500).
        for t in amd_trades:
            assert t.quantity < Decimal("1000"), f"AMD qty looks like FX rate: {t.quantity}"

    def test_us_long_name_includes_etf_tail(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """When the US name spills onto line 2, the 'ETF' fragment must be kept."""
        nvd_trades = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedTrade) and r.symbol == "US38747R6291"
        ]
        assert len(nvd_trades) >= 1
        # 종목명 = "그래닛셰어즈 엔비디아 데일리 2배 인버스 ETF"
        assert any("ETF" in t.name for t in nvd_trades), (
            f"ETF fragment missing from names: {[t.name for t in nvd_trades]}"
        )

    def test_us_securities_carry_a_name(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """Every US trade must have a non-empty display name parsed from the PDF.

        The resolver later turns ISIN → ticker; the parser's job is to preserve
        the Korean security name so AssetSymbol.name doesn't fall back to ISIN.
        """
        us_trades = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedTrade) and r.asset_type == AssetType.US_STOCK
        ]
        missing = [t for t in us_trades if not t.name]
        assert not missing, "Trades missing name: " + ", ".join(t.symbol for t in missing)

    def test_kyg_isin_parsed(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """Cayman-domiciled tickers (KYG…) are parsed as US_STOCK with KYG ISIN."""
        joby = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedTrade) and r.symbol == "KYG651631007"
        ]
        assert len(joby) >= 1
        assert "조비" in joby[0].name

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


class TestTradeFee:
    """Trade fees must be captured so cash_flow can subtract them.

    KRW trade fees come from 수수료 (numeric_tokens[3]) only — 거래세 and
    제세금 are reported on the row but Toss already nets them out of the
    잔액 column, so subtracting them again double-counts. USD trade fees
    come from line 2's fee + tax2 ($ values [2] + [3]).
    """

    def test_krw_trade_carries_fee(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        from decimal import Decimal

        # 코나아이 BUY on 2025.05.14 — fee=84 (수수료 column)
        kr = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedTrade)
            and r.symbol == "052400"
            and r.side == TransactionType.BUY
            and r.quantity == Decimal("12")
        ]
        assert kr, "expected 코나아이 BUY 12 trade in fixture"
        assert kr[0].fee == Decimal("84")

    def test_usd_trade_carries_fee(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        from decimal import Decimal

        # Any AMD trade — line2 has ($ fee) at index 2
        usd = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedTrade)
            and r.symbol == "US0079031078"
            and r.side == TransactionType.BUY
        ]
        assert usd, "expected at least one AMD BUY in fixture"
        # All AMD BUYs charge a non-zero broker fee.
        assert all(t.fee > Decimal("0") for t in usd), (
            f"every USD BUY should have a non-zero fee, got fees={[t.fee for t in usd]}"
        )


class TestCancellationPrefix:
    """``환전외화입금취소`` must route to ``transfer_out``, not ``transfer_in``.

    The kind string starts with ``환전외화입금`` so a naive iteration of
    ``_USD_CASH_FLOW_MAP`` (insertion order) hits the deposit handler first
    and double-counts every cancellation as a credit. Order-by-length keeps
    the specific kind winning.
    """

    def test_cancellation_is_transfer_out(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        cancels = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedCashTx) and r.kind.value == "transfer_in" and r.currency == "USD"
        ]
        # No deposit-flavored record should have been emitted with the cancel
        # amount. Concretely: the fixture's 2025.07.11 cancellation is
        # ($ 647.09), which is also the corresponding 2025.07.10 deposit
        # amount. After the fix there is one transfer_in at 647.09 (the
        # deposit) and a transfer_out (the cancellation) — never two
        # transfer_ins at the same amount on consecutive days.
        from decimal import Decimal

        # The cancellation must show up under transfer_out, not transfer_in.
        outs = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedCashTx)
            and r.kind.value == "transfer_out"
            and r.currency == "USD"
            and r.amount == Decimal("647.09")
        ]
        assert outs, "expected a USD transfer_out at $647.09 from 환전외화입금취소"
        # And the deposit pair still exists.
        ins = [r for r in cancels if r.amount == Decimal("647.09")]
        assert ins, "expected the matching 환전외화입금 transfer_in at $647.09"


class TestFxCashAmount:
    """KRW cash-flow amount must come from the 거래대금 column, not the FX rate.

    Pre-fix the parser scanned for the first positive number — for 환전원화*
    rows that's the FX rate (~1,300–1,500), so a 4,999,998 KRW conversion was
    recorded as ~1,500 KRW and millions of KRW that had been swapped to USD
    still showed up as cash.
    """

    def test_krw_fx_transfer_uses_amount_not_rate(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """환전원화* rows must record the KRW principal, not the FX rate."""
        from decimal import Decimal

        fx_transfers = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedCashTx)
            and r.currency == "KRW"
            and r.kind.value in {"transfer_in", "transfer_out"}
        ]
        assert len(fx_transfers) >= 5
        # An FX rate sits in 1,300–1,600 KRW/USD with cents. Real FX
        # principals are whole-won integers — a recorded amount that is both
        # in that band AND non-integer would only come from picking the rate.
        for tx in fx_transfers:
            in_rate_band = Decimal("1200") <= tx.amount <= Decimal("1700")
            non_integer = tx.amount != tx.amount.to_integral_value()
            assert not (in_rate_band and non_integer), (
                f"transfer amount {tx.amount} looks like an FX rate, not a principal"
            )

    def test_known_fx_principal_matches_pdf(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """2025.07.10 환전원화출금 1,384.64 → 895,985 KRW principal."""
        from decimal import Decimal

        matching = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedCashTx)
            and r.currency == "KRW"
            and r.kind.value == "transfer_out"
            and r.amount == Decimal("895985")
        ]
        assert matching, "expected a 895,985 KRW transfer_out matching the PDF row"


class TestSameMinuteRoundTrip:
    """Same-day BUY/SELL pairs that net to zero must surface BUYs first.

    Without this, the moving-average cost-basis walker (sorted by traded_at, id)
    sees SELL-before-BUY at the same KST midnight, cannot flush against an empty
    inventory, and leaves the BUY as a phantom holding.
    """

    def test_kodex_leverage_round_trip_buy_first(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """KODEX 레버리지 on 2026.04.27: BUY 102 + SELL 100 + SELL 2 ⇒ BUY first."""
        kodex = [
            r for r in parse_result.records if isinstance(r, ParsedTrade) and r.symbol == "122630"
        ]
        assert len(kodex) == 3
        assert kodex[0].side == TransactionType.BUY
        assert kodex[1].side == TransactionType.SELL
        assert kodex[2].side == TransactionType.SELL


class TestLongName:
    def test_long_name_trade_parsed(self, parse_result) -> None:  # type: ignore[no-untyped-def]
        """Tickers that span two lines (name on line1, code on line2) must be parsed.

        ``US25461A8412`` is Direxion 2X GOOGL. The parser keeps the ISIN as
        symbol; resolver later turns it into ``GGLL`` at import time.
        """
        ggll_trades = [
            r
            for r in parse_result.records
            if isinstance(r, ParsedTrade) and r.symbol == "US25461A8412"
        ]
        assert len(ggll_trades) >= 1
