"""Symbol search domain types — shared between adapters and services."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.asset_type import AssetType


@dataclass(frozen=True)
class SymbolCandidate:
    """Immutable value object representing a symbol candidate from an external source.

    Fields:
        asset_type: Asset category (kr_stock / us_stock / crypto).
        symbol: Normalised ticker or pair string.
        name: Human-readable asset name.
        exchange: Exchange or market identifier.
        currency: Quote currency code.
    """

    asset_type: AssetType
    symbol: str
    name: str
    exchange: str
    currency: str
