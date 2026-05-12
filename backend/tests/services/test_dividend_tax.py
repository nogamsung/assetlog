"""Unit tests for TaxKrService.get_dividend_income_tax."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from app.exceptions import FxRateNotAvailableError
from app.repositories.asset_symbol import AssetSymbolRepository
from app.repositories.dividend import CalendarRow, DividendRepository
from app.repositories.portfolio_history import PortfolioHistoryRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.user_asset import UserAssetRepository
from app.services.fx_rate import FxRateService
from app.services.tax_kr import TaxKrService


def _calendar_row(
    *,
    asset_symbol_id: int = 1,
    symbol: str = "AAPL",
    name: str = "Apple",
    ex_date: date = date(2025, 5, 9),
    amount: str = "0.25",
    currency: str = "USD",
) -> CalendarRow:
    return CalendarRow(
        asset_symbol_id=asset_symbol_id,
        symbol=symbol,
        name=name,
        ex_date=ex_date,
        amount=Decimal(amount),
        currency=currency,
    )


def _make_service(
    rows: list[CalendarRow] | None = None,
    fx_rates: dict[tuple[str, str, str], Decimal] | None = None,
    has_dividend_repo: bool = True,
) -> TaxKrService:
    div_repo: DividendRepository | None
    if has_dividend_repo:
        div_repo = AsyncMock(spec=DividendRepository)
        div_repo.list_calendar_with_symbol.return_value = rows or []
    else:
        div_repo = None

    fx = AsyncMock(spec=FxRateService)

    async def _convert_at(amount: Decimal, frm: str, to: str, at: datetime) -> Decimal:
        if frm == to:
            return amount
        rate = (fx_rates or {}).get((frm, to, at.date().isoformat()))
        if rate is None:
            raise FxRateNotAvailableError()
        return amount * rate

    async def _convert(amount: Decimal, frm: str, to: str) -> Decimal:
        if frm == to:
            return amount
        raise FxRateNotAvailableError()

    fx.convert_at.side_effect = _convert_at
    fx.convert.side_effect = _convert

    return TaxKrService(
        history_repo=AsyncMock(spec=PortfolioHistoryRepository),
        symbol_repo=AsyncMock(spec=AssetSymbolRepository),
        tx_repo=AsyncMock(spec=TransactionRepository),
        user_asset_repo=AsyncMock(spec=UserAssetRepository),
        fx_service=fx,
        dividend_repo=div_repo,
    )


class TestDividendIncomeTax:
    async def test_dividend_repo_없으면_빈_결과(self) -> None:
        svc = _make_service(has_dividend_repo=False)
        result = await svc.get_dividend_income_tax(2025)
        assert result.total_dividend_krw == Decimal("0")
        assert result.entries == []
        assert result.comprehensive_threshold_breach is False

    async def test_정상_합산_원천징수(self) -> None:
        rows = [
            _calendar_row(amount="0.24", ex_date=date(2025, 2, 7)),
            _calendar_row(amount="0.25", ex_date=date(2025, 5, 9)),
        ]
        # FX 1300 KRW/USD
        # totals: (0.24 + 0.25) × 1300 = 0.49 × 1300 = 637 KRW
        # withholding = 637 × 0.154 = 98.098
        svc = _make_service(
            rows=rows,
            fx_rates={
                ("USD", "KRW", "2025-02-07"): Decimal("1300"),
                ("USD", "KRW", "2025-05-09"): Decimal("1300"),
            },
        )
        result = await svc.get_dividend_income_tax(2025)
        assert result.total_dividend_krw == Decimal("637.00")
        assert result.withholding_tax_krw == Decimal("98.09800")
        assert result.comprehensive_threshold_breach is False
        assert len(result.entries) == 2

    async def test_threshold_초과_플래그(self) -> None:
        # Construct dividends totalling > 20_000_000 KRW
        rows = [
            _calendar_row(amount="20000", ex_date=date(2025, 5, 9)),
        ]
        svc = _make_service(
            rows=rows,
            fx_rates={("USD", "KRW", "2025-05-09"): Decimal("1300")},
        )
        # 20_000 USD × 1300 = 26_000_000 KRW
        result = await svc.get_dividend_income_tax(2025)
        assert result.total_dividend_krw == Decimal("26000000.00")
        assert result.comprehensive_threshold_breach is True

    async def test_KRW_dividend_no_fx_required(self) -> None:
        rows = [
            _calendar_row(
                amount="100000",
                currency="KRW",
                ex_date=date(2025, 12, 30),
            ),
        ]
        svc = _make_service(rows=rows, fx_rates={})
        result = await svc.get_dividend_income_tax(2025)
        assert result.total_dividend_krw == Decimal("100000")
        assert result.warnings == []

    async def test_FX_누락_warning(self) -> None:
        rows = [_calendar_row(amount="0.25", ex_date=date(2025, 5, 9))]
        # No FX rate at all
        svc = _make_service(rows=rows, fx_rates={})
        result = await svc.get_dividend_income_tax(2025)
        assert any(w.startswith("fx_rate_missing:") for w in result.warnings)

    async def test_custom_rate_and_threshold(self) -> None:
        rows = [_calendar_row(amount="1000", currency="KRW", ex_date=date(2025, 6, 1))]
        svc = _make_service(rows=rows)
        result = await svc.get_dividend_income_tax(
            2025,
            withholding_rate=Decimal("0.20"),
            comprehensive_threshold_krw=Decimal("500"),
        )
        assert result.withholding_rate == Decimal("0.20")
        assert result.comprehensive_threshold_breach is True  # 1000 > 500
        assert result.withholding_tax_krw == Decimal("200.00")
