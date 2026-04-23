"""Transaction service — business logic for trade recording and summary."""

from __future__ import annotations

import logging

from app.exceptions import NotFoundError
from app.models.transaction import Transaction
from app.repositories.transaction import TransactionRepository
from app.repositories.user_asset import UserAssetRepository
from app.schemas.transaction import TransactionCreate, UserAssetSummaryResponse

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

        total_qty, avg_price, total_invested, count = await self._tx_repo.get_summary(user_asset_id)

        return UserAssetSummaryResponse(
            user_asset_id=user_asset_id,
            total_quantity=total_qty,
            avg_buy_price=avg_price,
            total_invested=total_invested,
            transaction_count=count,
            currency=ua.asset_symbol.currency,
        )

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
