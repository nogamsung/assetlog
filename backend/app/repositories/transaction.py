"""Transaction repository — pure data access, no business logic."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.transaction_type import TransactionType
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate


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
    ) -> list[Transaction]:
        """Return transactions for a UserAsset ordered by traded_at DESC."""
        stmt = (
            select(Transaction)
            .where(Transaction.user_asset_id == user_asset_id)
            .order_by(Transaction.traded_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_summary(
        self,
        user_asset_id: int,
    ) -> tuple[Decimal, Decimal, Decimal, int]:
        """Return (total_quantity, avg_buy_price, total_invested, count) for BUY rows.

        Uses a single SQL aggregation query to avoid Python-level iteration.
        Returns zeroed-out tuple when there are no transactions.
        """
        stmt = select(
            func.coalesce(func.sum(Transaction.quantity), Decimal("0")).label("total_qty"),
            func.coalesce(func.sum(Transaction.quantity * Transaction.price), Decimal("0")).label(
                "total_cost"
            ),
            func.count(Transaction.id).label("tx_count"),
        ).where(
            Transaction.user_asset_id == user_asset_id,
            Transaction.type == TransactionType.BUY,
        )
        row = (await self._session.execute(stmt)).one()

        total_qty: Decimal = Decimal(str(row.total_qty))
        total_cost: Decimal = Decimal(str(row.total_cost))
        count: int = int(row.tx_count)

        avg_price = total_cost / total_qty if total_qty != Decimal("0") else Decimal("0")
        return total_qty, avg_price, total_cost, count

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
