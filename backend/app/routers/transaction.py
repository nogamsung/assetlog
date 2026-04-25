"""Transaction router — trade recording, listing, deletion, and summary."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Path, Query, UploadFile, status

from app.core.deps import CurrentUser, TransactionServiceDep
from app.schemas.auth import ErrorResponse
from app.schemas.transaction import (
    TransactionCreate,
    TransactionImportResponse,
    TransactionResponse,
    TransactionUpdate,  # ADDED
    UserAssetSummaryResponse,
)

_MAX_CSV_BYTES = 1_048_576  # 1 MB

router = APIRouter(prefix="/api/user-assets", tags=["transactions"])


# ---------------------------------------------------------------------------
# Static routes — MUST be declared before dynamic /{user_asset_id}/... routes
# to prevent FastAPI from treating "transactions" as a path parameter value.
# ---------------------------------------------------------------------------


@router.get(
    "/transactions/tags",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
    summary="List distinct tags used by the current user",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_user_tags(
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
) -> list[str]:
    """Return a deduplicated, alphabetically sorted list of all tags the
    authenticated user has attached to their transactions.

    Useful for autocomplete suggestions in the UI.  Returns an empty list
    when no transactions have been tagged yet.
    """
    return await transaction_service.list_distinct_tags(current_user.id)


@router.post(
    "/{user_asset_id}/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new BUY or SELL transaction for an asset holding",  # MODIFIED
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "UserAsset not found or not owned"},
        409: {
            "model": ErrorResponse,
            "description": "Insufficient holding quantity for SELL",
        },  # ADDED
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def add_transaction(
    data: TransactionCreate,
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
    user_asset_id: int = Path(..., ge=1, description="UserAsset ID to record a transaction for"),
) -> TransactionResponse:
    """Record a BUY or SELL transaction for the authenticated user's asset holding.

    Returns 404 if the user_asset_id does not exist or is not owned by the caller.
    Returns 409 if a SELL transaction exceeds the current remaining quantity.
    """  # MODIFIED
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
    tag: str | None = Query(default=None, max_length=50, description="Filter by tag"),
) -> list[TransactionResponse]:
    """Return paginated transactions for an asset holding (most recent first).

    Pass ``?tag=DCA`` to filter to only transactions with that exact tag.
    Returns 404 if the user_asset_id does not exist or is not owned by the caller.
    """
    transactions = await transaction_service.list(
        current_user.id, user_asset_id, limit=limit, offset=offset, tag=tag
    )
    return [TransactionResponse.model_validate(tx) for tx in transactions]


@router.put(  # ADDED
    "/{user_asset_id}/transactions/{transaction_id}",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing transaction",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Transaction or UserAsset not found"},
        409: {
            "model": ErrorResponse,
            "description": "Edit would result in negative holding",
        },
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_transaction(
    data: TransactionUpdate,
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
    user_asset_id: int = Path(..., ge=1, description="UserAsset ID that owns the transaction"),
    transaction_id: int = Path(..., ge=1, description="Transaction ID to update"),
) -> TransactionResponse:
    """Replace all fields of an existing transaction (full PUT replace semantics).

    Returns 404 if the transaction or user_asset_id does not exist or is not owned by the caller.
    Returns 409 if the edit would result in negative remaining holding.
    """
    tx = await transaction_service.edit(current_user.id, user_asset_id, transaction_id, data)
    return TransactionResponse.model_validate(tx)


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


@router.post(
    "/{user_asset_id}/transactions/import",
    response_model=TransactionImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk import transactions from CSV",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "File too large, bad encoding, or CSV header error",
        },
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "UserAsset not found or not owned"},
        413: {"model": ErrorResponse, "description": "File exceeds 1 MB limit"},
        422: {"model": ErrorResponse, "description": "CSV rows failed validation"},
    },
)
async def import_transactions_csv(
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
    user_asset_id: int = Path(..., ge=1, description="UserAsset ID to import transactions into"),
    file: UploadFile = File(..., description="UTF-8 CSV file (≤ 1 MB)"),
) -> TransactionImportResponse:
    """Bulk-import transactions from a UTF-8 CSV file (all-or-nothing).

    The CSV must include a header row with at least these columns (any order):
    ``type``, ``quantity``, ``price``, ``traded_at``, ``memo``.
    Additional columns are silently ignored.

    ``type`` accepts: ``buy`` / ``sell`` (case-insensitive) or ``매수`` / ``매도``.
    ``traded_at`` must be an ISO 8601 timezone-aware datetime string.
    ``memo`` may be empty (treated as null).

    Returns 422 with a per-row ``errors`` array if any row fails validation.
    Returns 413 if the file exceeds 1 MB.
    Returns 400 if the file cannot be decoded as UTF-8 or the header is missing.
    """
    raw_bytes = await file.read()

    # Size guard
    if len(raw_bytes) > _MAX_CSV_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large: {len(raw_bytes)} bytes (limit {_MAX_CSV_BYTES} bytes).",
        )

    # Decode — try utf-8-sig first (handles BOM from Excel) then plain utf-8
    try:
        csv_text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            csv_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UTF-8 encoding. Please export the CSV as UTF-8.",
            ) from exc

    imported_count, preview_txs = await transaction_service.import_csv(
        user_id=current_user.id,
        user_asset_id=user_asset_id,
        csv_text=csv_text,
    )

    return TransactionImportResponse(
        imported_count=imported_count,
        preview=[TransactionResponse.model_validate(tx) for tx in preview_txs],
    )


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
