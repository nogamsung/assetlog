"""UserAsset router — user holding declaration, listing, and removal."""

from __future__ import annotations

from fastapi import APIRouter, Path, status

from app.core.deps import CurrentUser, UserAssetServiceDep
from app.schemas.asset import UserAssetCreate, UserAssetResponse
from app.schemas.auth import ErrorResponse

router = APIRouter(prefix="/api/user-assets", tags=["user-assets"])


@router.get(
    "",
    response_model=list[UserAssetResponse],
    status_code=status.HTTP_200_OK,
    summary="List all asset holdings for the current user",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_user_assets(
    current_user: CurrentUser,
    user_asset_service: UserAssetServiceDep,
) -> list[UserAssetResponse]:
    """Return all declared asset holdings for the authenticated user."""
    holdings = await user_asset_service.list(current_user.id)
    return [UserAssetResponse.model_validate(h) for h in holdings]


@router.post(
    "",
    response_model=UserAssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Declare a new asset holding",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "AssetSymbol not found"},
        409: {"model": ErrorResponse, "description": "Asset already held"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def add_user_asset(
    data: UserAssetCreate,
    current_user: CurrentUser,
    user_asset_service: UserAssetServiceDep,
) -> UserAssetResponse:
    """Declare ownership of an asset symbol for the authenticated user.

    Returns 404 if the asset_symbol_id does not exist.
    Returns 409 if the user already holds the same symbol.
    """
    holding = await user_asset_service.add(current_user.id, data)
    return UserAssetResponse.model_validate(holding)


@router.delete(
    "/{user_asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an asset holding",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Asset holding not found"},
    },
)
async def remove_user_asset(
    current_user: CurrentUser,
    user_asset_service: UserAssetServiceDep,
    user_asset_id: int = Path(..., ge=1, description="UserAsset ID to remove"),
) -> None:
    """Hard-delete a declared asset holding.

    Returns 404 if the holding does not exist or is not owned by the current user.
    """
    await user_asset_service.remove(current_user.id, user_asset_id)
