"""In-memory symbol list cache with TTL and single-flight loading."""

from __future__ import annotations

import asyncio
import time as _time_module
from collections.abc import Awaitable, Callable
from typing import Any

from app.domain.symbol_search import SymbolCandidate

_SENTINEL: list[SymbolCandidate] = []  # sentinel used before first load


class SymbolListCache:
    """Generic in-memory cache for a full symbol list with TTL expiry.

    The cache holds a single list of SymbolCandidate items, loaded on first
    access and refreshed after TTL has elapsed.  An asyncio.Lock ensures only
    one coroutine loads the list at a time (single-flight pattern).

    Args:
        ttl_seconds: Cache TTL in seconds (default 24 hours).
        now: Callable returning the current monotonic clock value.
            Injected in tests to control time without sleeping.
    """

    def __init__(
        self,
        ttl_seconds: float = 86400.0,
        now: Callable[[], float] | None = None,
    ) -> None:
        self._ttl = ttl_seconds
        self._now: Callable[[], float] = now if now is not None else _time_module.monotonic
        self._lock: asyncio.Lock = asyncio.Lock()
        self._data: list[SymbolCandidate] = _SENTINEL
        self._loaded_at: float = -1.0

    def _is_stale(self) -> bool:
        if self._data is _SENTINEL:
            return True
        return (self._now() - self._loaded_at) >= self._ttl

    async def get_or_load(
        self,
        loader: Callable[[], Awaitable[list[SymbolCandidate]]],
    ) -> list[SymbolCandidate]:
        """Return cached list, or call *loader* to populate it.

        Uses an asyncio.Lock to ensure only one coroutine runs the loader
        even under concurrent access (single-flight).

        Args:
            loader: Async callable that fetches the full symbol list.

        Returns:
            The cached (or freshly loaded) list.
        """
        if not self._is_stale():
            return self._data

        async with self._lock:
            # Re-check under lock — another coroutine may have loaded already.
            if not self._is_stale():
                return self._data

            loaded = await loader()
            self._data = loaded
            self._loaded_at = self._now()

        return self._data

    def invalidate(self) -> None:
        """Force the next call to get_or_load to re-fetch from the source."""
        self._data = _SENTINEL
        self._loaded_at = -1.0

    # ------------------------------------------------------------------
    # Typed read-only access helpers
    # ------------------------------------------------------------------

    def is_loaded(self) -> bool:
        """Return True if the cache has been populated at least once."""
        return self._data is not _SENTINEL

    # Allow equality checks in tests by delegating to internal list.
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SymbolListCache):
            return self._data == other._data
        return NotImplemented
