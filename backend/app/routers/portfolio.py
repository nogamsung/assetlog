"""Portfolio router — aggregated summary and per-holding endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, PortfolioServiceDep
from app.schemas.auth import ErrorResponse
from app.schemas.portfolio import HoldingResponse, PortfolioSummaryResponse

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get(
    "/summary",
    response_model=PortfolioSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get currency-bucketed portfolio summary",
    description=(
        "Returns total market value, cost basis, P&L, and asset-class allocation "
        "grouped by currency. Holdings whose last_price is NULL are excluded from "
        "value/P&L totals but counted in ``pending_count``."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_portfolio_summary(
    current_user: CurrentUser,
    portfolio_service: PortfolioServiceDep,
) -> PortfolioSummaryResponse:
    """Return aggregated portfolio summary for the authenticated user."""
    return await portfolio_service.get_summary(current_user.id)


@router.get(
    "/holdings",
    response_model=list[HoldingResponse],
    status_code=status.HTTP_200_OK,
    summary="List per-holding valuation rows",
    description=(
        "Returns one row per UserAsset with derived fields: latest_price, "
        "latest_value, pnl_abs, pnl_pct, weight_pct, is_stale, is_pending. "
        "Decimal fields are serialised as strings."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_portfolio_holdings(
    current_user: CurrentUser,
    portfolio_service: PortfolioServiceDep,
) -> list[HoldingResponse]:
    """Return per-holding valuation rows for the authenticated user."""
    return await portfolio_service.get_holdings(current_user.id)
