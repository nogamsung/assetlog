"""Integration tests for FxRateRepository — SQLite in-memory DB."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.fx_rate import FxRateRepository


@pytest.fixture()
def repo(db_session: AsyncSession) -> FxRateRepository:
    return FxRateRepository(db_session)


class TestFxRateRepositoryUpsert:
    async def test_신규_행_삽입(self, repo: FxRateRepository, db_session: AsyncSession) -> None:
        await repo.upsert("USD", "KRW", Decimal("1380.25"), datetime.now(UTC))
        await db_session.flush()

        row = await repo.get_latest("USD", "KRW")
        assert row is not None
        assert row.base_currency == "USD"
        assert row.quote_currency == "KRW"
        assert row.rate == Decimal("1380.25")

    async def test_기존_행_업데이트(self, repo: FxRateRepository, db_session: AsyncSession) -> None:
        t1 = datetime(2026, 4, 24, 10, 0, 0, tzinfo=UTC)
        t2 = datetime(2026, 4, 24, 11, 0, 0, tzinfo=UTC)

        await repo.upsert("USD", "KRW", Decimal("1380.00"), t1)
        await db_session.flush()
        await repo.upsert("USD", "KRW", Decimal("1390.00"), t2)
        await db_session.flush()

        row = await repo.get_latest("USD", "KRW")
        assert row is not None
        assert row.rate == Decimal("1390.00")

    async def test_다른_페어는_독립(self, repo: FxRateRepository, db_session: AsyncSession) -> None:
        await repo.upsert("USD", "KRW", Decimal("1380.00"), datetime.now(UTC))
        await repo.upsert("USD", "EUR", Decimal("0.92"), datetime.now(UTC))
        await db_session.flush()

        krw = await repo.get_latest("USD", "KRW")
        eur = await repo.get_latest("USD", "EUR")
        assert krw is not None
        assert eur is not None
        assert krw.rate == Decimal("1380.00")
        assert eur.rate == Decimal("0.92")


class TestFxRateRepositoryGetLatest:
    async def test_없는_페어는_None(self, repo: FxRateRepository) -> None:
        result = await repo.get_latest("USD", "JPY")
        assert result is None

    async def test_저장된_페어_반환(self, repo: FxRateRepository, db_session: AsyncSession) -> None:
        await repo.upsert("EUR", "USD", Decimal("1.08"), datetime.now(UTC))
        await db_session.flush()

        row = await repo.get_latest("EUR", "USD")
        assert row is not None
        assert row.base_currency == "EUR"
        assert row.quote_currency == "USD"


class TestFxRateRepositoryListAll:
    async def test_빈_DB_빈_리스트(self, repo: FxRateRepository) -> None:
        rows = await repo.list_all()
        assert rows == []

    async def test_여러_행_모두_반환(
        self, repo: FxRateRepository, db_session: AsyncSession
    ) -> None:
        now = datetime.now(UTC)
        await repo.upsert("USD", "KRW", Decimal("1380.00"), now)
        await repo.upsert("USD", "EUR", Decimal("0.92"), now)
        await repo.upsert("KRW", "USD", Decimal("0.000724"), now)
        await db_session.flush()

        rows = await repo.list_all()
        assert len(rows) == 3

    async def test_정렬_순서_base_quote(
        self, repo: FxRateRepository, db_session: AsyncSession
    ) -> None:
        now = datetime.now(UTC)
        await repo.upsert("USD", "KRW", Decimal("1380.00"), now)
        await repo.upsert("EUR", "KRW", Decimal("1500.00"), now)
        await db_session.flush()

        rows = await repo.list_all()
        bases = [r.base_currency for r in rows]
        assert bases == sorted(bases)
