"""Portfolio service — aggregation, derived-value computation, classification."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from app.domain.portfolio import STALE_THRESHOLD, HoldingRow
from app.exceptions import FxRateNotAvailableError  # ADDED
from app.repositories.portfolio import PortfolioRepository
from app.schemas.portfolio import (
    AllocationEntry,
    HoldingResponse,
    PnlEntry,
    PortfolioSummaryResponse,
    SymbolEmbedded,
)

if TYPE_CHECKING:
    from app.services.fx_rate import FxRateService

logger = logging.getLogger(__name__)


class PortfolioService:
    """Compute derived portfolio values from cached price data.

    No external API calls — reads only from ``asset_symbol.last_price``.
    Optionally accepts an FxRateService to compute converted totals.
    """

    def __init__(
        self,
        repository: PortfolioRepository,
        fx_service: FxRateService | None = None,
    ) -> None:
        self._repo = repository
        self._fx_service = fx_service

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

        # ADDED — optional per-row currency conversion (partial allowed)
        if convert_to is not None and self._fx_service is not None:
            for h in holdings:
                h.display_currency = convert_to  # ADDED — set regardless of rate availability
                from_currency = h.asset_symbol.currency
                try:
                    # converted_cost_basis — always available when fx rate exists
                    h.converted_cost_basis = await self._fx_service.convert(
                        h.cost_basis, from_currency, convert_to
                    )
                    # converted_realized_pnl — always available when fx rate exists
                    h.converted_realized_pnl = await self._fx_service.convert(
                        h.realized_pnl, from_currency, convert_to
                    )
                    # converted_latest_value / converted_pnl_abs — only when not pending
                    if h.latest_value is not None:
                        h.converted_latest_value = await self._fx_service.convert(
                            h.latest_value, from_currency, convert_to
                        )
                    if h.pnl_abs is not None:
                        h.converted_pnl_abs = await self._fx_service.convert(
                            h.pnl_abs, from_currency, convert_to
                        )
                except FxRateNotAvailableError:  # ADDED — row-level catch; others proceed normally
                    logger.debug(
                        "get_holdings: FX rate unavailable for %s→%s, holding user_asset_id=%s converted_* set null",
                        from_currency,
                        convert_to,
                        h.user_asset_id,
                    )
                    h.converted_latest_value = None
                    h.converted_cost_basis = None
                    h.converted_pnl_abs = None
                    h.converted_realized_pnl = None

        return holdings

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
        allocation_value: dict[str, Decimal] = {}  # asset_type → Decimal
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

            allocation_value[asset_type] = (
                allocation_value.get(asset_type, Decimal("0")) + latest_value
            )

        # P&L per currency.
        pnl_by_currency: dict[str, PnlEntry] = {}
        for cur, val in total_value.items():
            cost = total_cost.get(cur, Decimal("0"))
            pnl_abs = val - cost
            try:
                pnl_pct = float(pnl_abs / cost * 100) if cost > Decimal("0") else 0.0
            except InvalidOperation:
                pnl_pct = 0.0
            pnl_by_currency[cur] = PnlEntry(abs=pnl_abs, pct=round(pnl_pct, 2))

        # Allocation.
        grand_total = sum(allocation_value.values(), Decimal("0"))
        allocation: list[AllocationEntry] = []
        if grand_total > Decimal("0"):
            for asset_type_str, val in sorted(allocation_value.items()):
                pct = round(float(val / grand_total * 100), 2)
                allocation.append(AllocationEntry(asset_type=asset_type_str, pct=pct))

        # last_price_refreshed_at = max across non-null values.
        last_refreshed: datetime | None = max(refreshed_times) if refreshed_times else None

        # Serialise Decimal totals to str for schema.
        total_value_str: dict[str, str] = {k: str(v) for k, v in total_value.items()}
        total_cost_str: dict[str, str] = {k: str(v) for k, v in total_cost.items()}
        realized_pnl_str: dict[str, str] = {k: str(v) for k, v in realized_pnl_acc.items()}  # ADDED

        logger.debug(
            "get_summary: currencies=%s pending=%d stale=%d convert_to=%s",
            list(total_value.keys()),
            pending_count,
            stale_count,
            convert_to,
        )

        # ------------------------------------------------------------------
        # Optional currency conversion
        # ------------------------------------------------------------------
        converted_total_value: Decimal | None = None
        converted_total_cost: Decimal | None = None
        converted_pnl_abs: Decimal | None = None
        converted_realized_pnl: Decimal | None = None
        display_currency: str | None = None

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
                converted_pnl_abs = conv_value - conv_cost
                converted_realized_pnl = conv_realized
                display_currency = convert_to
            else:
                logger.debug(
                    "get_summary: conversion to %s skipped — missing FX rates",
                    convert_to,
                )

        return PortfolioSummaryResponse(
            total_value_by_currency=total_value_str,
            total_cost_by_currency=total_cost_str,
            pnl_by_currency=pnl_by_currency,
            realized_pnl_by_currency=realized_pnl_str,  # ADDED
            allocation=allocation,
            last_price_refreshed_at=last_refreshed,
            pending_count=pending_count,
            stale_count=stale_count,
            converted_total_value=converted_total_value,
            converted_total_cost=converted_total_cost,
            converted_pnl_abs=converted_pnl_abs,
            converted_realized_pnl=converted_realized_pnl,
            display_currency=display_currency,
        )

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
