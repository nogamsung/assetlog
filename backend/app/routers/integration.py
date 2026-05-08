"""Integration router — POST /api/integrations/upbit/sync."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.config import settings
from app.core.deps import CurrentUser, ExchangeSyncServiceDep
from app.exceptions import ExternalIntegrationError
from app.schemas.auth import ErrorResponse
from app.schemas.integration import SyncResultResponse

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.post(
    "/upbit/sync",
    response_model=SyncResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Manual Upbit account sync — pulls trades and writes Transactions",
    description=(
        "Calls the Upbit private API with the configured read-only keys "
        "(``UPBIT_ACCESS_KEY`` / ``UPBIT_SECRET_KEY`` env vars), maps each "
        "trade to a Transaction, and dedupes by (external_source, external_id). "
        "Missing AssetSymbols / UserAssets are auto-created."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        502: {
            "model": ErrorResponse,
            "description": "Upbit keys not configured or upstream call failed",
        },
    },
)
async def sync_upbit(
    _current_user: CurrentUser,
    sync_service: ExchangeSyncServiceDep,
) -> SyncResultResponse:
    from app.adapters.upbit_account import UpbitAccountAdapter  # noqa: PLC0415  # lazy
    from app.domain.exchange_sync import ExchangeSource  # noqa: PLC0415

    if settings.upbit_access_key is None or settings.upbit_secret_key is None:
        raise ExternalIntegrationError(
            "Upbit API keys are not configured. Set UPBIT_ACCESS_KEY and UPBIT_SECRET_KEY env vars."
        )

    adapter = UpbitAccountAdapter(
        access_key=settings.upbit_access_key,
        secret_key=settings.upbit_secret_key,
    )
    trades = await adapter.fetch_trades()
    result = await sync_service.import_trades(ExchangeSource.UPBIT, trades)
    return SyncResultResponse.model_validate(result)
