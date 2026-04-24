"""FxRate repository — upsert and query for cached exchange rates."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fx_rate import FxRate
from app.repositories._dialect import get_dialect_name

logger = logging.getLogger("app.repositories.fx_rate")


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

    async def list_all(self) -> list[FxRate]:
        """Return all cached FX rate rows ordered by base then quote currency.

        Returns:
            List of FxRate rows — empty if no rates have been fetched yet.
        """
        stmt = select(FxRate).order_by(FxRate.base_currency, FxRate.quote_currency)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
