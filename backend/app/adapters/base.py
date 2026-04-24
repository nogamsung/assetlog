"""Adapter base — Protocol + shared failure helper."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.domain.asset_type import AssetType
from app.domain.price_refresh import FetchBatchResult, FetchFailure, SymbolRef


def _wrap_failure(ref: SymbolRef, exc: BaseException) -> FetchFailure:
    """Convert any exception into a structured FetchFailure.

    Args:
        ref: The symbol that could not be fetched.
        exc: The exception that was caught.

    Returns:
        FetchFailure with error_class and a sanitised message (no PII).
    """
    return FetchFailure(
        ref=ref,
        error_class=type(exc).__name__,
        error_msg=str(exc)[:500],  # truncate to avoid log bloat
    )


@runtime_checkable
class PriceAdapter(Protocol):
    """Contract every concrete adapter must implement.

    Implementations must be safe to instantiate once at lifespan startup
    and re-used for every scheduler tick.
    """

    asset_type: AssetType

    async def fetch_batch(
        self,
        symbols: Sequence[SymbolRef],
    ) -> FetchBatchResult:
        """Fetch prices for all *symbols* in a single adapter call.

        Failures for individual symbols must be caught internally and
        returned as ``FetchBatchResult.failures`` — they must NOT raise.

        Args:
            symbols: Non-empty sequence of SymbolRef for this adapter's
                     ``asset_type``.

        Returns:
            FetchBatchResult with successes and per-symbol failures.
        """
        ...
