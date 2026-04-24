"""Portfolio history service — time-series computation from transactions + price points."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.portfolio_history import (
    PERIOD_BUCKET,
    HistoryPeriod,
    HistoryPoint,
    bucket_to_timedelta,
)
from app.repositories.portfolio_history import PortfolioHistoryRepository, TransactionRow
from app.schemas.portfolio import HistoryPointResponse, PortfolioHistoryResponse

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")


def _ensure_utc(dt: datetime) -> datetime:
    """Return a timezone-aware UTC datetime; attach UTC if naive."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _generate_bucket_timestamps(
    start: datetime,
    end: datetime,
    delta: timedelta,
) -> list[datetime]:
    """Generate bucket boundary timestamps from *start* to *end* (inclusive).

    The final element is exactly *end* — the last regular bucket boundary that
    would exceed *end* is clamped to *end* itself.
    """
    timestamps: list[datetime] = []
    current = start
    while current < end:
        timestamps.append(current)
        current = current + delta
    timestamps.append(end)
    return timestamps


def _price_at(
    sym_id: int,
    ts: datetime,
    price_index: dict[int, list[tuple[datetime, Decimal]]],
    pointer: dict[int, int],
) -> Decimal | None:
    """Return the most recent price for *sym_id* at or before *ts*.

    Uses a forward-scan pointer per symbol. The price list is sorted **ascending**
    by fetched_at so as bucket timestamps increase monotonically the pointer only
    moves forward — O(N_price_points) total across all buckets.

    The pointer tracks the last index whose fetched_at ≤ ts. Advancing it when
    the next entry is also ≤ ts keeps it at the most-recent eligible price.

    Returns None if no price point exists at or before *ts*.
    """
    pts = price_index.get(sym_id)
    if not pts:
        return None

    ptr = pointer.get(sym_id, -1)
    # Advance pointer while the next entry still fits within ts
    while ptr + 1 < len(pts) and pts[ptr + 1][0] <= ts:
        ptr += 1
    pointer[sym_id] = ptr

    if ptr < 0:
        return None
    return pts[ptr][1]


class PortfolioHistoryService:
    """Compute portfolio value time series from transactions and price points."""

    def __init__(self, repo: PortfolioHistoryRepository) -> None:
        self._repo = repo

    async def get_history(
        self,
        user_id: int,
        period: HistoryPeriod,
        currency: str,
    ) -> PortfolioHistoryResponse:
        """Compute the portfolio value time series for *user_id* over *period*.

        Algorithm (O(N_buckets + N_tx + N_price_points)):
        1. Determine (start_dt, end_dt, bucket) from *period*.
        2. Load all BUY transactions for user in *currency*.
        3. Collect symbol IDs; load price points since start_dt.
        4. Generate bucket timestamps.
        5. For each bucket T:
           - Advance a tx pointer to accumulate qty / cost_basis for tx.traded_at ≤ T.
           - Advance a price pointer per symbol to find price_at(T).
           - value_at_T = Σ(qty_at_T × price_at_T) across symbols.
        6. Return PortfolioHistoryResponse.

        Args:
            user_id: Authenticated user's PK.
            period: Requested time window.
            currency: Quote currency (e.g. "KRW").

        Returns:
            PortfolioHistoryResponse with a list of HistoryPointResponse.
        """
        bucket = PERIOD_BUCKET[period]
        end_dt = datetime.now(UTC)

        # ------------------------------------------------------------------
        # Step 1 — Load transactions
        # ------------------------------------------------------------------
        txs = await self._repo.list_user_transactions(user_id, currency)

        if not txs:
            logger.debug(
                "get_history: user_id=%s currency=%s has no transactions — returning empty",
                user_id,
                currency,
            )
            return PortfolioHistoryResponse(
                currency=currency,
                period=period,
                bucket=bucket,
                points=[],
            )

        # ------------------------------------------------------------------
        # Step 2 — Determine start_dt
        # ------------------------------------------------------------------
        start_dt = self._compute_start_dt(period, end_dt, txs)

        # ------------------------------------------------------------------
        # Step 3 — Load price points
        # ------------------------------------------------------------------
        symbol_ids = list({tx.symbol_id for tx in txs})
        price_index = await self._repo.list_price_points_for_symbols(symbol_ids, since=start_dt)

        # ------------------------------------------------------------------
        # Step 4 — Generate bucket timestamps
        # ------------------------------------------------------------------
        delta = bucket_to_timedelta(bucket)
        bucket_timestamps = _generate_bucket_timestamps(start_dt, end_dt, delta)

        # ------------------------------------------------------------------
        # Step 5 — Compute value and cost_basis per bucket
        # ------------------------------------------------------------------
        points = self._compute_history_points(txs, price_index, bucket_timestamps)

        logger.debug(
            "get_history: user_id=%s period=%s currency=%s buckets=%d",
            user_id,
            period,
            currency,
            len(points),
        )

        return PortfolioHistoryResponse(
            currency=currency,
            period=period,
            bucket=bucket,
            points=[
                HistoryPointResponse(
                    timestamp=p.timestamp,
                    value=p.value,
                    cost_basis=p.cost_basis,
                )
                for p in points
            ],
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_start_dt(
        period: HistoryPeriod,
        end_dt: datetime,
        txs: list[TransactionRow],
    ) -> datetime:
        """Determine the history start datetime based on *period*.

        For HistoryPeriod.ALL, the start is the earliest transaction's traded_at.
        """
        if period == HistoryPeriod.ALL:
            first_traded = min(txs, key=lambda t: t.traded_at).traded_at
            return _ensure_utc(first_traded)

        offsets: dict[HistoryPeriod, timedelta] = {
            HistoryPeriod.ONE_DAY: timedelta(days=1),
            HistoryPeriod.ONE_WEEK: timedelta(weeks=1),
            HistoryPeriod.ONE_MONTH: timedelta(days=30),
            HistoryPeriod.ONE_YEAR: timedelta(days=365),
        }
        return end_dt - offsets[period]

    @staticmethod
    def _compute_history_points(
        txs: list[TransactionRow],
        price_index: dict[int, list[tuple[datetime, Decimal]]],
        bucket_timestamps: list[datetime],
    ) -> list[HistoryPoint]:
        """Compute HistoryPoint for each bucket using pointer-based O(N) scan.

        txs must be sorted by traded_at ASC (guaranteed by the repository).
        price_index inner lists must be sorted by fetched_at DESC.
        """
        # Per-symbol cumulative quantity accumulator
        qty_by_symbol: dict[int, Decimal] = {}
        # Cumulative cost basis across all symbols
        running_cost = _ZERO

        # Pointer into txs — advanced as bucket timestamps increase
        tx_ptr = 0
        n_txs = len(txs)

        # Per-symbol pointer into price_index (descending lists)
        price_ptr: dict[int, int] = {}

        points: list[HistoryPoint] = []

        for ts in bucket_timestamps:
            # Ensure ts is tz-aware for comparison
            ts_aware = _ensure_utc(ts)

            # Advance tx_ptr: accumulate all txs with traded_at ≤ ts
            while tx_ptr < n_txs:
                tx = txs[tx_ptr]
                tx_time = _ensure_utc(tx.traded_at)
                if tx_time > ts_aware:
                    break
                qty_by_symbol[tx.symbol_id] = qty_by_symbol.get(tx.symbol_id, _ZERO) + tx.quantity
                running_cost += tx.quantity * tx.price
                tx_ptr += 1

            # Compute portfolio value at ts
            value = _ZERO
            for sym_id, qty in qty_by_symbol.items():
                if qty <= _ZERO:
                    continue
                price = _price_at(sym_id, ts_aware, price_index, price_ptr)
                if price is not None:
                    value += qty * price

            points.append(
                HistoryPoint(
                    timestamp=ts_aware,
                    value=value,
                    cost_basis=running_cost,
                )
            )

        return points
