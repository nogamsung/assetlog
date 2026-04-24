"""PriceRefreshService — orchestrates adapter calls, DB writes, and result reporting."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from app.adapters import AdapterRegistry
from app.domain.price_refresh import (
    FetchBatchResult,
    FetchFailure,
    PriceQuote,
    RefreshResult,
    SymbolRef,
)
from app.repositories.asset_symbol import AssetSymbolRepository
from app.repositories.price_point import PricePointRepository

logger = logging.getLogger("app.services.price_refresh")


def _utcnow() -> datetime:
    """Return the current UTC datetime (injectable for testing)."""
    return datetime.now(tz=UTC)


def _group_by_type(
    targets: list[SymbolRef],
) -> dict[str, list[SymbolRef]]:
    """Group SymbolRef list by asset_type value string."""
    grouped: dict[str, list[SymbolRef]] = {}
    for ref in targets:
        key = str(ref.asset_type)
        grouped.setdefault(key, []).append(ref)
    return grouped


class PriceRefreshService:
    """Coordinate price refresh across all asset types.

    One instance is created per scheduler tick inside the job function.
    It must not be shared across ticks.

    Args:
        asset_symbol_repo: Repository for reading targets and writing cache.
        price_point_repo: Repository for appending historical price ticks.
        adapters: Registry mapping AssetType → PriceAdapter.
        clock: Callable returning current UTC datetime (injectable for tests).
    """

    def __init__(
        self,
        asset_symbol_repo: AssetSymbolRepository,
        price_point_repo: PricePointRepository,
        adapters: AdapterRegistry,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._asset_symbol_repo = asset_symbol_repo
        self._price_point_repo = price_point_repo
        self._adapters = adapters
        self._clock = clock

    async def refresh_all_prices(self) -> RefreshResult:
        """Fetch prices for all known symbols and persist the results.

        Workflow:
        1. Load all SymbolRef targets from the database.
        2. Group by asset_type and dispatch to the matching adapter in parallel.
        3. Persist successes (price_points + asset_symbol cache).
        4. Log failures and return a RefreshResult summary.

        Returns:
            RefreshResult summarising the outcome of this refresh run.
        """
        t0 = time.monotonic()
        targets = await self._asset_symbol_repo.list_distinct_refresh_targets()
        total = len(targets)

        logger.info(
            "price_refresh started",
            extra={"event": "price_refresh_start", "total_symbols": total},
        )

        if total == 0:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            logger.info(
                "price_refresh finished — no symbols registered",
                extra={
                    "event": "price_refresh_done",
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "elapsed_ms": elapsed_ms,
                },
            )
            return RefreshResult(total=0, success=0, failed=0, elapsed_ms=elapsed_ms)

        grouped = _group_by_type(targets)

        # Run each adapter in parallel; catch adapter-level exceptions individually.
        gather_results = await asyncio.gather(
            *(self._run_adapter(asset_type_str, refs) for asset_type_str, refs in grouped.items()),
            return_exceptions=True,
        )

        all_successes: list[PriceQuote] = []
        all_failures: list[FetchFailure] = []

        for idx, result in enumerate(gather_results):
            asset_type_str = list(grouped.keys())[idx]
            if isinstance(result, BaseException):
                # Entire adapter crashed — mark all its symbols as failures
                refs = grouped[asset_type_str]
                logger.error(
                    "adapter %s raised unexpectedly: %s",
                    asset_type_str,
                    result,
                    extra={
                        "event": "adapter_crash",
                        "asset_type": asset_type_str,
                        "error_class": type(result).__name__,
                    },
                )
                for ref in refs:
                    all_failures.append(
                        FetchFailure(
                            ref=ref,
                            error_class=type(result).__name__,
                            error_msg=str(result)[:500],
                        )
                    )
            else:
                batch: FetchBatchResult = result
                all_successes.extend(batch.successes)
                all_failures.extend(batch.failures)

        # Persist price history
        await self._price_point_repo.bulk_insert(all_successes)

        # Update cache columns on AssetSymbol
        cache_rows: list[tuple[int, Decimal, datetime]] = [
            (q.ref.asset_symbol_id, q.price, q.fetched_at) for q in all_successes
        ]
        if cache_rows:
            await self._asset_symbol_repo.bulk_update_cache(cache_rows)

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        success_count = len(all_successes)
        failed_count = len(all_failures)

        if all_failures:
            logger.warning(
                "price_refresh completed with failures",
                extra={
                    "event": "price_refresh_done",
                    "total": total,
                    "success": success_count,
                    "failed": failed_count,
                    "elapsed_ms": elapsed_ms,
                    "failed_symbols": [f.ref.symbol for f in all_failures],
                },
            )
        else:
            logger.info(
                "price_refresh completed successfully",
                extra={
                    "event": "price_refresh_done",
                    "total": total,
                    "success": success_count,
                    "failed": failed_count,
                    "elapsed_ms": elapsed_ms,
                },
            )

        return RefreshResult(
            total=total,
            success=success_count,
            failed=failed_count,
            elapsed_ms=elapsed_ms,
            failures=all_failures,
        )

    async def _run_adapter(
        self,
        asset_type_str: str,
        refs: list[SymbolRef],
    ) -> FetchBatchResult:
        """Dispatch a batch to the appropriate adapter.

        Args:
            asset_type_str: String value of AssetType enum.
            refs: All SymbolRef instances for this asset type.

        Returns:
            FetchBatchResult from the adapter.

        Raises:
            KeyError: If no adapter is registered for the asset type.
        """
        from app.domain.asset_type import AssetType

        asset_type = AssetType(asset_type_str)
        adapter = self._adapters.get(asset_type)
        return await adapter.fetch_batch(refs)
