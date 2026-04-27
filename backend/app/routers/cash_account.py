"""CashAccount router — REST endpoints for cash balance management."""

from __future__ import annotations

from fastapi import APIRouter, Path, status

from app.core.deps import CashAccountServiceDep, CurrentUser
from app.schemas.auth import ErrorResponse
from app.schemas.cash_account import (
    CashAccountCreate,
    CashAccountResponse,
    CashAccountUpdate,
)

router = APIRouter(prefix="/api/cash-accounts", tags=["cash-accounts"])


@router.get(
    "",
    response_model=list[CashAccountResponse],
    status_code=status.HTTP_200_OK,
    summary="List all cash accounts",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_cash_accounts(
    _current_user: CurrentUser,
    service: CashAccountServiceDep,
) -> list[CashAccountResponse]:
    """Return all cash accounts ordered by creation date descending."""
    accounts = await service.list()
    return [CashAccountResponse.model_validate(a) for a in accounts]


@router.post(
    "",
    response_model=CashAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new cash account",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_cash_account(
    data: CashAccountCreate,
    _current_user: CurrentUser,
    service: CashAccountServiceDep,
) -> CashAccountResponse:
    """Create a cash account with the specified label, currency, and balance."""
    account = await service.create(data)
    return CashAccountResponse.model_validate(account)


@router.patch(
    "/{id}",
    response_model=CashAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Partially update a cash account",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Cash account not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_cash_account(
    data: CashAccountUpdate,
    _current_user: CurrentUser,
    service: CashAccountServiceDep,
    id: int = Path(..., ge=1, description="Cash account ID to update"),
) -> CashAccountResponse:
    """Update label and/or balance of an existing cash account.

    Returns 404 if the cash account does not exist.
    Returns 422 if neither label nor balance is provided, or if currency is sent.
    """
    account = await service.update(id, data)
    return CashAccountResponse.model_validate(account)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a cash account",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Cash account not found"},
    },
)
async def delete_cash_account(
    _current_user: CurrentUser,
    service: CashAccountServiceDep,
    id: int = Path(..., ge=1, description="Cash account ID to delete"),
) -> None:
    """Hard-delete a cash account by id.

    Returns 404 if the cash account does not exist.
    """
    await service.delete(id)
