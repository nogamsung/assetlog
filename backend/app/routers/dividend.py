"""Dividend router — GET /api/dividends."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DividendServiceDep
from app.schemas.auth import ErrorResponse
from app.schemas.dividend import (
    DividendCalendarResponse,
    DividendListResponse,
    YieldOnCostResponse,
)

router = APIRouter(prefix="/api/dividends", tags=["dividends"])


@router.get(
    "",
    response_model=DividendListResponse,
    status_code=status.HTTP_200_OK,
    summary="List dividend distributions with optional filters",
    description=(
        "Returns dividends from the local database (refreshed daily by the "
        "scheduler) filtered by asset_symbol_id and/or ex_date range. "
        "The response also includes a cumulative summary per symbol "
        "for yield-on-cost computation in the UI."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def list_dividends(
    _current_user: CurrentUser,
    dividend_service: DividendServiceDep,
    asset_symbol_id: int | None = Query(default=None, ge=1),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
) -> DividendListResponse:
    return await dividend_service.list_dividends(
        asset_symbol_id=asset_symbol_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get(
    "/calendar",
    response_model=DividendCalendarResponse,
    status_code=status.HTTP_200_OK,
    summary="Chronological dividend calendar (joined with symbol/name)",
    description=(
        "Returns dividend rows ordered ascending by ex_date for use in a "
        "calendar UI. Each entry includes asset_symbol.symbol and name so "
        "the client doesn't need an extra round-trip. Use ``from=YYYY-MM-DD`` "
        "(typically today) to fetch upcoming-only events."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_dividend_calendar(
    _current_user: CurrentUser,
    dividend_service: DividendServiceDep,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
) -> DividendCalendarResponse:
    return await dividend_service.get_calendar(
        date_from=date_from,
        date_to=date_to,
    )


@router.get(
    "/yield-on-cost",
    response_model=YieldOnCostResponse,
    status_code=status.HTTP_200_OK,
    summary="Yield-on-cost per current holding",
    description=(
        "Returns cumulative-dividend yield-on-cost = total_dividend / cost_basis "
        "for every UserAsset. cost_basis is the remaining-share cost in the "
        "asset's native currency (matching dividend currency). Holdings with "
        "zero cost basis return null yield."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_yield_on_cost(
    _current_user: CurrentUser,
    dividend_service: DividendServiceDep,
) -> YieldOnCostResponse:
    return await dividend_service.get_yield_on_cost()
