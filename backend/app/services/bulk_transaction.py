"""BulkTransactionService — multi-symbol transaction import (JSON and CSV modes)."""

from __future__ import annotations

import csv
import io
import logging
import time
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from pydantic import ValidationError

from app.domain.transaction_type import TransactionType
from app.exceptions import CsvImportValidationError
from app.models.transaction import Transaction
from app.repositories.transaction import TransactionRepository
from app.repositories.user_asset import UserAssetRepository
from app.schemas.bulk_transaction import BulkTransactionRow

_REQUIRED_CSV_COLUMNS: frozenset[str] = frozenset(
    {"symbol", "exchange", "type", "quantity", "price", "traded_at"}
)
_TYPE_NORMALISATION: dict[str, str] = {
    "buy": "buy",
    "sell": "sell",
    "매수": "buy",
    "매도": "sell",
}
_MAX_ROWS = 500

logger = logging.getLogger(__name__)


class BulkTransactionService:
    """Import multi-symbol transactions in bulk — all-or-nothing semantics.

    No FastAPI / HTTP imports allowed.  Domain exceptions are raised and
    converted to HTTP responses in the router layer.
    """

    def __init__(
        self,
        transaction_repo: TransactionRepository,
        user_asset_repo: UserAssetRepository,
    ) -> None:
        self._tx_repo = transaction_repo
        self._ua_repo = user_asset_repo

    async def import_json(
        self,
        rows: list[BulkTransactionRow],
    ) -> tuple[int, list[Transaction]]:
        """Import transactions from validated BulkTransactionRow objects.

        All rows are validated as a batch before any DB write.  A single
        ``session.add_all`` + ``session.flush`` is used for all-or-nothing
        semantics (commit is handled by the session dependency).

        Args:
            rows: Pre-validated transaction rows (1–500 items).

        Returns:
            Tuple of (imported_count, preview) where preview is the first
            10 inserted transactions ordered by traded_at ASC.

        Raises:
            CsvImportValidationError: If any row fails symbol resolution or
                running-balance validation.
        """
        start_ms = time.monotonic()

        if not rows:
            raise CsvImportValidationError(
                [{"row": 0, "field": None, "message": "No rows to import."}]
            )
        if len(rows) > _MAX_ROWS:
            raise CsvImportValidationError(
                [
                    {
                        "row": 0,
                        "field": None,
                        "message": f"Too many rows: {len(rows)} (limit {_MAX_ROWS}).",
                    }
                ]
            )

        # Step 1: resolve (symbol, exchange) → user_asset_id in one query.
        pairs: list[tuple[str, str]] = [(r.symbol.upper(), r.exchange.upper()) for r in rows]
        symbol_map = await self._ua_repo.get_user_asset_ids_by_symbol_exchange(pairs)

        errors: list[dict[str, object]] = []
        row_user_asset_ids: list[int | None] = []

        for idx, row in enumerate(rows):
            key = (row.symbol.upper(), row.exchange.upper())
            uid = symbol_map.get(key)
            if uid is None:
                errors.append(
                    {
                        "row": idx + 1,
                        "field": "symbol",
                        "message": (
                            f"Unknown (symbol={row.symbol!r}, exchange={row.exchange!r}) — "
                            "register the asset first."
                        ),
                    }
                )
            row_user_asset_ids.append(uid)

        if errors:
            raise CsvImportValidationError(errors)

        # Step 2: load existing transactions for all involved user_assets (1 query).
        involved_ids: list[int] = list({uid for uid in row_user_asset_ids if uid is not None})
        existing_by_ua = await self._tx_repo.list_all_for_user_assets(involved_ids)

        # Step 3: running-balance validation per user_asset.
        balance_errors = self._validate_running_balance(rows, row_user_asset_ids, existing_by_ua)
        if balance_errors:
            raise CsvImportValidationError(balance_errors)

        # Step 4: insert all rows in one flush (all-or-nothing).
        new_txs: list[Transaction] = []
        for row, uid in zip(rows, row_user_asset_ids, strict=True):
            tx = Transaction(
                user_asset_id=uid,
                type=row.type,
                quantity=row.quantity,
                price=row.price,
                traded_at=row.traded_at,
                memo=row.memo,
                tag=row.tag,
            )
            new_txs.append(tx)

        self._tx_repo._session.add_all(new_txs)
        await self._tx_repo._session.flush()
        for tx in new_txs:
            await self._tx_repo._session.refresh(tx)

        imported_count = len(new_txs)
        duration_ms = int((time.monotonic() - start_ms) * 1000)
        logger.info(
            "bulk_import: imported=%d row_count=%d duration_ms=%d",
            imported_count,
            len(rows),
            duration_ms,
        )

        preview = sorted(new_txs, key=lambda t: t.traded_at)[:10]
        return imported_count, preview

    async def import_csv(
        self,
        csv_text: str,
    ) -> tuple[int, list[Transaction]]:
        """Parse a UTF-8 CSV string and delegate to import_json.

        Validates the header row first, then converts each CSV row into a
        BulkTransactionRow before calling import_json for all-or-nothing
        semantics.

        Args:
            csv_text: UTF-8 (or UTF-8-BOM) CSV content as a string.

        Returns:
            Same as import_json.

        Raises:
            CsvImportValidationError: If the header is missing required columns
                or any data row fails validation.
        """
        cleaned = csv_text.lstrip("﻿")
        reader = csv.DictReader(io.StringIO(cleaned))

        fieldnames_set: frozenset[str] = (
            frozenset(reader.fieldnames) if reader.fieldnames else frozenset()
        )
        if not _REQUIRED_CSV_COLUMNS.issubset(fieldnames_set):
            missing = _REQUIRED_CSV_COLUMNS - fieldnames_set
            raise CsvImportValidationError(
                [
                    {
                        "row": 0,
                        "field": None,
                        "message": f"Missing required CSV columns: {', '.join(sorted(missing))}",
                    }
                ]
            )

        errors: list[dict[str, object]] = []
        validated_rows: list[BulkTransactionRow] = []

        for row_idx, raw_row in enumerate(reader, start=1):
            raw_type = (raw_row.get("type") or "").strip()
            normalised_type = _TYPE_NORMALISATION.get(raw_type.lower(), raw_type.lower())

            raw_memo = (raw_row.get("memo") or "").strip()
            memo_value: str | None = raw_memo if raw_memo else None

            raw_tag = (raw_row.get("tag") or "").strip() if "tag" in raw_row else ""
            tag_value: str | None = raw_tag if raw_tag else None

            try:
                bulk_row = BulkTransactionRow.model_validate(
                    {
                        "symbol": (raw_row.get("symbol") or "").strip(),
                        "exchange": (raw_row.get("exchange") or "").strip(),
                        "type": normalised_type,
                        "quantity": (raw_row.get("quantity") or "").strip(),
                        "price": (raw_row.get("price") or "").strip(),
                        "traded_at": (raw_row.get("traded_at") or "").strip(),
                        "memo": memo_value,
                        "tag": tag_value,
                    }
                )
                validated_rows.append(bulk_row)
            except ValidationError as exc:
                for err in exc.errors():
                    loc = err.get("loc", ())
                    field_name: str | None = str(loc[-1]) if loc else None
                    errors.append(
                        {
                            "row": row_idx,
                            "field": field_name,
                            "message": err.get("msg", "Validation error"),
                        }
                    )

        if errors:
            raise CsvImportValidationError(errors)

        if not validated_rows:
            raise CsvImportValidationError(
                [{"row": 0, "field": None, "message": "CSV contains no data rows."}]
            )

        return await self.import_json(validated_rows)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_running_balance(
        self,
        rows: list[BulkTransactionRow],
        row_user_asset_ids: list[int | None],
        existing_by_ua: dict[int, list[Transaction]],
    ) -> list[dict[str, object]]:
        """Validate that no running balance goes negative after the new rows are applied.

        For each user_asset, merges existing transactions with the new rows for that
        asset, sorts by traded_at ASC, and checks the cumulative balance.

        Args:
            rows: The incoming transaction rows (already symbol-resolved).
            row_user_asset_ids: Parallel list mapping each row to its user_asset_id.
            existing_by_ua: Dict of existing transactions keyed by user_asset_id.

        Returns:
            List of error dicts (may be empty if all balances are OK).
        """

        class _TxProxy:
            __slots__ = ("traded_at", "tx_type", "quantity", "row_idx")

            def __init__(
                self,
                traded_at: datetime,
                tx_type: TransactionType,
                quantity: Decimal,
                row_idx: int,
            ) -> None:
                self.traded_at = traded_at
                self.tx_type = tx_type
                self.quantity = quantity
                self.row_idx = row_idx  # -1 for existing rows

        # Build per-asset timelines.
        new_by_ua: dict[int, list[_TxProxy]] = defaultdict(list)
        for idx, (row, uid) in enumerate(zip(rows, row_user_asset_ids, strict=True)):
            if uid is not None:
                new_by_ua[uid].append(_TxProxy(row.traded_at, row.type, row.quantity, idx + 1))

        balance_errors: list[dict[str, object]] = []

        for uid, new_proxies in new_by_ua.items():
            existing_proxies = [
                _TxProxy(tx.traded_at, tx.type, tx.quantity, -1)
                for tx in existing_by_ua.get(uid, [])
            ]
            timeline = existing_proxies + new_proxies
            timeline.sort(key=lambda p: p.traded_at)

            running: Decimal = Decimal("0")
            for proxy in timeline:
                if proxy.tx_type == TransactionType.BUY:
                    running += proxy.quantity
                else:
                    running -= proxy.quantity
                if running < Decimal("0"):
                    balance_errors.append(
                        {
                            "row": proxy.row_idx if proxy.row_idx > 0 else 0,
                            "field": None,
                            "message": (
                                f"Running balance would go negative at "
                                f"traded_at={proxy.traded_at} (net={running})."
                            ),
                        }
                    )
                    break  # one error per asset is enough

        return balance_errors
