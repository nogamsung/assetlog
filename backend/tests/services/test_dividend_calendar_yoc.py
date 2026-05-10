"""Unit tests for DividendService.get_calendar / get_yield_on_cost."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.adapters.kr_dividends import KrDividendAdapter
from app.adapters.us_dividends import UsDividendAdapter
from app.domain.asset_type import AssetType
from app.domain.portfolio import HoldingRow
from app.models.asset_symbol import AssetSymbol
from app.repositories.asset_symbol import AssetSymbolRepository
from app.repositories.dividend import CalendarRow, DividendRepository
from app.repositories.portfolio import PortfolioRepository
from app.services.dividend import DividendService


def _make_symbol(
    sym_id: int = 1,
    symbol: str = "AAPL",
    name: str = "Apple Inc.",
    currency: str = "USD",
    asset_type: AssetType = AssetType.US_STOCK,
) -> AssetSymbol:
    sym = AssetSymbol(
        asset_type=asset_type,
        symbol=symbol,
        exchange="NASDAQ",
        name=name,
        currency=currency,
    )
    sym.id = sym_id
    sym.last_price = None
    sym.last_price_refreshed_at = None
    sym.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    sym.updated_at = datetime(2024, 1, 1, tzinfo=UTC)
    return sym


def _make_service(
    *,
    calendar_rows: list[CalendarRow] | None = None,
    holdings: list[HoldingRow] | None = None,
    sum_map: dict[int, Decimal] | None = None,
) -> DividendService:
    repo = AsyncMock(spec=DividendRepository)
    repo.list_calendar_with_symbol.return_value = calendar_rows or []
    repo.sum_by_symbol.return_value = sum_map or {}

    symbol_repo = AsyncMock(spec=AssetSymbolRepository)
    us_adapter = MagicMock(spec=UsDividendAdapter)
    kr_adapter = MagicMock(spec=KrDividendAdapter)

    portfolio_repo = AsyncMock(spec=PortfolioRepository)
    portfolio_repo.list_holdings_with_aggregates.return_value = holdings or []

    return DividendService(
        repo=repo,
        symbol_repo=symbol_repo,
        us_adapter=us_adapter,
        kr_adapter=kr_adapter,
        portfolio_repo=portfolio_repo,
    )


class TestGetCalendar:
    async def test_빈_결과(self) -> None:
        svc = _make_service()
        result = await svc.get_calendar()
        assert result.entries == []

    async def test_정상_매핑(self) -> None:
        rows = [
            CalendarRow(
                asset_symbol_id=1,
                symbol="AAPL",
                name="Apple Inc.",
                ex_date=date(2026, 2, 7),
                amount=Decimal("0.24"),
                currency="USD",
            ),
            CalendarRow(
                asset_symbol_id=1,
                symbol="AAPL",
                name="Apple Inc.",
                ex_date=date(2026, 5, 9),
                amount=Decimal("0.25"),
                currency="USD",
            ),
        ]
        svc = _make_service(calendar_rows=rows)
        result = await svc.get_calendar()
        assert len(result.entries) == 2
        assert result.entries[0].symbol == "AAPL"
        assert result.entries[0].amount == Decimal("0.24")

    async def test_date_filter_전파(self) -> None:
        svc = _make_service()
        await svc.get_calendar(date_from=date(2026, 1, 1), date_to=date(2026, 12, 31))
        svc._repo.list_calendar_with_symbol.assert_awaited_with(  # type: ignore[attr-defined]
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
        )


class TestGetYieldOnCost:
    async def test_portfolio_repo_없으면_빈_응답(self) -> None:
        repo = AsyncMock(spec=DividendRepository)
        sym_repo = AsyncMock(spec=AssetSymbolRepository)
        svc = DividendService(
            repo=repo,
            symbol_repo=sym_repo,
            us_adapter=MagicMock(spec=UsDividendAdapter),
            kr_adapter=MagicMock(spec=KrDividendAdapter),
            portfolio_repo=None,
        )
        result = await svc.get_yield_on_cost()
        assert result.entries == []

    async def test_holdings_없으면_빈_응답(self) -> None:
        svc = _make_service(holdings=[])
        result = await svc.get_yield_on_cost()
        assert result.entries == []

    async def test_yoc_계산(self) -> None:
        sym = _make_symbol(sym_id=7, symbol="AAPL")
        holding = HoldingRow(
            user_asset_id=12,
            asset_symbol=sym,
            total_qty=Decimal("10"),
            total_cost=Decimal("1705"),
            realized_pnl=Decimal("0"),
        )
        svc = _make_service(
            holdings=[holding],
            sum_map={7: Decimal("49.20")},
        )
        result = await svc.get_yield_on_cost()
        assert len(result.entries) == 1
        e = result.entries[0]
        assert e.asset_symbol_id == 7
        assert e.symbol == "AAPL"
        assert e.cost_basis == Decimal("1705")
        assert e.total_dividend == Decimal("49.20")
        assert e.yield_on_cost_pct is not None
        # 49.20 / 1705 ≈ 0.02886
        assert abs(float(e.yield_on_cost_pct) - 49.20 / 1705) < 1e-6

    async def test_cost_basis_0_yoc_None(self) -> None:
        sym = _make_symbol()
        holding = HoldingRow(
            user_asset_id=12,
            asset_symbol=sym,
            total_qty=Decimal("0"),
            total_cost=Decimal("0"),
            realized_pnl=Decimal("0"),
        )
        svc = _make_service(holdings=[holding], sum_map={1: Decimal("10")})
        result = await svc.get_yield_on_cost()
        assert result.entries[0].yield_on_cost_pct is None

    async def test_배당_0_yoc_0(self) -> None:
        sym = _make_symbol()
        holding = HoldingRow(
            user_asset_id=12,
            asset_symbol=sym,
            total_qty=Decimal("10"),
            total_cost=Decimal("1000"),
            realized_pnl=Decimal("0"),
        )
        svc = _make_service(holdings=[holding], sum_map={})
        result = await svc.get_yield_on_cost()
        assert result.entries[0].total_dividend == Decimal("0")
        assert result.entries[0].yield_on_cost_pct == Decimal("0")
