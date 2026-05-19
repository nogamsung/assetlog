"""Portfolio service — aggregation, derived-value computation, classification."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from app.domain.portfolio import STALE_THRESHOLD, HoldingRow
from app.exceptions import FxRateNotAvailableError
from app.repositories.portfolio import PortfolioRepository
from app.schemas.portfolio import (
    AllocationEntry,
    FxWarning,
    HoldingResponse,
    PnlEntry,
    PortfolioSummaryResponse,
    SymbolEmbedded,
)

if TYPE_CHECKING:
    from app.repositories.cash_account import CashAccountRepository
    from app.services.fx_rate import FxRateService

logger = logging.getLogger(__name__)


def _compute_price_fx_split(
    *,
    pnl_local: Decimal,
    cost_basis_local: Decimal,
    fx_now: Decimal,
    fx_buy_avg: Decimal,
) -> tuple[Decimal, Decimal]:
    """Decompose total P&L (in display currency) into price and FX components.

    Identity (algebraic):
        total_pnl_display
            = latest_value_local × fx_now − cost_basis_local × fx_buy_avg
            = (latest_value_local − cost_basis_local) × fx_now      ← price_pnl
              + cost_basis_local × (fx_now − fx_buy_avg)            ← fx_pnl

    Both inputs must be in the asset's native currency. ``pnl_local`` equals
    ``latest_value_local − cost_basis_local``.
    """
    price_pnl = pnl_local * fx_now
    fx_pnl = cost_basis_local * (fx_now - fx_buy_avg)
    return price_pnl, fx_pnl


def _weighted_avg_fx_buy(
    buy_lots: tuple[tuple[datetime, Decimal], ...],
    historical_rates: dict[datetime, Decimal | None],
) -> Decimal | None:
    """Cost-weighted average historical FX rate over BUY transactions.

    Returns:
        ``Σ(cost_local_i × fx_at_traded_at_i) / Σ(cost_local_i)`` if all
        timestamps have rates, ``None`` if any rate is missing or total cost
        is zero.
    """
    if not buy_lots:
        return None

    total_cost = Decimal("0")
    weighted_sum = Decimal("0")
    for traded_at, cost_local in buy_lots:
        rate = historical_rates.get(traded_at)
        if rate is None:
            return None
        total_cost += cost_local
        weighted_sum += cost_local * rate

    if total_cost == Decimal("0"):
        return None
    return weighted_sum / total_cost


class PortfolioService:
    """Compute derived portfolio values from cached price data.

    No external API calls — reads only from ``asset_symbol.last_price``.
    Optionally accepts an FxRateService to compute converted totals.
    Optionally accepts a CashAccountRepository to include cash in aggregation.
    """

    def __init__(
        self,
        repository: PortfolioRepository,
        fx_service: FxRateService | None = None,
        cash_repository: CashAccountRepository | None = None,
        cash_flow_service: object | None = None,
    ) -> None:
        self._repo = repository
        self._fx_service = fx_service
        self._cash_repo = cash_repository
        # Typed as ``object`` to avoid a hard import cycle. The concrete type
        # is ``CashFlowService`` and only one method is invoked.
        self._cash_flow_service = cash_flow_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_holdings(
        self,
        convert_to: str | None = None,
    ) -> list[HoldingResponse]:
        """Return per-holding rows with derived valuation fields.

        When *convert_to* is provided and a cached FX rate is available for the
        holding's currency, the converted_* fields are populated.  If any rate
        is missing only that holding's converted_* fields are null — other
        holdings are still converted (partial conversion allowed, row-level).
        """
        rows = await self._repo.list_holdings_with_aggregates()
        holdings = [self._compute_holding(row) for row in rows]

        # Inject 1d / 7d / 30d price change percentages. One query per window;
        # symbols missing a prior close in that window are silently left null.
        symbol_ids = [h.asset_symbol.id for h in holdings if h.latest_price is not None]
        if symbol_ids:
            windows = (
                ("change_1d_pct", 1),
                ("change_7d_pct", 7),
                ("change_30d_pct", 30),
            )
            for field_name, days in windows:
                prior = await self._repo.get_prior_closes(symbol_ids, days)
                for h in holdings:
                    if h.latest_price is None:
                        continue
                    prev = prior.get(h.asset_symbol.id)
                    if prev is None or prev == Decimal("0"):
                        continue
                    try:
                        pct = round(
                            float((h.latest_price - prev) / prev * Decimal("100")),
                            2,
                        )
                    except (InvalidOperation, ZeroDivisionError):
                        continue
                    setattr(h, field_name, pct)

        # Compute total value for weight_pct denominator (pending excluded).
        total_value_by_currency: dict[str, Decimal] = {}
        for h in holdings:
            if h.latest_value is not None and h.asset_symbol.currency:
                cur = h.asset_symbol.currency
                total_value_by_currency[cur] = (
                    total_value_by_currency.get(cur, Decimal("0")) + h.latest_value
                )

        # Inject weight_pct — use object.__setattr__ because Pydantic v2
        # model instances are mutable via normal attribute assignment after
        # construction.
        for h in holdings:
            cur = h.asset_symbol.currency
            denom = total_value_by_currency.get(cur, Decimal("0"))
            if h.latest_value is not None and denom > Decimal("0"):
                h.weight_pct = round(float(h.latest_value / denom * 100), 2)
            else:
                h.weight_pct = 0.0

        # Optional per-row currency conversion (partial allowed)
        if convert_to is not None and self._fx_service is not None:
            for h, row in zip(holdings, rows, strict=True):
                h.display_currency = convert_to
                from_currency = h.asset_symbol.currency
                fx_now: Decimal | None = None
                try:
                    h.converted_cost_basis = await self._fx_service.convert(
                        h.cost_basis, from_currency, convert_to
                    )
                    h.converted_realized_pnl = await self._fx_service.convert(
                        h.realized_pnl, from_currency, convert_to
                    )
                    if h.latest_value is not None:
                        h.converted_latest_value = await self._fx_service.convert(
                            h.latest_value, from_currency, convert_to
                        )
                    if h.pnl_abs is not None:
                        h.converted_pnl_abs = await self._fx_service.convert(
                            h.pnl_abs, from_currency, convert_to
                        )
                    fx_now = await self._fx_service.convert(Decimal("1"), from_currency, convert_to)
                except FxRateNotAvailableError:
                    logger.debug(
                        "get_holdings: FX rate unavailable for %s→%s, "
                        "holding user_asset_id=%s converted_* set null",
                        from_currency,
                        convert_to,
                        h.user_asset_id,
                    )
                    h.converted_latest_value = None
                    h.converted_cost_basis = None
                    h.converted_pnl_abs = None
                    h.converted_realized_pnl = None

                await self._compute_split(h, row, from_currency, convert_to, fx_now)

        # Hide fully closed positions (quantity == 0) from the holdings view.
        # Realized PnL for those is still captured in the per-symbol PnL report.
        return [h for h in holdings if h.quantity > Decimal("0")]

    async def _compute_split(
        self,
        holding: HoldingResponse,
        row: HoldingRow,
        from_currency: str,
        convert_to: str,
        fx_now: Decimal | None,
    ) -> None:
        """Populate ``price_pnl``, ``fx_pnl``, ``fx_warning`` on *holding*.

        See ``_compute_price_fx_split`` for the algebraic decomposition.
        Resolves historical FX rates for each BUY lot's traded_at via the
        injected FxRateService and computes the cost-weighted average buy FX.
        """
        if from_currency == convert_to:
            holding.price_pnl = holding.pnl_abs
            holding.fx_pnl = Decimal("0")
            holding.fx_warning = "same_currency"
            return

        if fx_now is None:
            holding.fx_warning = "missing_current_rate"
            return

        if holding.pnl_abs is None or not row.buy_lots:
            return

        timestamps = [traded_at for traded_at, _ in row.buy_lots]
        assert self._fx_service is not None
        historical = await self._fx_service.get_historical_rates_at(
            from_currency, convert_to, timestamps
        )
        fx_buy_avg = _weighted_avg_fx_buy(row.buy_lots, historical)
        if fx_buy_avg is None:
            holding.fx_warning = "missing_historical_rate"
            return

        price_pnl, fx_pnl = _compute_price_fx_split(
            pnl_local=holding.pnl_abs,
            cost_basis_local=row.total_cost,
            fx_now=fx_now,
            fx_buy_avg=fx_buy_avg,
        )
        holding.price_pnl = price_pnl
        holding.fx_pnl = fx_pnl
        holding.fx_warning = None

    async def get_summary(
        self,
        convert_to: str | None = None,
    ) -> PortfolioSummaryResponse:
        """Return currency-bucketed totals, P&L, allocation, and metadata.

        When *convert_to* is provided and all FX rates are available, the
        response also includes ``converted_total_value``, ``converted_total_cost``,
        ``converted_pnl_abs``, ``converted_realized_pnl``, and ``display_currency``.
        If any required rate is missing, all converted fields are left null
        to prevent partial / misleading totals.
        """
        rows = await self._repo.list_holdings_with_aggregates()

        total_value: dict[str, Decimal] = {}
        total_cost: dict[str, Decimal] = {}
        # asset_type → currency → native value. We delay FX conversion until
        # after the loop so we can fetch every rate we need in one batch.
        alloc_native: dict[str, dict[str, Decimal]] = {}
        realized_pnl_acc: dict[str, Decimal] = {}  # ADDED — currency → realized_pnl

        pending_count = 0
        stale_count = 0
        refreshed_times: list[datetime] = []

        for row in rows:
            sym = row.asset_symbol
            cur = sym.currency
            asset_type = str(sym.asset_type)
            latest_price = sym.last_price
            refreshed_at = sym.last_price_refreshed_at

            # Track latest refresh time.
            if refreshed_at is not None:
                # Ensure tz-aware for comparison.
                if refreshed_at.tzinfo is None:
                    refreshed_at = refreshed_at.replace(tzinfo=UTC)
                refreshed_times.append(refreshed_at)

            # Accumulate realized P&L regardless of price status  # ADDED
            realized_pnl_acc[cur] = realized_pnl_acc.get(cur, Decimal("0")) + row.realized_pnl

            # Pending check.
            if latest_price is None:
                pending_count += 1
                # Still accumulate cost.
                total_cost[cur] = total_cost.get(cur, Decimal("0")) + row.total_cost
                continue

            # Stale check — only possible when refreshed_at is not None.
            if refreshed_at is not None:
                now_utc = datetime.now(tz=UTC)
                if (now_utc - refreshed_at) > STALE_THRESHOLD:
                    stale_count += 1

            latest_value = row.total_qty * latest_price

            total_value[cur] = total_value.get(cur, Decimal("0")) + latest_value
            total_cost[cur] = total_cost.get(cur, Decimal("0")) + row.total_cost

            by_cur = alloc_native.setdefault(asset_type, {})
            by_cur[cur] = by_cur.get(cur, Decimal("0")) + latest_value

        # Cash holdings aggregation — prefer the import-derived cash-flow
        # totals (deposits/withdrawals/FX/buys/sells/dividends) over manually
        # entered CashAccount rows, since the former actually reflects the
        # user's broker balances. Falls back to the manual table when no
        # cash-flow service is wired.
        cash_totals: dict[str, Decimal] = {}
        if self._cash_flow_service is not None:
            cash_totals = await self._cash_flow_service.net_cash_by_currency()  # type: ignore[attr-defined]
            # Treat 0 / negative balances as "no cash" for allocation purposes.
            cash_totals = {c: v for c, v in cash_totals.items() if v > Decimal("0")}
        elif self._cash_repo is not None:
            cash_totals = await self._cash_repo.sum_balance_by_currency()

        # Snapshot assets-only value before cash merge — PnL must be computed
        # against invested principal, not (assets + cash). Including cash made
        # pnl_abs / pct overstate by exactly the cash balance per currency.
        assets_value: dict[str, Decimal] = dict(total_value)

        # Merge cash into total_value (cash is always "valued" — no pending state).
        for cur, cash_val in cash_totals.items():
            total_value[cur] = total_value.get(cur, Decimal("0")) + cash_val

        # P&L per currency — invested assets only.
        pnl_by_currency: dict[str, PnlEntry] = {}
        all_pnl_currencies = set(assets_value.keys()) | set(total_cost.keys())
        for cur in all_pnl_currencies:
            val = assets_value.get(cur, Decimal("0"))
            cost = total_cost.get(cur, Decimal("0"))
            pnl_abs = val - cost
            try:
                pnl_pct = float(pnl_abs / cost * 100) if cost > Decimal("0") else 0.0
            except InvalidOperation:
                pnl_pct = 0.0
            pnl_by_currency[cur] = PnlEntry(abs=pnl_abs, pct=round(pnl_pct, 2))

        # ------------------------------------------------------------------
        # Allocation — convert every native total into a single base currency
        # so KR/US/crypto buckets are actually comparable. Pie wedges should
        # answer "how is my net worth split", not "how does USD compare to
        # KRW numerically". Falls back to native sums only if FX is missing.
        # ------------------------------------------------------------------
        alloc_base_ccy = (convert_to or "KRW").upper()
        currencies_in_play = {c for d in alloc_native.values() for c in d} | set(cash_totals.keys())

        # Single-currency portfolios don't need FX — pie ratios are well-defined
        # in any base. Multi-currency portfolios MUST convert; if a non-base
        # currency has no FX rate, we drop that slice rather than mix units
        # (the old fallback added e.g. 1,000 USD into a KRW total as 1,000,
        # producing meaningless pie wedges).
        single_currency = len(currencies_in_play) <= 1

        alloc_rate_map: dict[str, Decimal] | None = None
        if not single_currency and self._fx_service is not None and currencies_in_play:
            try:
                alloc_rate_map = await self._fx_service.get_all_rates_for_conversion(
                    list(currencies_in_play), alloc_base_ccy
                )
            except Exception:  # noqa: BLE001
                alloc_rate_map = None

        def _to_base(value: Decimal, ccy: str) -> Decimal | None:
            if single_currency or ccy == alloc_base_ccy:
                return value
            if alloc_rate_map is None:
                return None
            rate = alloc_rate_map.get(ccy)
            return value * rate if rate is not None else None

        allocation_value: dict[str, Decimal] = {}
        for asset_type_str, by_cur in alloc_native.items():
            total = Decimal("0")
            for ccy, v in by_cur.items():
                converted = _to_base(v, ccy)
                if converted is None:
                    logger.warning(
                        "allocation: dropping %s value %s in %s (no FX → %s)",
                        asset_type_str,
                        v,
                        ccy,
                        alloc_base_ccy,
                    )
                    continue
                total += converted
            allocation_value[asset_type_str] = total

        cash_grand_total = Decimal("0")
        for ccy, v in cash_totals.items():
            converted = _to_base(v, ccy)
            if converted is None:
                logger.warning(
                    "allocation: dropping cash %s in %s (no FX → %s)",
                    v,
                    ccy,
                    alloc_base_ccy,
                )
                continue
            cash_grand_total += converted

        grand_total = sum(allocation_value.values(), Decimal("0")) + cash_grand_total
        allocation: list[AllocationEntry] = []
        if grand_total > Decimal("0"):
            for asset_type_str, val in sorted(allocation_value.items()):
                pct = round(float(val / grand_total * 100), 2)
                allocation.append(AllocationEntry(asset_type=asset_type_str, pct=pct))
            if cash_grand_total > Decimal("0"):
                cash_pct = round(float(cash_grand_total / grand_total * 100), 2)
                allocation.append(AllocationEntry(asset_type="cash", pct=cash_pct))

        # last_price_refreshed_at = max across non-null values.
        last_refreshed: datetime | None = max(refreshed_times) if refreshed_times else None

        # Serialise Decimal totals to str for schema.
        total_value_str: dict[str, str] = {k: str(v) for k, v in total_value.items()}
        total_cost_str: dict[str, str] = {k: str(v) for k, v in total_cost.items()}
        realized_pnl_str: dict[str, str] = {k: str(v) for k, v in realized_pnl_acc.items()}  # ADDED
        cash_total_str: dict[str, str] = {k: str(v) for k, v in cash_totals.items()}

        logger.debug(
            "get_summary: currencies=%s pending=%d stale=%d convert_to=%s cash_currencies=%s",
            list(total_value.keys()),
            pending_count,
            stale_count,
            convert_to,
            list(cash_totals.keys()),
        )

        # ------------------------------------------------------------------
        # Optional currency conversion
        # ------------------------------------------------------------------
        converted_total_value: Decimal | None = None
        converted_total_cost: Decimal | None = None
        converted_pnl_abs: Decimal | None = None
        converted_realized_pnl: Decimal | None = None
        converted_price_pnl: Decimal | None = None
        converted_fx_pnl: Decimal | None = None
        display_currency: str | None = None
        summary_fx_warning: FxWarning | None = None

        if convert_to is not None and self._fx_service is not None and total_value:
            all_currencies = list(
                set(total_value.keys()) | set(total_cost.keys()) | set(realized_pnl_acc.keys())
            )
            rate_map = await self._fx_service.get_all_rates_for_conversion(
                all_currencies, convert_to
            )
            if rate_map is not None:
                conv_value = sum(
                    (total_value.get(cur, Decimal("0")) * rate_map[cur] for cur in all_currencies),
                    Decimal("0"),
                )
                conv_assets = sum(
                    (assets_value.get(cur, Decimal("0")) * rate_map[cur] for cur in all_currencies),
                    Decimal("0"),
                )
                conv_cost = sum(
                    (total_cost.get(cur, Decimal("0")) * rate_map[cur] for cur in all_currencies),
                    Decimal("0"),
                )
                conv_realized = sum(
                    (
                        realized_pnl_acc.get(cur, Decimal("0")) * rate_map[cur]
                        for cur in all_currencies
                    ),
                    Decimal("0"),
                )
                converted_total_value = conv_value
                converted_total_cost = conv_cost
                # PnL excludes cash — same fix as pnl_by_currency above.
                converted_pnl_abs = conv_assets - conv_cost
                converted_realized_pnl = conv_realized
                display_currency = convert_to
            else:
                logger.debug(
                    "get_summary: conversion to %s skipped — missing FX rates",
                    convert_to,
                )

            split_result = await self._aggregate_split(rows, convert_to)
            converted_price_pnl = split_result[0]
            converted_fx_pnl = split_result[1]
            summary_fx_warning = split_result[2]

        return PortfolioSummaryResponse(
            total_value_by_currency=total_value_str,
            total_cost_by_currency=total_cost_str,
            pnl_by_currency=pnl_by_currency,
            realized_pnl_by_currency=realized_pnl_str,
            cash_total_by_currency=cash_total_str,
            allocation=allocation,
            last_price_refreshed_at=last_refreshed,
            pending_count=pending_count,
            stale_count=stale_count,
            converted_total_value=converted_total_value,
            converted_total_cost=converted_total_cost,
            converted_pnl_abs=converted_pnl_abs,
            converted_realized_pnl=converted_realized_pnl,
            display_currency=display_currency,
            converted_price_pnl=converted_price_pnl,
            converted_fx_pnl=converted_fx_pnl,
            fx_warning=summary_fx_warning,
        )

    async def _aggregate_split(
        self,
        rows: list[HoldingRow],
        convert_to: str,
    ) -> tuple[Decimal | None, Decimal | None, FxWarning | None]:
        """Sum per-holding ``price_pnl``/``fx_pnl`` for the summary card.

        Returns:
            ``(price_pnl_sum, fx_pnl_sum, warning)``. If any non-pending holding
            with the asset's currency != display currency lacks rates,
            both sums are ``None`` and *warning* is set to the first
            propagating reason. ``same_currency`` is never propagated to
            the summary level (only zero-contribution).
        """
        assert self._fx_service is not None
        price_total = Decimal("0")
        fx_total = Decimal("0")
        first_warning: FxWarning | None = None

        for row in rows:
            sym = row.asset_symbol
            from_currency = sym.currency
            latest_price = sym.last_price
            if latest_price is None:
                continue

            pnl_local = row.total_qty * latest_price - row.total_cost

            if from_currency == convert_to:
                price_total += pnl_local
                continue

            try:
                fx_now = await self._fx_service.convert(Decimal("1"), from_currency, convert_to)
            except FxRateNotAvailableError:
                if first_warning is None:
                    first_warning = "missing_current_rate"
                continue

            if not row.buy_lots:
                continue

            timestamps = [traded_at for traded_at, _ in row.buy_lots]
            historical = await self._fx_service.get_historical_rates_at(
                from_currency, convert_to, timestamps
            )
            fx_buy_avg = _weighted_avg_fx_buy(row.buy_lots, historical)
            if fx_buy_avg is None:
                if first_warning is None:
                    first_warning = "missing_historical_rate"
                continue

            price_pnl, fx_pnl = _compute_price_fx_split(
                pnl_local=pnl_local,
                cost_basis_local=row.total_cost,
                fx_now=fx_now,
                fx_buy_avg=fx_buy_avg,
            )
            price_total += price_pnl
            fx_total += fx_pnl

        if first_warning is not None:
            return None, None, first_warning
        return price_total, fx_total, None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_holding(self, row: HoldingRow) -> HoldingResponse:
        """Build a HoldingResponse from a single HoldingRow.

        Derived values (latest_value, pnl_abs, etc.) are computed in Python
        using Decimal arithmetic — no float intermediates.
        weight_pct is set to 0.0 here and overwritten by get_holdings().
        """
        sym = row.asset_symbol
        latest_price = sym.last_price
        refreshed_at = sym.last_price_refreshed_at
        total_qty = row.total_qty
        total_cost = row.total_cost
        realized_pnl = row.realized_pnl  # ADDED

        avg_cost = total_cost / total_qty if total_qty > Decimal("0") else Decimal("0")

        is_pending = latest_price is None
        is_stale = False

        if refreshed_at is not None:
            if refreshed_at.tzinfo is None:
                refreshed_at = refreshed_at.replace(tzinfo=UTC)
            is_stale = (datetime.now(tz=UTC) - refreshed_at) > STALE_THRESHOLD

        latest_value: Decimal | None = None
        pnl_abs: Decimal | None = None
        pnl_pct: float | None = None

        if latest_price is not None:
            latest_value = total_qty * latest_price
            pnl_abs = latest_value - total_cost
            if total_cost > Decimal("0"):
                try:
                    pnl_pct = round(float(pnl_abs / total_cost * 100), 2)
                except InvalidOperation:
                    pnl_pct = None

        return HoldingResponse(
            user_asset_id=row.user_asset_id,
            asset_symbol=SymbolEmbedded.model_validate(sym),
            quantity=total_qty,
            avg_cost=avg_cost,
            cost_basis=total_cost,
            realized_pnl=realized_pnl,  # ADDED
            latest_price=latest_price,
            latest_value=latest_value,
            pnl_abs=pnl_abs,
            pnl_pct=pnl_pct,
            weight_pct=0.0,
            last_price_refreshed_at=refreshed_at,
            is_stale=is_stale,
            is_pending=is_pending,
        )
