"""Portfolio domain constants and value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.asset_symbol import AssetSymbol

STALE_THRESHOLD: timedelta = timedelta(hours=3)


@dataclass(frozen=True)
class HoldingRow:
    """Aggregated row returned by the portfolio repository.

    Carries denormalised BUY/SELL-transaction aggregates alongside the loaded
    AssetSymbol so the service layer can compute derived values without
    additional DB round-trips.

    ``buy_lots`` holds (traded_at, cost_local) tuples for each BUY transaction
    where cost_local = quantity × price in the asset's native currency.
    Used by PortfolioService to compute cost-weighted average historical FX
    rates for the price/FX P&L decomposition.
    """

    user_asset_id: int
    asset_symbol: AssetSymbol
    total_qty: Decimal
    total_cost: Decimal
    realized_pnl: Decimal
    buy_lots: tuple[tuple[datetime, Decimal], ...] = field(default_factory=tuple)
