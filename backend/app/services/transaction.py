"""Transaction service — business logic for trade recording and summary."""

from __future__ import annotations

import builtins
import csv
import io
import logging
from datetime import datetime
from decimal import Decimal

from pydantic import ValidationError

from app.domain.transaction_type import TransactionType
from app.exceptions import (
    CsvImportValidationError,
    InsufficientHoldingError,
    NotFoundError,
)
from app.models.transaction import Transaction
from app.repositories.transaction import TransactionRepository
from app.repositories.user_asset import UserAssetRepository
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    UserAssetSummaryResponse,
)

_REQUIRED_CSV_COLUMNS: frozenset[str] = frozenset(
    {"type", "quantity", "price", "traded_at", "memo"}
)
_TYPE_NORMALISATION: dict[str, str] = {
    "buy": "buy",
    "sell": "sell",
    "매수": "buy",
    "매도": "sell",
}

logger = logging.getLogger(__name__)


class TransactionService:
    """Handles Transaction lifecycle — no FastAPI/HTTP imports allowed."""

    def __init__(
        self,
        transaction_repo: TransactionRepository,
        user_asset_repo: UserAssetRepository,
    ) -> None:
        self._tx_repo = transaction_repo
        self._ua_repo = user_asset_repo

    async def add(
        self,
        user_asset_id: int,
        data: TransactionCreate,
    ) -> Transaction:
        """Record a new transaction for a UserAsset.

        Raises:
            NotFoundError: If the UserAsset does not exist.
            InsufficientHoldingError: If a SELL would leave a negative balance.
        """
        ua = await self._ua_repo.get_by_id(user_asset_id)
        if ua is None:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found.")

        if data.type == TransactionType.SELL:
            remaining = await self._tx_repo.get_remaining_quantity(user_asset_id)
            if data.quantity > remaining:
                raise InsufficientHoldingError(
                    f"Cannot sell {data.quantity} units: only {remaining} units held."
                )

        tx = await self._tx_repo.create(user_asset_id=user_asset_id, data=data)
        logger.info(
            "Transaction added: id=%s user_asset_id=%s type=%s quantity=%s price=%s",
            tx.id,
            user_asset_id,
            data.type,
            data.quantity,
            data.price,
        )
        return tx

    async def list(
        self,
        user_asset_id: int,
        limit: int = 100,
        offset: int = 0,
        tag: str | None = None,
    ) -> list[Transaction]:
        """Return paginated transactions for a UserAsset.

        Raises:
            NotFoundError: If the UserAsset does not exist.
        """
        ua = await self._ua_repo.get_by_id(user_asset_id)
        if ua is None:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found.")
        return await self._tx_repo.list_for_user_asset(
            user_asset_id, limit=limit, offset=offset, tag=tag
        )

    async def list_distinct_tags(self) -> builtins.list[str]:
        """Return distinct non-null tags across all transactions."""
        return await self._tx_repo.list_distinct_tags()

    async def summary(
        self,
        user_asset_id: int,
    ) -> UserAssetSummaryResponse:
        """Return aggregated BUY/SELL summary for a UserAsset.

        Raises:
            NotFoundError: If the UserAsset does not exist.
        """
        ua = await self._ua_repo.get_by_id(user_asset_id)
        if ua is None:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found.")

        agg = await self._tx_repo.get_summary(user_asset_id)

        zero = Decimal("0")
        avg_buy_price = (
            agg.total_bought_cost / agg.total_bought_qty if agg.total_bought_qty != zero else zero
        )
        remaining_quantity = agg.total_bought_qty - agg.total_sold_qty
        realized_pnl = agg.total_sold_value - agg.total_sold_qty * avg_buy_price

        return UserAssetSummaryResponse(
            user_asset_id=user_asset_id,
            total_bought_quantity=agg.total_bought_qty,
            total_sold_quantity=agg.total_sold_qty,
            remaining_quantity=remaining_quantity,
            avg_buy_price=avg_buy_price,
            total_invested=agg.total_bought_cost,
            total_sold_value=agg.total_sold_value,
            realized_pnl=realized_pnl,
            transaction_count=agg.tx_count,
            currency=ua.asset_symbol.currency,
        )

    async def edit(
        self,
        user_asset_id: int,
        transaction_id: int,
        data: TransactionUpdate,
    ) -> Transaction:
        """Replace all fields of an existing transaction.

        Raises:
            NotFoundError: If the UserAsset or Transaction does not exist.
            InsufficientHoldingError: If the edit would produce a negative holding.
        """
        ua = await self._ua_repo.get_by_id(user_asset_id)
        if ua is None:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found.")

        tx = await self._tx_repo.get_by_id_for_user_asset(transaction_id, user_asset_id)
        if tx is None:
            raise NotFoundError(
                f"Transaction with id={transaction_id} not found in UserAsset id={user_asset_id}."
            )

        agg = await self._tx_repo.get_summary(user_asset_id)
        if tx.type == TransactionType.BUY:
            other_bought = agg.total_bought_qty - tx.quantity
            other_bought_cost = agg.total_bought_cost - tx.quantity * tx.price
        else:
            other_bought = agg.total_bought_qty
            other_bought_cost = agg.total_bought_cost
        if tx.type == TransactionType.SELL:
            other_sold = agg.total_sold_qty - tx.quantity
        else:
            other_sold = agg.total_sold_qty

        if data.type == TransactionType.BUY:
            hypothetical_remaining = other_bought + data.quantity - other_sold
        else:
            hypothetical_remaining = other_bought - other_sold - data.quantity

        if hypothetical_remaining < 0:
            raise InsufficientHoldingError("Edit would leave negative holding.")

        _ = other_bought_cost  # noqa: F841  # referenced for clarity, unused in update path

        updated = await self._tx_repo.update(transaction_id, user_asset_id, data)
        if updated is None:
            raise NotFoundError(
                f"Transaction with id={transaction_id} not found in UserAsset id={user_asset_id}."
            )
        logger.info(
            "Transaction updated: id=%s user_asset_id=%s type=%s quantity=%s price=%s",
            transaction_id,
            user_asset_id,
            data.type,
            data.quantity,
            data.price,
        )
        return updated

    async def remove(
        self,
        user_asset_id: int,
        transaction_id: int,
    ) -> None:
        """Hard-delete a transaction.

        Raises:
            NotFoundError: If the UserAsset or Transaction does not exist.
        """
        ua = await self._ua_repo.get_by_id(user_asset_id)
        if ua is None:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found.")

        deleted = await self._tx_repo.delete_by_id_for_user_asset(transaction_id, user_asset_id)
        if not deleted:
            raise NotFoundError(
                f"Transaction with id={transaction_id} not found in UserAsset id={user_asset_id}."
            )
        logger.info(
            "Transaction removed: id=%s user_asset_id=%s",
            transaction_id,
            user_asset_id,
        )

    async def import_csv(
        self,
        user_asset_id: int,
        csv_text: str,
    ) -> tuple[int, builtins.list[Transaction]]:
        """Bulk-import transactions from a CSV string (all-or-nothing semantics).

        Returns:
            (imported_count, preview_transactions) — first 10 inserted in traded_at ASC.

        Raises:
            NotFoundError: If the UserAsset does not exist.
            CsvImportValidationError: If any row fails validation (no rows are inserted).
        """
        ua = await self._ua_repo.get_by_id(user_asset_id)
        if ua is None:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found.")

        cleaned = csv_text.lstrip("﻿")
        reader = csv.DictReader(io.StringIO(cleaned))

        if reader.fieldnames is None or not _REQUIRED_CSV_COLUMNS.issubset(set(reader.fieldnames)):
            missing = (
                _REQUIRED_CSV_COLUMNS - set(reader.fieldnames)
                if reader.fieldnames
                else _REQUIRED_CSV_COLUMNS
            )
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
        validated_rows: list[TransactionCreate] = []

        for row_idx, raw_row in enumerate(reader, start=1):
            raw_type = (raw_row.get("type") or "").strip()
            normalised_type = _TYPE_NORMALISATION.get(raw_type.lower(), raw_type.lower())

            raw_memo = raw_row.get("memo", "").strip()
            memo_value: str | None = raw_memo if raw_memo else None

            raw_tag = raw_row.get("tag", "").strip() if "tag" in (raw_row or {}) else ""
            tag_value: str | None = raw_tag if raw_tag else None

            try:
                create_data = TransactionCreate.model_validate(
                    {
                        "type": normalised_type,
                        "quantity": raw_row.get("quantity", "").strip(),
                        "price": raw_row.get("price", "").strip(),
                        "traded_at": raw_row.get("traded_at", "").strip(),
                        "memo": memo_value,
                        "tag": tag_value,
                    }
                )
                validated_rows.append(create_data)
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

        existing_txs = await self._tx_repo.list_all_for_user_asset(user_asset_id)

        class _TxProxy:
            """Lightweight proxy to unify ORM Transaction and TransactionCreate for sorting."""

            __slots__ = ("traded_at", "tx_type", "quantity")

            def __init__(
                self,
                traded_at: datetime,
                tx_type: TransactionType,
                quantity: Decimal,
            ) -> None:
                self.traded_at = traded_at
                self.tx_type = tx_type
                self.quantity = quantity

        timeline: list[_TxProxy] = [
            _TxProxy(tx.traded_at, tx.type, tx.quantity) for tx in existing_txs
        ] + [_TxProxy(row.traded_at, row.type, row.quantity) for row in validated_rows]
        timeline.sort(key=lambda p: p.traded_at)

        running: Decimal = Decimal("0")
        balance_errors: list[dict[str, object]] = []
        for proxy in timeline:
            if proxy.tx_type == TransactionType.BUY:
                running += proxy.quantity
            else:
                running -= proxy.quantity
            if running < Decimal("0"):
                balance_errors.append(
                    {
                        "row": 0,
                        "field": None,
                        "message": (
                            f"Running balance would go negative at traded_at="
                            f"{proxy.traded_at} (net={running})."
                        ),
                    }
                )
                break

        if balance_errors:
            raise CsvImportValidationError(balance_errors)

        new_txs: list[Transaction] = []
        for row in validated_rows:
            tx = Transaction(
                user_asset_id=user_asset_id,
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
        logger.info(
            "CSV import: user_asset_id=%s imported=%s",
            user_asset_id,
            imported_count,
        )

        preview = sorted(new_txs, key=lambda t: t.traded_at)[:10]
        return imported_count, preview
