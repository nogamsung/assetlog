"""Unit tests for LoginRateLimiter."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.exceptions import TooManyAttemptsError
from app.services.login_rate_limiter import LoginRateLimiter


def _make_limiter(max_attempts: int = 5, lockout_seconds: int = 600) -> LoginRateLimiter:
    return LoginRateLimiter(max_attempts=max_attempts, lockout_seconds=lockout_seconds)


class TestLoginRateLimiterCheck:
    async def test_새_IP는_차단하지_않는다(self) -> None:
        limiter = _make_limiter()
        await limiter.check("1.2.3.4")  # should not raise

    async def test_락아웃_전_실패는_차단하지_않는다(self) -> None:
        limiter = _make_limiter(max_attempts=5)
        for _ in range(4):
            await limiter.record_failure("1.2.3.4")
        await limiter.check("1.2.3.4")  # should not raise

    async def test_최대_시도_초과하면_TooManyAttemptsError를_던진다(self) -> None:
        limiter = _make_limiter(max_attempts=3, lockout_seconds=60)
        for _ in range(3):
            await limiter.record_failure("1.2.3.4")
        with pytest.raises(TooManyAttemptsError) as exc_info:
            await limiter.check("1.2.3.4")
        assert exc_info.value.retry_after_seconds > 0

    async def test_retry_after_seconds가_잠금_시간과_일치한다(self) -> None:
        limiter = _make_limiter(max_attempts=2, lockout_seconds=300)
        for _ in range(2):
            await limiter.record_failure("10.0.0.1")
        with pytest.raises(TooManyAttemptsError) as exc_info:
            await limiter.check("10.0.0.1")
        # Should be close to 300s (allow a few seconds drift)
        assert 295 <= exc_info.value.retry_after_seconds <= 301


class TestLoginRateLimiterRecordFailure:
    async def test_실패_카운터가_증가한다(self) -> None:
        limiter = _make_limiter(max_attempts=5)
        await limiter.record_failure("2.2.2.2")
        await limiter.record_failure("2.2.2.2")
        state = limiter._states.get("2.2.2.2")
        assert state is not None
        assert state.failure_count == 2

    async def test_최대_시도_도달_시_locked_until이_설정된다(self) -> None:
        limiter = _make_limiter(max_attempts=3, lockout_seconds=120)
        for _ in range(3):
            await limiter.record_failure("3.3.3.3")
        state = limiter._states.get("3.3.3.3")
        assert state is not None
        assert state.locked_until is not None


class TestLoginRateLimiterRecordSuccess:
    async def test_성공_시_카운터가_리셋된다(self) -> None:
        limiter = _make_limiter(max_attempts=5)
        for _ in range(3):
            await limiter.record_failure("4.4.4.4")
        await limiter.record_success("4.4.4.4")
        assert "4.4.4.4" not in limiter._states

    async def test_기록_없는_IP는_성공_시_오류_없이_통과한다(self) -> None:
        limiter = _make_limiter()
        await limiter.record_success("9.9.9.9")  # should not raise

    async def test_성공_후_다시_로그인_시도가_가능하다(self) -> None:
        limiter = _make_limiter(max_attempts=3, lockout_seconds=60)
        for _ in range(3):
            await limiter.record_failure("5.5.5.5")
        await limiter.record_success("5.5.5.5")
        await limiter.check("5.5.5.5")  # should not raise after reset


class TestLoginRateLimiterLockoutExpiry:
    async def test_잠금_만료_후_재시도가_가능하다(self) -> None:
        limiter = _make_limiter(max_attempts=2, lockout_seconds=10)
        for _ in range(2):
            await limiter.record_failure("6.6.6.6")

        # Simulate lockout expiry by manipulating state directly
        now = datetime.now(UTC)
        state = limiter._states["6.6.6.6"]
        state.locked_until = now - timedelta(seconds=1)  # expired

        await limiter.check("6.6.6.6")  # should not raise — lockout expired

    async def test_잠금_중에는_TooManyAttemptsError를_던진다(self) -> None:
        limiter = _make_limiter(max_attempts=2, lockout_seconds=600)
        for _ in range(2):
            await limiter.record_failure("7.7.7.7")
        with pytest.raises(TooManyAttemptsError):
            await limiter.check("7.7.7.7")


class TestLoginRateLimiterEviction:
    async def test_비활성_IP가_정리된다(self) -> None:
        limiter = _make_limiter()
        ip = "8.8.8.8"
        await limiter.record_failure(ip)

        # Force the last_seen to be older than TTL
        state = limiter._states[ip]
        state.last_seen = datetime.now(UTC) - timedelta(seconds=1900)

        # Trigger eviction via any record call
        await limiter.record_failure("new-ip")
        assert ip not in limiter._states

    async def test_다른_IP의_상태는_영향받지_않는다(self) -> None:
        limiter = _make_limiter(max_attempts=5)
        await limiter.record_failure("a.a.a.a")
        await limiter.record_failure("b.b.b.b")
        await limiter.record_success("a.a.a.a")
        assert "b.b.b.b" in limiter._states
