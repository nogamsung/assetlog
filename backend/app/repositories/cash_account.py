"""CashAccount repository — pure data access, no business logic."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cash_account import CashAccount
from app.models.cash_account_transaction import CashAccountTransaction, CashTxKind

logger = logging.getLogger(__name__)


class CashAccountRepository:
    """Async CRUD operations for the CashAccount model.

    Single-owner mode — queries are not user-scoped.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> Sequence[CashAccount]:
        """Return all cash accounts ordered by creation date descending."""
        stmt = select(CashAccount).order_by(CashAccount.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, id_: int) -> CashAccount | None:
        """Return a CashAccount by primary key, or None if not found."""
        stmt = select(CashAccount).where(CashAccount.id == id_)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        label: str,
        currency: str,
        balance: Decimal,
        interest_rate_annual: Decimal | None = None,
    ) -> CashAccount:
        """Persist a new CashAccount and return the refreshed instance.

        Commit is handled by the caller via ``Depends(get_db_session)``.
        Refresh is required to populate server_default columns (created_at, updated_at).
        """
        account = CashAccount(
            label=label,
            currency=currency,
            balance=balance,
            interest_rate_annual=interest_rate_annual,
        )
        self._session.add(account)
        await self._session.flush()
        await self._session.refresh(account)
        logger.debug("CashAccount created: id=%s currency=%s", account.id, account.currency)
        return account

    async def update(
        self,
        entity: CashAccount,
        *,
        label: str | None,
        balance: Decimal | None,
        interest_rate_annual: Decimal | None = None,
    ) -> CashAccount:
        """Apply partial field updates, flush, and refresh. Returns the updated entity."""
        if label is not None:
            entity.label = label
        if balance is not None:
            entity.balance = balance
        if interest_rate_annual is not None:
            entity.interest_rate_annual = interest_rate_annual
        await self._session.flush()
        await self._session.refresh(entity)
        logger.debug("CashAccount updated: id=%s", entity.id)
        return entity

    async def delete(self, entity: CashAccount) -> None:
        """Delete the given CashAccount and flush."""
        await self._session.delete(entity)
        await self._session.flush()
        logger.debug("CashAccount deleted: id=%s", entity.id)

    async def list_transactions(
        self,
        *,
        kind: CashTxKind | None = None,
    ) -> Sequence[CashAccountTransaction]:
        """Return cash account transactions, newest first. Optional kind filter."""
        stmt = select(CashAccountTransaction).order_by(
            CashAccountTransaction.traded_at.desc(),
            CashAccountTransaction.id.desc(),
        )
        if kind is not None:
            stmt = stmt.where(CashAccountTransaction.kind == kind)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def sum_balance_by_currency(self) -> dict[str, Decimal]:
        """Return total balance per currency across all cash accounts.

        Used by PortfolioService to include cash in portfolio aggregation.
        Returns an empty dict if there are no accounts.
        """
        stmt = select(
            CashAccount.currency,
            func.sum(CashAccount.balance).label("total"),
        ).group_by(CashAccount.currency)
        result = await self._session.execute(stmt)
        rows = result.all()
        return {row.currency: Decimal(str(row.total)) for row in rows}
