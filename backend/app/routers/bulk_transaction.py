"""Bulk transaction router — multi-symbol import via JSON or multipart CSV."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.deps import BulkTransactionServiceDep, CurrentUser
from app.exceptions import CsvImportValidationError
from app.models.transaction import Transaction
from app.schemas.auth import ErrorResponse
from app.schemas.bulk_transaction import (
    BulkTransactionRequest,
    BulkTransactionResponse,
    BulkValidationErrorResponse,
)
from app.schemas.transaction import TransactionResponse

_MAX_CSV_BYTES = 1_048_576  # 1 MB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transactions", tags=["bulk-transactions"])


@router.post(
    "/bulk",
    response_model=BulkTransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk import multi-symbol transactions (JSON or CSV)",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Bad request — invalid JSON, bad encoding, or CSV header missing",
        },
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        413: {
            "model": ErrorResponse,
            "description": "File exceeds 1 MB limit (CSV mode only)",
        },
        415: {
            "model": ErrorResponse,
            "description": "Unsupported media type — use application/json or multipart/form-data",
        },
        422: {
            "model": BulkValidationErrorResponse,
            "description": "Bulk validation failed — per-row errors included",
        },
    },
)
async def bulk_import_transactions(
    request: Request,
    _current_user: CurrentUser,
    bulk_service: BulkTransactionServiceDep,
    file: UploadFile = File(
        default=None,
        description="UTF-8 CSV file (≤ 1 MB, multipart/form-data only)",
    ),
) -> BulkTransactionResponse:
    """Import multiple transactions across different asset symbols in one request.

    **JSON mode** — send ``Content-Type: application/json`` with a
    ``BulkTransactionRequest`` body::

        {
          "rows": [
            {"symbol": "BTC", "exchange": "UPBIT", "type": "buy",
             "quantity": "0.5", "price": "85000000",
             "traded_at": "2026-04-20T10:00:00+09:00"}
          ]
        }

    **CSV mode** — send ``Content-Type: multipart/form-data`` with a ``file``
    field containing a UTF-8 CSV (≤ 1 MB).  Required header columns:
    ``symbol``, ``exchange``, ``type``, ``quantity``, ``price``, ``traded_at``.
    Optional: ``memo``, ``tag``.

    All rows are validated atomically — a single invalid row rejects the whole
    batch (all-or-nothing).  ``(symbol, exchange)`` pairs that have no
    declared UserAsset are rejected with 422 (auto-creation is not performed).
    """
    content_type: str = request.headers.get("content-type", "")

    try:
        if content_type.startswith("application/json"):
            imported_count, preview_txs = await _handle_json(request, bulk_service)
        elif content_type.startswith("multipart/form-data"):
            imported_count, preview_txs = await _handle_csv(file, bulk_service)
        else:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    "Unsupported Content-Type. "
                    "Use 'application/json' for JSON mode or "
                    "'multipart/form-data' for CSV mode."
                ),
            )
    except CsvImportValidationError as exc:
        return JSONResponse(  # type: ignore[return-value]  # FastAPI accepts JSONResponse
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Bulk validation failed",
                "errors": exc.errors,
            },
        )

    return BulkTransactionResponse(
        imported_count=imported_count,
        preview=[TransactionResponse.model_validate(tx) for tx in preview_txs],
    )


# ---------------------------------------------------------------------------
# Private helpers — keep the endpoint function readable
# ---------------------------------------------------------------------------


async def _handle_json(
    request: Request,
    bulk_service: BulkTransactionServiceDep,
) -> tuple[int, list[Transaction]]:
    """Parse JSON body and delegate to service."""
    try:
        body = await request.json()
        bulk_request = BulkTransactionRequest.model_validate(body)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON body: {exc}",
        ) from exc

    return await bulk_service.import_json(bulk_request.rows)


async def _handle_csv(
    file: UploadFile,
    bulk_service: BulkTransactionServiceDep,
) -> tuple[int, list[Transaction]]:
    """Read multipart file, validate size and encoding, delegate to service."""
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multipart field 'file' is required for CSV mode.",
        )

    raw_bytes = await file.read()

    if len(raw_bytes) > _MAX_CSV_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large: {len(raw_bytes)} bytes (limit {_MAX_CSV_BYTES} bytes).",
        )

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

    return await bulk_service.import_csv(csv_text)
