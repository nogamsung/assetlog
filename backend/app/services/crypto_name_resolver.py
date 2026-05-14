"""CryptoNameResolver — base ticker → Korean display name."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.upbit_market_meta import fetch_korean_name_from_upbit
from app.models.crypto_name_cache import CryptoNameCache

logger = logging.getLogger(__name__)


class CryptoNameResolver:
    """Resolve a crypto base ticker to its Korean display name.

    Lookup order: DB cache (positive + negative) → Upbit /v1/market/all.
    Any failure degrades to ``None`` so callers fall back to the base ticker.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve(self, base: str) -> str | None:
        base_upper = base.upper()

        # 1) DB cache — wrapped in SAVEPOINT so a missing table can't poison
        # the surrounding import transaction.
        try:
            async with self._session.begin_nested():
                cached = await self._session.get(CryptoNameCache, base_upper)
                if cached is not None:
                    return cached.name
        except Exception as exc:  # noqa: BLE001
            logger.warning("crypto_name_resolver: cache lookup failed (%s)", exc)

        # 2) Upbit market-all endpoint
        try:
            name = await fetch_korean_name_from_upbit(base_upper)
        except Exception as exc:  # noqa: BLE001
            logger.warning("crypto_name_resolver: upbit call failed: %s", exc)
            return None

        # 3) Persist outcome (positive or negative) inside a SAVEPOINT
        try:
            async with self._session.begin_nested():
                self._session.add(
                    CryptoNameCache(base=base_upper, name=name, source="upbit")
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("crypto_name_resolver: cache write failed (%s)", exc)

        if name:
            logger.info("crypto_name_resolver: upbit mapped %s → %s", base_upper, name)
        return name
