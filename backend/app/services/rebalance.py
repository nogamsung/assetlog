"""RebalanceService — compare current vs target allocation, suggest moves.

Reuses PortfolioService.get_summary to get current asset-class weights
(including cash) and TargetAllocationService for the desired weights.
Computes per-bucket drift and a recommended action (buy / sell / hold)
based on an absolute threshold.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from app.schemas.portfolio import AllocationEntry, PortfolioSummaryResponse
from app.schemas.rebalance import RebalanceEntry, RebalanceSuggestionResponse
from app.schemas.target_allocation import TargetAllocationListResponse
from app.services.portfolio import PortfolioService
from app.services.target_allocation import TargetAllocationService

logger = logging.getLogger(__name__)


_ZERO = Decimal("0")
_HUNDRED = Decimal("100")
_DEFAULT_THRESHOLD = Decimal("0.05")  # 5%


def _decide_action(
    drift_pct: Decimal,
    threshold: Decimal,
) -> str:
    """Return 'buy' / 'sell' / 'hold' based on signed drift vs threshold."""
    if drift_pct <= -threshold:
        return "buy"
    if drift_pct >= threshold:
        return "sell"
    return "hold"


def _allocation_pct_map(allocation: list[AllocationEntry]) -> dict[str, Decimal]:
    """Build {bucket → fraction} map from PortfolioSummary.allocation entries.

    AllocationEntry.pct is stored as a 0–100 float for display; convert
    to a 0–1 fraction so it lines up with target_pct semantics.
    """
    result: dict[str, Decimal] = {}
    for entry in allocation:
        key = str(entry.asset_type)
        result[key] = Decimal(str(entry.pct)) / _HUNDRED
    return result


class RebalanceService:
    """Composes target + current allocation → rebalance suggestion."""

    def __init__(
        self,
        target_service: TargetAllocationService,
        portfolio_service: PortfolioService,
    ) -> None:
        self._target = target_service
        self._portfolio = portfolio_service

    async def suggest(
        self,
        currency: str,
        threshold_pct: Decimal | None = None,
    ) -> RebalanceSuggestionResponse:
        threshold = threshold_pct if threshold_pct is not None else _DEFAULT_THRESHOLD
        warnings: list[str] = []

        targets: TargetAllocationListResponse = await self._target.list_targets()
        summary: PortfolioSummaryResponse = await self._portfolio.get_summary(convert_to=currency)

        if not targets.entries:
            warnings.append("no_target_configured")

        # Total value in display currency — null if FX is unavailable for any leg
        if summary.converted_total_value is None:
            warnings.append("no_portfolio_value")
            total_value = _ZERO
        else:
            total_value = summary.converted_total_value

        current_map = _allocation_pct_map(summary.allocation)
        target_map = {str(e.asset_type): e.target_pct for e in targets.entries}

        all_buckets = sorted(set(target_map.keys()) | set(current_map.keys()))
        entries: list[RebalanceEntry] = []
        for bucket in all_buckets:
            target_pct = target_map.get(bucket, _ZERO)
            current_pct = current_map.get(bucket, _ZERO)
            drift = current_pct - target_pct
            delta_amount = (target_pct - current_pct) * total_value
            action = _decide_action(drift, threshold)
            entries.append(
                RebalanceEntry.model_validate(
                    {
                        "asset_type": bucket,
                        "target_pct": target_pct,
                        "current_pct": current_pct,
                        "drift_pct": drift,
                        "delta_amount": delta_amount,
                        "action": action,
                    }
                )
            )

        return RebalanceSuggestionResponse(
            currency=currency,
            total_value=total_value,
            threshold_pct=threshold,
            entries=entries,
            warnings=warnings,
        )
