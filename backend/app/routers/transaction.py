"""Transaction router — trade recording, listing, deletion, and summary."""

from __future__ import annotations

from fastapi import APIRouter, Path, Query, status

from app.core.deps import CurrentUser, TransactionServiceDep
from app.schemas.auth import ErrorResponse
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    UserAssetSummaryResponse,
)

router = APIRouter(prefix="/api/user-assets", tags=["transactions"])


@router.post(
    "/{user_asset_id}/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new transaction for an asset holding",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "UserAsset not found or not owned"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def add_transaction(
    data: TransactionCreate,
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
    user_asset_id: int = Path(..., ge=1, description="UserAsset ID to record a transaction for"),
) -> TransactionResponse:
    """Record a BUY transaction for the authenticated user's asset holding.

    Returns 404 if the user_asset_id does not exist or is not owned by the caller.
    """
    tx = await transaction_service.add(current_user.id, user_asset_id, data)
    return TransactionResponse.model_validate(tx)


@router.get(
    "/{user_asset_id}/transactions",
    response_model=list[TransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="List transactions for an asset holding",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "UserAsset not found or not owned"},
    },
)
async def list_transactions(
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
    user_asset_id: int = Path(..., ge=1, description="UserAsset ID to query"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> list[TransactionResponse]:
    """Return paginated transactions for an asset holding (most recent first).

    Returns 404 if the user_asset_id does not exist or is not owned by the caller.
    """
    transactions = await transaction_service.list(
        current_user.id, user_asset_id, limit=limit, offset=offset
    )
    return [TransactionResponse.model_validate(tx) for tx in transactions]


@router.delete(
    "/{user_asset_id}/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a transaction",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Transaction or UserAsset not found"},
    },
)
async def delete_transaction(
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
    user_asset_id: int = Path(..., ge=1, description="UserAsset ID that owns the transaction"),
    transaction_id: int = Path(..., ge=1, description="Transaction ID to delete"),
) -> None:
    """Hard-delete a transaction.

    Returns 404 if the transaction or user_asset_id does not exist or is not owned by the caller.
    """
    await transaction_service.remove(current_user.id, user_asset_id, transaction_id)


@router.get(
    "/{user_asset_id}/summary",
    response_model=UserAssetSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated BUY summary for an asset holding",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "UserAsset not found or not owned"},
    },
)
async def get_summary(
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
    user_asset_id: int = Path(..., ge=1, description="UserAsset ID to summarise"),
) -> UserAssetSummaryResponse:
    """Return total_quantity, avg_buy_price, total_invested, and currency for a holding.

    All figures are calculated from BUY transactions only (MVP).
    Returns 404 if the user_asset_id does not exist or is not owned by the caller.
    """
    return await transaction_service.summary(current_user.id, user_asset_id)
