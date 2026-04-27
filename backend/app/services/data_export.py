"""DataExportService — assembles user data for JSON or CSV/ZIP export.

No FastAPI imports — HTTP concerns live exclusively in the router layer.
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from datetime import UTC, datetime

from app.models.transaction import Transaction
from app.models.user_asset import UserAsset
from app.repositories.transaction import TransactionRepository
from app.repositories.user_asset import UserAssetRepository
from app.schemas.export import (
    ExportAssetSymbol,
    ExportEnvelope,
    ExportTransaction,
    ExportUserAsset,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CSV column definitions
# ---------------------------------------------------------------------------

_USER_ASSETS_HEADERS: list[str] = [
    "id",
    "asset_type",
    "symbol",
    "exchange",
    "name",
    "currency",
    "memo",
    "created_at",
]

_TRANSACTIONS_HEADERS: list[str] = [
    "id",
    "user_asset_id",
    "asset_symbol",
    "type",
    "quantity",
    "price",
    "traded_at",
    "memo",
    "tag",
    "created_at",
]


class DataExportService:
    """Assembles full user data snapshots for download.

    Intentionally does NOT import any FastAPI symbols — the router layer owns
    all HTTP serialisation (JSONResponse, Response, custom_encoder, etc.).
    """

    def __init__(
        self,
        user_asset_repo: UserAssetRepository,
        transaction_repo: TransactionRepository,
    ) -> None:
        self._ua_repo = user_asset_repo
        self._tx_repo = transaction_repo

    async def export_json(self) -> ExportEnvelope:
        """Return a validated ExportEnvelope.

        Fetches user_assets (with eager-loaded asset_symbol) and all transactions
        in two DB round-trips — no N+1.
        """
        logger.info("export requested: format=json")

        user_assets, transactions = await self._fetch_all()

        # Build symbol lookup for transaction enrichment (asset_symbol field)
        # (not needed for JSON envelope — transactions reference user_asset_id)

        exported_at = datetime.now(tz=UTC)

        export_user_assets: list[ExportUserAsset] = []
        for ua in user_assets:
            sym = ua.asset_symbol
            export_sym = ExportAssetSymbol(
                id=sym.id,
                asset_type=sym.asset_type,
                symbol=sym.symbol,
                exchange=sym.exchange,
                name=sym.name,
                currency=sym.currency,
                last_price=sym.last_price,
            )
            export_user_assets.append(
                ExportUserAsset(
                    id=ua.id,
                    asset_symbol_id=ua.asset_symbol_id,
                    memo=ua.memo,
                    created_at=ua.created_at,
                    asset_symbol=export_sym,
                )
            )

        export_transactions: list[ExportTransaction] = [
            ExportTransaction(
                id=tx.id,
                user_asset_id=tx.user_asset_id,
                type=tx.type,
                quantity=tx.quantity,
                price=tx.price,
                traded_at=tx.traded_at,
                memo=tx.memo,
                tag=tx.tag,
                created_at=tx.created_at,
            )
            for tx in transactions
        ]

        return ExportEnvelope(
            exported_at=exported_at,
            user_assets=export_user_assets,
            transactions=export_transactions,
        )

    async def export_csv_zip(self) -> bytes:
        """Return ZIP bytes containing user_assets.csv + transactions.csv.

        Uses stdlib ``csv`` + ``io.BytesIO`` + ``zipfile.ZipFile`` — no
        external dependencies. Headers are English-only for Excel compatibility.

        Decimal values are serialised as plain strings (e.g. ``"1.5000000000"``).
        Datetime values are ISO 8601 with UTC offset.

        Returns:
            In-memory ZIP bytes ready to be streamed as ``application/zip``.
        """
        logger.info("export requested: format=csv")

        user_assets, transactions = await self._fetch_all()

        # Build symbol lookup: user_asset_id → AssetSymbol
        symbol_by_ua_id: dict[int, object] = {ua.id: ua.asset_symbol for ua in user_assets}

        # --- user_assets.csv ---
        ua_buf = io.StringIO()
        ua_writer = csv.writer(ua_buf, lineterminator="\n")
        ua_writer.writerow(_USER_ASSETS_HEADERS)
        for ua in user_assets:
            sym = ua.asset_symbol
            ua_writer.writerow(
                [
                    ua.id,
                    sym.asset_type.value,
                    sym.symbol,
                    sym.exchange,
                    sym.name,
                    sym.currency,
                    ua.memo if ua.memo is not None else "",
                    ua.created_at.isoformat(),
                ]
            )

        # --- transactions.csv ---
        tx_buf = io.StringIO()
        tx_writer = csv.writer(tx_buf, lineterminator="\n")
        tx_writer.writerow(_TRANSACTIONS_HEADERS)
        for tx in transactions:
            sym_obj = symbol_by_ua_id.get(tx.user_asset_id)
            symbol_str = getattr(sym_obj, "symbol", "") if sym_obj is not None else ""
            tx_writer.writerow(
                [
                    tx.id,
                    tx.user_asset_id,
                    symbol_str,
                    tx.type.value,
                    str(tx.quantity),
                    str(tx.price),
                    tx.traded_at.isoformat(),
                    tx.memo if tx.memo is not None else "",
                    tx.tag if tx.tag is not None else "",
                    tx.created_at.isoformat(),
                ]
            )

        # --- Pack into ZIP ---
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("user_assets.csv", ua_buf.getvalue())
            zf.writestr("transactions.csv", tx_buf.getvalue())

        return zip_buf.getvalue()

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    async def _fetch_all(self) -> tuple[list[UserAsset], list[Transaction]]:
        """Fetch user_assets (with asset_symbol) and all transactions in two queries."""
        user_assets = await self._ua_repo.list_all()
        transactions = await self._tx_repo.list_all()
        return user_assets, transactions
