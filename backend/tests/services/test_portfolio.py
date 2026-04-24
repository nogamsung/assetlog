"""Unit tests for PortfolioService — mocked repository, pure logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

from app.domain.asset_type import AssetType
from app.domain.portfolio import STALE_THRESHOLD, HoldingRow
from app.models.asset_symbol import AssetSymbol
from app.repositories.portfolio import PortfolioRepository
from app.services.portfolio import PortfolioService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_symbol(
    sym_id: int = 1,
    symbol: str = "BTC",
    currency: str = "KRW",
    asset_type: AssetType = AssetType.CRYPTO,
    last_price: Decimal | None = None,
    refreshed_at: datetime | None = None,
) -> AssetSymbol:
    sym = AssetSymbol(
        asset_type=asset_type,
        symbol=symbol,
        exchange="upbit",
        name=symbol,
        currency=currency,
    )
    sym.id = sym_id
    sym.last_price = last_price
    sym.last_price_refreshed_at = refreshed_at
    sym.created_at = datetime.now(UTC)
    sym.updated_at = datetime.now(UTC)
    return sym


def _make_row(
    ua_id: int = 1,
    total_qty: str = "10",
    total_cost: str = "1000",
    symbol: AssetSymbol | None = None,
    realized_pnl: str = "0",  # ADDED — kept last to preserve positional call compat
) -> HoldingRow:
    if symbol is None:
        symbol = _make_symbol()
    return HoldingRow(
        user_asset_id=ua_id,
        asset_symbol=symbol,
        total_qty=Decimal(total_qty),
        total_cost=Decimal(total_cost),
        realized_pnl=Decimal(realized_pnl),  # ADDED
    )


def _make_service(rows: list[HoldingRow]) -> PortfolioService:
    mock_repo = AsyncMock(spec=PortfolioRepository)
    mock_repo.list_user_holdings_with_aggregates.return_value = rows
    return PortfolioService(mock_repo)


# ---------------------------------------------------------------------------
# get_holdings
# ---------------------------------------------------------------------------


class TestPortfolioServiceGetHoldings:
    async def test_pending만_있는_경우_is_pending_true(self) -> None:
        sym = _make_symbol(last_price=None)
        row = _make_row(symbol=sym)
        svc = _make_service([row])

        holdings = await svc.get_holdings(user_id=1)
        assert len(holdings) == 1
        h = holdings[0]
        assert h.is_pending is True
        assert h.latest_price is None
        assert h.latest_value is None

    async def test_가격_있는_경우_파생값_계산(self) -> None:
        sym = _make_symbol(last_price=Decimal("200"), refreshed_at=datetime.now(UTC))
        row = _make_row(total_qty="5", total_cost="800", symbol=sym)
        svc = _make_service([row])

        holdings = await svc.get_holdings(user_id=1)
        h = holdings[0]
        assert h.latest_price == Decimal("200")
        assert h.latest_value == Decimal("1000")  # 5 * 200
        assert h.pnl_abs == Decimal("200")  # 1000 - 800
        assert h.cost_basis == Decimal("800")

    async def test_비중_합이_100_이내(self) -> None:
        sym1 = _make_symbol(1, "AAPL", "USD", AssetType.US_STOCK, Decimal("100"), datetime.now(UTC))
        sym2 = _make_symbol(2, "GOOG", "USD", AssetType.US_STOCK, Decimal("200"), datetime.now(UTC))
        rows = [
            _make_row(1, "3", "250", sym1),  # value = 300
            _make_row(2, "1", "180", sym2),  # value = 200
        ]
        svc = _make_service(rows)

        holdings = await svc.get_holdings(user_id=1)
        total_weight = sum(h.weight_pct for h in holdings)
        assert abs(total_weight - 100.0) < 0.01

    async def test_pending_종목은_비중_계산에서_제외(self) -> None:
        sym_ok = _make_symbol(
            1, "AAPL", "USD", last_price=Decimal("100"), refreshed_at=datetime.now(UTC)
        )
        sym_pending = _make_symbol(2, "BTC", "KRW", last_price=None)
        rows = [
            _make_row(1, "5", "400", sym_ok),
            _make_row(2, "1", "50000", sym_pending),
        ]
        svc = _make_service(rows)

        holdings = await svc.get_holdings(user_id=1)
        pending_h = next(h for h in holdings if h.is_pending)
        assert pending_h.weight_pct == 0.0

    async def test_stale_판정_3h_초과(self) -> None:
        stale_time = datetime.now(UTC) - STALE_THRESHOLD - timedelta(seconds=1)
        sym = _make_symbol(last_price=Decimal("50"), refreshed_at=stale_time)
        row = _make_row(symbol=sym)
        svc = _make_service([row])

        holdings = await svc.get_holdings(user_id=1)
        assert holdings[0].is_stale is True

    async def test_stale_판정_정확히_3h_이하_아님(self) -> None:
        fresh_time = datetime.now(UTC) - STALE_THRESHOLD + timedelta(seconds=1)
        sym = _make_symbol(last_price=Decimal("50"), refreshed_at=fresh_time)
        row = _make_row(symbol=sym)
        svc = _make_service([row])

        holdings = await svc.get_holdings(user_id=1)
        assert holdings[0].is_stale is False

    async def test_빈_포트폴리오(self) -> None:
        svc = _make_service([])
        holdings = await svc.get_holdings(user_id=1)
        assert holdings == []


# ---------------------------------------------------------------------------
# get_summary
# ---------------------------------------------------------------------------


class TestPortfolioServiceGetSummary:
    async def test_pending만_있는_경우_total_value_빈_dict(self) -> None:
        sym = _make_symbol(last_price=None)
        row = _make_row(symbol=sym)
        svc = _make_service([row])

        summary = await svc.get_summary(user_id=1)
        assert summary.total_value_by_currency == {}
        assert summary.pending_count == 1

    async def test_mixed_currency_집계_분리(self) -> None:
        sym_krw = _make_symbol(
            1, "BTC", "KRW", last_price=Decimal("50000000"), refreshed_at=datetime.now(UTC)
        )
        sym_usd = _make_symbol(
            2, "AAPL", "USD", AssetType.US_STOCK, Decimal("200"), datetime.now(UTC)
        )
        rows = [
            _make_row(1, "1", "40000000", sym_krw),
            _make_row(2, "5", "900", sym_usd),
        ]
        svc = _make_service(rows)

        summary = await svc.get_summary(user_id=1)
        assert "KRW" in summary.total_value_by_currency
        assert "USD" in summary.total_value_by_currency
        assert summary.total_value_by_currency["KRW"] == str(Decimal("50000000"))
        assert summary.total_value_by_currency["USD"] == str(Decimal("1000"))

    async def test_stale_판정_경계_3h_초과(self) -> None:
        stale_time = datetime.now(UTC) - STALE_THRESHOLD - timedelta(seconds=2)
        sym = _make_symbol(last_price=Decimal("100"), refreshed_at=stale_time)
        row = _make_row(symbol=sym)
        svc = _make_service([row])

        summary = await svc.get_summary(user_id=1)
        assert summary.stale_count == 1

    async def test_stale_판정_경계_3h_미만(self) -> None:
        fresh_time = datetime.now(UTC) - STALE_THRESHOLD + timedelta(seconds=2)
        sym = _make_symbol(last_price=Decimal("100"), refreshed_at=fresh_time)
        row = _make_row(symbol=sym)
        svc = _make_service([row])

        summary = await svc.get_summary(user_id=1)
        assert summary.stale_count == 0

    async def test_allocation_합_100_근사(self) -> None:
        sym1 = _make_symbol(1, "A", "USD", AssetType.US_STOCK, Decimal("10"), datetime.now(UTC))
        sym2 = _make_symbol(2, "B", "USD", AssetType.CRYPTO, Decimal("10"), datetime.now(UTC))
        rows = [
            _make_row(1, "3", "20", sym1),  # value=30
            _make_row(2, "7", "40", sym2),  # value=70
        ]
        svc = _make_service(rows)

        summary = await svc.get_summary(user_id=1)
        total_pct = sum(a.pct for a in summary.allocation)
        assert abs(total_pct - 100.0) < 0.1

    async def test_last_price_refreshed_at_max값(self) -> None:
        older = datetime(2026, 1, 1, tzinfo=UTC)
        newer = datetime(2026, 6, 1, tzinfo=UTC)
        sym1 = _make_symbol(1, "A", "KRW", last_price=Decimal("100"), refreshed_at=older)
        sym2 = _make_symbol(2, "B", "KRW", last_price=Decimal("200"), refreshed_at=newer)
        rows = [_make_row(1, symbol=sym1), _make_row(2, symbol=sym2)]
        svc = _make_service(rows)

        summary = await svc.get_summary(user_id=1)
        assert summary.last_price_refreshed_at == newer

    async def test_모두_pending이면_last_refreshed_null(self) -> None:
        sym = _make_symbol(last_price=None, refreshed_at=None)
        svc = _make_service([_make_row(symbol=sym)])

        summary = await svc.get_summary(user_id=1)
        assert summary.last_price_refreshed_at is None

    async def test_빈_포트폴리오_empty_summary(self) -> None:
        svc = _make_service([])
        summary = await svc.get_summary(user_id=1)
        assert summary.total_value_by_currency == {}
        assert summary.pending_count == 0
        assert summary.stale_count == 0
        assert summary.allocation == []

    async def test_pnl_by_currency_계산(self) -> None:
        sym = _make_symbol(last_price=Decimal("110"), refreshed_at=datetime.now(UTC))
        row = _make_row(total_qty="10", total_cost="1000", symbol=sym)  # value=1100, pnl=100
        svc = _make_service([row])

        summary = await svc.get_summary(user_id=1)
        krw_pnl = summary.pnl_by_currency["KRW"]
        assert krw_pnl.abs == Decimal("100")
        assert round(krw_pnl.pct, 2) == 10.0

    async def test_realized_pnl_by_currency_집계(self) -> None:  # ADDED
        sym_krw = _make_symbol(
            1, "BTC", "KRW", last_price=Decimal("50000000"), refreshed_at=datetime.now(UTC)
        )
        sym_usd = _make_symbol(
            2, "AAPL", "USD", AssetType.US_STOCK, Decimal("200"), datetime.now(UTC)
        )
        rows = [
            _make_row(1, "1", "40000000", realized_pnl="300000", symbol=sym_krw),
            _make_row(2, "5", "900", realized_pnl="50", symbol=sym_usd),
        ]
        svc = _make_service(rows)

        summary = await svc.get_summary(user_id=1)
        assert summary.realized_pnl_by_currency.get("KRW") == "300000"
        assert summary.realized_pnl_by_currency.get("USD") == "50"

    async def test_realized_pnl_pending_종목도_포함(self) -> None:  # ADDED
        sym = _make_symbol(last_price=None)
        row = _make_row(realized_pnl="1000", symbol=sym)
        svc = _make_service([row])

        summary = await svc.get_summary(user_id=1)
        assert summary.realized_pnl_by_currency.get("KRW") == "1000"
