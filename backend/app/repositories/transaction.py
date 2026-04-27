"""Transaction repository — pure data access, no business logic."""

from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple  # ADDED

from sqlalchemy import case, func, select  # MODIFIED
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.transaction_type import TransactionType
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate


class SummaryAggregates(NamedTuple):  # ADDED
    """BUY/SELL aggregates for a single user_asset."""

    total_bought_qty: Decimal
    total_bought_cost: Decimal
    total_sold_qty: Decimal
    total_sold_value: Decimal
    tx_count: int


class TransactionRepository:
    """Async CRUD + aggregation operations for the Transaction model.

    All queries are scoped to a specific user_asset_id so that service-layer
    ownership checks remain the single source of truth for access control.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_asset_id: int,
        data: TransactionCreate,
    ) -> Transaction:
        """Persist a new Transaction row and return the flushed instance."""
        tx = Transaction(
            user_asset_id=user_asset_id,
            type=data.type,
            quantity=data.quantity,
            price=data.price,
            traded_at=data.traded_at,
            memo=data.memo,
            tag=data.tag,
        )
        self._session.add(tx)
        await self._session.flush()
        await self._session.refresh(tx)
        return tx

    async def list_for_user_asset(
        self,
        user_asset_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
        tag: str | None = None,
    ) -> list[Transaction]:
        """Return transactions for a UserAsset ordered by traded_at DESC.

        If *tag* is provided (non-empty), only transactions with that exact tag
        are returned.  An empty string is treated the same as None (no filter).
        """
        stmt = select(Transaction).where(Transaction.user_asset_id == user_asset_id)
        if tag:
            stmt = stmt.where(Transaction.tag == tag)
        stmt = stmt.order_by(Transaction.traded_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all_for_user_asset(self, user_asset_id: int) -> list[Transaction]:
        """Return all transactions for a UserAsset ordered by traded_at ASC.

        Used by import_csv to perform running-balance validation against existing
        transactions before bulk-inserting new ones.
        """
        stmt = (
            select(Transaction)
            .where(Transaction.user_asset_id == user_asset_id)
            .order_by(Transaction.traded_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_summary(  # MODIFIED — BUY/SELL 분리 집계
        self,
        user_asset_id: int,
    ) -> SummaryAggregates:
        """Return BUY/SELL aggregates for a single user_asset in one SQL round-trip.

        Uses conditional aggregation to split BUY vs SELL without a subquery.
        Returns zeroed-out SummaryAggregates when there are no transactions.
        """
        stmt = select(
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == TransactionType.BUY, Transaction.quantity),
                        else_=Decimal("0"),
                    )
                ),
                Decimal("0"),
            ).label("total_bought_qty"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Transaction.type == TransactionType.BUY,
                            Transaction.quantity * Transaction.price,
                        ),
                        else_=Decimal("0"),
                    )
                ),
                Decimal("0"),
            ).label("total_bought_cost"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == TransactionType.SELL, Transaction.quantity),
                        else_=Decimal("0"),
                    )
                ),
                Decimal("0"),
            ).label("total_sold_qty"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Transaction.type == TransactionType.SELL,
                            Transaction.quantity * Transaction.price,
                        ),
                        else_=Decimal("0"),
                    )
                ),
                Decimal("0"),
            ).label("total_sold_value"),
            func.count(Transaction.id).label("tx_count"),
        ).where(Transaction.user_asset_id == user_asset_id)

        row = (await self._session.execute(stmt)).one()

        return SummaryAggregates(
            total_bought_qty=Decimal(str(row.total_bought_qty)),
            total_bought_cost=Decimal(str(row.total_bought_cost)),
            total_sold_qty=Decimal(str(row.total_sold_qty)),
            total_sold_value=Decimal(str(row.total_sold_value)),
            tx_count=int(row.tx_count),
        )

    async def get_remaining_quantity(self, user_asset_id: int) -> Decimal:  # ADDED
        """Return current remaining quantity (Σbuy_qty - Σsell_qty) for a user_asset."""
        agg = await self.get_summary(user_asset_id)
        return agg.total_bought_qty - agg.total_sold_qty

    async def get_by_id_for_user_asset(
        self,
        transaction_id: int,
        user_asset_id: int,
    ) -> Transaction | None:
        """Return a Transaction that belongs to the given user_asset, or None."""
        stmt = select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_asset_id == user_asset_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(  # ADDED
        self,
        transaction_id: int,
        user_asset_id: int,
        data: TransactionUpdate,
    ) -> Transaction | None:
        """Apply full-replace update to a Transaction belonging to user_asset.

        Returns the refreshed Transaction, or None if the row does not exist.
        """
        tx = await self.get_by_id_for_user_asset(transaction_id, user_asset_id)
        if tx is None:
            return None
        tx.type = data.type
        tx.quantity = data.quantity
        tx.price = data.price
        tx.traded_at = data.traded_at
        tx.memo = data.memo
        tx.tag = data.tag
        await self._session.flush()
        await self._session.refresh(tx)
        return tx

    async def delete_by_id_for_user_asset(
        self,
        transaction_id: int,
        user_asset_id: int,
    ) -> bool:
        """Hard-delete a Transaction belonging to the given user_asset.

        Returns True if the row existed and was deleted, False otherwise.
        """
        tx = await self.get_by_id_for_user_asset(transaction_id, user_asset_id)
        if tx is None:
            return False
        await self._session.delete(tx)
        await self._session.flush()
        return True

    async def list_all(self) -> list[Transaction]:
        """Return all transactions across all user_assets in single-owner mode.

        Results are ordered by user_asset_id ASC, then traded_at ASC for reproducible
        export ordering.
        """
        stmt = select(Transaction).order_by(
            Transaction.user_asset_id.asc(), Transaction.traded_at.asc()
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_distinct_tags(self) -> list[str]:
        """Return distinct non-null tags across all transactions.

        Results are ordered alphabetically (ASC).
        Returns an empty list when no tagged transactions exist.
        """
        stmt = (
            select(Transaction.tag)
            .where(Transaction.tag.is_not(None))
            .distinct()
            .order_by(Transaction.tag.asc())
        )
        result = await self._session.execute(stmt)
        return [row for (row,) in result.all()]
