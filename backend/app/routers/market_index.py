"""Market index router — GET /api/market/indices."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, MarketIndexServiceDep
from app.schemas.auth import ErrorResponse
from app.schemas.market_index import IndicesResponse

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get(
    "/indices",
    response_model=IndicesResponse,
    status_code=status.HTTP_200_OK,
    summary="List major market indices",
    description=(
        "Return latest quotes for major equity indices (S&P 500, NASDAQ, KOSPI, "
        "KOSDAQ) and BTC-KRW. Quotes are cached in-process for 5 minutes."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_market_indices(
    current_user: CurrentUser,
    service: MarketIndexServiceDep,
) -> IndicesResponse:
    """Return cached index quotes."""
    quotes = await service.list_indices()
    return IndicesResponse(indices=quotes)
