"""Target allocation router — GET / PUT /api/target-allocation."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, TargetAllocationServiceDep
from app.schemas.auth import ErrorResponse
from app.schemas.target_allocation import (
    TargetAllocationListResponse,
    TargetAllocationUpsertRequest,
)

router = APIRouter(prefix="/api/target-allocation", tags=["target-allocation"])


@router.get(
    "",
    response_model=TargetAllocationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current target asset allocation",
    description=(
        "Returns the user's configured target weights per asset_type bucket. "
        "Empty entries list means no target is configured. "
        "Weights are fractions (0–1) and the sum should be ≤ 1.0."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_target_allocation(
    _current_user: CurrentUser,
    service: TargetAllocationServiceDep,
) -> TargetAllocationListResponse:
    return await service.list_targets()


@router.put(
    "",
    response_model=TargetAllocationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Replace the target asset allocation atomically",
    description=(
        "Atomically replaces all existing target rows with the supplied "
        "entries. Sum of target_pct must be ≤ 1.0. An empty entries list "
        "clears the configuration."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def replace_target_allocation(
    payload: TargetAllocationUpsertRequest,
    _current_user: CurrentUser,
    service: TargetAllocationServiceDep,
) -> TargetAllocationListResponse:
    return await service.replace(payload)
