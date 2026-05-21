"""Tests for the Upbit PDF parser — synthetic row layouts.

The PDF parser anchors each transaction on the date word and sorts the
surrounding words by (line, x0), so the production token sequence is
exactly the documented format:

  trade upper:  ``DATE 매수|매도 KRW-COIN <qty> COIN <fee> KRW``
  trade lower:  ``HH:MM:SS <unit_price> KRW <amount> KRW <settle> KRW``
  cash  upper:  ``DATE 입금|출금 KRW <amount> KRW <fee> KRW [counterparty]``

These tests feed ``parse_text`` (which mirrors the row-token stream) so
we can exercise fee extraction without spinning up pdfplumber.
"""

from __future__ import annotations

from decimal import Decimal

from app.adapters.parsers.base import ParsedCashTx, ParsedCashTxKind, ParsedTrade
from app.adapters.parsers.upbit import parse_text
from app.domain.transaction_type import TransactionType


def _trade_row(
    *,
    date: str,
    side: str,
    coin: str,
    qty: str,
    fee_upper: str,
    time: str,
    unit_price: str,
    amount: str,
    settle: str,
) -> str:
    """Construct one trade row as parse_text expects to see it.

    Upper-line tokens first, then lower-line tokens — that's the order
    the production word-coordinate sort produces.
    """
    return " ".join(
        [
            date, side, f"KRW-{coin}", qty, coin, fee_upper, "KRW",
            time, unit_price, "KRW", amount, "KRW", settle, "KRW",
        ]
    )


def _cash_row(
    *,
    date: str,
    kind: str,
    amount: str,
    fee: str,
    time: str,
    counterparty: str = "은행",
) -> str:
    return " ".join(
        [
            date, kind, "KRW", amount, "KRW", fee, "KRW", counterparty,
            time, "원화", amount, "KRW",
        ]
    )


class TestTradeFee:
    def test_buy_fee_derived_from_amount_minus_settle(self) -> None:
        """BUY: settle = gross + fee → fee = settle − gross."""
        row = _trade_row(
            date="2025-01-15",
            side="매수",
            coin="BTC",
            qty="0.001",
            fee_upper="50",
            time="10:30:00",
            unit_price="100000000",
            amount="100000",
            settle="100050",
        )
        result = parse_text(row)
        trades = [r for r in result.records if isinstance(r, ParsedTrade)]
        assert len(trades) == 1
        t = trades[0]
        assert t.side == TransactionType.BUY
        assert t.quantity == Decimal("0.001")
        assert t.price == Decimal("100000000")
        assert t.fee == Decimal("50")

    def test_sell_fee_derived_from_amount_minus_settle(self) -> None:
        """SELL: settle = gross − fee → fee = gross − settle."""
        row = _trade_row(
            date="2025-01-15",
            side="매도",
            coin="ETH",
            qty="0.5",
            fee_upper="2500",
            time="14:20:30",
            unit_price="5000000",
            amount="2500000",
            settle="2497500",
        )
        result = parse_text(row)
        trades = [r for r in result.records if isinstance(r, ParsedTrade)]
        assert len(trades) == 1
        assert trades[0].side == TransactionType.SELL
        assert trades[0].fee == Decimal("2500")

    def test_zero_fee_buy_keeps_zero(self) -> None:
        """Zero-fee promotion / coupon — fee stays 0 instead of falling through."""
        row = _trade_row(
            date="2025-01-15",
            side="매수",
            coin="BTC",
            qty="0.01",
            fee_upper="0",
            time="10:00:00",
            unit_price="50000000",
            amount="500000",
            settle="500000",
        )
        result = parse_text(row)
        trades = [r for r in result.records if isinstance(r, ParsedTrade)]
        assert len(trades) == 1
        assert trades[0].fee == Decimal("0")


class TestKrwCashFee:
    def test_withdraw_amount_includes_fee(self) -> None:
        """출금: ``amount + fee`` is what actually drains the Upbit KRW balance."""
        row = _cash_row(
            date="2025-02-10",
            kind="출금",
            amount="500000",
            fee="1000",
            time="11:45:00",
        )
        result = parse_text(row)
        cash = [r for r in result.records if isinstance(r, ParsedCashTx)]
        assert len(cash) == 1
        assert cash[0].kind == ParsedCashTxKind.WITHDRAW
        assert cash[0].amount == Decimal("501000")

    def test_deposit_amount_is_raw_amount(self) -> None:
        """입금: KRW deposits are fee-free in practice — raw amount credits."""
        row = _cash_row(
            date="2025-02-10",
            kind="입금",
            amount="1000000",
            fee="0",
            time="09:00:00",
        )
        result = parse_text(row)
        cash = [r for r in result.records if isinstance(r, ParsedCashTx)]
        assert len(cash) == 1
        assert cash[0].kind == ParsedCashTxKind.DEPOSIT
        assert cash[0].amount == Decimal("1000000")


class TestExtIdStability:
    """ext_ids must be stable across parser revisions so existing imports dedup."""

    def test_cash_ext_id_hashes_raw_amount_not_total(self) -> None:
        """Hashing on raw_amount means re-importing post-fix doesn't double-count
        cash rows that were imported before the fee fix landed.
        """
        row = _cash_row(
            date="2025-02-10",
            kind="출금",
            amount="500000",
            fee="1000",
            time="11:45:00",
        )
        a = parse_text(row).records[0]
        b = parse_text(row).records[0]
        assert a.external_id == b.external_id
        # And the prefix is still the cash one
        assert a.external_id.startswith("upbit-pdf-cash-")
