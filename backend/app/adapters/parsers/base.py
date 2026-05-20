"""Shared dataclasses for file-based import parsers."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType


class ParsedCashTxKind(enum.StrEnum):
    """Kind of cash transaction produced by a parser."""

    INTEREST = "interest"
    INTEREST_TAX = "interest_tax"
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    # FX-leg pairs. An FX trade emits one TRANSFER_OUT (currency A) plus one
    # TRANSFER_IN (currency B) — keeps each currency's balance accurate without
    # having to model the two halves of a swap explicitly.
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


@dataclass(frozen=True)
class ParsedTrade:
    """A BUY or SELL trade produced by a parser."""

    external_id: str
    symbol: str
    asset_type: AssetType
    exchange: str
    side: TransactionType
    quantity: Decimal
    price: Decimal
    currency: str
    traded_at: datetime
    name: str = ""
    # Broker commission paid on this trade, in the trade's quote currency.
    # Parsers that don't (or can't) extract a fee leave this at zero — that
    # makes the cash impact strictly conservative (won't double-count).
    fee: Decimal = Decimal("0")


@dataclass(frozen=True)
class ParsedDividend:
    """A dividend receipt produced by a parser."""

    external_id: str
    symbol: str
    asset_type: AssetType
    exchange: str
    gross_amount: Decimal
    currency: str
    traded_at: datetime
    name: str = ""
    # Withholding tax already netted out at source — actual cash credited
    # is ``gross_amount - withholding_tax``. Parsers that can't (or don't)
    # report it leave 0, in which case cash_flow assumes no withholding.
    withholding_tax: Decimal = Decimal("0")


@dataclass(frozen=True)
class ParsedCashTx:
    """An interest payment or other cash-flow event produced by a parser."""

    external_id: str
    kind: ParsedCashTxKind
    amount: Decimal
    currency: str
    traded_at: datetime
    # For INTEREST events: tax already withheld at source so the actual
    # cash credited is ``amount - withholding_tax``. Defaults to 0 for
    # other kinds (deposit, withdraw, transfer_*, interest_tax itself).
    withholding_tax: Decimal = Decimal("0")


@dataclass(frozen=True)
class ParsedSkip:
    """A line that was skipped (unsupported type)."""

    raw_kind: str
    reason: str


ParsedRecord = ParsedTrade | ParsedDividend | ParsedCashTx


@dataclass
class ParseResult:
    """Aggregate result from a single file parse."""

    records: list[ParsedRecord] = field(default_factory=list)
    skipped: list[ParsedSkip] = field(default_factory=list)

    @property
    def trade_count(self) -> int:
        return sum(1 for r in self.records if isinstance(r, ParsedTrade))

    @property
    def dividend_count(self) -> int:
        return sum(1 for r in self.records if isinstance(r, ParsedDividend))

    @property
    def cash_tx_count(self) -> int:
        return sum(1 for r in self.records if isinstance(r, ParsedCashTx))
