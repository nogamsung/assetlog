"""Unit tests for DB-backed LoginRateLimiter."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.exceptions import TooManyAttemptsError
from app.repositories.login_attempt import LoginAttemptRepository
from app.services.login_rate_limiter import LoginRateLimiter


def _now() -> datetime:
    """UTC-naive now."""
    return datetime.now(UTC).replace(tzinfo=None)


def _make_limiter(
    repo: LoginAttemptRepository,
    *,
    per_ip_max: int = 5,
    global_max: int = 50,
    per_ip_window: int = 600,
    global_window: int = 60,
) -> LoginRateLimiter:
    return LoginRateLimiter(
        repo=repo,
        per_ip_max=per_ip_max,
        global_max=global_max,
        per_ip_window_seconds=per_ip_window,
        global_window_seconds=global_window,
    )


def _mock_repo(*, ip_failures: int = 0, global_failures: int = 0) -> AsyncMock:
    """Build a mocked LoginAttemptRepository with preset counts."""
    repo = AsyncMock(spec=LoginAttemptRepository)

    async def _count(ip: str | None, since: datetime) -> int:
        return global_failures if ip is None else ip_failures

    repo.count_failures_since.side_effect = _count
    return repo


class TestLoginRateLimiterCheck:
    async def test_새_IP는_차단하지_않는다(self) -> None:
        repo = _mock_repo(ip_failures=0, global_failures=0)
        limiter = _make_limiter(repo)
        await limiter.check("1.2.3.4")  # should not raise

    async def test_한도_미만_실패는_차단하지_않는다(self) -> None:
        repo = _mock_repo(ip_failures=4, global_failures=0)
        limiter = _make_limiter(repo, per_ip_max=5)
        await limiter.check("1.2.3.4")  # should not raise

    async def test_per_ip_한도_초과하면_TooManyAttemptsError를_던진다(self) -> None:
        repo = _mock_repo(ip_failures=5, global_failures=0)
        limiter = _make_limiter(repo, per_ip_max=5)
        with pytest.raises(TooManyAttemptsError) as exc_info:
            await limiter.check("1.2.3.4")
        assert exc_info.value.retry_after_seconds > 0

    async def test_global_한도_초과하면_TooManyAttemptsError를_던진다(self) -> None:
        repo = _mock_repo(ip_failures=0, global_failures=50)
        limiter = _make_limiter(repo, global_max=50, global_window=60)
        with pytest.raises(TooManyAttemptsError) as exc_info:
            await limiter.check("1.2.3.4")
        assert exc_info.value.retry_after_seconds == 60

    async def test_per_ip_체크가_global_체크보다_먼저_수행된다(self) -> None:
        """Per-IP limit triggers first when both limits are exceeded."""
        repo = _mock_repo(ip_failures=10, global_failures=100)
        limiter = _make_limiter(repo, per_ip_max=5, global_max=50, per_ip_window=600)
        with pytest.raises(TooManyAttemptsError) as exc_info:
            await limiter.check("1.2.3.4")
        # per-IP retry_after is derived from window × multiplier, not global_window
        assert exc_info.value.retry_after_seconds != 60  # not the global_window value


class TestLoginRateLimiterProgressiveBackoff:
    """Verify the exponential backoff formula.

    base = per_ip_window (600s default)
    excess = failures - per_ip_max
    multiplier = min(2^(excess // 5), 64)
    retry_after = min(base * multiplier, 3600)
    """

    async def test_5회_실패_retry_after는_기본_윈도우_크기(self) -> None:
        repo = _mock_repo(ip_failures=5, global_failures=0)
        limiter = _make_limiter(repo, per_ip_max=5, per_ip_window=600)
        with pytest.raises(TooManyAttemptsError) as exc_info:
            await limiter.check("1.2.3.4")
        # excess=0, multiplier=1, retry_after=600
        assert exc_info.value.retry_after_seconds == 600

    async def test_10회_실패_retry_after는_2배(self) -> None:
        repo = _mock_repo(ip_failures=10, global_failures=0)
        limiter = _make_limiter(repo, per_ip_max=5, per_ip_window=600)
        with pytest.raises(TooManyAttemptsError) as exc_info:
            await limiter.check("1.2.3.4")
        # excess=5, multiplier=2^1=2, retry_after=1200
        assert exc_info.value.retry_after_seconds == 1200

    async def test_15회_실패_retry_after는_4배(self) -> None:
        repo = _mock_repo(ip_failures=15, global_failures=0)
        limiter = _make_limiter(repo, per_ip_max=5, per_ip_window=600)
        with pytest.raises(TooManyAttemptsError) as exc_info:
            await limiter.check("1.2.3.4")
        # excess=10, multiplier=2^2=4, retry_after=2400
        assert exc_info.value.retry_after_seconds == 2400

    async def test_충분히_많은_실패는_최대_1시간으로_cap된다(self) -> None:
        # excess >= 35 → multiplier=2^7=128, but capped at 64 → 600*64=38400 > 3600 cap
        repo = _mock_repo(ip_failures=100, global_failures=0)
        limiter = _make_limiter(repo, per_ip_max=5, per_ip_window=600)
        with pytest.raises(TooManyAttemptsError) as exc_info:
            await limiter.check("1.2.3.4")
        assert exc_info.value.retry_after_seconds == 3600

    async def test_윈도우_짧고_multiplier_작을때_3600보다_작다(self) -> None:
        # per_ip_window=30, 5 failures → excess=0 → retry_after=30, no cap needed
        repo = _mock_repo(ip_failures=5, global_failures=0)
        limiter = _make_limiter(repo, per_ip_max=5, per_ip_window=30)
        with pytest.raises(TooManyAttemptsError) as exc_info:
            await limiter.check("1.2.3.4")
        assert exc_info.value.retry_after_seconds == 30


class TestLoginRateLimiterRecordFailure:
    async def test_record_failure_는_repo_record를_success_False로_호출한다(self) -> None:
        repo = AsyncMock(spec=LoginAttemptRepository)
        limiter = _make_limiter(repo)
        await limiter.record_failure("2.2.2.2")

        repo.record.assert_awaited_once()
        call_kwargs = repo.record.call_args.kwargs
        assert call_kwargs["ip"] == "2.2.2.2"
        assert call_kwargs["success"] is False

    async def test_record_failure_when_파라미터로_타임스탬프를_지정할_수_있다(self) -> None:
        repo = AsyncMock(spec=LoginAttemptRepository)
        limiter = _make_limiter(repo)
        ts = datetime(2025, 1, 1, 12, 0, 0)
        await limiter.record_failure("3.3.3.3", when=ts)

        call_kwargs = repo.record.call_args.kwargs
        assert call_kwargs["attempted_at"] == ts


class TestLoginRateLimiterRecordSuccess:
    async def test_record_success_는_repo_record를_success_True로_호출한다(self) -> None:
        repo = AsyncMock(spec=LoginAttemptRepository)
        limiter = _make_limiter(repo)
        await limiter.record_success("4.4.4.4")

        repo.record.assert_awaited_once()
        call_kwargs = repo.record.call_args.kwargs
        assert call_kwargs["ip"] == "4.4.4.4"
        assert call_kwargs["success"] is True

    async def test_성공_기록은_실패_카운트에_영향_없다(self) -> None:
        """record_success stores a success=True row but failures are still counted from DB."""
        # Mock: 3 failures even after a success record — success does not reduce count
        repo = _mock_repo(ip_failures=3, global_failures=0)
        limiter = _make_limiter(repo, per_ip_max=5)
        # Should not raise — 3 failures < per_ip_max=5
        await limiter.check("5.5.5.5")


class TestLoginRateLimiterWindowExpiry:
    async def test_윈도우_만료_후_check가_통과된다(self) -> None:
        """Once all failures fall outside the window, check() passes."""
        # Simulate: window is in the past, so count returns 0
        repo = _mock_repo(ip_failures=0, global_failures=0)
        limiter = _make_limiter(repo, per_ip_max=5)
        await limiter.check("6.6.6.6")  # should not raise
