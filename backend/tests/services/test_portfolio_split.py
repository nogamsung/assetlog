"""Unit + integration tests for the price/FX P&L split (issue #63)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from app.domain.asset_type import AssetType
from app.domain.portfolio import HoldingRow
from app.exceptions import FxRateNotAvailableError
from app.models.asset_symbol import AssetSymbol
from app.repositories.portfolio import PortfolioRepository
from app.services.fx_rate import FxRateService
from app.services.portfolio import (
    PortfolioService,
    _compute_price_fx_split,
    _weighted_avg_fx_buy,
)

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestComputePriceFxSplit:
    def test_가격만_상승_환율_동일_fx_pnl_0(self) -> None:
        # USD asset: bought at price 100 (cost 1000, qty 10), now price 120
        # FX unchanged: fx_buy_avg=1300, fx_now=1300
        # pnl_local = 10 * 120 - 1000 = 200
        # cost_basis_local = 1000
        price_pnl, fx_pnl = _compute_price_fx_split(
            pnl_local=Decimal("200"),
            cost_basis_local=Decimal("1000"),
            fx_now=Decimal("1300"),
            fx_buy_avg=Decimal("1300"),
        )
        assert price_pnl == Decimal("260000")  # 200 * 1300
        assert fx_pnl == Decimal("0")  # 1000 * 0

    def test_환율만_상승_가격_동일_price_pnl_0(self) -> None:
        # No price change, FX +10%
        # pnl_local = 0
        # cost_basis_local = 1000, fx_buy_avg=1300, fx_now=1430 (+10%)
        price_pnl, fx_pnl = _compute_price_fx_split(
            pnl_local=Decimal("0"),
            cost_basis_local=Decimal("1000"),
            fx_now=Decimal("1430"),
            fx_buy_avg=Decimal("1300"),
        )
        assert price_pnl == Decimal("0")
        assert fx_pnl == Decimal("130000")  # 1000 * 130

    def test_가격_환율_동시상승_분리_정확성(self) -> None:
        # Price +20%, FX +10%
        price_pnl, fx_pnl = _compute_price_fx_split(
            pnl_local=Decimal("200"),  # 10 qty * (120-100)
            cost_basis_local=Decimal("1000"),
            fx_now=Decimal("1430"),
            fx_buy_avg=Decimal("1300"),
        )
        assert price_pnl == Decimal("286000")  # 200 * 1430
        assert fx_pnl == Decimal("130000")  # 1000 * 130
        # Identity check: total_pnl_display == price_pnl + fx_pnl
        # = 10 * 120 * 1430 - 1000 * 1300 = 1716000 - 1300000 = 416000
        assert price_pnl + fx_pnl == Decimal("416000")

    def test_가격_손실_환율_상승(self) -> None:
        price_pnl, fx_pnl = _compute_price_fx_split(
            pnl_local=Decimal("-100"),
            cost_basis_local=Decimal("1000"),
            fx_now=Decimal("1430"),
            fx_buy_avg=Decimal("1300"),
        )
        assert price_pnl == Decimal("-143000")
        assert fx_pnl == Decimal("130000")


class TestWeightedAvgFxBuy:
    def test_단일_buy_lot(self) -> None:
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        result = _weighted_avg_fx_buy(
            buy_lots=((ts, Decimal("1000")),),
            historical_rates={ts: Decimal("1300")},
        )
        assert result == Decimal("1300")

    def test_복수_buy_lot_가중평균(self) -> None:
        # 1000 USD at 1300 KRW + 2000 USD at 1400 KRW
        # weighted = (1000*1300 + 2000*1400) / 3000 = (1300000 + 2800000)/3000
        ts1 = datetime(2026, 1, 1, tzinfo=UTC)
        ts2 = datetime(2026, 2, 1, tzinfo=UTC)
        result = _weighted_avg_fx_buy(
            buy_lots=((ts1, Decimal("1000")), (ts2, Decimal("2000"))),
            historical_rates={ts1: Decimal("1300"), ts2: Decimal("1400")},
        )
        assert result == Decimal("4100000") / Decimal("3000")

    def test_lot_없음_None(self) -> None:
        assert _weighted_avg_fx_buy((), {}) is None

    def test_역사_환율_누락_None(self) -> None:
        ts1 = datetime(2026, 1, 1, tzinfo=UTC)
        ts2 = datetime(2026, 2, 1, tzinfo=UTC)
        result = _weighted_avg_fx_buy(
            buy_lots=((ts1, Decimal("1000")), (ts2, Decimal("2000"))),
            historical_rates={ts1: Decimal("1300"), ts2: None},
        )
        assert result is None

    def test_총비용_0_None(self) -> None:
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        result = _weighted_avg_fx_buy(
            buy_lots=((ts, Decimal("0")),),
            historical_rates={ts: Decimal("1300")},
        )
        assert result is None


# ---------------------------------------------------------------------------
# Service-level integration
# ---------------------------------------------------------------------------


def _make_symbol(
    sym_id: int = 1,
    symbol: str = "AAPL",
    currency: str = "USD",
    asset_type: AssetType = AssetType.US_STOCK,
    last_price: Decimal | None = Decimal("120"),
) -> AssetSymbol:
    sym = AssetSymbol(
        asset_type=asset_type,
        symbol=symbol,
        exchange="NASDAQ",
        name=symbol,
        currency=currency,
    )
    sym.id = sym_id
    sym.last_price = last_price
    sym.last_price_refreshed_at = datetime.now(UTC)
    sym.created_at = datetime.now(UTC)
    sym.updated_at = datetime.now(UTC)
    return sym


def _make_row(
    ua_id: int = 1,
    total_qty: str = "10",
    total_cost: str = "1000",
    symbol: AssetSymbol | None = None,
    realized_pnl: str = "0",
    buy_lots: tuple[tuple[datetime, Decimal], ...] | None = None,
) -> HoldingRow:
    if symbol is None:
        symbol = _make_symbol()
    if buy_lots is None:
        buy_lots = ((datetime(2026, 1, 1, tzinfo=UTC), Decimal(total_cost)),)
    return HoldingRow(
        user_asset_id=ua_id,
        asset_symbol=symbol,
        total_qty=Decimal(total_qty),
        total_cost=Decimal(total_cost),
        realized_pnl=Decimal(realized_pnl),
        buy_lots=buy_lots,
    )


def _make_fx_service(
    *,
    convert_rates: dict[tuple[str, str], Decimal] | None = None,
    historical_rates: dict[tuple[str, str], dict[datetime, Decimal | None]] | None = None,
) -> FxRateService:
    """Build an FxRateService mock that supports convert + historical lookups."""
    mock_fx = AsyncMock(spec=FxRateService)

    async def _convert(amount: Decimal, from_cur: str, to_cur: str) -> Decimal:
        if from_cur == to_cur:
            return amount
        if convert_rates is None:
            raise FxRateNotAvailableError()
        rate = convert_rates.get((from_cur, to_cur))
        if rate is None:
            raise FxRateNotAvailableError()
        return amount * rate

    async def _get_all_rates(
        from_currencies: list[str], to_currency: str
    ) -> dict[str, Decimal] | None:
        if convert_rates is None:
            return None
        result: dict[str, Decimal] = {}
        for cur in from_currencies:
            if cur == to_currency:
                result[cur] = Decimal("1")
                continue
            rate = convert_rates.get((cur, to_currency))
            if rate is None:
                return None
            result[cur] = rate
        return result

    async def _get_historical(
        from_cur: str, to_cur: str, timestamps: list[datetime]
    ) -> dict[datetime, Decimal | None]:
        if from_cur == to_cur:
            return {ts: Decimal("1") for ts in timestamps}
        if historical_rates is None:
            return dict.fromkeys(timestamps)
        snaps = historical_rates.get((from_cur, to_cur), {})
        return {ts: snaps.get(ts) for ts in timestamps}

    mock_fx.convert.side_effect = _convert
    mock_fx.get_all_rates_for_conversion.side_effect = _get_all_rates
    mock_fx.get_historical_rates_at.side_effect = _get_historical
    return mock_fx  # type: ignore[return-value]  # AsyncMock satisfies the spec


def _make_service(
    rows: list[HoldingRow],
    fx_service: FxRateService | None = None,
) -> PortfolioService:
    mock_repo = AsyncMock(spec=PortfolioRepository)
    mock_repo.list_holdings_with_aggregates.return_value = rows
    return PortfolioService(mock_repo, fx_service=fx_service)


class TestGetHoldingsSplit:
    async def test_USD_자산_KRW_환산_정상_분리(self) -> None:
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        sym = _make_symbol(currency="USD", last_price=Decimal("120"))
        row = _make_row(
            symbol=sym,
            total_qty="10",
            total_cost="1000",
            buy_lots=((ts, Decimal("1000")),),
        )
        fx = _make_fx_service(
            convert_rates={("USD", "KRW"): Decimal("1430")},
            historical_rates={("USD", "KRW"): {ts: Decimal("1300")}},
        )
        svc = _make_service([row], fx_service=fx)

        holdings = await svc.get_holdings(convert_to="KRW")
        h = holdings[0]
        assert h.fx_warning is None
        # pnl_local = 10 * 120 - 1000 = 200
        # price_pnl = 200 * 1430 = 286000
        # fx_pnl = 1000 * (1430 - 1300) = 130000
        assert h.price_pnl == Decimal("286000")
        assert h.fx_pnl == Decimal("130000")

    async def test_같은_통화_same_currency_경고(self) -> None:
        sym = _make_symbol(currency="KRW", last_price=Decimal("100"))
        row = _make_row(symbol=sym, total_qty="10", total_cost="800")
        fx = _make_fx_service(convert_rates={})
        svc = _make_service([row], fx_service=fx)

        holdings = await svc.get_holdings(convert_to="KRW")
        h = holdings[0]
        assert h.fx_warning == "same_currency"
        assert h.fx_pnl == Decimal("0")
        assert h.price_pnl == h.pnl_abs

    async def test_역사_환율_누락_missing_historical_rate(self) -> None:
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        sym = _make_symbol(currency="USD", last_price=Decimal("120"))
        row = _make_row(
            symbol=sym,
            total_qty="10",
            total_cost="1000",
            buy_lots=((ts, Decimal("1000")),),
        )
        fx = _make_fx_service(
            convert_rates={("USD", "KRW"): Decimal("1430")},
            historical_rates={("USD", "KRW"): {}},  # no historical snapshots
        )
        svc = _make_service([row], fx_service=fx)

        holdings = await svc.get_holdings(convert_to="KRW")
        h = holdings[0]
        assert h.fx_warning == "missing_historical_rate"
        assert h.price_pnl is None
        assert h.fx_pnl is None

    async def test_현재_환율_누락_missing_current_rate(self) -> None:
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        sym = _make_symbol(currency="USD", last_price=Decimal("120"))
        row = _make_row(
            symbol=sym,
            total_qty="10",
            total_cost="1000",
            buy_lots=((ts, Decimal("1000")),),
        )
        fx = _make_fx_service(convert_rates={})
        svc = _make_service([row], fx_service=fx)

        holdings = await svc.get_holdings(convert_to="KRW")
        h = holdings[0]
        assert h.fx_warning == "missing_current_rate"
        assert h.price_pnl is None
        assert h.fx_pnl is None

    async def test_convert_to_미지정_split_없음(self) -> None:
        sym = _make_symbol(currency="USD", last_price=Decimal("120"))
        row = _make_row(symbol=sym)
        fx = _make_fx_service(convert_rates={("USD", "KRW"): Decimal("1430")})
        svc = _make_service([row], fx_service=fx)

        holdings = await svc.get_holdings()
        h = holdings[0]
        assert h.fx_warning is None
        assert h.price_pnl is None
        assert h.fx_pnl is None

    async def test_pending_holding_split_skip(self) -> None:
        sym = _make_symbol(currency="USD", last_price=None)
        row = _make_row(symbol=sym, total_qty="10", total_cost="1000")
        fx = _make_fx_service(
            convert_rates={("USD", "KRW"): Decimal("1430")},
            historical_rates={
                ("USD", "KRW"): {
                    datetime(2026, 1, 1, tzinfo=UTC): Decimal("1300"),
                }
            },
        )
        svc = _make_service([row], fx_service=fx)

        holdings = await svc.get_holdings(convert_to="KRW")
        h = holdings[0]
        # pending → pnl_abs is None → split skipped
        assert h.price_pnl is None
        assert h.fx_pnl is None
        assert h.fx_warning is None


class TestGetSummarySplit:
    async def test_USD_KRW_summary_분리_합계(self) -> None:
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        usd_sym = _make_symbol(currency="USD", last_price=Decimal("120"))
        krw_sym = _make_symbol(2, "BTC", "KRW", AssetType.CRYPTO, Decimal("50000000"))
        rows = [
            _make_row(
                1,
                "10",
                "1000",
                usd_sym,
                buy_lots=((ts, Decimal("1000")),),
            ),
            _make_row(2, "1", "40000000", krw_sym),
        ]
        fx = _make_fx_service(
            convert_rates={("USD", "KRW"): Decimal("1430")},
            historical_rates={("USD", "KRW"): {ts: Decimal("1300")}},
        )
        svc = _make_service(rows, fx_service=fx)

        summary = await svc.get_summary(convert_to="KRW")
        assert summary.fx_warning is None
        # USD holding: price_pnl=286000, fx_pnl=130000
        # KRW holding: price_pnl = 50_000_000 - 40_000_000 = 10_000_000, fx_pnl=0
        # Sum: price_pnl=10_286_000, fx_pnl=130_000
        assert summary.converted_price_pnl == Decimal("10286000")
        assert summary.converted_fx_pnl == Decimal("130000")

    async def test_summary_역사_환율_누락_warning_전파(self) -> None:
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        sym = _make_symbol(currency="USD", last_price=Decimal("120"))
        row = _make_row(
            symbol=sym,
            buy_lots=((ts, Decimal("1000")),),
        )
        fx = _make_fx_service(
            convert_rates={("USD", "KRW"): Decimal("1430")},
            historical_rates={("USD", "KRW"): {}},  # missing
        )
        svc = _make_service([row], fx_service=fx)

        summary = await svc.get_summary(convert_to="KRW")
        assert summary.fx_warning == "missing_historical_rate"
        assert summary.converted_price_pnl is None
        assert summary.converted_fx_pnl is None
