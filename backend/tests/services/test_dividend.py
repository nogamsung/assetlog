"""Unit tests for DividendService — mocked adapter & repositories."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.adapters.kr_dividends import KrDividendAdapter
from app.adapters.us_dividends import UsDividendAdapter
from app.domain.asset_type import AssetType
from app.domain.dividend import DividendQuote, DividendSource
from app.models.asset_symbol import AssetSymbol
from app.models.dividend import Dividend
from app.repositories.asset_symbol import AssetSymbolRepository
from app.repositories.dividend import DividendRepository
from app.services.dividend import DividendService


def _make_symbol(sym_id: int, symbol: str = "AAPL") -> AssetSymbol:
    sym = AssetSymbol(
        asset_type=AssetType.US_STOCK,
        symbol=symbol,
        exchange="NASDAQ",
        name=symbol,
        currency="USD",
    )
    sym.id = sym_id
    return sym


def _make_dividend_row(
    *,
    row_id: int = 1,
    asset_symbol_id: int = 1,
    ex_date: date = date(2026, 2, 7),
    amount: str = "0.24",
) -> Dividend:
    row = Dividend(
        asset_symbol_id=asset_symbol_id,
        ex_date=ex_date,
        amount=Decimal(amount),
        currency="USD",
        source=DividendSource.YFINANCE,
    )
    row.id = row_id
    row.created_at = datetime(2026, 2, 8)
    return row


def _make_service(
    *,
    symbols: list[AssetSymbol],
    fetch_quotes: dict[str, list[DividendQuote]] | None = None,
    kr_fetch_quotes: dict[str, list[DividendQuote]] | None = None,
    list_rows: list[Dividend] | None = None,
    sum_map: dict[int, Decimal] | None = None,
    insert_count: int = 0,
    kr_symbols: list[AssetSymbol] | None = None,
) -> DividendService:
    repo = AsyncMock(spec=DividendRepository)
    repo.insert_quotes.return_value = insert_count
    repo.list_filtered.return_value = list_rows or []
    repo.sum_by_symbol.return_value = sum_map or {}

    symbol_repo = AsyncMock(spec=AssetSymbolRepository)

    async def _search(
        *, asset_type: AssetType | None = None, **_: object
    ) -> list[AssetSymbol]:
        if asset_type == AssetType.KR_STOCK:
            return kr_symbols or []
        return symbols

    symbol_repo.search.side_effect = _search

    us_adapter = MagicMock(spec=UsDividendAdapter)

    async def _fetch_us(ticker: str) -> list[DividendQuote]:
        return (fetch_quotes or {}).get(ticker, [])

    us_adapter.fetch_dividends.side_effect = _fetch_us

    kr_adapter = MagicMock(spec=KrDividendAdapter)

    async def _fetch_kr(ticker: str) -> list[DividendQuote]:
        return (kr_fetch_quotes or {}).get(ticker, [])

    kr_adapter.fetch_dividends.side_effect = _fetch_kr

    return DividendService(
        repo=repo,
        symbol_repo=symbol_repo,
        us_adapter=us_adapter,
        kr_adapter=kr_adapter,
    )


class TestRefreshUsDividends:
    async def test_심볼_없으면_0(self) -> None:
        svc = _make_service(symbols=[])
        result = await svc.refresh_us_dividends()
        assert result == 0

    async def test_quotes_삽입_합계(self) -> None:
        sym = _make_symbol(1, "AAPL")
        quotes = [
            DividendQuote(date(2026, 2, 7), Decimal("0.24"), "USD"),
            DividendQuote(date(2026, 5, 9), Decimal("0.25"), "USD"),
        ]
        svc = _make_service(
            symbols=[sym],
            fetch_quotes={"AAPL": quotes},
            insert_count=2,
        )
        total = await svc.refresh_us_dividends()
        assert total == 2

    async def test_adapter_실패_무시(self) -> None:
        sym = _make_symbol(1, "AAPL")
        svc = _make_service(symbols=[sym])
        svc._us_adapter.fetch_dividends.side_effect = RuntimeError("boom")  # type: ignore[attr-defined]  # mocked
        result = await svc.refresh_us_dividends()
        assert result == 0


class TestRefreshKrDividends:
    async def test_심볼_없으면_0(self) -> None:
        svc = _make_service(symbols=[])
        assert await svc.refresh_kr_dividends() == 0

    async def test_KR_심볼만_조회(self) -> None:
        kr_sym = AssetSymbol(
            asset_type=AssetType.KR_STOCK,
            symbol="005930",
            exchange="KRX",
            name="삼성전자",
            currency="KRW",
        )
        kr_sym.id = 11
        kr_quotes = [
            DividendQuote(date(2024, 12, 30), Decimal("1444"), "KRW"),
            DividendQuote(date(2025, 12, 30), Decimal("1500"), "KRW"),
        ]
        svc = _make_service(
            symbols=[],
            kr_symbols=[kr_sym],
            kr_fetch_quotes={"005930": kr_quotes},
            insert_count=2,
        )
        total = await svc.refresh_kr_dividends()
        assert total == 2
        svc._repo.insert_quotes.assert_awaited_with(  # type: ignore[attr-defined]  # AsyncMock
            asset_symbol_id=11,
            quotes=kr_quotes,
            source=DividendSource.PYKRX,
        )

    async def test_kr_adapter_예외_무시(self) -> None:
        kr_sym = AssetSymbol(
            asset_type=AssetType.KR_STOCK,
            symbol="005930",
            exchange="KRX",
            name="삼성전자",
            currency="KRW",
        )
        kr_sym.id = 11
        svc = _make_service(symbols=[], kr_symbols=[kr_sym])
        svc._kr_adapter.fetch_dividends.side_effect = RuntimeError("boom")  # type: ignore[attr-defined]  # mocked
        assert await svc.refresh_kr_dividends() == 0


class TestListDividends:
    async def test_빈_결과(self) -> None:
        svc = _make_service(symbols=[])
        response = await svc.list_dividends()
        assert response.items == []
        assert response.summary_by_symbol == []

    async def test_summary_정렬과_currency(self) -> None:
        rows = [
            _make_dividend_row(row_id=1, asset_symbol_id=1, amount="0.24"),
            _make_dividend_row(
                row_id=2, asset_symbol_id=1, amount="0.25", ex_date=date(2026, 5, 9)
            ),
            _make_dividend_row(
                row_id=3, asset_symbol_id=2, amount="0.75", ex_date=date(2026, 3, 7)
            ),
        ]
        svc = _make_service(
            symbols=[],
            list_rows=rows,
            sum_map={1: Decimal("0.49"), 2: Decimal("0.75")},
        )
        response = await svc.list_dividends()
        assert len(response.items) == 3
        assert [s.asset_symbol_id for s in response.summary_by_symbol] == [1, 2]
        assert response.summary_by_symbol[0].total_amount == Decimal("0.49")
        assert response.summary_by_symbol[0].currency == "USD"

    async def test_asset_symbol_id_필터(self) -> None:
        rows = [_make_dividend_row(row_id=1, asset_symbol_id=7)]
        svc = _make_service(
            symbols=[],
            list_rows=rows,
            sum_map={7: Decimal("0.24")},
        )
        response = await svc.list_dividends(asset_symbol_id=7)
        assert len(response.items) == 1
        svc._repo.list_filtered.assert_awaited_with(  # type: ignore[attr-defined]  # AsyncMock
            asset_symbol_ids=[7], date_from=None, date_to=None
        )
