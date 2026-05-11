"""Rebalance router — GET /api/rebalance/suggestion."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, RebalanceServiceDep
from app.schemas.auth import ErrorResponse
from app.schemas.rebalance import RebalanceSuggestionResponse

router = APIRouter(prefix="/api/rebalance", tags=["rebalance"])


@router.get(
    "/suggestion",
    response_model=RebalanceSuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get per-bucket rebalance suggestion against target allocation",
    description=(
        "Compares current asset-class weights (incl. cash) against the "
        "configured target allocation. Returns per-bucket drift and a "
        "buy/sell/hold action based on an absolute threshold. delta_amount "
        "is in the report currency."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_rebalance_suggestion(
    _current_user: CurrentUser,
    service: RebalanceServiceDep,
    currency: str = Query(default="KRW", min_length=3, max_length=10),
    threshold_pct: Decimal = Query(
        default=Decimal("0.05"),
        ge=0,
        le=1,
        description=(
            "Absolute drift threshold (fraction). Buckets within ±threshold "
            "are marked 'hold' (default 0.05 = 5%)."
        ),
    ),
) -> RebalanceSuggestionResponse:
    return await service.suggest(currency.upper(), threshold_pct)
