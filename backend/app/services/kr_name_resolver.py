"""KrNameResolver — Korean security name → KRX 6-digit code resolver.

Lookup order:
1. **DB cache** (``kr_name_cache``) — remembers prior resolutions including
   negative results
2. **Naver Finance autocomplete** — last resort; result (hit or miss) is
   cached so the same unknown name doesn't keep hammering the API.

Designed to degrade gracefully — a network error or unknown name yields
``None`` and the caller keeps using the Korean name as-is.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.naver_stock_lookup import fetch_kr_code_from_naver
from app.models.kr_name_cache import KrNameCache

logger = logging.getLogger(__name__)

# Names containing any Hangul syllable look like Korean security names. The
# parser already produces these for Shinhan rows. Pure 6-digit codes (Toss
# KR rows) won't match — we leave them alone.
_HANGUL_RE = re.compile(r"[가-힣]")
_KR_CODE_RE = re.compile(r"^\d{6}$")


def looks_like_kr_name(symbol: str) -> bool:
    """Return True if *symbol* contains at least one Hangul character."""
    return bool(_HANGUL_RE.search(symbol))


def looks_like_kr_code(symbol: str) -> bool:
    """Return True if *symbol* is already a KRX 6-digit code (e.g. ``005930``)."""
    return bool(_KR_CODE_RE.match(symbol))


class KrNameResolver:
    """Resolve a Korean security name to its KRX 6-digit code."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve(self, name: str) -> str | None:
        """Return the 6-digit KRX code for *name*, or None if unknown.

        Result is persisted to ``kr_name_cache`` so future calls are O(1).
        Any failure (missing cache table, Naver outage, network error)
        degrades to ``None`` so callers fall back to the original Korean
        name — never propagates an exception that would abort the
        surrounding import.
        """
        # 1) DB cache — including negative entries. Wrapped in a SAVEPOINT
        # so a missing table (migration not yet applied) doesn't poison the
        # outer transaction.
        try:
            async with self._session.begin_nested():
                cached = await self._session.get(KrNameCache, name)
                if cached is not None:
                    return cached.code
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "kr_name_resolver: cache lookup failed (%s) — skipping cache tier",
                exc,
            )

        # 2) Naver autocomplete — network call, then persist outcome
        try:
            code = await fetch_kr_code_from_naver(name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("kr_name_resolver: naver call failed: %s", exc)
            return None

        # Wrap the cache INSERT in a SAVEPOINT so a write failure (most
        # commonly: ``kr_name_cache`` migration not applied yet in this
        # environment) only rolls back the cache write, leaving the
        # surrounding import transaction usable.
        try:
            async with self._session.begin_nested():
                self._session.add(KrNameCache(name=name, code=code, source="naver"))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "kr_name_resolver: failed to persist cache row (%s) — returning result without caching",
                exc,
            )

        if code:
            logger.info("kr_name_resolver: naver mapped %s → %s", name, code)
        return code
