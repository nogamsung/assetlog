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


class TestFxRateRepositoryGetAt:
    async def test_at_이전_환율_반환(
        self, repo: FxRateRepository, db_session: AsyncSession
    ) -> None:
        """get_at은 fetched_at <= at 인 행을 반환한다.

        fx_rates 테이블은 (base, quote) unique constraint 로 통화쌍당 1행만 유지.
        upsert 로 삽입 후 fetched_at 이후 시각으로 조회하면 해당 행을 반환한다.
        """
        fetched_ts = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        query_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)  # 2h later

        await repo.upsert("USD", "KRW", Decimal("1350.00"), fetched_ts)
        await db_session.flush()

        result = await repo.get_at("USD", "KRW", query_at)
        assert result is not None
        assert result.rate == Decimal("1350.00")
        # SQLite stores datetime as timezone-naive; compare naive form
        assert result.fetched_at.replace(tzinfo=None) == fetched_ts.replace(tzinfo=None)

    async def test_at_이후_환율만_있으면_None(
        self, repo: FxRateRepository, db_session: AsyncSession
    ) -> None:
        """fetched_at > at 이면 None 반환."""
        future_ts = datetime(2030, 1, 1, 0, 0, 0, tzinfo=UTC)
        query_at = datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)

        await repo.upsert("EUR", "KRW", Decimal("1500.00"), future_ts)
        await db_session.flush()

        result = await repo.get_at("EUR", "KRW", query_at)
        assert result is None

    async def test_정확히_at_경계_포함(
        self, repo: FxRateRepository, db_session: AsyncSession
    ) -> None:
        """fetched_at == at 인 경우 포함 (inclusive upper bound)."""
        exact_ts = datetime(2024, 6, 15, 9, 0, 0, tzinfo=UTC)

        await repo.upsert("GBP", "KRW", Decimal("1700.00"), exact_ts)
        await db_session.flush()

        # Query exactly at fetched_at → must be included
        result = await repo.get_at("GBP", "KRW", exact_ts)
        assert result is not None
        assert result.rate == Decimal("1700.00")

    async def test_존재하지_않는_페어_None(self, repo: FxRateRepository) -> None:
        """존재하지 않는 페어는 None 반환."""
        result = await repo.get_at("JPY", "KRW", datetime.now(UTC))
        assert result is None


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


class TestFxRateRepositorySnapshots:
    async def test_insert_snapshot_저장(
        self, repo: FxRateRepository, db_session: AsyncSession
    ) -> None:
        ts = datetime(2026, 5, 7, 10, 0, tzinfo=UTC)
        await repo.insert_snapshot("USD", "KRW", Decimal("1380.50"), ts)
        await db_session.flush()

        snap = await repo.get_rate_at("USD", "KRW", ts)
        assert snap is not None
        assert snap.rate == Decimal("1380.50")
        # SQLite drops tz; compare on the naive value
        assert snap.recorded_at.replace(tzinfo=None) == ts.replace(tzinfo=None)

    async def test_insert_snapshot_중복_무시(
        self, repo: FxRateRepository, db_session: AsyncSession
    ) -> None:
        ts = datetime(2026, 5, 7, 10, 0, tzinfo=UTC)
        await repo.insert_snapshot("USD", "KRW", Decimal("1380.50"), ts)
        await db_session.flush()
        await repo.insert_snapshot("USD", "KRW", Decimal("9999.99"), ts)
        await db_session.flush()

        # Same timestamp → second insert silently dropped, original rate kept
        snap = await repo.get_rate_at("USD", "KRW", ts)
        assert snap is not None
        assert snap.rate == Decimal("1380.50")

    async def test_get_rate_at_없는_페어_None(self, repo: FxRateRepository) -> None:
        result = await repo.get_rate_at("USD", "JPY", datetime.now(UTC))
        assert result is None

    async def test_get_rate_at_과거_시점_이전_None(
        self, repo: FxRateRepository, db_session: AsyncSession
    ) -> None:
        ts_future = datetime(2026, 5, 7, tzinfo=UTC)
        ts_past = datetime(2026, 1, 1, tzinfo=UTC)
        await repo.insert_snapshot("USD", "KRW", Decimal("1380"), ts_future)
        await db_session.flush()

        result = await repo.get_rate_at("USD", "KRW", ts_past)
        assert result is None

    async def test_get_rate_at_가장_가까운_과거_반환(
        self, repo: FxRateRepository, db_session: AsyncSession
    ) -> None:
        ts1 = datetime(2026, 1, 1, tzinfo=UTC)
        ts2 = datetime(2026, 3, 1, tzinfo=UTC)
        ts3 = datetime(2026, 5, 1, tzinfo=UTC)
        await repo.insert_snapshot("USD", "KRW", Decimal("1300"), ts1)
        await repo.insert_snapshot("USD", "KRW", Decimal("1350"), ts2)
        await repo.insert_snapshot("USD", "KRW", Decimal("1400"), ts3)
        await db_session.flush()

        # at = 2026-04-01 → should pick ts2 (1350), not ts3 (future)
        result = await repo.get_rate_at("USD", "KRW", datetime(2026, 4, 1, tzinfo=UTC))
        assert result is not None
        assert result.rate == Decimal("1350")

    async def test_get_rates_at_batch_빈_입력_빈_dict(self, repo: FxRateRepository) -> None:
        result = await repo.get_rates_at_batch("USD", "KRW", [])
        assert result == {}

    async def test_get_rates_at_batch_여러_시점_매칭(
        self, repo: FxRateRepository, db_session: AsyncSession
    ) -> None:
        ts1 = datetime(2026, 1, 1, tzinfo=UTC)
        ts2 = datetime(2026, 3, 1, tzinfo=UTC)
        await repo.insert_snapshot("USD", "KRW", Decimal("1300"), ts1)
        await repo.insert_snapshot("USD", "KRW", Decimal("1400"), ts2)
        await db_session.flush()

        ats = [
            datetime(2025, 12, 1, tzinfo=UTC),  # before any snapshot
            datetime(2026, 2, 1, tzinfo=UTC),  # between ts1 and ts2 → ts1
            datetime(2026, 4, 1, tzinfo=UTC),  # after ts2 → ts2
        ]
        result = await repo.get_rates_at_batch("USD", "KRW", ats)
        assert result[ats[0]] is None
        assert result[ats[1]] is not None
        assert result[ats[1]].rate == Decimal("1300")
        assert result[ats[2]] is not None
        assert result[ats[2]].rate == Decimal("1400")
