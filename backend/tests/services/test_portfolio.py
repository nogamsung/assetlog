"""Unit tests for PortfolioService — mocked repository, pure logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

from app.domain.asset_type import AssetType
from app.domain.portfolio import STALE_THRESHOLD, HoldingRow
from app.exceptions import FxRateNotAvailableError  # ADDED
from app.models.asset_symbol import AssetSymbol
from app.repositories.cash_account import CashAccountRepository
from app.repositories.portfolio import PortfolioRepository
from app.services.fx_rate import FxRateService
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


def _make_service(
    rows: list[HoldingRow],
    fx_service: FxRateService | None = None,
    cash_totals: dict[str, Decimal] | None = None,
) -> PortfolioService:
    mock_repo = AsyncMock(spec=PortfolioRepository)
    mock_repo.list_holdings_with_aggregates.return_value = rows
    if cash_totals is not None:
        mock_cash_repo = AsyncMock(spec=CashAccountRepository)
        mock_cash_repo.sum_balance_by_currency.return_value = cash_totals
        return PortfolioService(mock_repo, fx_service=fx_service, cash_repository=mock_cash_repo)
    return PortfolioService(mock_repo, fx_service=fx_service)


def _make_fx_service(
    rates: dict[tuple[str, str], Decimal] | None = None,
) -> FxRateService:
    """Build a FxRateService mock with a simple rate map.

    Supports both get_all_rates_for_conversion (used by get_summary) and
    convert (used by get_holdings row-level conversion).
    """
    mock_fx = AsyncMock(spec=FxRateService)

    async def _get_all_rates(
        from_currencies: list[str], to_currency: str
    ) -> dict[str, Decimal] | None:
        if rates is None:
            return None
        result: dict[str, Decimal] = {}
        for cur in from_currencies:
            if cur == to_currency:
                result[cur] = Decimal("1")
                continue
            key = (cur, to_currency)
            if key not in rates:
                return None  # partial — return None
            result[cur] = rates[key]
        return result

    async def _convert(amount: Decimal, from_currency: str, to_currency: str) -> Decimal:  # ADDED
        if from_currency == to_currency:  # ADDED
            return amount  # ADDED
        if rates is None:  # ADDED
            raise FxRateNotAvailableError()  # ADDED
        key = (from_currency, to_currency)  # ADDED
        if key not in rates:  # ADDED
            raise FxRateNotAvailableError()  # ADDED
        return amount * rates[key]  # ADDED

    mock_fx.get_all_rates_for_conversion.side_effect = _get_all_rates
    mock_fx.convert.side_effect = _convert  # ADDED
    return mock_fx  # type: ignore[return-value]  # AsyncMock satisfies FxRateService protocol


# ---------------------------------------------------------------------------
# get_holdings
# ---------------------------------------------------------------------------


class TestPortfolioServiceGetHoldings:
    async def test_pending만_있는_경우_is_pending_true(self) -> None:
        sym = _make_symbol(last_price=None)
        row = _make_row(symbol=sym)
        svc = _make_service([row])

        holdings = await svc.get_holdings()
        assert len(holdings) == 1
        h = holdings[0]
        assert h.is_pending is True
        assert h.latest_price is None
        assert h.latest_value is None

    async def test_가격_있는_경우_파생값_계산(self) -> None:
        sym = _make_symbol(last_price=Decimal("200"), refreshed_at=datetime.now(UTC))
        row = _make_row(total_qty="5", total_cost="800", symbol=sym)
        svc = _make_service([row])

        holdings = await svc.get_holdings()
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

        holdings = await svc.get_holdings()
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

        holdings = await svc.get_holdings()
        pending_h = next(h for h in holdings if h.is_pending)
        assert pending_h.weight_pct == 0.0

    async def test_stale_판정_3h_초과(self) -> None:
        stale_time = datetime.now(UTC) - STALE_THRESHOLD - timedelta(seconds=1)
        sym = _make_symbol(last_price=Decimal("50"), refreshed_at=stale_time)
        row = _make_row(symbol=sym)
        svc = _make_service([row])

        holdings = await svc.get_holdings()
        assert holdings[0].is_stale is True

    async def test_stale_판정_정확히_3h_이하_아님(self) -> None:
        fresh_time = datetime.now(UTC) - STALE_THRESHOLD + timedelta(seconds=1)
        sym = _make_symbol(last_price=Decimal("50"), refreshed_at=fresh_time)
        row = _make_row(symbol=sym)
        svc = _make_service([row])

        holdings = await svc.get_holdings()
        assert holdings[0].is_stale is False

    async def test_빈_포트폴리오(self) -> None:
        svc = _make_service([])
        holdings = await svc.get_holdings()
        assert holdings == []


# ---------------------------------------------------------------------------
# get_holdings with convert_to
# ---------------------------------------------------------------------------


class TestPortfolioServiceGetHoldingsConversion:  # ADDED
    async def test_convert_to_없으면_converted_필드_전부_null(self) -> None:  # ADDED
        sym = _make_symbol(last_price=Decimal("200"), refreshed_at=datetime.now(UTC))
        row = _make_row(total_qty="5", total_cost="800", symbol=sym)
        svc = _make_service([row])

        holdings = await svc.get_holdings()
        h = holdings[0]
        assert h.converted_latest_value is None
        assert h.converted_cost_basis is None
        assert h.converted_pnl_abs is None
        assert h.converted_realized_pnl is None
        assert h.display_currency is None

    async def test_convert_to_KRW_USD_holding_환산값_채워짐(self) -> None:  # ADDED
        sym = _make_symbol(1, "AAPL", "USD", AssetType.US_STOCK, Decimal("100"), datetime.now(UTC))
        # qty=10, cost=800, latest_value=1000, pnl_abs=200
        row = _make_row(1, "10", "800", sym, realized_pnl="50")
        fx = _make_fx_service(rates={("USD", "KRW"): Decimal("1380")})
        svc = _make_service([row], fx_service=fx)

        holdings = await svc.get_holdings(convert_to="KRW")
        h = holdings[0]
        assert h.display_currency == "KRW"
        assert h.converted_latest_value == Decimal("1000") * Decimal("1380")
        assert h.converted_cost_basis == Decimal("800") * Decimal("1380")
        assert h.converted_pnl_abs == Decimal("200") * Decimal("1380")
        assert h.converted_realized_pnl == Decimal("50") * Decimal("1380")

    async def test_rate_없는_통화_holding만_converted_null_나머지_정상(self) -> None:  # ADDED
        sym_usd = _make_symbol(
            1, "AAPL", "USD", AssetType.US_STOCK, Decimal("100"), datetime.now(UTC)
        )
        sym_eur = _make_symbol(
            2, "SAP", "EUR", AssetType.US_STOCK, Decimal("200"), datetime.now(UTC)
        )
        rows = [
            _make_row(1, "10", "800", sym_usd),  # USD→KRW 환율 있음
            _make_row(2, "5", "900", sym_eur),  # EUR→KRW 환율 없음
        ]
        # Only USD→KRW provided; EUR→KRW missing → EUR holding converted_* must be null
        fx = _make_fx_service(rates={("USD", "KRW"): Decimal("1380")})
        svc = _make_service(rows, fx_service=fx)

        holdings = await svc.get_holdings(convert_to="KRW")
        usd_h = next(h for h in holdings if h.asset_symbol.currency == "USD")
        eur_h = next(h for h in holdings if h.asset_symbol.currency == "EUR")

        assert usd_h.display_currency == "KRW"
        assert usd_h.converted_latest_value == Decimal("1000") * Decimal("1380")
        assert usd_h.converted_cost_basis == Decimal("800") * Decimal("1380")

        assert eur_h.display_currency == "KRW"
        assert eur_h.converted_latest_value is None
        assert eur_h.converted_cost_basis is None
        assert eur_h.converted_pnl_abs is None
        assert eur_h.converted_realized_pnl is None

    async def test_native_currency_같으면_환산값_동일(self) -> None:  # ADDED
        sym = _make_symbol(
            1, "BTC", "KRW", AssetType.CRYPTO, Decimal("50000000"), datetime.now(UTC)
        )
        row = _make_row(1, "1", "40000000", sym, realized_pnl="300000")
        # KRW→KRW: no rate entry needed (convert() returns amount directly)
        fx = _make_fx_service(rates={})
        svc = _make_service([row], fx_service=fx)

        holdings = await svc.get_holdings(convert_to="KRW")
        h = holdings[0]
        assert h.display_currency == "KRW"
        assert h.converted_latest_value == Decimal("50000000")
        assert h.converted_cost_basis == Decimal("40000000")
        assert h.converted_pnl_abs == Decimal("10000000")
        assert h.converted_realized_pnl == Decimal("300000")

    async def test_pending_holding_converted_latest_value_pnl_abs_null_cost_basis_환산(
        self,
    ) -> None:  # ADDED
        sym = _make_symbol(1, "AAPL", "USD", AssetType.US_STOCK, last_price=None)
        row = _make_row(1, "10", "800", sym, realized_pnl="50")
        fx = _make_fx_service(rates={("USD", "KRW"): Decimal("1380")})
        svc = _make_service([row], fx_service=fx)

        holdings = await svc.get_holdings(convert_to="KRW")
        h = holdings[0]
        assert h.display_currency == "KRW"
        # pending → latest_value/pnl_abs null → converted도 null
        assert h.converted_latest_value is None
        assert h.converted_pnl_abs is None
        # cost_basis/realized_pnl은 가능한 한 환산
        assert h.converted_cost_basis == Decimal("800") * Decimal("1380")
        assert h.converted_realized_pnl == Decimal("50") * Decimal("1380")


# ---------------------------------------------------------------------------
# get_summary
# ---------------------------------------------------------------------------


class TestPortfolioServiceGetSummary:
    async def test_pending만_있는_경우_total_value_빈_dict(self) -> None:
        sym = _make_symbol(last_price=None)
        row = _make_row(symbol=sym)
        svc = _make_service([row])

        summary = await svc.get_summary()
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

        summary = await svc.get_summary()
        assert "KRW" in summary.total_value_by_currency
        assert "USD" in summary.total_value_by_currency
        assert summary.total_value_by_currency["KRW"] == str(Decimal("50000000"))
        assert summary.total_value_by_currency["USD"] == str(Decimal("1000"))

    async def test_stale_판정_경계_3h_초과(self) -> None:
        stale_time = datetime.now(UTC) - STALE_THRESHOLD - timedelta(seconds=2)
        sym = _make_symbol(last_price=Decimal("100"), refreshed_at=stale_time)
        row = _make_row(symbol=sym)
        svc = _make_service([row])

        summary = await svc.get_summary()
        assert summary.stale_count == 1

    async def test_stale_판정_경계_3h_미만(self) -> None:
        fresh_time = datetime.now(UTC) - STALE_THRESHOLD + timedelta(seconds=2)
        sym = _make_symbol(last_price=Decimal("100"), refreshed_at=fresh_time)
        row = _make_row(symbol=sym)
        svc = _make_service([row])

        summary = await svc.get_summary()
        assert summary.stale_count == 0

    async def test_allocation_합_100_근사(self) -> None:
        sym1 = _make_symbol(1, "A", "USD", AssetType.US_STOCK, Decimal("10"), datetime.now(UTC))
        sym2 = _make_symbol(2, "B", "USD", AssetType.CRYPTO, Decimal("10"), datetime.now(UTC))
        rows = [
            _make_row(1, "3", "20", sym1),  # value=30
            _make_row(2, "7", "40", sym2),  # value=70
        ]
        svc = _make_service(rows)

        summary = await svc.get_summary()
        total_pct = sum(a.pct for a in summary.allocation)
        assert abs(total_pct - 100.0) < 0.1

    async def test_last_price_refreshed_at_max값(self) -> None:
        older = datetime(2026, 1, 1, tzinfo=UTC)
        newer = datetime(2026, 6, 1, tzinfo=UTC)
        sym1 = _make_symbol(1, "A", "KRW", last_price=Decimal("100"), refreshed_at=older)
        sym2 = _make_symbol(2, "B", "KRW", last_price=Decimal("200"), refreshed_at=newer)
        rows = [_make_row(1, symbol=sym1), _make_row(2, symbol=sym2)]
        svc = _make_service(rows)

        summary = await svc.get_summary()
        assert summary.last_price_refreshed_at == newer

    async def test_모두_pending이면_last_refreshed_null(self) -> None:
        sym = _make_symbol(last_price=None, refreshed_at=None)
        svc = _make_service([_make_row(symbol=sym)])

        summary = await svc.get_summary()
        assert summary.last_price_refreshed_at is None

    async def test_빈_포트폴리오_empty_summary(self) -> None:
        svc = _make_service([])
        summary = await svc.get_summary()
        assert summary.total_value_by_currency == {}
        assert summary.pending_count == 0
        assert summary.stale_count == 0
        assert summary.allocation == []

    async def test_pnl_by_currency_계산(self) -> None:
        sym = _make_symbol(last_price=Decimal("110"), refreshed_at=datetime.now(UTC))
        row = _make_row(total_qty="10", total_cost="1000", symbol=sym)  # value=1100, pnl=100
        svc = _make_service([row])

        summary = await svc.get_summary()
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

        summary = await svc.get_summary()
        assert summary.realized_pnl_by_currency.get("KRW") == "300000"
        assert summary.realized_pnl_by_currency.get("USD") == "50"

    async def test_realized_pnl_pending_종목도_포함(self) -> None:  # ADDED
        sym = _make_symbol(last_price=None)
        row = _make_row(realized_pnl="1000", symbol=sym)
        svc = _make_service([row])

        summary = await svc.get_summary()
        assert summary.realized_pnl_by_currency.get("KRW") == "1000"


# ---------------------------------------------------------------------------
# get_summary with convert_to
# ---------------------------------------------------------------------------


class TestPortfolioServiceGetSummaryConversion:
    async def test_convert_to_KRW_환산값_계산(self) -> None:
        sym_usd = _make_symbol(
            1, "AAPL", "USD", AssetType.US_STOCK, Decimal("100"), datetime.now(UTC)
        )
        # value = 10 * 100 = 1000 USD, cost = 800 USD
        row = _make_row(1, "10", "800", symbol=sym_usd)

        fx = _make_fx_service(rates={("USD", "KRW"): Decimal("1380")})
        svc = _make_service([row], fx_service=fx)

        summary = await svc.get_summary(convert_to="KRW")

        assert summary.display_currency == "KRW"
        assert summary.converted_total_value == Decimal("1000") * Decimal("1380")
        assert summary.converted_total_cost == Decimal("800") * Decimal("1380")
        assert (
            summary.converted_pnl_abs
            == summary.converted_total_value - summary.converted_total_cost
        )

    async def test_rate_없으면_converted_필드_모두_null(self) -> None:
        sym_usd = _make_symbol(
            1, "AAPL", "USD", AssetType.US_STOCK, Decimal("100"), datetime.now(UTC)
        )
        row = _make_row(1, "10", "800", symbol=sym_usd)

        # No rates provided → get_all_rates_for_conversion returns None
        fx = _make_fx_service(rates=None)
        svc = _make_service([row], fx_service=fx)

        summary = await svc.get_summary(convert_to="KRW")

        assert summary.converted_total_value is None
        assert summary.converted_total_cost is None
        assert summary.converted_pnl_abs is None
        assert summary.converted_realized_pnl is None
        assert summary.display_currency is None

    async def test_convert_to_없으면_converted_필드_null(self) -> None:
        sym = _make_symbol(
            1, "BTC", "KRW", last_price=Decimal("50000000"), refreshed_at=datetime.now(UTC)
        )
        row = _make_row(1, "1", "40000000", symbol=sym)
        svc = _make_service([row])

        summary = await svc.get_summary()  # no convert_to

        assert summary.converted_total_value is None
        assert summary.display_currency is None

    async def test_같은_통화_convert_to_환산값_동일(self) -> None:
        sym_krw = _make_symbol(
            1, "BTC", "KRW", last_price=Decimal("50000000"), refreshed_at=datetime.now(UTC)
        )
        # value = 50000000, cost = 40000000
        row = _make_row(1, "1", "40000000", symbol=sym_krw)

        # KRW→KRW rate = 1
        fx = _make_fx_service(rates={})  # same currency — no key needed
        svc = _make_service([row], fx_service=fx)

        summary = await svc.get_summary(convert_to="KRW")

        assert summary.display_currency == "KRW"
        assert summary.converted_total_value == Decimal("50000000")

    async def test_다중_통화_환산_합산(self) -> None:
        sym_usd = _make_symbol(
            1, "AAPL", "USD", AssetType.US_STOCK, Decimal("100"), datetime.now(UTC)
        )
        sym_krw = _make_symbol(
            2, "BTC", "KRW", last_price=Decimal("50000000"), refreshed_at=datetime.now(UTC)
        )
        rows = [
            _make_row(1, "10", "800", symbol=sym_usd),  # value=1000 USD
            _make_row(2, "1", "40000000", symbol=sym_krw),  # value=50000000 KRW
        ]

        fx = _make_fx_service(
            rates={
                ("USD", "KRW"): Decimal("1380"),
                # KRW→KRW is handled as same-currency (rate=1)
            }
        )
        svc = _make_service(rows, fx_service=fx)

        summary = await svc.get_summary(convert_to="KRW")

        assert summary.display_currency == "KRW"
        expected_value = Decimal("1000") * Decimal("1380") + Decimal("50000000")
        assert summary.converted_total_value == expected_value

    async def test_converted_realized_pnl_환산(self) -> None:
        sym_usd = _make_symbol(
            1, "AAPL", "USD", AssetType.US_STOCK, Decimal("100"), datetime.now(UTC)
        )
        row = _make_row(1, "10", "800", realized_pnl="50", symbol=sym_usd)

        fx = _make_fx_service(rates={("USD", "KRW"): Decimal("1380")})
        svc = _make_service([row], fx_service=fx)

        summary = await svc.get_summary(convert_to="KRW")
        assert summary.converted_realized_pnl == Decimal("50") * Decimal("1380")

    async def test_fx_service_없으면_convert_to_무시(self) -> None:
        sym = _make_symbol(1, "AAPL", "USD", AssetType.US_STOCK, Decimal("100"), datetime.now(UTC))
        row = _make_row(1, "10", "800", symbol=sym)
        # No fx_service injected
        svc = _make_service([row])

        summary = await svc.get_summary(convert_to="KRW")
        assert summary.converted_total_value is None
        assert summary.display_currency is None


# ---------------------------------------------------------------------------
# get_summary with cash holdings
# ---------------------------------------------------------------------------


class TestPortfolioServiceGetSummaryWithCash:
    async def test_현금만_있을때_total_value_by_currency에_현금_표시(self) -> None:
        svc = _make_service([], cash_totals={"KRW": Decimal("1500000")})
        summary = await svc.get_summary()
        assert summary.total_value_by_currency.get("KRW") == str(Decimal("1500000"))

    async def test_현금만_있을때_cash_total_by_currency_정확(self) -> None:
        svc = _make_service([], cash_totals={"KRW": Decimal("1500000")})
        summary = await svc.get_summary()
        assert summary.cash_total_by_currency.get("KRW") == str(Decimal("1500000"))

    async def test_holdings_와_현금_통화별_합산(self) -> None:
        sym = _make_symbol(
            1, "BTC", "KRW", AssetType.CRYPTO, Decimal("50000000"), datetime.now(UTC)
        )
        row = _make_row(1, "1", "40000000", symbol=sym)
        svc = _make_service([row], cash_totals={"KRW": Decimal("500000"), "USD": Decimal("1000")})
        summary = await svc.get_summary()
        # KRW: holdings(50000000) + cash(500000) = 50500000
        assert summary.total_value_by_currency.get("KRW") == str(Decimal("50500000"))
        # USD: only cash
        assert summary.total_value_by_currency.get("USD") == str(Decimal("1000"))

    async def test_cash_allocation_entry_포함(self) -> None:
        sym = _make_symbol(1, "BTC", "KRW", AssetType.CRYPTO, Decimal("100"), datetime.now(UTC))
        # holdings value = 10*100 = 1000 KRW
        row = _make_row(1, "10", "800", symbol=sym)
        # cash = 1000 KRW → grand_total = 2000
        svc = _make_service([row], cash_totals={"KRW": Decimal("1000")})
        summary = await svc.get_summary()

        cash_entries = [a for a in summary.allocation if a.asset_type == "cash"]
        assert len(cash_entries) == 1
        assert abs(cash_entries[0].pct - 50.0) < 0.1

    async def test_현금_없을때_cash_allocation_없음(self) -> None:
        sym = _make_symbol(1, "BTC", "KRW", AssetType.CRYPTO, Decimal("100"), datetime.now(UTC))
        row = _make_row(1, "10", "800", symbol=sym)
        # cash_totals = {} → no cash entry
        svc = _make_service([row], cash_totals={})
        summary = await svc.get_summary()

        cash_entries = [a for a in summary.allocation if a.asset_type == "cash"]
        assert len(cash_entries) == 0

    async def test_allocation_pct_합_100(self) -> None:
        sym = _make_symbol(1, "BTC", "KRW", AssetType.CRYPTO, Decimal("100"), datetime.now(UTC))
        row = _make_row(1, "3", "200", symbol=sym)  # value=300
        svc = _make_service([row], cash_totals={"KRW": Decimal("700")})  # grand=1000
        summary = await svc.get_summary()

        total_pct = sum(a.pct for a in summary.allocation)
        assert abs(total_pct - 100.0) < 0.2

    async def test_cash_repository_없으면_빈_cash_totals(self) -> None:
        sym = _make_symbol(1, "BTC", "KRW", AssetType.CRYPTO, Decimal("100"), datetime.now(UTC))
        row = _make_row(1, "10", "800", symbol=sym)
        # No cash_repository injected
        svc = _make_service([row])
        summary = await svc.get_summary()
        assert summary.cash_total_by_currency == {}

    async def test_convert_to_KRW_cash도_환산에_포함(self) -> None:
        sym_usd = _make_symbol(
            1, "AAPL", "USD", AssetType.US_STOCK, Decimal("100"), datetime.now(UTC)
        )
        row = _make_row(1, "10", "800", symbol=sym_usd)  # value=1000 USD
        fx = _make_fx_service(rates={("USD", "KRW"): Decimal("1380")})
        svc = _make_service([row], fx_service=fx, cash_totals={"USD": Decimal("500")})
        summary = await svc.get_summary(convert_to="KRW")

        # total USD value = 1000 (holdings) + 500 (cash) = 1500 * 1380 = 2070000
        assert summary.display_currency == "KRW"
        assert summary.converted_total_value == Decimal("1500") * Decimal("1380")
