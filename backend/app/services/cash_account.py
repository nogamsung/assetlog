"""CashAccount service — business logic for cash balance management."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from app.exceptions import NotFoundError
from app.models.cash_account import CashAccount
from app.repositories.cash_account import CashAccountRepository
from app.schemas.cash_account import CashAccountCreate, CashAccountUpdate

logger = logging.getLogger(__name__)


class CashAccountService:
    """Handles CashAccount lifecycle — no FastAPI/HTTP imports."""

    def __init__(self, repository: CashAccountRepository) -> None:
        self._repo = repository

    async def list(self) -> Sequence[CashAccount]:
        """Return all cash accounts ordered by creation date descending."""
        return await self._repo.list_all()

    async def create(self, data: CashAccountCreate) -> CashAccount:
        """Create a new cash account.

        Args:
            data: Validated creation payload.

        Returns:
            The persisted CashAccount instance.
        """
        account = await self._repo.create(
            label=data.label,
            currency=data.currency,
            balance=data.balance,
        )
        logger.info(
            "CashAccount created: id=%s currency=%s",
            account.id,
            account.currency,
        )
        return account

    async def update(self, id_: int, data: CashAccountUpdate) -> CashAccount:
        """Partially update an existing cash account.

        Args:
            id_: Primary key of the cash account to update.
            data: Validated update payload (at least one field set).

        Raises:
            NotFoundError: If no CashAccount with the given id exists.

        Returns:
            The updated CashAccount instance.
        """
        account = await self._repo.get_by_id(id_)
        if account is None:
            raise NotFoundError(f"CashAccount {id_} not found")
        updated = await self._repo.update(account, label=data.label, balance=data.balance)
        logger.info("CashAccount updated: id=%s", updated.id)
        return updated

    async def delete(self, id_: int) -> None:
        """Delete a cash account by id.

        Args:
            id_: Primary key of the cash account to delete.

        Raises:
            NotFoundError: If no CashAccount with the given id exists.
        """
        account = await self._repo.get_by_id(id_)
        if account is None:
            raise NotFoundError(f"CashAccount {id_} not found")
        await self._repo.delete(account)
        logger.info("CashAccount deleted: id=%s", id_)
