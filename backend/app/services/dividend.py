"""DividendService — fetch / persist / query dividend distributions."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from app.adapters.kr_dividends import KrDividendAdapter
from app.adapters.us_dividends import UsDividendAdapter
from app.domain.asset_type import AssetType
from app.domain.dividend import DividendSource
from app.repositories.asset_symbol import AssetSymbolRepository
from app.repositories.dividend import DividendRepository
from app.repositories.portfolio import PortfolioRepository
from app.schemas.dividend import (
    DividendCalendarEntry,
    DividendCalendarResponse,
    DividendListResponse,
    DividendResponse,
    DividendSummaryEntry,
    YieldOnCostEntry,
    YieldOnCostResponse,
)

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")


class DividendService:
    """Coordinator between yfinance/pykrx adapters and the dividends table.

    The refresh path is per-symbol: fetch full history and dedup-insert via
    the repository.  Read paths return Pydantic responses with summary
    rollups for cumulative-yield UI.
    """

    def __init__(
        self,
        repo: DividendRepository,
        symbol_repo: AssetSymbolRepository,
        us_adapter: UsDividendAdapter,
        kr_adapter: KrDividendAdapter | None = None,
        portfolio_repo: PortfolioRepository | None = None,
    ) -> None:
        self._repo = repo
        self._symbol_repo = symbol_repo
        self._us_adapter = us_adapter
        self._kr_adapter = kr_adapter or KrDividendAdapter()
        self._portfolio_repo = portfolio_repo

    async def refresh_us_dividends(self) -> int:
        """Fetch and store dividends for every US-listed AssetSymbol.

        Returns:
            Total number of newly inserted dividend rows across all symbols.
        """
        symbols = await self._symbol_repo.search(
            asset_type=AssetType.US_STOCK,
            limit=1000,
        )
        if not symbols:
            logger.debug(
                "refresh_us_dividends no symbols",
                extra={"event": "us_div_refresh_empty"},
            )
            return 0

        total_inserted = 0
        for sym in symbols:
            try:
                quotes = await self._us_adapter.fetch_dividends(sym.symbol)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "refresh_us_dividends fetch failed for %s: %s",
                    sym.symbol,
                    exc,
                    extra={
                        "event": "us_div_refresh_fetch_fail",
                        "symbol": sym.symbol,
                        "error": str(exc),
                    },
                )
                continue
            inserted = await self._repo.insert_quotes(
                asset_symbol_id=sym.id,
                quotes=quotes,
                source=DividendSource.YFINANCE,
            )
            total_inserted += inserted

        logger.info(
            "refresh_us_dividends done: %d inserted",
            total_inserted,
            extra={
                "event": "us_div_refresh_done",
                "inserted": total_inserted,
                "symbols": len(symbols),
            },
        )
        return total_inserted

    async def refresh_kr_dividends(self) -> int:
        """Fetch and store dividends for every KR-listed AssetSymbol.

        Uses pykrx fundamentals (trailing-12m DPS sampled at year-ends) since
        KRX exposes no event-level dividend feed. Each non-zero year produces
        one synthetic ``Dividend`` row keyed by year-end ex_date.

        Returns:
            Total number of newly inserted dividend rows across all symbols.
        """
        symbols = await self._symbol_repo.search(
            asset_type=AssetType.KR_STOCK,
            limit=1000,
        )
        if not symbols:
            logger.debug(
                "refresh_kr_dividends no symbols",
                extra={"event": "kr_div_refresh_empty"},
            )
            return 0

        total_inserted = 0
        for sym in symbols:
            try:
                quotes = await self._kr_adapter.fetch_dividends(sym.symbol)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "refresh_kr_dividends fetch failed for %s: %s",
                    sym.symbol,
                    exc,
                    extra={
                        "event": "kr_div_refresh_fetch_fail",
                        "symbol": sym.symbol,
                        "error": str(exc),
                    },
                )
                continue
            inserted = await self._repo.insert_quotes(
                asset_symbol_id=sym.id,
                quotes=quotes,
                source=DividendSource.PYKRX,
            )
            total_inserted += inserted

        logger.info(
            "refresh_kr_dividends done: %d inserted",
            total_inserted,
            extra={
                "event": "kr_div_refresh_done",
                "inserted": total_inserted,
                "symbols": len(symbols),
            },
        )
        return total_inserted

    async def list_dividends(
        self,
        *,
        asset_symbol_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> DividendListResponse:
        """Return dividends with cumulative summary by symbol."""
        ids = [asset_symbol_id] if asset_symbol_id is not None else None
        rows = await self._repo.list_filtered(
            asset_symbol_ids=ids,
            date_from=date_from,
            date_to=date_to,
        )
        items = [DividendResponse.model_validate(row) for row in rows]

        sums = await self._repo.sum_by_symbol(asset_symbol_ids=ids)
        currency_by_id: dict[int, str] = {}
        for row in rows:
            currency_by_id.setdefault(row.asset_symbol_id, row.currency)
        summary = [
            DividendSummaryEntry(
                asset_symbol_id=sym_id,
                total_amount=total,
                currency=currency_by_id.get(sym_id, ""),
            )
            for sym_id, total in sorted(sums.items())
        ]
        return DividendListResponse(items=items, summary_by_symbol=summary)

    async def get_calendar(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> DividendCalendarResponse:
        """Return chronological dividend rows joined with symbol/name."""
        rows = await self._repo.list_calendar_with_symbol(
            date_from=date_from,
            date_to=date_to,
        )
        entries = [
            DividendCalendarEntry(
                asset_symbol_id=row.asset_symbol_id,
                symbol=row.symbol,
                name=row.name,
                ex_date=row.ex_date,
                amount=row.amount,
                currency=row.currency,
            )
            for row in rows
        ]
        return DividendCalendarResponse(entries=entries)

    async def get_yield_on_cost(self) -> YieldOnCostResponse:
        """Return cumulative-dividend yield-on-cost per current holding.

        Joins ``DividendRepository.sum_by_symbol`` with the user's holdings
        (cost basis, symbol metadata) from PortfolioRepository. Falls back to
        an empty response if no portfolio_repo was injected — caller is
        expected to wire it in when this endpoint is exposed.
        """
        if self._portfolio_repo is None:
            logger.debug(
                "get_yield_on_cost called without portfolio_repo — returning empty",
                extra={"event": "yoc_no_portfolio_repo"},
            )
            return YieldOnCostResponse(entries=[])

        holdings = await self._portfolio_repo.list_holdings_with_aggregates()
        if not holdings:
            return YieldOnCostResponse(entries=[])

        sym_ids = [h.asset_symbol.id for h in holdings]
        sums = await self._repo.sum_by_symbol(asset_symbol_ids=sym_ids)

        entries: list[YieldOnCostEntry] = []
        for h in holdings:
            sym = h.asset_symbol
            total = sums.get(sym.id, _ZERO)
            cost_basis = h.total_cost
            yoc = (total / cost_basis) if cost_basis > _ZERO else None
            entries.append(
                YieldOnCostEntry(
                    asset_symbol_id=sym.id,
                    symbol=sym.symbol,
                    name=sym.name,
                    currency=sym.currency,
                    cost_basis=cost_basis,
                    total_dividend=total,
                    yield_on_cost_pct=yoc,
                )
            )
        return YieldOnCostResponse(entries=entries)
