"""Performance metrics — TWR / MWR(IRR) / cashflow extraction / value series.

Public functions are PURE — no I/O, no side effects. Repository / FX I/O is
done in PerformanceService and the inputs are passed to the pure functions.
This decoupling is intentional — issues #62 (benchmark), #66 (Sharpe / MDD),
and #67 (monthly heatmap) reuse build_value_series / compute_twr by direct import.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.performance import (
    Cashflow,
    PerformanceMethod,
    PerformancePeriod,
    ValuePoint,
)
from app.domain.transaction_type import TransactionType
from app.exceptions import FxRateNotAvailableError
from app.repositories.portfolio_history import AllTxRow, PortfolioHistoryRepository
from app.schemas.performance import CashflowEntry, PerformanceResponse
from app.services.fx_rate import FxRateService

# Re-export _price_at from portfolio_history to avoid drift
from app.services.portfolio_history import _price_at as _price_at_impl  # noqa: PLC2701

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")
_ONE = Decimal("1")
_IRR_TOL = 1e-9
_IRR_MAX_ITER = 100
_IRR_SEED = 0.10


# ---------------------------------------------------------------------------
# Pure helper — forward-pointer price lookup (re-exported from portfolio_history)
# ---------------------------------------------------------------------------


def _price_at_local(
    sym_id: int,
    ts: datetime,
    price_index: dict[int, list[tuple[datetime, Decimal]]],
    pointer: dict[int, int],
) -> Decimal | None:
    """Return the most recent price for *sym_id* at or before *ts*.

    Delegates to the identical implementation in portfolio_history to avoid
    drift — single source of truth.
    """
    return _price_at_impl(sym_id, ts, price_index, pointer)


def _ensure_utc(dt: datetime) -> datetime:
    """Return a timezone-aware UTC datetime; attach UTC if naive."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


# ---------------------------------------------------------------------------
# Public pure functions — signature must NOT change (issues #62/#66/#67 import)
# ---------------------------------------------------------------------------


def extract_cashflows(
    txs: list[AllTxRow],
    report_currency: str,
    fx_at: Callable[[Decimal, str, str, datetime], Decimal],
    window_start: datetime,
    window_end: datetime,
) -> list[Cashflow]:
    """Convert transactions in [window_start, window_end] to signed cashflows
    in report_currency.

    BUY  → -(quantity * price * fx)
    SELL → +(quantity * price * fx)

    Same-timestamp BUY+SELL are merged into one Cashflow (sum amounts, kind
    keeps the dominant sign: kind="buy" if sum < 0 else "sell").

    fx_at(amount, from_cur, to_cur, at) is injected so tests can stub it
    without async / DB. In production it wraps PerformanceService's internal
    sync helper that calls FxRateService.convert_at.
    """
    ws = _ensure_utc(window_start)
    we = _ensure_utc(window_end)

    # Accumulate amounts per timestamp — {ts: total_amount}
    by_ts: dict[datetime, Decimal] = {}

    for tx in txs:
        ts = _ensure_utc(tx.traded_at)
        if ts < ws or ts > we:
            continue

        raw_amount = tx.quantity * tx.price
        converted = fx_at(raw_amount, tx.currency, report_currency, ts)

        if tx.tx_type == TransactionType.BUY:
            signed = -converted  # outflow from investor
        else:
            signed = converted  # inflow from SELL

        by_ts[ts] = by_ts.get(ts, _ZERO) + signed

    # Build final list, sorted by timestamp
    result: list[Cashflow] = []
    for ts in sorted(by_ts):
        total = by_ts[ts]
        kind = "buy" if total < _ZERO else "sell"
        result.append(Cashflow(date=ts, amount=total, kind=kind))

    return result


def build_value_series(
    txs: list[AllTxRow],
    price_index: dict[int, list[tuple[datetime, Decimal]]],
    symbol_currency: dict[int, str],
    fx_at: Callable[[Decimal, str, str, datetime], Decimal],
    report_currency: str,
    timestamps: list[datetime],
) -> list[ValuePoint]:
    """For each ts in `timestamps`, compute portfolio value in report_currency.

    Algorithm — same forward-pointer scan as PortfolioHistoryService but with
    per-tx FX conversion at the timestamp `ts`:
      1. Walk txs sorted by traded_at; maintain qty_by_symbol (BUY+, SELL-).
      2. For each ts, sum qty_by_symbol[sym] * price_at(sym, ts) converted
         via fx_at(.., symbol_currency[sym], report_currency, ts).
      3. Return list[ValuePoint].

    Pure — no I/O. price_at uses the existing _price_at helper from
    portfolio_history.py (re-exported from there to avoid drift).

    Note: "value at cashflow time" uses the latest price series sample whose
    timestamp is ≤ ts (deterministic forward-pointer scan). For daily series
    with intra-day cashflows this is an acceptable approximation.
    """
    if not timestamps:
        return []

    sorted_txs = sorted(txs, key=lambda t: _ensure_utc(t.traded_at))
    sorted_ts = [_ensure_utc(t) for t in timestamps]

    qty_by_symbol: dict[int, Decimal] = {}
    price_ptr: dict[int, int] = {}
    tx_ptr = 0
    n_txs = len(sorted_txs)

    points: list[ValuePoint] = []

    for ts in sorted_ts:
        # Advance tx pointer — accumulate all txs with traded_at ≤ ts
        while tx_ptr < n_txs:
            tx = sorted_txs[tx_ptr]
            tx_time = _ensure_utc(tx.traded_at)
            if tx_time > ts:
                break
            if tx.tx_type == TransactionType.BUY:
                qty_by_symbol[tx.symbol_id] = qty_by_symbol.get(tx.symbol_id, _ZERO) + tx.quantity
            else:  # SELL
                qty_by_symbol[tx.symbol_id] = max(
                    qty_by_symbol.get(tx.symbol_id, _ZERO) - tx.quantity, _ZERO
                )
            tx_ptr += 1

        # Compute value at ts
        value = _ZERO
        for sym_id, qty in qty_by_symbol.items():
            if qty <= _ZERO:
                continue
            price = _price_at_local(sym_id, ts, price_index, price_ptr)
            if price is None:
                continue
            sym_currency = symbol_currency.get(sym_id, report_currency)
            try:
                converted_price = fx_at(price, sym_currency, report_currency, ts)
                value += qty * converted_price
            except FxRateNotAvailableError:
                # Missing FX rate — skip this symbol's contribution (caller warns)
                logger.info(
                    "build_value_series: FX rate missing for %s → %s at %s, symbol_id=%d",
                    sym_currency,
                    report_currency,
                    ts,
                    sym_id,
                )

        points.append(ValuePoint(timestamp=ts, value=value))

    return points


def compute_twr(
    value_series: list[ValuePoint],
    cashflows: list[Cashflow],
) -> Decimal | None:
    """Time-Weighted Return over [value_series[0].timestamp, value_series[-1].timestamp].

    Algorithm — standard GIPS-compliant TWR (chain-linking sub-period returns):

    The period is partitioned at each external cashflow timestamp.
    For each sub-period [t_{i-1}, t_i]:

        r_i = V_end_i / V_start_i - 1

    where:
        V_start_i = market value at t_{i-1} AFTER any cashflow AT t_{i-1}.
                    For the first sub-period, V_start_0 = V_at(window_start).
                    The value series is assumed to reflect the portfolio value
                    AFTER all cashflows at that timestamp (i.e. if a BUY occurs
                    at T0, V_series[T0] already includes those holdings).
        V_end_i   = market value just BEFORE any cashflow at t_i
                    (i.e. V_at(t_i) from the series — market move only).

    TWR = ∏(1 + r_i) - 1

    Returns None if value_series is empty or V_start of any sub-period ≤ 0.

    Note: "V_at(ts)" is the latest value_series entry with timestamp ≤ ts
    (deterministic forward-pointer scan). For daily series with intra-day
    cashflows this is an acceptable approximation.
    """
    if not value_series:
        return None

    sorted_series = sorted(value_series, key=lambda v: v.timestamp)

    def _value_at(ts: datetime) -> Decimal:
        """Latest value_series entry with timestamp ≤ ts (0 if none)."""
        candidate = _ZERO
        for vp in sorted_series:
            if vp.timestamp <= ts:
                candidate = vp.value
            else:
                break
        return candidate

    # Group cashflows by timestamp (net per ts)
    cf_by_ts: dict[datetime, Decimal] = {}
    for cf in sorted(cashflows, key=lambda c: _ensure_utc(c.date)):
        ts = _ensure_utc(cf.date)
        cf_by_ts[ts] = cf_by_ts.get(ts, _ZERO) + cf.amount

    # Build sub-period boundary timestamps (sorted, deduped, within window).
    # Only include cashflow timestamps that fall STRICTLY between start and end —
    # the start cashflow is already baked into V_series[start_ts].
    start_ts = sorted_series[0].timestamp
    end_ts = sorted_series[-1].timestamp

    raw_boundaries = (
        [start_ts] + sorted(ts for ts in cf_by_ts if start_ts < ts <= end_ts) + [end_ts]
    )
    seen_set: set[datetime] = set()
    boundaries: list[datetime] = []
    for b in raw_boundaries:
        if b not in seen_set:
            seen_set.add(b)
            boundaries.append(b)

    if len(boundaries) < 2:
        # start == end (or only one point) — return 0% TWR
        return _ZERO

    # V_start_0 = value at the start of the window.
    # build_value_series applies ALL transactions with traded_at ≤ ts, so V_series[ts]
    # is the POST-cashflow value at each timestamp.
    # V_start_0 = V_series[start_ts]  (post-cashflow at window start)
    v_start = _value_at(start_ts)
    if v_start <= _ZERO:
        # Zero or negative opening value — cannot compute meaningful TWR.
        return None

    cumulative = _ONE

    for i in range(1, len(boundaries)):
        cur_ts = boundaries[i]
        net_cf = cf_by_ts.get(cur_ts, _ZERO)
        # V_series[cur_ts] is the post-cashflow market value at cur_ts.
        # V_before_cashflow = V_post + net_cf
        #   BUY (net_cf < 0): V_post includes the new shares; V_before = V_post + (-|cf|)
        #     = V_post - |cf| = value before buying additional shares ✓
        #   SELL (net_cf > 0): V_post excludes sold shares; V_before = V_post + |cf|
        #     = value before selling (higher holdings) ✓
        # Sign rationale: cashflow sign is investor-perspective (BUY=-, SELL=+).
        # Portfolio-perspective: BUY adds shares (+to portfolio), SELL removes (-from portfolio).
        # So V_before = V_post - portfolio_delta = V_post - (-cashflow) = V_post + cashflow.
        v_post = _value_at(cur_ts)
        v_before = v_post + net_cf  # reconstruct pre-cashflow market value

        if v_start <= _ZERO:
            return None

        r_i = v_before / v_start - _ONE
        cumulative = cumulative * (_ONE + r_i)

        # V_start of next sub-period = post-cashflow value
        v_start = v_post
        if v_start <= _ZERO:
            # Zero post-cashflow value — cannot continue
            return None

    return cumulative - _ONE


def compute_mwr(
    cashflows: list[Cashflow],
    terminal_value: Decimal,
    terminal_date: datetime,
    *,
    initial_value: Decimal = Decimal("0"),
    initial_date: datetime | None = None,
) -> Decimal | None:
    """Money-Weighted Return = annualized IRR.

    Solves for r:
        -initial_value + Σ cashflows[i].amount / (1+r)^t_i
                       + terminal_value / (1+r)^t_terminal = 0

    where t_i = (cashflows[i].date - reference_date).days / 365.0.

    reference_date = initial_date or cashflows[0].date (if no initial_value).
    initial_value treated as a synthetic cashflow at reference_date with
    amount = -initial_value.

    Algorithm — Newton-Raphson with seed r=0.10, max 100 iter, tol=1e-9.
    Fallback to bisection on [-0.99, 10] if Newton diverges or NPV doesn't
    change sign at the bracket. Returns None if both fail (e.g. all-same-sign
    cashflows have no IRR).

    Use Decimal throughout — convert (1+r) ** t via float ONLY for the
    exponent; cast back to Decimal each iteration to limit float drift.
    """
    terminal_date_utc = _ensure_utc(terminal_date)

    # Build synthetic cashflow list
    all_cfs: list[tuple[datetime, Decimal]] = []

    if initial_value > _ZERO and initial_date is not None:
        # Treat opening value as outflow at reference_date
        all_cfs.append((_ensure_utc(initial_date), -initial_value))
    elif initial_value > _ZERO:
        # Will be handled after we know reference_date from cashflows
        pass

    for cf in cashflows:
        all_cfs.append((_ensure_utc(cf.date), cf.amount))

    # Terminal value as positive inflow
    all_cfs.append((terminal_date_utc, terminal_value))

    if not all_cfs:
        return None

    # Sort and determine reference_date
    all_cfs.sort(key=lambda x: x[0])

    # If initial_value provided but initial_date not, prepend at first cashflow date
    if initial_value > _ZERO and initial_date is None:
        ref_date = all_cfs[0][0]
        # Prepend the initial outflow
        all_cfs.insert(0, (ref_date, -initial_value))
    elif initial_value > _ZERO and initial_date is not None:
        ref_date = _ensure_utc(initial_date)
    else:
        ref_date = all_cfs[0][0]

    # Compute time fractions in years (float for exponent only).
    # Use .days / 365.0 so that a 365-day cashflow gives t=1.0 exactly,
    # matching PRD G-4 fixture precision (1bp tolerance).
    times: list[float] = [(ts - ref_date).days / 365.0 for ts, _ in all_cfs]
    amounts: list[Decimal] = [amt for _, amt in all_cfs]

    # Check if there's any sign variation — if all same sign, no IRR
    pos = any(a > _ZERO for a in amounts)
    neg = any(a < _ZERO for a in amounts)
    if not (pos and neg):
        logger.info("compute_mwr: all-same-sign cashflows — IRR has no solution")
        return None

    def npv(r: float) -> float:
        """Net present value at rate r (float for speed in iteration)."""
        total = 0.0
        for t, amt in zip(times, amounts, strict=True):
            total += float(amt) / ((1.0 + r) ** t)
        return total

    def dnpv(r: float) -> float:
        """Derivative of NPV with respect to r."""
        total = 0.0
        for t, amt in zip(times, amounts, strict=True):
            total += -t * float(amt) / ((1.0 + r) ** (t + 1.0))
        return total

    # Newton-Raphson
    r = _IRR_SEED
    converged = False
    for _ in range(_IRR_MAX_ITER):
        f = npv(r)
        if abs(f) < _IRR_TOL:
            converged = True
            break
        df = dnpv(r)
        if df == 0.0:
            break
        r_new = r - f / df
        # Guard against divergence (e.g. r ≤ -1)
        if r_new <= -0.999:
            break
        r = r_new

    if converged:
        return Decimal(str(round(r, 10)))

    # Bisection fallback on [-0.99, 10]
    lo, hi = -0.99, 10.0
    f_lo = npv(lo)
    f_hi = npv(hi)

    if f_lo * f_hi > 0:
        # Same sign — no root in bracket
        logger.info("compute_mwr: bisection bracket same sign — IRR unsolvable")
        return None

    for _ in range(200):
        mid = (lo + hi) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < _IRR_TOL or (hi - lo) < 1e-12:
            return Decimal(str(round(mid, 10)))
        if f_lo * f_mid < 0:
            hi = mid
            # f_hi = f_mid (not needed after this)
        else:
            lo = mid
            f_lo = f_mid

    logger.info("compute_mwr: bisection did not converge — IRR unsolvable")
    return None


# ---------------------------------------------------------------------------
# PerformanceService — async, DI-friendly
# ---------------------------------------------------------------------------


def _annualize(rate: Decimal, days: float) -> Decimal | None:
    """Annualize a return using the CAGR formula: (1+r)^(365/days) - 1.

    Returns None if days <= 0 or rate <= -1 (undefined).
    """
    if days <= 0:
        return None
    if rate <= Decimal("-1"):
        return None
    years = days / 365.0
    # Use float for exponent only; cast back to Decimal
    result = float(Decimal("1") + rate) ** (1.0 / years) - 1.0
    return Decimal(str(round(result, 10)))


def _compute_window(
    period: PerformancePeriod,
    end_dt: datetime,
    txs: list[AllTxRow],
) -> tuple[datetime, datetime]:
    """Compute (start_dt, end_dt) for the performance window.

    PRD 5절 US-3 수락 기준:
    - 1W → end - 7d, 1M → end - 30d, 3M → end - 90d, 6M → end - 180d, 1Y → end - 365d
    - YTD → Jan 1 of end.year (UTC)
    - ALL → earliest tx.traded_at (UTC); if no txs → end - 30d fallback
    """
    end_utc = _ensure_utc(end_dt)

    if period == PerformancePeriod.YTD:
        start = datetime(end_utc.year, 1, 1, tzinfo=UTC)
        return start, end_utc

    if period == PerformancePeriod.ALL:
        if txs:
            earliest = min(_ensure_utc(tx.traded_at) for tx in txs)
            return earliest, end_utc
        return end_utc - timedelta(days=30), end_utc

    offsets: dict[PerformancePeriod, timedelta] = {
        PerformancePeriod.ONE_WEEK: timedelta(days=7),
        PerformancePeriod.ONE_MONTH: timedelta(days=30),
        PerformancePeriod.THREE_MONTHS: timedelta(days=90),
        PerformancePeriod.SIX_MONTHS: timedelta(days=180),
        PerformancePeriod.ONE_YEAR: timedelta(days=365),
    }
    return end_utc - offsets[period], end_utc


class PerformanceService:
    """Compute TWR / MWR portfolio performance from transactions + price history.

    All heavy I/O (DB queries, FX lookups) is done upfront; pure functions
    receive pre-fetched data so they remain testable without async / DB.
    """

    def __init__(
        self,
        history_repo: PortfolioHistoryRepository,
        fx_service: FxRateService,
    ) -> None:
        self._repo = history_repo
        self._fx = fx_service

    async def get_performance(
        self,
        period: PerformancePeriod,
        method: PerformanceMethod,
        currency: str,
    ) -> PerformanceResponse:
        """Compute portfolio performance metrics.

        Steps:
        1.  Compute window (start_dt, end_dt).
        2.  Load all transactions (all currencies).
        3.  Load price points for symbols in the window.
        4.  Pre-fetch all needed FX rates; build sync fx_at_sync closure.
        5.  Extract cashflows (in-window transactions only).
        6.  Build value series at cashflow timestamps + start/end.
        7.  Compute TWR / MWR based on *method*.
        8.  Annualize and build PerformanceResponse.
        """
        warnings: list[str] = []
        end_dt = datetime.now(UTC)

        # Step 1 — Load all transactions
        all_txs = await self._repo.list_all_transactions()
        start_dt, end_dt = _compute_window(period, end_dt, all_txs)

        # Separate in-window txs (for cashflows) from all txs (for value series)
        in_window_txs = [tx for tx in all_txs if start_dt <= _ensure_utc(tx.traded_at) <= end_dt]

        if not in_window_txs and not any(_ensure_utc(tx.traded_at) <= end_dt for tx in all_txs):
            logger.info("get_performance: no transactions found at all for period=%s", period)
            warnings.append("no_activity_in_period")
            return PerformanceResponse(
                period=period,
                method=method,
                currency=currency,
                start_date=start_dt,
                end_date=end_dt,
                twr=None,
                mwr=None,
                annualized_twr=None,
                annualized_mwr=None,
                start_value=None,
                end_value=None,
                cashflows=[],
                warnings=warnings,
            )

        # Step 2 — Load price points
        symbol_ids = list({tx.symbol_id for tx in all_txs})
        price_index = await self._repo.list_price_points_for_symbols(symbol_ids, since=start_dt)

        # Step 3 — Build symbol_currency map
        symbol_currency: dict[int, str] = {tx.symbol_id: tx.currency for tx in all_txs}

        # Step 4 — Pre-fetch FX rates; cache in dict keyed by (from, to, hour)
        fx_cache: dict[tuple[str, str, datetime], Decimal] = {}
        fx_missing = False

        # Collect all (from_currency, ts) pairs we'll need
        unique_pairs: set[tuple[str, datetime]] = set()

        # For cashflow FX: all in-window tx currencies × traded_at (truncated to hour)
        for tx in in_window_txs:
            ts_hour = _ensure_utc(tx.traded_at).replace(minute=0, second=0, microsecond=0)
            unique_pairs.add((tx.currency, ts_hour))

        # For value series FX: symbol currencies × cashflow timestamps + start/end
        cf_timestamps = sorted(
            {_ensure_utc(tx.traded_at) for tx in in_window_txs} | {start_dt, end_dt}
        )
        for ts in cf_timestamps:
            ts_hour = ts.replace(minute=0, second=0, microsecond=0)
            for sym_id in symbol_ids:
                sym_cur = symbol_currency.get(sym_id, currency)
                if sym_cur != currency:
                    unique_pairs.add((sym_cur, ts_hour))

        # Batch-fetch FX rates using asyncio.gather
        async def _fetch_one(
            from_cur: str, to_cur: str, at: datetime
        ) -> tuple[tuple[str, str, datetime], Decimal | None]:
            if from_cur == to_cur:
                return (from_cur, to_cur, at), _ONE
            try:
                rate = await self._fx.convert_at(Decimal("1"), from_cur, to_cur, at)
                return (from_cur, to_cur, at), rate
            except FxRateNotAvailableError:
                return (from_cur, to_cur, at), None

        fetch_tasks = [_fetch_one(from_cur, currency, at) for from_cur, at in unique_pairs]
        fetch_results = await asyncio.gather(*fetch_tasks)

        for key, rate in fetch_results:
            if rate is None:
                fx_missing = True
                logger.info(
                    "get_performance: FX rate missing for %s → %s at %s",
                    key[0],
                    key[1],
                    key[2],
                )
            else:
                fx_cache[key] = rate

        if fx_missing:
            warnings.append("fx_rate_missing")

        def fx_at_sync(amount: Decimal, from_cur: str, to_cur: str, at: datetime) -> Decimal:
            """Sync closure over pre-fetched FX cache — called from pure functions."""
            if from_cur == to_cur:
                return amount
            at_hour = _ensure_utc(at).replace(minute=0, second=0, microsecond=0)
            rate = fx_cache.get((from_cur, to_cur, at_hour))
            if rate is None:
                raise FxRateNotAvailableError(
                    f"FX rate not in cache for {from_cur}/{to_cur} at {at_hour}"
                )
            return amount * rate

        # Step 5 — Extract cashflows
        cashflows = extract_cashflows(in_window_txs, currency, fx_at_sync, start_dt, end_dt)

        # Check for no activity
        if not cashflows and not any(_ensure_utc(tx.traded_at) <= start_dt for tx in all_txs):
            logger.info(
                "get_performance: no cashflows and no pre-window holdings for period=%s",
                period,
            )
            if "no_activity_in_period" not in warnings:
                warnings.append("no_activity_in_period")

        # Step 6 — Build value series timestamps
        cf_ts_set = {cf.date for cf in cashflows}
        ts_list = sorted(cf_ts_set | {start_dt, end_dt})

        # Step 7 — Build value series
        value_series = build_value_series(
            all_txs, price_index, symbol_currency, fx_at_sync, currency, ts_list
        )

        start_value: Decimal | None = value_series[0].value if value_series else None
        end_value: Decimal | None = value_series[-1].value if value_series else None

        # Step 8 — Compute TWR / MWR
        twr: Decimal | None = None
        mwr: Decimal | None = None

        if method in (PerformanceMethod.TWR, PerformanceMethod.BOTH):
            if not fx_missing:
                twr = compute_twr(value_series, cashflows)
            # fx_missing already in warnings

        if method in (PerformanceMethod.MWR, PerformanceMethod.BOTH):
            if not fx_missing:
                mwr = compute_mwr(
                    cashflows,
                    terminal_value=end_value if end_value is not None else _ZERO,
                    terminal_date=end_dt,
                    initial_value=start_value if start_value is not None else _ZERO,
                    initial_date=start_dt,
                )
                if mwr is None:
                    logger.info("get_performance: MWR unsolvable for period=%s", period)
                    if "mwr_unsolvable" not in warnings:
                        warnings.append("mwr_unsolvable")

        # Step 9 — Annualize
        window_days = (end_dt - start_dt).total_seconds() / 86400.0
        annualized_twr = _annualize(twr, window_days) if twr is not None else None
        # MWR (IRR) is already annualized by definition
        annualized_mwr = mwr

        # Build cashflow entries
        cashflow_entries = [
            CashflowEntry(date=cf.date, amount=cf.amount, kind=cf.kind) for cf in cashflows
        ]

        return PerformanceResponse(
            period=period,
            method=method,
            currency=currency,
            start_date=start_dt,
            end_date=end_dt,
            twr=twr,
            mwr=mwr,
            annualized_twr=annualized_twr,
            annualized_mwr=annualized_mwr,
            start_value=start_value,
            end_value=end_value,
            cashflows=cashflow_entries,
            warnings=warnings,
        )
