"""Dividend router — GET /api/dividends."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DividendServiceDep
from app.schemas.auth import ErrorResponse
from app.schemas.dividend import DividendListResponse

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
