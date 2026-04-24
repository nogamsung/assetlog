"""Price refresh domain dataclasses — shared between adapters, service, and scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.domain.asset_type import AssetType


@dataclass(frozen=True)
class SymbolRef:
    """Identifies a single tradeable asset to be refreshed.

    Attributes:
        asset_type: Category of the asset (KR_STOCK, US_STOCK, CRYPTO).
        symbol: Normalised ticker symbol stored in the DB.
        exchange: Exchange or market identifier (e.g. "KRX", "NASDAQ", "binance").
        asset_symbol_id: PK of the corresponding AssetSymbol row.
    """

    asset_type: AssetType
    symbol: str
    exchange: str
    asset_symbol_id: int


@dataclass(frozen=True)
class PriceQuote:
    """A successfully fetched price for one symbol.

    Attributes:
        ref: The SymbolRef that was resolved.
        price: Fetched price — Decimal to avoid float precision loss.
        currency: ISO 4217 currency code (e.g. "KRW", "USD").
        fetched_at: UTC timestamp when the price was observed.
    """

    ref: SymbolRef
    price: Decimal
    currency: str
    fetched_at: datetime


@dataclass(frozen=True)
class FetchFailure:
    """A failed price fetch for one symbol.

    Attributes:
        ref: The SymbolRef that could not be resolved.
        error_class: Class name of the exception (e.g. "ValueError").
        error_msg: Human-readable message — no PII, no secrets.
    """

    ref: SymbolRef
    error_class: str
    error_msg: str


@dataclass(frozen=True)
class FetchBatchResult:
    """Aggregated outcome of a single adapter's batch fetch.

    Attributes:
        successes: Successfully fetched quotes.
        failures: Symbols that could not be resolved.
    """

    successes: list[PriceQuote] = field(default_factory=list)
    failures: list[FetchFailure] = field(default_factory=list)


@dataclass(frozen=True)
class RefreshResult:
    """Summary returned by PriceRefreshService.refresh_all_prices().

    Attributes:
        total: Total number of symbols targeted.
        success: Number of symbols successfully updated.
        failed: Number of symbols that failed.
        elapsed_ms: Wall-clock time in milliseconds.
        failures: Detail records for each failure.
    """

    total: int
    success: int
    failed: int
    elapsed_ms: int
    failures: list[FetchFailure] = field(default_factory=list)
