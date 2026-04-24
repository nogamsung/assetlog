"""Portfolio domain constants and value objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from app.models.asset_symbol import AssetSymbol

# Threshold after which a cached price is considered stale.
STALE_THRESHOLD: timedelta = timedelta(hours=3)


@dataclass(frozen=True)
class HoldingRow:
    """Aggregated row returned by the portfolio repository.

    Carries denormalised BUY-transaction aggregates alongside the loaded
    AssetSymbol so the service layer can compute derived values without
    additional DB round-trips.
    """

    user_asset_id: int
    asset_symbol: AssetSymbol
    total_qty: Decimal
    total_cost: Decimal
