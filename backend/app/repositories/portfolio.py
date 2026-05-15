"""Portfolio repository — aggregated holdings query, no business logic."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select, text
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
        - ``total_qty``     — remaining quantity (BUY − SELL, never negative).
        - ``total_cost``    — cost basis of the *remaining* lot only.
        - ``realized_pnl``  — Σ over SELLs of ``(sell_price − avg_at_sell) × qty``.

        Uses a **moving weighted average** cost-basis so a SELL flushes its
        share of the running cost. A user who buys at 60k, sells, then re-
        buys at 280k sees the average move to the re-buy price — not stay
        anchored at the historical 60k. Korean brokers' "평단가" follows
        the same rule.
        """
        # Pull every transaction in chronological order — moving averages
        # are order-sensitive, so we walk the timeline in Python.
        stmt = (
            select(UserAsset)
            .options(selectinload(UserAsset.asset_symbol))
            .order_by(UserAsset.created_at)
        )
        user_assets = list((await self._session.execute(stmt)).scalars().all())

        ua_ids = [ua.id for ua in user_assets]
        txs_by_ua = await self._load_transactions_ordered(ua_ids)
        buy_lots_by_ua = await self._load_buy_lots(ua_ids)

        zero = Decimal("0")
        result: list[HoldingRow] = []
        for ua in user_assets:
            txs = txs_by_ua.get(ua.id, [])
            running_qty = zero
            running_cost = zero
            realized = zero
            for tx_type, qty, price in txs:
                if tx_type == TransactionType.BUY:
                    running_cost += qty * price
                    running_qty += qty
                else:  # SELL
                    if running_qty > zero:
                        avg = running_cost / running_qty
                        sold_qty = qty if qty <= running_qty else running_qty
                        realized += (price - avg) * sold_qty
                        running_cost -= sold_qty * avg
                        running_qty -= sold_qty
                    # A SELL that exceeds remaining qty is silently capped —
                    # the parsers occasionally over-report a fully-closed
                    # position. The realized PnL on the capped portion is
                    # zero by construction.

            # Guard against tiny float-style residuals leaving cost_basis
            # nonzero when qty has gone to (effectively) zero.
            if running_qty <= zero:
                running_qty = zero
                running_cost = zero

            result.append(
                HoldingRow(
                    user_asset_id=ua.id,
                    asset_symbol=ua.asset_symbol,
                    total_qty=running_qty,
                    total_cost=running_cost,
                    realized_pnl=realized,
                    buy_lots=buy_lots_by_ua.get(ua.id, ()),
                )
            )

        logger.debug(
            "list_holdings_with_aggregates returned %d rows",
            len(result),
        )
        return result

    async def _load_transactions_ordered(
        self, user_asset_ids: list[int]
    ) -> dict[int, list[tuple[TransactionType, Decimal, Decimal]]]:
        """Return ``{ua_id: [(type, qty, price), …]}`` ordered by traded_at ASC.

        One query per call regardless of holdings count — the result is
        grouped in Python so the moving-average walk can iterate per UA.
        """
        if not user_asset_ids:
            return {}
        stmt = (
            select(
                Transaction.user_asset_id,
                Transaction.type,
                Transaction.quantity,
                Transaction.price,
            )
            .where(Transaction.user_asset_id.in_(user_asset_ids))
            .order_by(Transaction.traded_at.asc(), Transaction.id.asc())
        )
        out: dict[int, list[tuple[TransactionType, Decimal, Decimal]]] = {}
        for ua_id, tx_type, qty, price in (await self._session.execute(stmt)).all():
            out.setdefault(ua_id, []).append((tx_type, qty, price))
        return out

    async def _load_buy_lots(
        self,
        user_asset_ids: list[int],
    ) -> dict[int, tuple[tuple[datetime, Decimal], ...]]:
        """Fetch BUY transactions grouped by user_asset_id.

        Each entry maps user_asset_id → tuple of (traded_at, cost_local) tuples
        ordered by traded_at where cost_local = quantity × price in the asset's
        native currency. Used by PortfolioService to compute cost-weighted
        average historical FX rates.
        """
        if not user_asset_ids:
            return {}

        stmt = (
            select(
                Transaction.user_asset_id,
                Transaction.traded_at,
                (Transaction.quantity * Transaction.price).label("cost_local"),
            )
            .where(
                Transaction.user_asset_id.in_(user_asset_ids),
                Transaction.type == TransactionType.BUY,
            )
            .order_by(Transaction.user_asset_id, Transaction.traded_at)
        )
        rows = (await self._session.execute(stmt)).all()

        grouped: dict[int, list[tuple[datetime, Decimal]]] = {}
        for row in rows:
            ua_id = int(row[0])
            traded_at: datetime = row[1]
            cost_local = Decimal(str(row[2]))
            grouped.setdefault(ua_id, []).append((traded_at, cost_local))

        return {ua_id: tuple(lots) for ua_id, lots in grouped.items()}

    async def get_prior_closes(
        self,
        symbol_ids: list[int],
        days_ago: int,
    ) -> dict[int, Decimal]:
        """Return ``{asset_symbol_id: close_price}`` for the nearest price_points
        row at or before ``today − days_ago``.

        Weekends/holidays fall back to the most recent prior trading day. A
        symbol with no history at the cutoff is simply absent from the result.
        """
        from datetime import UTC, datetime, timedelta  # noqa: PLC0415

        from app.models.price_point import PricePoint  # noqa: PLC0415

        if not symbol_ids:
            return {}
        cutoff_date = (datetime.now(UTC) - timedelta(days=days_ago)).date()

        max_date_subq = (
            select(
                PricePoint.asset_symbol_id.label("sid"),
                func.max(func.date(PricePoint.fetched_at)).label("max_date"),
            )
            .where(
                PricePoint.asset_symbol_id.in_(symbol_ids),
                func.date(PricePoint.fetched_at) <= cutoff_date,
            )
            .group_by(PricePoint.asset_symbol_id)
            .subquery()
        )

        stmt = (
            select(PricePoint.asset_symbol_id, PricePoint.price)
            .join(
                max_date_subq,
                (PricePoint.asset_symbol_id == max_date_subq.c.sid)
                & (func.date(PricePoint.fetched_at) == max_date_subq.c.max_date),
            )
        )
        out: dict[int, Decimal] = {}
        for sid, price in (await self._session.execute(stmt)).all():
            out[int(sid)] = Decimal(str(price))
        return out

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
