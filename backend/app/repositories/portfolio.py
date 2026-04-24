"""Portfolio repository — aggregated holdings query, no business logic."""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.portfolio import HoldingRow
from app.domain.transaction_type import TransactionType
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset

logger = logging.getLogger(__name__)


class PortfolioRepository:
    """Read-only aggregation queries scoped to a single user.

    The single public method issues one database round-trip by combining
    a correlated subquery for BUY-transaction aggregates with selectinload
    for the AssetSymbol relationship — N+1 is explicitly prevented.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_user_holdings_with_aggregates(
        self,
        user_id: int,
    ) -> list[HoldingRow]:
        """Return aggregated holding rows for all UserAsset rows owned by *user_id*.

        Each row contains:
        - ``user_asset_id`` — PK of the UserAsset row.
        - ``asset_symbol``  — eagerly loaded AssetSymbol (last_price included).
        - ``total_qty``     — Σ quantity of BUY transactions (0 if none).
        - ``total_cost``    — Σ (quantity × price) of BUY transactions (0 if none).

        A UserAsset with zero transactions is **included** with zeroed aggregates
        so the service layer can expose it as a pending / zero-cost holding.
        """
        # Correlated subquery: BUY aggregates per user_asset
        buy_agg = (
            select(
                Transaction.user_asset_id.label("ua_id"),
                func.coalesce(func.sum(Transaction.quantity), Decimal("0")).label("total_qty"),
                func.coalesce(
                    func.sum(Transaction.quantity * Transaction.price),
                    Decimal("0"),
                ).label("total_cost"),
            )
            .where(Transaction.type == TransactionType.BUY)
            .group_by(Transaction.user_asset_id)
            .subquery()
        )

        stmt = (
            select(
                UserAsset,
                func.coalesce(buy_agg.c.total_qty, Decimal("0")).label("total_qty"),
                func.coalesce(buy_agg.c.total_cost, Decimal("0")).label("total_cost"),
            )
            .options(selectinload(UserAsset.asset_symbol))
            .outerjoin(buy_agg, UserAsset.id == buy_agg.c.ua_id)
            .where(UserAsset.user_id == user_id)
            .order_by(UserAsset.created_at)
        )

        rows = (await self._session.execute(stmt)).all()

        result: list[HoldingRow] = []
        for row in rows:
            user_asset: UserAsset = row[0]
            total_qty = Decimal(str(row.total_qty))
            total_cost = Decimal(str(row.total_cost))
            result.append(
                HoldingRow(
                    user_asset_id=user_asset.id,
                    asset_symbol=user_asset.asset_symbol,
                    total_qty=total_qty,
                    total_cost=total_cost,
                )
            )

        logger.debug(
            "list_user_holdings_with_aggregates: user_id=%s returned %d rows",
            user_id,
            len(result),
        )
        return result
