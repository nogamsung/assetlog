"""Domain types for exchange/broker sync (Upbit, KIS, etc.)."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.transaction_type import TransactionType


class ExchangeSource(enum.StrEnum):
    """Origin of an external sync — propagated to ``Transaction.external_source``."""

    UPBIT = "upbit"
    BITHUMB = "bithumb"
    BINANCE = "binance"
    SHINHAN = "shinhan_investment"
    KIS = "kis"
    TOSS_SECURITIES = "toss_investment"
    K_BANK = "k_bank"


@dataclass(frozen=True)
class ExternalTrade:
    """A single trade fetched from an external venue."""

    external_id: str
    symbol: str  # e.g. "BTC" or "AAPL"
    quote_currency: str  # what was paid in (KRW / USD)
    side: TransactionType
    quantity: Decimal
    price: Decimal  # per-unit price in quote_currency
    traded_at: datetime  # tz-aware UTC


@dataclass(frozen=True)
class SyncResult:
    """Aggregate counters returned by an exchange sync run."""

    fetched: int
    inserted: int
    skipped_duplicate: int
    skipped_no_symbol: int
