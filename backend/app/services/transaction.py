"""Transaction service — business logic for trade recording and summary."""

from __future__ import annotations

import logging
from decimal import Decimal

from app.domain.transaction_type import TransactionType  # ADDED
from app.exceptions import InsufficientHoldingError, NotFoundError  # MODIFIED
from app.models.transaction import Transaction
from app.repositories.transaction import TransactionRepository
from app.repositories.user_asset import UserAssetRepository
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    UserAssetSummaryResponse,
)  # MODIFIED

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
    ) -> list[Transaction]:
        """Return paginated transactions for a UserAsset owned by user_id.

        Args:
            user_id: The authenticated user's ID.
            user_asset_id: The UserAsset to query.
            limit: Maximum number of rows (default 100).
            offset: Pagination offset (default 0).

        Returns:
            List of Transaction rows ordered by traded_at DESC.

        Raises:
            NotFoundError: If the UserAsset does not exist or is not owned by user_id.
        """
        ua = await self._ua_repo.get_by_id_for_user(user_asset_id, user_id)
        if ua is None:
            raise NotFoundError(f"UserAsset with id={user_asset_id} not found or not owned by you.")
        return await self._tx_repo.list_for_user_asset(user_asset_id, limit=limit, offset=offset)

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
