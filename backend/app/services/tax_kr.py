"""TaxKrService — Korean capital-gains-tax estimator for foreign stocks.

Korean residents owe 22% (incl. 2% local) on annual foreign-stock capital
gains above a 2.5M KRW deduction. Gains are realised when SELLs occur
and computed in KRW: each side of a matched lot is converted at the
trade-date FX rate (or the latest available if a historical snapshot is
missing).

Two cost-basis matching methods are supported:
- FIFO: oldest BUY lots consumed first
- AVERAGE: weighted-average cost across all BUYs
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime
from decimal import Decimal

from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType
from app.exceptions import FxRateNotAvailableError
from app.models.asset_symbol import AssetSymbol
from app.models.transaction import Transaction
from app.repositories.asset_symbol import AssetSymbolRepository
from app.repositories.portfolio_history import PortfolioHistoryRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.user_asset import UserAssetRepository
from app.schemas.tax import (
    CapitalGainsTaxResponse,
    CostMethod,
    TaxableSaleEntry,
)
from app.services.fx_rate import FxRateService

logger = logging.getLogger(__name__)


_ZERO = Decimal("0")
_DEFAULT_DEDUCTION_KRW = Decimal("2500000")
_DEFAULT_TAX_RATE = Decimal("0.22")


class TaxKrService:
    """Realised P&L → Korean capital-gains-tax estimate."""

    def __init__(
        self,
        history_repo: PortfolioHistoryRepository,
        symbol_repo: AssetSymbolRepository,
        tx_repo: TransactionRepository,
        user_asset_repo: UserAssetRepository,
        fx_service: FxRateService,
    ) -> None:
        self._history_repo = history_repo
        self._symbol_repo = symbol_repo
        self._tx_repo = tx_repo
        self._user_asset_repo = user_asset_repo
        self._fx = fx_service

    async def get_capital_gains(
        self,
        year: int,
        method: CostMethod = "average",
        deduction_krw: Decimal = _DEFAULT_DEDUCTION_KRW,
        tax_rate: Decimal = _DEFAULT_TAX_RATE,
    ) -> CapitalGainsTaxResponse:
        warnings: list[str] = []

        # 1. Load all foreign-stock symbols (Korean residents pay this tax on
        # foreign stocks; KR stock gains are exempt up to thresholds and handled
        # separately — out of scope for this estimator).
        foreign_symbols = await self._load_foreign_symbols()
        if not foreign_symbols:
            return self._empty_response(year, method, deduction_krw, tax_rate, warnings)

        # 2. Per-symbol: get full transaction history, match cost basis on each
        # SELL falling within the target year.
        all_sales: list[TaxableSaleEntry] = []
        for sym in foreign_symbols:
            sym_sales = await self._sales_for_symbol(sym, year, method, warnings)
            all_sales.extend(sym_sales)

        gross = sum((s.realized_gain_krw for s in all_sales), _ZERO)
        taxable = max(_ZERO, gross - deduction_krw)
        estimated = taxable * tax_rate

        return CapitalGainsTaxResponse(
            year=year,
            method=method,
            sales=all_sales,
            gross_gain_krw=gross,
            deduction_krw=deduction_krw,
            taxable_gain_krw=taxable,
            tax_rate=tax_rate,
            estimated_tax_krw=estimated,
            warnings=warnings,
        )

    async def _load_foreign_symbols(self) -> list[AssetSymbol]:
        """Return AssetSymbols of foreign (non-KR_STOCK) types."""
        out: list[AssetSymbol] = []
        for asset_type in (AssetType.US_STOCK, AssetType.CRYPTO):
            rows = await self._symbol_repo.search(asset_type=asset_type, limit=1000)
            out.extend(rows)
        return out

    async def _sales_for_symbol(
        self,
        sym: AssetSymbol,
        year: int,
        method: CostMethod,
        warnings: list[str],
    ) -> list[TaxableSaleEntry]:
        """Match SELLs in *year* against BUYs (FIFO or average) for one symbol."""
        ua = await self._user_asset_repo.get_by_symbol(sym.id)
        if ua is None:
            return []
        txs = await self._tx_repo.list_all_for_user_asset(ua.id)
        if not txs:
            return []
        # list_all_for_user_asset returns in DB insertion order; explicit sort
        # by traded_at guarantees deterministic FIFO / average state.
        txs = sorted(txs, key=lambda t: t.traded_at)

        if method == "fifo":
            return await self._sales_fifo(sym, txs, year, warnings)
        return await self._sales_average(sym, txs, year, warnings)

    async def _sales_fifo(
        self,
        sym: AssetSymbol,
        txs: list[Transaction],
        year: int,
        warnings: list[str],
    ) -> list[TaxableSaleEntry]:
        """FIFO matching — each SELL consumes oldest BUY lots."""
        lots: deque[tuple[datetime, Decimal, Decimal]] = deque()
        # lot = (traded_at, remaining_qty, unit_price_local)
        sales: list[TaxableSaleEntry] = []
        for tx in txs:
            if tx.type == TransactionType.BUY:
                lots.append((tx.traded_at, tx.quantity, tx.price))
                continue

            # SELL
            if tx.traded_at.year != year:
                # Still consume FIFO inventory to keep state consistent
                self._consume_lots(lots, tx.quantity, warnings)
                continue

            qty_remaining = tx.quantity
            cost_basis_krw = _ZERO
            while qty_remaining > _ZERO and lots:
                lot_dt, lot_qty, lot_price = lots[0]
                take = min(lot_qty, qty_remaining)
                lot_cost_local = take * lot_price
                buy_fx = await self._fx_at_or_warn(sym.currency, lot_dt, warnings)
                cost_basis_krw += lot_cost_local * buy_fx
                qty_remaining -= take
                new_lot_qty = lot_qty - take
                if new_lot_qty == _ZERO:
                    lots.popleft()
                else:
                    lots[0] = (lot_dt, new_lot_qty, lot_price)

            if qty_remaining > _ZERO:
                warnings.append(f"oversold:{sym.symbol}")

            sell_value_local = tx.quantity * tx.price
            sell_fx = await self._fx_at_or_warn(sym.currency, tx.traded_at, warnings)
            sell_value_krw = sell_value_local * sell_fx
            sales.append(
                TaxableSaleEntry(
                    sold_at=tx.traded_at,
                    asset_symbol_id=sym.id,
                    symbol=sym.symbol,
                    quantity=tx.quantity,
                    sell_value_krw=sell_value_krw,
                    cost_basis_krw=cost_basis_krw,
                    realized_gain_krw=sell_value_krw - cost_basis_krw,
                )
            )
        return sales

    @staticmethod
    def _consume_lots(
        lots: deque[tuple[datetime, Decimal, Decimal]],
        quantity: Decimal,
        _warnings: list[str],
    ) -> None:
        """Discard *quantity* shares from the front of lots (state-keeping only)."""
        qty_remaining = quantity
        while qty_remaining > _ZERO and lots:
            lot_dt, lot_qty, lot_price = lots[0]
            take = min(lot_qty, qty_remaining)
            qty_remaining -= take
            new_lot_qty = lot_qty - take
            if new_lot_qty == _ZERO:
                lots.popleft()
            else:
                lots[0] = (lot_dt, new_lot_qty, lot_price)

    async def _sales_average(
        self,
        sym: AssetSymbol,
        txs: list[Transaction],
        year: int,
        warnings: list[str],
    ) -> list[TaxableSaleEntry]:
        """Weighted-average cost (single running ``avg_unit_krw`` across all BUYs).

        Each BUY updates avg_unit_krw using its trade-date FX. Each SELL in
        *year* realises ``qty × (sell_unit_krw - avg_unit_krw)``.
        """
        total_qty = _ZERO
        avg_unit_krw = _ZERO
        sales: list[TaxableSaleEntry] = []
        for tx in txs:
            if tx.type == TransactionType.BUY:
                buy_fx = await self._fx_at_or_warn(sym.currency, tx.traded_at, warnings)
                new_qty = total_qty + tx.quantity
                if new_qty > _ZERO:
                    incoming_krw = tx.quantity * tx.price * buy_fx
                    avg_unit_krw = (avg_unit_krw * total_qty + incoming_krw) / new_qty
                total_qty = new_qty
                continue

            # SELL
            if total_qty <= _ZERO or tx.quantity > total_qty:
                warnings.append(f"oversold:{sym.symbol}")

            if tx.traded_at.year != year:
                total_qty -= tx.quantity
                continue

            sell_fx = await self._fx_at_or_warn(sym.currency, tx.traded_at, warnings)
            sell_value_krw = tx.quantity * tx.price * sell_fx
            cost_basis_krw = tx.quantity * avg_unit_krw
            sales.append(
                TaxableSaleEntry(
                    sold_at=tx.traded_at,
                    asset_symbol_id=sym.id,
                    symbol=sym.symbol,
                    quantity=tx.quantity,
                    sell_value_krw=sell_value_krw,
                    cost_basis_krw=cost_basis_krw,
                    realized_gain_krw=sell_value_krw - cost_basis_krw,
                )
            )
            total_qty -= tx.quantity

        return sales

    async def _fx_at_or_warn(
        self,
        currency: str,
        at: datetime,
        warnings: list[str],
    ) -> Decimal:
        """Return FX rate (currency → KRW) at *at*; fall back to latest with warning.

        If the requested historical snapshot is missing and no current rate
        exists either, returns 1 (degraded — gain computed in local currency
        as a fallback) and emits ``fx_rate_missing:<currency>:<date>``.
        """
        if currency == "KRW":
            return Decimal("1")
        try:
            return await self._fx.convert_at(Decimal("1"), currency, "KRW", at)
        except FxRateNotAvailableError:
            warnings.append(f"fx_rate_missing:{currency}:{at.date().isoformat()}")
            try:
                return await self._fx.convert(Decimal("1"), currency, "KRW")
            except FxRateNotAvailableError:
                return Decimal("1")

    @staticmethod
    def _empty_response(
        year: int,
        method: CostMethod,
        deduction_krw: Decimal,
        tax_rate: Decimal,
        warnings: list[str],
    ) -> CapitalGainsTaxResponse:
        return CapitalGainsTaxResponse(
            year=year,
            method=method,
            sales=[],
            gross_gain_krw=_ZERO,
            deduction_krw=deduction_krw,
            taxable_gain_krw=_ZERO,
            tax_rate=tax_rate,
            estimated_tax_krw=_ZERO,
            warnings=warnings,
        )


