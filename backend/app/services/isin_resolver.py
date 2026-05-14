"""IsinResolver — three-tier ISIN → exchange ticker lookup.

Lookup order (cheapest first):

1. **Static map** (``isin_ticker_map.US_ISIN_TO_TICKER``) — hand-curated, no I/O
2. **DB cache** (``isin_ticker_cache`` table) — remembers previous resolutions
   *including negative results* so we never re-call OpenFIGI for an unknown
   ISIN
3. **OpenFIGI HTTP API** — last resort. The result (hit or miss) is written
   back into the DB cache so the next resolution is free.

Designed to be safe under partial failure: a network error or rate-limit
yields ``None`` and the caller falls back to using the raw ISIN as a
display ticker.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.openfigi_client import fetch_ticker_from_openfigi
from app.adapters.parsers.isin_ticker_map import lookup_us_ticker
from app.models.isin_ticker_cache import IsinTickerCache

logger = logging.getLogger(__name__)

# US/Cayman/Bermuda etc. — any ISIN-shaped 12-char alnum starting with two
# letters and a US-trading prefix. Used to recognise raw-ISIN symbols that
# should be resolved before we create an AssetSymbol row.
_ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


def looks_like_isin(symbol: str) -> bool:
    """Return True if *symbol* matches the 12-char ISIN pattern."""
    return bool(_ISIN_PATTERN.match(symbol))


class IsinResolver:
    """Resolve an ISIN to the best-known exchange ticker."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve(self, isin: str) -> str | None:
        """Return the ticker for *isin*, or None if unknown.

        Result is persisted to ``isin_ticker_cache`` so future calls are O(1).
        Any failure (missing cache table, OpenFIGI rate-limit, network error)
        degrades to ``None`` so callers fall back to the raw ISIN — never
        propagates an exception that would abort the surrounding import.
        """
        # 1) Static curated map — instant
        try:
            static_hit = lookup_us_ticker(isin)
            if static_hit is not None:
                return static_hit
        except Exception:  # noqa: BLE001
            pass

        # 2) DB cache — remember both positive and negative lookups. Wrapped in
        # a SAVEPOINT so a missing table (migration not yet applied) doesn't
        # poison the outer transaction.
        try:
            async with self._session.begin_nested():
                cached = await self._session.get(IsinTickerCache, isin)
                if cached is not None:
                    return cached.ticker  # may be None for known-unknown
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "isin_resolver: cache lookup failed (%s) — skipping cache tier",
                exc,
            )

        # 3) OpenFIGI — network call, then persist outcome
        try:
            ticker = await fetch_ticker_from_openfigi(isin)
        except Exception as exc:  # noqa: BLE001
            logger.warning("isin_resolver: openfigi call failed: %s", exc)
            return None

        # Wrap the cache INSERT in a SAVEPOINT so a write failure (most
        # commonly: ``isin_ticker_cache`` migration not applied yet in this
        # environment) only rolls back the cache write, leaving the
        # surrounding import transaction usable.
        try:
            async with self._session.begin_nested():
                self._session.add(
                    IsinTickerCache(isin=isin, ticker=ticker, source="openfigi")
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "isin_resolver: failed to persist cache row (%s) — returning result without caching",
                exc,
            )

        if ticker:
            logger.info("isin_resolver: openfigi mapped %s → %s", isin, ticker)
        return ticker
