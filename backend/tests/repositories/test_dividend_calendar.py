"""Integration tests for DividendRepository.list_calendar_with_symbol."""

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
    name: str = "Apple Inc.",
    asset_type: AssetType = AssetType.US_STOCK,
    currency: str = "USD",
) -> AssetSymbol:
    sym = AssetSymbol(
        asset_type=asset_type,
        symbol=symbol,
        exchange="NASDAQ",
        name=name,
        currency=currency,
    )
    session.add(sym)
    await session.flush()
    return sym


class TestListCalendarWithSymbol:
    async def test_빈_DB_빈_리스트(self, repo: DividendRepository) -> None:
        rows = await repo.list_calendar_with_symbol()
        assert rows == []

    async def test_심볼_조인_정상(
        self,
        repo: DividendRepository,
        db_session: AsyncSession,
    ) -> None:
        sym = await _create_symbol(db_session)
        await repo.insert_quotes(
            sym.id,
            [
                DividendQuote(date(2026, 2, 7), Decimal("0.24"), "USD"),
                DividendQuote(date(2026, 5, 9), Decimal("0.25"), "USD"),
            ],
            DividendSource.YFINANCE,
        )
        rows = await repo.list_calendar_with_symbol()
        assert len(rows) == 2
        assert rows[0].symbol == "AAPL"
        assert rows[0].name == "Apple Inc."
        # ascending — oldest first
        assert rows[0].ex_date == date(2026, 2, 7)
        assert rows[1].ex_date == date(2026, 5, 9)

    async def test_date_from_필터(
        self,
        repo: DividendRepository,
        db_session: AsyncSession,
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
        rows = await repo.list_calendar_with_symbol(date_from=date(2026, 1, 1))
        assert len(rows) == 2
        assert all(r.ex_date >= date(2026, 1, 1) for r in rows)

    async def test_date_to_필터(
        self,
        repo: DividendRepository,
        db_session: AsyncSession,
    ) -> None:
        sym = await _create_symbol(db_session)
        await repo.insert_quotes(
            sym.id,
            [
                DividendQuote(date(2025, 11, 7), Decimal("0.23"), "USD"),
                DividendQuote(date(2026, 5, 9), Decimal("0.25"), "USD"),
            ],
            DividendSource.YFINANCE,
        )
        rows = await repo.list_calendar_with_symbol(date_to=date(2026, 1, 1))
        assert len(rows) == 1
        assert rows[0].ex_date == date(2025, 11, 7)

    async def test_다중_심볼_정렬(
        self,
        repo: DividendRepository,
        db_session: AsyncSession,
    ) -> None:
        aapl = await _create_symbol(db_session, symbol="AAPL", name="Apple")
        msft = await _create_symbol(db_session, symbol="MSFT", name="Microsoft")
        await repo.insert_quotes(
            msft.id,
            [DividendQuote(date(2026, 3, 7), Decimal("0.75"), "USD")],
            DividendSource.YFINANCE,
        )
        await repo.insert_quotes(
            aapl.id,
            [DividendQuote(date(2026, 2, 7), Decimal("0.24"), "USD")],
            DividendSource.YFINANCE,
        )
        rows = await repo.list_calendar_with_symbol()
        # ascending by ex_date
        assert rows[0].symbol == "AAPL"
        assert rows[1].symbol == "MSFT"
