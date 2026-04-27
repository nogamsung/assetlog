"""Portfolio repository — aggregated holdings query, no business logic."""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import case, func, select, text  # MODIFIED — added text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.portfolio import HoldingRow
from app.domain.transaction_type import TransactionType
from app.models.asset_symbol import AssetSymbol
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset

logger = logging.getLogger(__name__)


class PortfolioRepository:
    """Read-only aggregation queries for the single owner.

    Issues one database round-trip by combining a correlated subquery for
    transaction aggregates with selectinload for the AssetSymbol relationship —
    N+1 is explicitly prevented.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_holdings_with_aggregates(self) -> list[HoldingRow]:
        """Return aggregated holding rows for all declared UserAssets.

        Each row contains:
        - ``user_asset_id`` — PK of the UserAsset row.
        - ``asset_symbol``  — eagerly loaded AssetSymbol (last_price included).
        - ``total_qty``     — Σ quantity of BUY transactions (0 if none).
        - ``total_cost``    — Σ (quantity × price) of BUY transactions (0 if none).

        A UserAsset with zero transactions is **included** with zeroed aggregates
        so the service layer can expose it as a pending / zero-cost holding.
        """
        # Correlated subquery: BUY/SELL aggregates per user_asset via conditional SUM  # MODIFIED
        tx_agg = (
            select(
                Transaction.user_asset_id.label("ua_id"),
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
            )
            .group_by(Transaction.user_asset_id)
            .subquery()
        )

        stmt = (
            select(
                UserAsset,
                func.coalesce(tx_agg.c.total_bought_qty, Decimal("0")).label("total_bought_qty"),
                func.coalesce(tx_agg.c.total_bought_cost, Decimal("0")).label("total_bought_cost"),
                func.coalesce(tx_agg.c.total_sold_qty, Decimal("0")).label("total_sold_qty"),
                func.coalesce(tx_agg.c.total_sold_value, Decimal("0")).label("total_sold_value"),
            )
            .options(selectinload(UserAsset.asset_symbol))
            .outerjoin(tx_agg, UserAsset.id == tx_agg.c.ua_id)
            .order_by(UserAsset.created_at)
        )

        rows = (await self._session.execute(stmt)).all()

        result: list[HoldingRow] = []
        for row in rows:
            user_asset: UserAsset = row[0]
            zero = Decimal("0")
            total_bought_qty = Decimal(str(row.total_bought_qty))
            total_bought_cost = Decimal(str(row.total_bought_cost))
            total_sold_qty = Decimal(str(row.total_sold_qty))
            total_sold_value = Decimal(str(row.total_sold_value))

            # Derived: remaining qty and cost basis of remaining shares  # ADDED
            remaining_qty = total_bought_qty - total_sold_qty
            avg_buy_price = (
                total_bought_cost / total_bought_qty if total_bought_qty != zero else zero
            )
            cost_basis_remaining = avg_buy_price * remaining_qty
            realized_pnl = total_sold_value - total_sold_qty * avg_buy_price  # ADDED

            result.append(
                HoldingRow(
                    user_asset_id=user_asset.id,
                    asset_symbol=user_asset.asset_symbol,
                    total_qty=remaining_qty,  # MODIFIED — remaining, not total bought
                    total_cost=cost_basis_remaining,  # MODIFIED — cost of remaining shares
                    realized_pnl=realized_pnl,  # ADDED
                )
            )

        logger.debug(
            "list_holdings_with_aggregates returned %d rows",
            len(result),
        )
        return result

    async def list_tag_breakdown_rows(
        self,
    ) -> list[tuple[str | None, str, str, Decimal, int]]:
        """Return one row per (tag, currency, transaction_type) triple.

        Issues a single GROUP BY query — no N+1.  NULL tag values are kept
        as a separate group by the database (consistent across MySQL/SQLite).

        Returns:
            List of (tag, currency, type, value_sum, count) tuples where
            ``value_sum`` = Σ(quantity × price) and ``count`` = COUNT(*).
        """
        stmt = (
            select(
                Transaction.tag,
                AssetSymbol.currency,
                Transaction.type,
                func.sum(Transaction.quantity * Transaction.price).label("value_sum"),
                func.count(text("*")).label("cnt"),
            )
            .join(UserAsset, Transaction.user_asset_id == UserAsset.id)
            .join(AssetSymbol, UserAsset.asset_symbol_id == AssetSymbol.id)
            .group_by(Transaction.tag, AssetSymbol.currency, Transaction.type)
        )

        rows = (await self._session.execute(stmt)).all()

        result: list[tuple[str | None, str, str, Decimal, int]] = []
        for row in rows:
            tag: str | None = row[0]
            currency: str = row[1]
            tx_type: str = str(row[2])
            value_sum = Decimal(str(row[3])) if row[3] is not None else Decimal("0")
            cnt: int = int(row[4])
            result.append((tag, currency, tx_type, value_sum, cnt))

        logger.debug(
            "list_tag_breakdown_rows returned %d raw rows",
            len(result),
        )
        return result
