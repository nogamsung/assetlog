"""Portfolio router — aggregated summary, per-holding, and history endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.deps import (
    CurrentUser,
    PortfolioHistoryServiceDep,
    PortfolioServiceDep,
    TagBreakdownServiceDep,
)
from app.domain.portfolio_history import HistoryPeriod
from app.schemas.auth import ErrorResponse
from app.schemas.portfolio import (
    HoldingResponse,
    PortfolioHistoryResponse,
    PortfolioSummaryResponse,
)
from app.schemas.tag_breakdown import TagBreakdownResponse

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get(
    "/summary",
    response_model=PortfolioSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get currency-bucketed portfolio summary",
    description=(
        "Returns total market value, cost basis, P&L, and asset-class allocation "
        "grouped by currency. Holdings whose last_price is NULL are excluded from "
        "value/P&L totals but counted in ``pending_count``. "
        "Pass ``convert_to`` (e.g. ``KRW``) to receive converted totals in addition to "
        "the per-currency breakdown. Converted fields are null if any required FX rate "
        "is unavailable — no partial conversion is performed."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        503: {
            "model": ErrorResponse,
            "description": "FX rate not yet available — retry after scheduler runs",
        },
    },
)
async def get_portfolio_summary(
    _current_user: CurrentUser,
    portfolio_service: PortfolioServiceDep,
    convert_to: str | None = Query(
        default=None,
        min_length=3,
        max_length=10,
        description="Target currency for conversion (e.g. KRW, USD, EUR)",
        examples=["KRW"],
    ),
) -> PortfolioSummaryResponse:
    """Return aggregated portfolio summary."""
    target = convert_to.upper() if convert_to else None
    return await portfolio_service.get_summary(convert_to=target)


@router.get(
    "/holdings",
    response_model=list[HoldingResponse],
    status_code=status.HTTP_200_OK,
    summary="List per-holding valuation rows",
    description=(
        "Returns one row per UserAsset with derived fields: latest_price, "
        "latest_value, pnl_abs, pnl_pct, weight_pct, is_stale, is_pending. "
        "Decimal fields are serialised as strings. "
        "Pass ``convert_to`` (e.g. ``KRW``) to receive per-row converted_* fields. "
        "If the FX rate for a holding's currency is unavailable, that holding's "
        "converted_* fields are null while others remain converted (partial conversion allowed)."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_portfolio_holdings(
    _current_user: CurrentUser,
    portfolio_service: PortfolioServiceDep,
    convert_to: str | None = Query(
        default=None,
        min_length=3,
        max_length=10,
        description="Target currency for per-row conversion (e.g. KRW, USD, EUR)",
        examples=["KRW"],
    ),
) -> list[HoldingResponse]:
    """Return per-holding valuation rows."""
    return await portfolio_service.get_holdings(
        convert_to=convert_to.upper() if convert_to else None,
    )


@router.get(
    "/history",
    response_model=PortfolioHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get portfolio value time series",
    description=(
        "Returns a bucketed time series of portfolio value and cost basis. "
        "Bucket granularity is determined by the requested period: "
        "1D → 5MIN, 1W → HOUR, 1M → DAY, 1Y → WEEK, ALL → MONTH. "
        "Points where no price data is available contribute 0 to value."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {
            "model": ErrorResponse,
            "description": "Validation error (invalid period or missing currency)",
        },
    },
)
async def get_portfolio_history(
    _current_user: CurrentUser,
    history_service: PortfolioHistoryServiceDep,
    period: HistoryPeriod = Query(default=HistoryPeriod.ONE_MONTH, description="Time window"),
    currency: str = Query(
        ...,
        min_length=1,
        max_length=10,
        description="Quote currency (e.g. KRW, USD)",
    ),
) -> PortfolioHistoryResponse:
    """Return portfolio value time series."""
    return await history_service.get_history(period, currency.upper())


@router.get(
    "/tags/breakdown",
    response_model=TagBreakdownResponse,
    status_code=status.HTTP_200_OK,
    summary="Per-tag transaction flow breakdown",
    description=(
        "Groups transactions by tag and returns per-tag buy/sell counts and "
        "currency-bucketed value totals. "
        "Untagged transactions are grouped under tag=null and always appear last. "
        "Returns entries=[] when there are no transactions."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_tag_breakdown(
    _current_user: CurrentUser,
    service: TagBreakdownServiceDep,
) -> TagBreakdownResponse:
    """Return per-tag transaction flow breakdown."""
    return await service.get_breakdown()
