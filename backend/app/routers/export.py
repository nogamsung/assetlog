"""Export router — download all data as JSON or CSV/ZIP."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Query, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.core.deps import CurrentUser, DataExportServiceDep
from app.schemas.auth import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get(
    "",
    summary="Export all data",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": (
                "JSON envelope (application/json) or ZIP archive (application/zip) "
                "depending on the ``format`` query parameter."
            ),
        },
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {"model": ErrorResponse, "description": "Invalid format parameter"},
    },
)
async def export_data(
    _current_user: CurrentUser,
    service: DataExportServiceDep,
    format: Literal["json", "csv"] = Query(  # noqa: A002  # shadows builtin — intentional param name
        default="json",
        description="Export format: ``json`` (default) or ``csv`` (ZIP archive with two CSV files).",
        examples=["json"],
    ),
) -> Response:
    """Download a full snapshot of all data."""
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")

    if format == "json":
        envelope = await service.export_json()
        return JSONResponse(
            content=jsonable_encoder(
                envelope.model_dump(),
                custom_encoder={Decimal: str},
            ),
            headers={
                "Content-Disposition": (f'attachment; filename="assetlog-export-{timestamp}.json"'),
            },
        )

    zip_bytes = await service.export_csv_zip()
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": (f'attachment; filename="assetlog-export-{timestamp}.zip"'),
        },
    )
