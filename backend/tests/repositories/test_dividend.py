"""Integration tests for DividendRepository — SQLite in-memory DB."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.asset_type import AssetType
from app.domain.dividend import DividendQuote, DividendSource
from app.models.asset_symbol import AssetSymbol
from app.repositories.dividend import DividendRepository


@pytest.fixture()
def repo(db_session: AsyncSession) -> DividendRepository:
    return DividendRepository(db_session)


async def _create_symbol(
    session: AsyncSession,
    *,
    symbol: str = "AAPL",
    asset_type: AssetType = AssetType.US_STOCK,
    currency: str = "USD",
) -> AssetSymbol:
    sym = AssetSymbol(
        asset_type=asset_type,
        symbol=symbol,
        exchange="NASDAQ",
        name=symbol,
        currency=currency,
    )
    session.add(sym)
    await session.flush()
    return sym


class TestInsertQuotes:
    async def test_빈_리스트_0_반환(
        self, repo: DividendRepository, db_session: AsyncSession
    ) -> None:
        sym = await _create_symbol(db_session)
        count = await repo.insert_quotes(sym.id, [], DividendSource.YFINANCE)
        assert count == 0

    async def test_신규_삽입(
        self, repo: DividendRepository, db_session: AsyncSession
    ) -> None:
        sym = await _create_symbol(db_session)
        quotes = [
            DividendQuote(date(2026, 2, 7), Decimal("0.24"), "USD"),
            DividendQuote(date(2026, 5, 9), Decimal("0.25"), "USD"),
        ]
        count = await repo.insert_quotes(sym.id, quotes, DividendSource.YFINANCE)
        assert count == 2

    async def test_중복_ex_date_건너뜀(
        self, repo: DividendRepository, db_session: AsyncSession
    ) -> None:
        sym = await _create_symbol(db_session)
        first = [DividendQuote(date(2026, 2, 7), Decimal("0.24"), "USD")]
        await repo.insert_quotes(sym.id, first, DividendSource.YFINANCE)
        again = [
            DividendQuote(date(2026, 2, 7), Decimal("9.99"), "USD"),
            DividendQuote(date(2026, 5, 9), Decimal("0.25"), "USD"),
        ]
        inserted = await repo.insert_quotes(sym.id, again, DividendSource.YFINANCE)
        assert inserted == 1


class TestListFiltered:
    async def test_빈_DB_빈_리스트(self, repo: DividendRepository) -> None:
        rows = await repo.list_filtered()
        assert rows == []

    async def test_빈_id_리스트_빈_결과(self, repo: DividendRepository) -> None:
        rows = await repo.list_filtered(asset_symbol_ids=[])
        assert rows == []

    async def test_심볼_필터(
        self, repo: DividendRepository, db_session: AsyncSession
    ) -> None:
        aapl = await _create_symbol(db_session, symbol="AAPL")
        msft = await _create_symbol(db_session, symbol="MSFT")
        await repo.insert_quotes(
            aapl.id,
            [DividendQuote(date(2026, 2, 7), Decimal("0.24"), "USD")],
            DividendSource.YFINANCE,
        )
        await repo.insert_quotes(
            msft.id,
            [DividendQuote(date(2026, 3, 7), Decimal("0.75"), "USD")],
            DividendSource.YFINANCE,
        )
        rows = await repo.list_filtered(asset_symbol_ids=[aapl.id])
        assert len(rows) == 1
        assert rows[0].asset_symbol_id == aapl.id

    async def test_날짜_범위_필터_정렬(
        self, repo: DividendRepository, db_session: AsyncSession
    ) -> None:
        sym = await _create_symbol(db_session)
        await repo.insert_quotes(
            sym.id,
            [
                DividendQuote(date(2025, 11, 7), Decimal("0.23"), "USD"),
                DividendQuote(date(2026, 2, 7), Decimal("0.24"), "USD"),
                DividendQuote(date(2026, 5, 9), Decimal("0.25"), "USD"),
            ],
            DividendSource.YFINANCE,
        )
        rows = await repo.list_filtered(
            date_from=date(2026, 1, 1),
            date_to=date(2026, 4, 1),
        )
        assert len(rows) == 1
        assert rows[0].ex_date == date(2026, 2, 7)


class TestSumBySymbol:
    async def test_빈_DB_빈_dict(self, repo: DividendRepository) -> None:
        result = await repo.sum_by_symbol()
        assert result == {}

    async def test_빈_id_리스트_빈_dict(self, repo: DividendRepository) -> None:
        result = await repo.sum_by_symbol(asset_symbol_ids=[])
        assert result == {}

    async def test_심볼별_누적_금액(
        self, repo: DividendRepository, db_session: AsyncSession
    ) -> None:
        aapl = await _create_symbol(db_session, symbol="AAPL")
        msft = await _create_symbol(db_session, symbol="MSFT")
        await repo.insert_quotes(
            aapl.id,
            [
                DividendQuote(date(2026, 2, 7), Decimal("0.24"), "USD"),
                DividendQuote(date(2026, 5, 9), Decimal("0.25"), "USD"),
            ],
            DividendSource.YFINANCE,
        )
        await repo.insert_quotes(
            msft.id,
            [DividendQuote(date(2026, 3, 7), Decimal("0.75"), "USD")],
            DividendSource.YFINANCE,
        )
        result = await repo.sum_by_symbol()
        assert result[aapl.id] == Decimal("0.49")
        assert result[msft.id] == Decimal("0.75")
