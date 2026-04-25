"""Transaction service — business logic for trade recording and summary."""

from __future__ import annotations

import builtins
import csv
import io
import logging
from datetime import datetime
from decimal import Decimal

from pydantic import ValidationError

from app.domain.transaction_type import TransactionType  # ADDED
from app.exceptions import (  # MODIFIED
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
)  # MODIFIED

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
        user_id: int,
        user_asset_id: int,
        data: TransactionCreate,
    ) -> Transaction:
        """Record a new transaction for a UserAsset owned by user_id.

        Args:
            user_id: The authenticated user's ID.
            user_asset_id: The UserAsset the transaction belongs to.
            data: Validated creation payload.

        Returns:
            The newly created Transaction row.

        Raises:
            NotFoundError: If the UserAsset does not exist or is not owned by user_id.
        """
        ua = await self._ua_repo.get_by_id_for_user(user_asset_id, user_id)
        if ua is None:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found or not owned by you.")

        if data.type == TransactionType.SELL:  # ADDED — SELL 유효성 검사
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
        user_id: int,
        user_asset_id: int,
        limit: int = 100,
        offset: int = 0,
        tag: str | None = None,
    ) -> list[Transaction]:
        """Return paginated transactions for a UserAsset owned by user_id.

        Args:
            user_id: The authenticated user's ID.
            user_asset_id: The UserAsset to query.
            limit: Maximum number of rows (default 100).
            offset: Pagination offset (default 0).
            tag: Optional tag filter.  None means no filter.

        Returns:
            List of Transaction rows ordered by traded_at DESC.

        Raises:
            NotFoundError: If the UserAsset does not exist or is not owned by user_id.
        """
        ua = await self._ua_repo.get_by_id_for_user(user_asset_id, user_id)
        if ua is None:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found or not owned by you.")
        return await self._tx_repo.list_for_user_asset(
            user_asset_id, limit=limit, offset=offset, tag=tag
        )

    async def list_distinct_tags(self, user_id: int) -> builtins.list[str]:
        """Return distinct non-null tags used across all transactions for user_id.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            Alphabetically sorted list of unique tags.  May be empty.
        """
        return await self._tx_repo.list_distinct_tags_for_user(user_id)

    async def summary(
        self,
        user_id: int,
        user_asset_id: int,
    ) -> UserAssetSummaryResponse:
        """Return aggregated BUY summary for a UserAsset owned by user_id.

        Args:
            user_id: The authenticated user's ID.
            user_asset_id: The UserAsset to summarise.

        Returns:
            UserAssetSummaryResponse with totals and currency.

        Raises:
            NotFoundError: If the UserAsset does not exist or is not owned by user_id.
        """
        ua = await self._ua_repo.get_by_id_for_user(user_asset_id, user_id)
        if ua is None:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found or not owned by you.")

        agg = await self._tx_repo.get_summary(user_asset_id)  # MODIFIED — SummaryAggregates

        # Derived fields
        zero = Decimal("0")
        avg_buy_price = (
            agg.total_bought_cost / agg.total_bought_qty if agg.total_bought_qty != zero else zero
        )
        remaining_quantity = agg.total_bought_qty - agg.total_sold_qty
        realized_pnl = agg.total_sold_value - agg.total_sold_qty * avg_buy_price  # ADDED

        return UserAssetSummaryResponse(
            user_asset_id=user_asset_id,
            total_bought_quantity=agg.total_bought_qty,  # MODIFIED
            total_sold_quantity=agg.total_sold_qty,  # ADDED
            remaining_quantity=remaining_quantity,  # ADDED
            avg_buy_price=avg_buy_price,
            total_invested=agg.total_bought_cost,
            total_sold_value=agg.total_sold_value,  # ADDED
            realized_pnl=realized_pnl,  # ADDED
            transaction_count=agg.tx_count,
            currency=ua.asset_symbol.currency,
        )

    async def edit(  # ADDED
        self,
        user_id: int,
        user_asset_id: int,
        transaction_id: int,
        data: TransactionUpdate,
    ) -> Transaction:
        """Replace all fields of an existing transaction.

        Args:
            user_id: The authenticated user's ID.
            user_asset_id: The UserAsset the transaction belongs to.
            transaction_id: The Transaction row to update.
            data: Validated replacement payload.

        Returns:
            The updated Transaction row.

        Raises:
            NotFoundError: If the UserAsset or Transaction does not exist / not owned.
            InsufficientHoldingError: If the edit would produce a negative holding.
        """
        ua = await self._ua_repo.get_by_id_for_user(user_asset_id, user_id)
        if ua is None:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found or not owned by you.")

        tx = await self._tx_repo.get_by_id_for_user_asset(transaction_id, user_asset_id)
        if tx is None:
            raise NotFoundError(
                f"Transaction with id={transaction_id} not found in UserAsset id={user_asset_id}."
            )

        # SELL 수량 검증 — 수정 대상 tx 를 제외한 나머지 집계로 가상 remaining 계산
        agg = await self._tx_repo.get_summary(user_asset_id)
        # 현재 tx 의 기여분을 제거해 "다른 tx 들만의" 집계로 환원
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

        # avg_buy_price 기반 realized P&L 재계산이 필요한 경우를 위해 other_bought_cost 는 보존
        _ = other_bought_cost  # noqa: F841  # referenced for clarity, unused in update path

        updated = await self._tx_repo.update(transaction_id, user_asset_id, data)
        if updated is None:  # 실제로는 위에서 이미 확인했으므로 방어 코드
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
        user_id: int,
        user_asset_id: int,
        transaction_id: int,
    ) -> None:
        """Hard-delete a transaction owned (transitively) by user_id.

        Args:
            user_id: The authenticated user's ID.
            user_asset_id: The UserAsset the transaction belongs to.
            transaction_id: The Transaction row to remove.

        Raises:
            NotFoundError: If the UserAsset or Transaction does not exist / not owned.
        """
        ua = await self._ua_repo.get_by_id_for_user(user_asset_id, user_id)
        if ua is None:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found or not owned by you.")

        deleted = await self._tx_repo.delete_by_id_for_user_asset(transaction_id, user_asset_id)
        if not deleted:
            raise NotFoundError(
                f"Transaction with id={transaction_id} not found in UserAsset id={user_asset_id}."
            )
        logger.info(
            "Transaction removed: id=%s user_asset_id=%s user_id=%s",
            transaction_id,
            user_asset_id,
            user_id,
        )

    async def import_csv(
        self,
        user_id: int,
        user_asset_id: int,
        csv_text: str,
    ) -> tuple[int, builtins.list[Transaction]]:
        """Bulk-import transactions from a CSV string (all-or-nothing semantics).

        Args:
            user_id: The authenticated user's ID (ownership check).
            user_asset_id: Target UserAsset to import transactions into.
            csv_text: UTF-8 CSV text with optional BOM prefix.

        Returns:
            A tuple of (imported_count, preview_transactions) where preview
            contains the first 10 inserted transactions in traded_at ASC order.

        Raises:
            NotFoundError: If the UserAsset does not exist or is not owned by user_id.
            CsvImportValidationError: If any row fails validation (no rows are
                inserted — all-or-nothing).
        """
        # 1. Ownership check
        ua = await self._ua_repo.get_by_id_for_user(user_asset_id, user_id)
        if ua is None:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found or not owned by you.")

        # 2. Strip BOM and parse CSV
        cleaned = csv_text.lstrip("﻿")
        reader = csv.DictReader(io.StringIO(cleaned))

        # 3. Header validation
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

        # 4. Per-row validation
        errors: list[dict[str, object]] = []
        validated_rows: list[TransactionCreate] = []

        for row_idx, raw_row in enumerate(reader, start=1):
            # Normalize type
            raw_type = (raw_row.get("type") or "").strip()
            normalised_type = _TYPE_NORMALISATION.get(raw_type.lower(), raw_type.lower())

            # Normalize memo
            raw_memo = raw_row.get("memo", "").strip()
            memo_value: str | None = raw_memo if raw_memo else None

            # Normalize tag — present only when CSV has a "tag" column
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

        # Short-circuit if any individual row errors exist — do not insert
        if errors:
            raise CsvImportValidationError(errors)

        # 5. SELL running-balance validation
        existing_txs = await self._tx_repo.list_all_for_user_asset(user_asset_id)

        # Merge existing + new rows into a unified timeline (traded_at ASC)
        # New rows do not have a DB id yet; represent them as plain dicts for sorting
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
                break  # one report is sufficient; abort early

        if balance_errors:
            raise CsvImportValidationError(balance_errors)

        # 6. All rows are valid — bulk insert in a single flush
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
            "CSV import: user_id=%s user_asset_id=%s imported=%s",
            user_id,
            user_asset_id,
            imported_count,
        )

        # 7. Return count + first 10 (sorted ASC by traded_at to match insertion timeline)
        preview = sorted(new_txs, key=lambda t: t.traded_at)[:10]
        return imported_count, preview
