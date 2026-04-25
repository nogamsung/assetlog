"""Sample data router — one-click portfolio seed for new users."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, SampleSeedServiceDep
from app.schemas.auth import ErrorResponse
from app.schemas.sample_seed import SampleSeedResponse

router = APIRouter(prefix="/api/sample", tags=["sample"])


@router.post(
    "/seed",
    response_model=SampleSeedResponse,
    status_code=status.HTTP_200_OK,
    summary="Seed sample portfolio data for the current user",
    description=(
        "Creates 5 sample assets (BTC, ETH, AAPL, 삼성전자, 현대차) with 2-4 BUY "
        "transactions each, spread over the past 12 months.  "
        "Idempotent — skipped if the user already has any user_assets."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def seed_sample(
    current_user: CurrentUser,
    seed_service: SampleSeedServiceDep,
) -> SampleSeedResponse:
    """Seed sample portfolio data for the authenticated user.

    Returns ``seeded=true`` with creation counts on success, or
    ``seeded=false`` with a reason when the seed was skipped.
    """
    return await seed_service.seed_for_user(current_user.id)
