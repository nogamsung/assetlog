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
from app.domain.transaction_type import TransactionType  # ADDED
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

    def __init__(
        self,
        repo: PortfolioHistoryRepository,
        fx_service: object | None = None,
    ) -> None:
        self._repo = repo
        # Optional. When supplied, multi-currency holdings get FX-converted
        # to the requested display currency at *each bucket's* timestamp.
        self._fx_service = fx_service

    async def get_history(
        self,
        period: HistoryPeriod,
        currency: str,
    ) -> PortfolioHistoryResponse:
        """Compute the portfolio value time series over *period*.

        Algorithm (O(N_buckets + N_tx + N_price_points)):
        1. Determine (start_dt, end_dt, bucket) from *period*.
        2. Load all transactions in *currency*.
        3. Collect symbol IDs; load price points since start_dt.
        4. Generate bucket timestamps.
        5. For each bucket T compute qty/cost via tx pointer and price via
           per-symbol price pointer, then sum value_at_T.
        6. Return PortfolioHistoryResponse.
        """
        bucket = PERIOD_BUCKET[period]
        end_dt = datetime.now(UTC)

        # Pull every transaction (across currencies) instead of filtering on
        # AssetSymbol.currency. USD holdings need to appear on a KRW chart
        # converted at *that day's* FX rate, not be silently dropped.
        all_rows = await self._repo.list_all_transactions()

        if not all_rows:
            logger.debug(
                "get_history: no transactions — returning empty",
            )
            return PortfolioHistoryResponse(
                currency=currency,
                period=period,
                bucket=bucket,
                points=[],
            )

        # AllTxRow carries every TransactionRow field plus .currency. The
        # legacy pipeline only reads the shared subset, so a typing cast
        # avoids re-allocating row objects.
        from typing import cast  # noqa: PLC0415

        txs = cast("list[TransactionRow]", all_rows)

        start_dt = self._compute_start_dt(period, end_dt, txs)
        symbol_ids = list({tx.symbol_id for tx in txs})
        price_index = await self._repo.list_price_points_for_symbols(symbol_ids, since=start_dt)
        delta = bucket_to_timedelta(bucket)
        bucket_timestamps = _generate_bucket_timestamps(start_dt, end_dt, delta)

        # ------------------------------------------------------------------
        # Historical FX — one batch call per source-currency. Each call
        # returns a {bucket_ts: rate} dict so the per-bucket loop is O(1).
        # ------------------------------------------------------------------
        target = currency.upper()
        source_currencies = {row.currency for row in all_rows} - {target}
        fx_index: dict[str, dict[datetime, Decimal | None]] = {}
        if self._fx_service is not None and source_currencies:
            for src in source_currencies:
                try:
                    fx_index[src] = await self._fx_service.get_historical_rates_at(  # type: ignore[attr-defined]
                        src, target, bucket_timestamps
                    )
                except Exception:  # noqa: BLE001
                    fx_index[src] = {}

        symbol_currency: dict[int, str] = {row.symbol_id: row.currency for row in all_rows}

        points = self._compute_history_points(
            txs,
            price_index,
            bucket_timestamps,
            target_currency=target,
            symbol_currency=symbol_currency,
            fx_index=fx_index,
        )

        logger.debug(
            "get_history: period=%s currency=%s buckets=%d",
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
        target_currency: str | None = None,
        symbol_currency: dict[int, str] | None = None,
        fx_index: dict[str, dict[datetime, Decimal | None]] | None = None,
    ) -> list[HistoryPoint]:
        """Compute HistoryPoint for each bucket using pointer-based O(N) scan.

        If ``target_currency`` + ``symbol_currency`` + ``fx_index`` are
        supplied, per-symbol value and cost are converted to the target
        currency at *that bucket's* FX rate. Missing rates fall back to
        native (the symbol's holding contributes 0 — better than skewing
        the total with a wrong rate).
        """
        qty_by_symbol: dict[int, Decimal] = {}
        cumulative_buy_qty: dict[int, Decimal] = {}
        cumulative_buy_cost: dict[int, Decimal] = {}

        tx_ptr = 0
        n_txs = len(txs)
        price_ptr: dict[int, int] = {}
        points: list[HistoryPoint] = []

        symbol_currency = symbol_currency or {}
        fx_index = fx_index or {}

        def _convert(value: Decimal, src_ccy: str, ts: datetime) -> Decimal | None:
            if target_currency is None or src_ccy == target_currency:
                return value
            rates = fx_index.get(src_ccy)
            if rates is None:
                return None
            rate = rates.get(ts)
            return value * rate if rate is not None else None

        for ts in bucket_timestamps:
            ts_aware = _ensure_utc(ts)

            while tx_ptr < n_txs:
                tx = txs[tx_ptr]
                tx_time = _ensure_utc(tx.traded_at)
                if tx_time > ts_aware:
                    break
                if tx.tx_type == TransactionType.BUY:
                    qty_by_symbol[tx.symbol_id] = (
                        qty_by_symbol.get(tx.symbol_id, _ZERO) + tx.quantity
                    )
                    cumulative_buy_qty[tx.symbol_id] = (
                        cumulative_buy_qty.get(tx.symbol_id, _ZERO) + tx.quantity
                    )
                    cumulative_buy_cost[tx.symbol_id] = (
                        cumulative_buy_cost.get(tx.symbol_id, _ZERO) + tx.quantity * tx.price
                    )
                else:
                    qty_by_symbol[tx.symbol_id] = max(
                        qty_by_symbol.get(tx.symbol_id, _ZERO) - tx.quantity, _ZERO
                    )
                tx_ptr += 1

            running_cost = _ZERO
            for sym_id, qty in qty_by_symbol.items():
                if qty <= _ZERO:
                    continue
                buy_qty = cumulative_buy_qty.get(sym_id, _ZERO)
                buy_cost = cumulative_buy_cost.get(sym_id, _ZERO)
                avg_price = buy_cost / buy_qty if buy_qty > _ZERO else _ZERO
                native_cost = avg_price * qty
                src_ccy = symbol_currency.get(sym_id, target_currency or "KRW")
                converted = _convert(native_cost, src_ccy, ts_aware)
                if converted is not None:
                    running_cost += converted

            value = _ZERO
            for sym_id, qty in qty_by_symbol.items():
                if qty <= _ZERO:
                    continue
                price = _price_at(sym_id, ts_aware, price_index, price_ptr)
                if price is None:
                    continue
                native_value = qty * price
                src_ccy = symbol_currency.get(sym_id, target_currency or "KRW")
                converted = _convert(native_value, src_ccy, ts_aware)
                if converted is not None:
                    value += converted

            points.append(
                HistoryPoint(
                    timestamp=ts_aware,
                    value=value,
                    cost_basis=running_cost,
                )
            )

        return points
