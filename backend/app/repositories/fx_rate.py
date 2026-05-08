"""FxRate repository — upsert and query for cached exchange rates."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fx_rate import FxRate
from app.models.fx_rate_snapshot import FxRateSnapshot
from app.repositories._dialect import get_dialect_name

logger = logging.getLogger("app.repositories.fx_rate")


def _ensure_utc(value: datetime) -> datetime:
    """Return a tz-aware datetime — assume UTC for naive values.

    SQLite drops timezone info on round-trip; production MySQL preserves it.
    Comparisons across the Python boundary need a uniform tzinfo.
    """
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class FxRateRepository:
    """Persist and retrieve cached FX rates.

    Rows are keyed by (base_currency, quote_currency).  Upsert keeps only
    the most recent rate — no historical append.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        base: str,
        quote: str,
        rate: Decimal,
        fetched_at: datetime,
    ) -> None:
        """Insert or update a single FX rate row.

        Uses MySQL ``INSERT ... ON DUPLICATE KEY UPDATE`` for atomicity.
        Falls back to a select-then-update pattern for SQLite (used in tests).

        Args:
            base: Base currency code (e.g. "USD").
            quote: Quote currency code (e.g. "KRW").
            rate: Exchange rate — 1 base = rate quote.
            fetched_at: Timestamp when the rate was fetched from the external API.
        """
        dialect = get_dialect_name(self._session)

        if dialect == "mysql":
            # MySQL-specific upsert — single atomic statement.
            stmt = text(
                "INSERT INTO fx_rates (base_currency, quote_currency, rate, fetched_at)"
                " VALUES (:base, :quote, :rate, :fetched_at)"
                " ON DUPLICATE KEY UPDATE rate = VALUES(rate), fetched_at = VALUES(fetched_at)"
            )
            await self._session.execute(
                stmt,
                {
                    "base": base,
                    "quote": quote,
                    "rate": str(rate),
                    "fetched_at": fetched_at,
                },
            )
            logger.debug(
                "fx_rate upserted (mysql)",
                extra={"event": "fx_rate_upsert", "base": base, "quote": quote},
            )
        else:
            # SQLite fallback — used by tests.
            existing = await self.get_latest(base, quote)
            if existing is None:
                fx = FxRate(
                    base_currency=base,
                    quote_currency=quote,
                    rate=rate,
                    fetched_at=fetched_at,
                )
                self._session.add(fx)
            else:
                existing.rate = rate
                existing.fetched_at = fetched_at
            logger.debug(
                "fx_rate upserted (sqlite fallback)",
                extra={"event": "fx_rate_upsert", "base": base, "quote": quote},
            )

    async def get_latest(self, base: str, quote: str) -> FxRate | None:
        """Return the cached FX rate for a currency pair, or None if absent.

        Args:
            base: Base currency code.
            quote: Quote currency code.

        Returns:
            FxRate row or None if not yet fetched.
        """
        stmt = select(FxRate).where(
            FxRate.base_currency == base,
            FxRate.quote_currency == quote,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_at(
        self,
        base_currency: str,
        quote_currency: str,
        at: datetime,
    ) -> FxRate | None:
        """Return the most recent FX rate for (base, quote) at or before *at*.

        Queries the row whose fetched_at is the latest timestamp ≤ at.
        Returns None if no such row exists (caller must handle missing rate).

        Args:
            base_currency: Base currency code (e.g. "USD").
            quote_currency: Quote currency code (e.g. "KRW").
            at: Upper bound for fetched_at (inclusive).

        Returns:
            FxRate row with fetched_at ≤ at, or None if absent.
        """
        stmt = (
            select(FxRate)
            .where(
                FxRate.base_currency == base_currency,
                FxRate.quote_currency == quote_currency,
                FxRate.fetched_at <= at,
            )
            .order_by(FxRate.fetched_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[FxRate]:
        """Return all cached FX rate rows ordered by base then quote currency.

        Returns:
            List of FxRate rows — empty if no rates have been fetched yet.
        """
        stmt = select(FxRate).order_by(FxRate.base_currency, FxRate.quote_currency)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def insert_snapshot(
        self,
        base: str,
        quote: str,
        rate: Decimal,
        recorded_at: datetime,
    ) -> None:
        """Insert a new FX rate snapshot row.

        Silently ignores duplicate inserts (same base/quote/recorded_at) to
        safely handle scheduler retries that fire twice in the same tick.
        Pre-checks existence rather than catching ``IntegrityError`` because
        savepoint semantics differ across SQLite/MySQL and the test fixture
        relies on a single-session rollback for isolation.

        Args:
            base: Base currency code (e.g. "USD").
            quote: Quote currency code (e.g. "KRW").
            rate: Exchange rate — 1 base = rate quote.
            recorded_at: Timestamp when the rate was recorded (scheduler tick time).
        """
        existing_stmt = (
            select(FxRateSnapshot.id)
            .where(
                FxRateSnapshot.base_currency == base,
                FxRateSnapshot.quote_currency == quote,
                FxRateSnapshot.recorded_at == recorded_at,
            )
            .limit(1)
        )
        existing = (await self._session.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            logger.debug(
                "fx_rate_snapshot duplicate suppressed",
                extra={
                    "event": "fx_snapshot_duplicate",
                    "base": base,
                    "quote": quote,
                    "recorded_at": recorded_at.isoformat(),
                },
            )
            return

        snapshot = FxRateSnapshot(
            base_currency=base,
            quote_currency=quote,
            rate=rate,
            recorded_at=recorded_at,
        )
        self._session.add(snapshot)
        await self._session.flush()
        logger.debug(
            "fx_rate_snapshot inserted",
            extra={
                "event": "fx_snapshot_insert",
                "base": base,
                "quote": quote,
                "recorded_at": recorded_at.isoformat(),
            },
        )

    async def get_rate_at(
        self,
        base: str,
        quote: str,
        at: datetime,
    ) -> FxRateSnapshot | None:
        """Return the nearest snapshot at or before *at* for the given pair.

        Uses a "nearest-past" strategy: the most recent snapshot whose
        ``recorded_at <= at`` is returned.

        Args:
            base: Base currency code.
            quote: Quote currency code.
            at: Reference timestamp — returns the latest snapshot on or before this.

        Returns:
            FxRateSnapshot row or None if no snapshot exists at or before *at*.
        """
        stmt = (
            select(FxRateSnapshot)
            .where(
                FxRateSnapshot.base_currency == base,
                FxRateSnapshot.quote_currency == quote,
                FxRateSnapshot.recorded_at <= at,
            )
            .order_by(FxRateSnapshot.recorded_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_rates_at_batch(
        self,
        base: str,
        quote: str,
        ats: list[datetime],
    ) -> dict[datetime, FxRateSnapshot | None]:
        """Return nearest-past snapshots for multiple timestamps in one query.

        Fetches all snapshots for the pair then performs nearest-past matching
        in Python.  This avoids N+1 queries when resolving multiple BUY lot
        timestamps for a single currency pair.

        Args:
            base: Base currency code.
            quote: Quote currency code.
            ats: List of reference timestamps to resolve.

        Returns:
            Dict mapping each requested timestamp to its matching snapshot
            (or None if no snapshot exists at or before that timestamp).
        """
        if not ats:
            return {}

        max_at = max(ats)
        stmt = (
            select(FxRateSnapshot)
            .where(
                FxRateSnapshot.base_currency == base,
                FxRateSnapshot.quote_currency == quote,
                FxRateSnapshot.recorded_at <= max_at,
            )
            .order_by(FxRateSnapshot.recorded_at)
        )
        result = await self._session.execute(stmt)
        all_snaps: list[FxRateSnapshot] = list(result.scalars().all())

        # SQLite returns naive datetimes; production MySQL returns aware.
        # Normalise via _ensure_utc before comparing against the request's
        # tz-aware timestamps.
        resolved: dict[datetime, FxRateSnapshot | None] = {}
        for at in ats:
            match: FxRateSnapshot | None = None
            for snap in all_snaps:
                if _ensure_utc(snap.recorded_at) <= at:
                    match = snap
                else:
                    break
            resolved[at] = match
        return resolved
