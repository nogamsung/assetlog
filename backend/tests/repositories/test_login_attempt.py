"""Unit tests for LoginAttemptRepository — uses SQLite in-memory via conftest."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.login_attempt import LoginAttemptRepository


def _now() -> datetime:
    """UTC-naive now — matches how the repo stores timestamps."""
    return datetime.now(UTC).replace(tzinfo=None)


class TestLoginAttemptRepositoryRecord:
    async def test_실패_기록을_저장한다(self, db_session: AsyncSession) -> None:
        repo = LoginAttemptRepository(db_session)
        now = _now()
        await repo.record(ip="1.2.3.4", success=False, attempted_at=now)

        count = await repo.count_failures_since("1.2.3.4", now - timedelta(seconds=1))
        assert count == 1

    async def test_성공_기록을_저장한다(self, db_session: AsyncSession) -> None:
        repo = LoginAttemptRepository(db_session)
        now = _now()
        await repo.record(ip="1.2.3.4", success=True, attempted_at=now)

        # success row must NOT count as a failure
        count = await repo.count_failures_since("1.2.3.4", now - timedelta(seconds=1))
        assert count == 0

    async def test_여러_IP_기록이_독립적으로_저장된다(self, db_session: AsyncSession) -> None:
        repo = LoginAttemptRepository(db_session)
        now = _now()
        await repo.record(ip="10.0.0.1", success=False, attempted_at=now)
        await repo.record(ip="10.0.0.2", success=False, attempted_at=now)

        count_1 = await repo.count_failures_since("10.0.0.1", now - timedelta(seconds=1))
        count_2 = await repo.count_failures_since("10.0.0.2", now - timedelta(seconds=1))
        assert count_1 == 1
        assert count_2 == 1


class TestLoginAttemptRepositoryCountFailuresSince:
    async def test_윈도우_밖_기록은_카운트_안된다(self, db_session: AsyncSession) -> None:
        repo = LoginAttemptRepository(db_session)
        old = _now() - timedelta(hours=2)
        await repo.record(ip="2.2.2.2", success=False, attempted_at=old)

        # look back only 10 minutes — the old record should not be counted
        since = _now() - timedelta(minutes=10)
        count = await repo.count_failures_since("2.2.2.2", since)
        assert count == 0

    async def test_윈도우_내_기록만_카운트된다(self, db_session: AsyncSession) -> None:
        repo = LoginAttemptRepository(db_session)
        now = _now()
        old = now - timedelta(hours=2)

        await repo.record(ip="3.3.3.3", success=False, attempted_at=old)
        await repo.record(ip="3.3.3.3", success=False, attempted_at=now - timedelta(minutes=5))
        await repo.record(ip="3.3.3.3", success=False, attempted_at=now)

        since = now - timedelta(minutes=10)
        count = await repo.count_failures_since("3.3.3.3", since)
        assert count == 2  # old record excluded

    async def test_ip_None이면_모든_IP_합산_카운트된다(self, db_session: AsyncSession) -> None:
        repo = LoginAttemptRepository(db_session)
        now = _now()
        await repo.record(ip="4.4.4.1", success=False, attempted_at=now)
        await repo.record(ip="4.4.4.2", success=False, attempted_at=now)
        await repo.record(ip="4.4.4.3", success=False, attempted_at=now)

        global_count = await repo.count_failures_since(None, now - timedelta(seconds=1))
        assert global_count >= 3

    async def test_성공_기록은_카운트에서_제외된다(self, db_session: AsyncSession) -> None:
        repo = LoginAttemptRepository(db_session)
        now = _now()
        await repo.record(ip="5.5.5.5", success=False, attempted_at=now)
        await repo.record(ip="5.5.5.5", success=True, attempted_at=now)
        await repo.record(ip="5.5.5.5", success=False, attempted_at=now)

        count = await repo.count_failures_since("5.5.5.5", now - timedelta(seconds=1))
        assert count == 2  # success row excluded


class TestLoginAttemptRepositoryGetLastFailure:
    async def test_최근_실패_시간을_반환한다(self, db_session: AsyncSession) -> None:
        repo = LoginAttemptRepository(db_session)
        now = _now()
        earlier = now - timedelta(minutes=3)

        await repo.record(ip="6.6.6.6", success=False, attempted_at=earlier)
        await repo.record(ip="6.6.6.6", success=False, attempted_at=now)

        last = await repo.get_last_failure("6.6.6.6", now - timedelta(minutes=10))
        assert last is not None
        # Should be the more recent timestamp (within a 1-second tolerance)
        assert abs((last - now).total_seconds()) < 2

    async def test_기록_없으면_None을_반환한다(self, db_session: AsyncSession) -> None:
        repo = LoginAttemptRepository(db_session)
        now = _now()

        last = await repo.get_last_failure("7.7.7.7", now - timedelta(minutes=10))
        assert last is None

    async def test_성공_기록은_반환하지_않는다(self, db_session: AsyncSession) -> None:
        repo = LoginAttemptRepository(db_session)
        now = _now()
        await repo.record(ip="8.8.8.8", success=True, attempted_at=now)

        last = await repo.get_last_failure("8.8.8.8", now - timedelta(minutes=10))
        assert last is None


class TestLoginAttemptRepositoryPurgeOlderThan:
    async def test_오래된_기록을_삭제한다(self, db_session: AsyncSession) -> None:
        repo = LoginAttemptRepository(db_session)
        now = _now()
        old = now - timedelta(days=100)
        recent = now - timedelta(days=30)

        await repo.record(ip="9.9.9.1", success=False, attempted_at=old)
        await repo.record(ip="9.9.9.2", success=False, attempted_at=recent)

        cutoff = now - timedelta(days=90)
        deleted = await repo.purge_older_than(cutoff)

        assert deleted == 1

    async def test_cutoff_이후_기록은_유지된다(self, db_session: AsyncSession) -> None:
        repo = LoginAttemptRepository(db_session)
        now = _now()

        await repo.record(ip="9.9.9.9", success=False, attempted_at=now)

        cutoff = now - timedelta(days=90)
        deleted = await repo.purge_older_than(cutoff)

        assert deleted == 0

    async def test_모두_오래되면_전부_삭제된다(self, db_session: AsyncSession) -> None:
        repo = LoginAttemptRepository(db_session)
        old_base = _now() - timedelta(days=200)

        for i in range(3):
            await repo.record(
                ip=f"10.10.10.{i}",
                success=False,
                attempted_at=old_base - timedelta(days=i),
            )

        cutoff = _now() - timedelta(days=90)
        deleted = await repo.purge_older_than(cutoff)

        assert deleted == 3
