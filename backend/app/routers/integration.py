"""Integration router — POST /api/integrations/upbit/sync, /api/integrations/import-file."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.core.config import settings
from app.core.deps import CurrentUser, ExchangeSyncServiceDep
from app.domain.exchange_sync import ExchangeSource
from app.exceptions import ExternalIntegrationError, ValidationError
from app.schemas.auth import ErrorResponse
from app.schemas.integration import ImportFileResponse, SyncResultResponse

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

_SUPPORTED_FILE_SOURCES: frozenset[str] = frozenset(["toss_securities", "shinhan"])


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

    if settings.upbit_access_key is None or settings.upbit_secret_key is None:
        raise ExternalIntegrationError(
            "Upbit API keys are not configured. Set UPBIT_ACCESS_KEY and UPBIT_SECRET_KEY env vars."
        )

    adapter = UpbitAccountAdapter(
        access_key=settings.upbit_access_key,
        secret_key=settings.upbit_secret_key,
    )
    trades = await adapter.fetch_trades()
    result = await sync_service.replace_trades(ExchangeSource.UPBIT, trades)

    # Best-effort: pull KRW deposit/withdrawal history so the per-account
    # cash balance reflects what the user actually sees on Upbit. Failures
    # log only — they don't taint the trade-sync result.
    try:
        cash_rows = await adapter.fetch_cash_flow()
        if cash_rows:
            await sync_service.upsert_cash_transactions(
                ExchangeSource.UPBIT, cash_rows
            )
    except Exception:  # noqa: BLE001
        pass

    return SyncResultResponse.model_validate(result)


@router.post(
    "/import-file",
    response_model=ImportFileResponse,
    status_code=status.HTTP_200_OK,
    summary="Import transactions from a broker statement file",
    description=(
        "Upload a PDF (or future: Excel) statement from a supported broker and import "
        "trades, dividends, and interest payments. Deduplication is handled automatically. "
        "Use ``dry_run=true`` to preview what would be inserted without writing to the DB."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {"model": ErrorResponse, "description": "Unsupported source or invalid file"},
    },
)
async def import_file(
    _current_user: CurrentUser,
    sync_service: ExchangeSyncServiceDep,
    source: str = Query(
        ...,
        description="Broker identifier",
        examples=["toss_securities"],
    ),
    dry_run: bool = Query(
        default=False,
        description="When true, parse and count without persisting to DB",
    ),
    file: UploadFile = File(..., description="PDF statement file"),
    password: str | None = Form(
        default=None,
        description="Optional PDF decryption password (some brokers ship encrypted statements)",
    ),
) -> ImportFileResponse:
    if source not in _SUPPORTED_FILE_SOURCES:
        raise ValidationError(
            f"Unsupported source '{source}'. Supported: {sorted(_SUPPORTED_FILE_SOURCES)}"
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise ValidationError("Uploaded file is empty.")

    if source == "shinhan":
        from app.adapters.parsers.shinhan_securities import parse_pdf  # noqa: PLC0415
    else:
        from app.adapters.parsers.toss_securities import parse_pdf  # noqa: PLC0415

    try:
        parse_result = parse_pdf(file_bytes, password=password)
    except Exception as exc:  # pdfplumber raises pikepdf.PasswordError on bad/missing pwd
        if "password" in str(exc).lower() or "encrypted" in str(exc).lower():
            raise ValidationError(
                "PDF is password-protected or password is incorrect. "
                "Provide the correct password via the 'password' form field."
            ) from exc
        raise

    exchange_source = ExchangeSource(source)
    import_result = await sync_service.import_records(
        exchange_source, parse_result, dry_run=dry_run
    )

    preview: list[dict[str, object]] = []
    if dry_run:
        for rec in parse_result.records[:20]:
            preview.append(
                {
                    "type": type(rec).__name__,
                    "external_id": rec.external_id,
                    "traded_at": rec.traded_at.isoformat(),
                }
            )

    return ImportFileResponse(
        inserted_trades=import_result.inserted_trades,
        inserted_dividends=import_result.inserted_dividends,
        inserted_cash_txs=import_result.inserted_cash_txs,
        skipped_duplicate=import_result.skipped_duplicate,
        skipped_unsupported=import_result.skipped_unsupported,
        skipped_breakdown=import_result.skipped_breakdown,
        dry_run=dry_run,
        preview=preview,
    )
