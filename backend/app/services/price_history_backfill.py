"""Historical price back-fill service.

Pulls daily closes from yfinance going back to each symbol's earliest trade
date and writes them to ``price_points`` so ``PortfolioHistoryService`` can
draw a continuous chart from the first transaction onward.

The scheduler's hourly ``price_refresh`` only adds a single point per run, so
imports of pre-existing transactions leave the chart with no data before the
scheduler started. Back-fill closes that gap.

Skips symbols whose ``symbol`` we cannot map to a yfinance ticker:
- KR_STOCK without a 6-digit code (e.g. Shinhan rows that store the Korean
  product name)
- US_STOCK whose symbol still looks like an ISIN (resolver miss)

Idempotency:
- For each symbol we look up the oldest existing ``price_points`` row and
  request history starting from one day before that — anything yfinance
  returns *strictly before* the existing oldest row is inserted; the rest is
  treated as already covered.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.asset_type import AssetType
from app.domain.price_refresh import PriceQuote, SymbolRef
from app.models.asset_symbol import AssetSymbol
from app.models.price_point import PricePoint
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset
from app.repositories.price_point import PricePointRepository

logger = logging.getLogger(__name__)

_KR_CODE_RE = re.compile(r"^\d{6}$")
_US_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


@dataclass(frozen=True)
class BackfillResult:
    symbols_attempted: int
    symbols_skipped: int
    points_inserted: int


def _yfinance_ticker_for(symbol: AssetSymbol) -> str | None:
    """Return the yfinance ticker for an AssetSymbol, or None if we cannot map."""
    if symbol.asset_type == AssetType.US_STOCK:
        if _US_ISIN_RE.match(symbol.symbol):
            return None  # raw ISIN — resolver hasn't translated yet
        return symbol.symbol
    if symbol.asset_type == AssetType.KR_STOCK:
        if _KR_CODE_RE.match(symbol.symbol):
            # KOSPI first; yfinance returns empty for unknown suffix and we'll skip
            return f"{symbol.symbol}.KS"
        return None
    return None


def _fetch_history_sync(ticker: str, start: date) -> list[tuple[date, Decimal]]:
    """Blocking yfinance call — returns [(date, close), …] ascending by date.

    yfinance occasionally emits ``NaN`` for halt days or pre-IPO periods. Those
    rows must be filtered out — Decimal('NaN') survives the constructor but
    MySQL rejects the INSERT with ``Unknown column 'NaN' in 'field list'``,
    which then rolls back every other symbol's backfill in the same batch.
    """
    import math  # noqa: PLC0415

    import yfinance as yf  # noqa: PLC0415

    df = yf.Ticker(ticker).history(start=start.isoformat(), auto_adjust=True)
    if df.empty:
        return []
    rows: list[tuple[date, Decimal]] = []
    for ts, row in df.iterrows():
        d = ts.date() if hasattr(ts, "date") else ts
        close = row.get("Close")
        if close is None:
            continue
        try:
            f = float(close)
        except (TypeError, ValueError):
            continue
        if math.isnan(f) or math.isinf(f) or f <= 0:
            continue
        try:
            rows.append((d, Decimal(str(f))))
        except (TypeError, ValueError):
            continue
    return rows


class PriceHistoryBackfillService:
    """Back-fill ``price_points`` from yfinance based on earliest trade dates."""

    def __init__(
        self,
        session: AsyncSession,
        price_point_repo: PricePointRepository,
    ) -> None:
        self._session = session
        self._repo = price_point_repo

    async def backfill_all(self) -> BackfillResult:
        """Back-fill history for every symbol that has at least one transaction.

        Returns:
            BackfillResult with symbols_attempted / symbols_skipped /
            points_inserted counts.
        """
        # Earliest traded_at per asset_symbol
        stmt = (
            select(
                AssetSymbol,
                func.min(Transaction.traded_at).label("earliest_trade"),
            )
            .join(UserAsset, UserAsset.asset_symbol_id == AssetSymbol.id)
            .join(Transaction, Transaction.user_asset_id == UserAsset.id)
            .group_by(AssetSymbol.id)
        )
        rows = (await self._session.execute(stmt)).all()

        attempted = 0
        skipped = 0
        total_inserted = 0

        for symbol, earliest in rows:
            ticker = _yfinance_ticker_for(symbol)
            if not ticker or earliest is None:
                skipped += 1
                logger.debug(
                    "backfill skip: symbol_id=%s symbol=%s (unmappable)",
                    symbol.id,
                    symbol.symbol,
                )
                continue

            attempted += 1
            start_date = earliest.date() if isinstance(earliest, datetime) else earliest

            # What's the oldest fetched_at we already have for this symbol?
            existing_oldest_stmt = (
                select(func.min(PricePoint.fetched_at))
                .where(PricePoint.asset_symbol_id == symbol.id)
            )
            existing_oldest = (
                await self._session.execute(existing_oldest_stmt)
            ).scalar_one_or_none()
            existing_oldest_date = (
                existing_oldest.date() if existing_oldest is not None else None
            )

            try:
                rows_ascending = await asyncio.to_thread(
                    _fetch_history_sync, ticker, start_date - timedelta(days=1)
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "backfill yfinance error for %s: %s",
                    ticker,
                    exc,
                    extra={"event": "backfill_error", "ticker": ticker},
                )
                continue

            if not rows_ascending:
                logger.info(
                    "backfill empty for %s (yfinance returned no rows)",
                    ticker,
                )
                continue

            quotes: list[PriceQuote] = []
            ref = SymbolRef(
                asset_symbol_id=symbol.id,
                asset_type=symbol.asset_type,
                symbol=symbol.symbol,
                exchange=symbol.exchange,
            )
            for d, close_price in rows_ascending:
                fetched_at = datetime(d.year, d.month, d.day, 16, 0, tzinfo=UTC)
                if existing_oldest_date and d >= existing_oldest_date:
                    continue  # already covered by scheduler runs
                quotes.append(
                    PriceQuote(
                        ref=ref,
                        price=close_price,
                        currency=symbol.currency,
                        fetched_at=fetched_at,
                    )
                )
            if quotes:
                inserted = await self._repo.bulk_insert(quotes)
                total_inserted += inserted
                logger.info(
                    "backfill inserted %d points for %s (%s)",
                    inserted,
                    ticker,
                    symbol.name,
                )

        return BackfillResult(
            symbols_attempted=attempted,
            symbols_skipped=skipped,
            points_inserted=total_inserted,
        )

    async def backfill_for_symbols(
        self, symbol_ids: Sequence[int]
    ) -> BackfillResult:
        """Variant: back-fill only the given subset of asset_symbol ids."""
        if not symbol_ids:
            return BackfillResult(0, 0, 0)
        stmt = (
            select(
                AssetSymbol,
                func.min(Transaction.traded_at).label("earliest_trade"),
            )
            .join(UserAsset, UserAsset.asset_symbol_id == AssetSymbol.id)
            .join(Transaction, Transaction.user_asset_id == UserAsset.id)
            .where(AssetSymbol.id.in_(symbol_ids))
            .group_by(AssetSymbol.id)
        )
        # Reuse the per-symbol loop body via backfill_all on a filtered set
        rows = (await self._session.execute(stmt)).all()
        # Inline: same handling as backfill_all
        attempted = 0
        skipped = 0
        total_inserted = 0
        for symbol, earliest in rows:
            ticker = _yfinance_ticker_for(symbol)
            if not ticker or earliest is None:
                skipped += 1
                continue
            attempted += 1
            start_date = earliest.date() if isinstance(earliest, datetime) else earliest
            existing_oldest = (
                await self._session.execute(
                    select(func.min(PricePoint.fetched_at)).where(
                        PricePoint.asset_symbol_id == symbol.id
                    )
                )
            ).scalar_one_or_none()
            existing_oldest_date = (
                existing_oldest.date() if existing_oldest is not None else None
            )
            try:
                rows_asc = await asyncio.to_thread(
                    _fetch_history_sync, ticker, start_date - timedelta(days=1)
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("backfill yfinance error for %s: %s", ticker, exc)
                continue
            quotes: list[PriceQuote] = []
            ref = SymbolRef(
                asset_symbol_id=symbol.id,
                asset_type=symbol.asset_type,
                symbol=symbol.symbol,
                exchange=symbol.exchange,
            )
            for d, close_price in rows_asc:
                if existing_oldest_date and d >= existing_oldest_date:
                    continue
                fetched_at = datetime(d.year, d.month, d.day, 16, 0, tzinfo=UTC)
                quotes.append(
                    PriceQuote(
                        ref=ref,
                        price=close_price,
                        currency=symbol.currency,
                        fetched_at=fetched_at,
                    )
                )
            if quotes:
                total_inserted += await self._repo.bulk_insert(quotes)
        return BackfillResult(attempted, skipped, total_inserted)
