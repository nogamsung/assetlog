"""FX rate router — GET /api/fx/rates."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, FxRateServiceDep
from app.models.fx_rate import FxRate
from app.schemas.auth import ErrorResponse
from app.schemas.fx_rate import FxRateEntry, FxRatesResponse

router = APIRouter(prefix="/api/fx", tags=["fx"])


@router.get(
    "/rates",
    response_model=FxRatesResponse,
    status_code=status.HTTP_200_OK,
    summary="List all cached exchange rates",
    description=(
        "Returns all currently cached FX rate pairs fetched from the Frankfurter API. "
        "Rates are refreshed hourly by the scheduler. "
        "An empty list is returned if no rates have been fetched yet."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_fx_rates(
    current_user: CurrentUser,
    fx_service: FxRateServiceDep,
) -> FxRatesResponse:
    """Return all cached FX rate pairs for the authenticated user."""
    rows: list[FxRate] = await fx_service.list_all_rates()
    entries = [
        FxRateEntry(
            base=row.base_currency,
            quote=row.quote_currency,
            rate=row.rate,
            fetched_at=row.fetched_at,
        )
        for row in rows
    ]
    return FxRatesResponse(rates=entries)
