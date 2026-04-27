"""Portfolio history repository — read-only queries for time-series computation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.transaction_type import TransactionType
from app.models.asset_symbol import AssetSymbol
from app.models.price_point import PricePoint
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset

logger = logging.getLogger(__name__)


def _to_utc(dt: datetime) -> datetime:
    """Attach UTC to naive datetimes (SQLite strips tzinfo on read)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class TransactionRow:
    """Lightweight value object — one BUY or SELL transaction record."""

    __slots__ = ("symbol_id", "traded_at", "quantity", "price", "tx_type")  # MODIFIED

    def __init__(
        self,
        symbol_id: int,
        traded_at: datetime,
        quantity: Decimal,
        price: Decimal,
        tx_type: TransactionType,  # ADDED
    ) -> None:
        self.symbol_id = symbol_id
        self.traded_at = traded_at
        self.quantity = quantity
        self.price = price
        self.tx_type = tx_type  # ADDED


class PortfolioHistoryRepository:
    """Read-only queries for portfolio history computation.

    Both public methods issue a single DB round-trip each — no N+1 patterns.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_transactions(self, currency: str) -> list[TransactionRow]:
        """Return all BUY and SELL transactions in *currency*, ordered by traded_at ASC.

        Joins transactions → user_assets → asset_symbols so the service layer
        can directly compute cumulative quantities and cost basis.
        """
        stmt = (
            select(
                AssetSymbol.id.label("symbol_id"),
                Transaction.traded_at,
                Transaction.quantity,
                Transaction.price,
                Transaction.type.label("tx_type"),
            )
            .join(UserAsset, Transaction.user_asset_id == UserAsset.id)
            .join(AssetSymbol, UserAsset.asset_symbol_id == AssetSymbol.id)
            .where(AssetSymbol.currency == currency)
            .order_by(Transaction.traded_at.asc())
        )

        rows = (await self._session.execute(stmt)).all()

        result: list[TransactionRow] = []
        for row in rows:
            result.append(
                TransactionRow(
                    symbol_id=row.symbol_id,
                    traded_at=_to_utc(row.traded_at),
                    quantity=Decimal(str(row.quantity)),
                    price=Decimal(str(row.price)),
                    tx_type=row.tx_type,
                )
            )

        logger.debug(
            "list_transactions: currency=%s returned %d rows",
            currency,
            len(result),
        )
        return result

    async def list_price_points_for_symbols(
        self,
        symbol_ids: list[int],
        since: datetime,
    ) -> dict[int, list[tuple[datetime, Decimal]]]:
        """Return price points for *symbol_ids* since *since*, plus the most recent
        pre-*since* point per symbol (needed as the rollforward starting value).

        The result is grouped by symbol_id; each inner list is sorted by
        fetched_at **ascending** so the service can efficiently find the price
        at or before any given timestamp with a forward scan pointer.

        Args:
            symbol_ids: List of AssetSymbol PKs to fetch prices for.
            since: Lower bound (inclusive) for fetched_at.

        Returns:
            dict mapping symbol_id → [(fetched_at, price)] sorted desc by fetched_at.
        """
        if not symbol_ids:
            return {}

        # Branch A: all points at or after `since`
        after_stmt = select(
            PricePoint.asset_symbol_id,
            PricePoint.fetched_at,
            PricePoint.price,
        ).where(
            PricePoint.asset_symbol_id.in_(symbol_ids),
            PricePoint.fetched_at >= since,
        )

        # Branch B: for each symbol, the single most recent point before `since`
        # We fetch all pre-since rows and post-filter in Python — avoids a
        # correlated subquery per symbol which is slow on large tables.
        before_stmt = select(
            PricePoint.asset_symbol_id,
            PricePoint.fetched_at,
            PricePoint.price,
        ).where(
            PricePoint.asset_symbol_id.in_(symbol_ids),
            PricePoint.fetched_at < since,
        )

        combined_stmt = union_all(after_stmt, before_stmt).order_by(
            "asset_symbol_id",
            "fetched_at",
        )

        rows = (await self._session.execute(combined_stmt)).all()

        # Group: symbol_id → list[(fetched_at, price)], collect all rows first
        grouped: dict[int, list[tuple[datetime, Decimal]]] = {}
        # Track the latest pre-since row per symbol for rollforward seed
        latest_before: dict[int, tuple[datetime, Decimal]] = {}

        # since is always UTC-aware; rows from SQLite may be naive — normalise
        since_utc = _to_utc(since)

        for row in rows:
            sym_id: int = row.asset_symbol_id
            ts: datetime = _to_utc(row.fetched_at)
            price = Decimal(str(row.price))

            if ts < since_utc:
                # Keep only the latest pre-since row per symbol
                if sym_id not in latest_before or ts > latest_before[sym_id][0]:
                    latest_before[sym_id] = (ts, price)
            else:
                if sym_id not in grouped:
                    grouped[sym_id] = []
                grouped[sym_id].append((ts, price))

        # Inject the pre-since seed at the beginning of each symbol's list
        for sym_id, seed in latest_before.items():
            if sym_id not in grouped:
                grouped[sym_id] = []
            grouped[sym_id].insert(0, seed)

        # Sort each inner list by fetched_at ascending (service uses forward pointer scan)
        for sym_id in grouped:
            grouped[sym_id].sort(key=lambda t: t[0])

        logger.debug(
            "list_price_points_for_symbols: symbol_ids=%s since=%s symbols_found=%d",
            symbol_ids,
            since,
            len(grouped),
        )
        return grouped
