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


@dataclass(frozen=True)
class ParsedCashTx:
    """An interest payment or other cash-flow event produced by a parser."""

    external_id: str
    kind: ParsedCashTxKind
    amount: Decimal
    currency: str
    traded_at: datetime


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
