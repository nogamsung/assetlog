"""Tests for login_attempt_cleanup_job scheduler job."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.scheduler.login_attempt_cleanup_job import login_attempt_cleanup_job

# patch target: the lazy-imported class lives at its canonical module path
_REPO_PATCH = "app.repositories.login_attempt.LoginAttemptRepository"


class TestLoginAttemptCleanupJob:
    async def test_오래된_기록을_삭제하고_삭제_수를_반환한다(self) -> None:
        """Job should call purge_older_than with the correct cutoff and return the count."""
        mock_repo = AsyncMock()
        mock_repo.purge_older_than.return_value = 42

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        mock_session_factory = MagicMock()
        mock_session_factory.return_value = mock_session

        # Patch the class inside its own module (lazy import resolves to this path)
        with patch(_REPO_PATCH, return_value=mock_repo):
            result = await login_attempt_cleanup_job(
                session_factory=mock_session_factory,
                retention_days=90,
            )

        assert result == 42
        mock_repo.purge_older_than.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    async def test_cutoff가_retention_days_만큼_과거이다(self) -> None:
        """The cutoff passed to purge_older_than must be ~retention_days ago."""
        captured_cutoff: list[datetime] = []
        mock_repo = AsyncMock()

        async def _capture(cutoff: datetime) -> int:  # type: ignore[misc]
            captured_cutoff.append(cutoff)
            return 0

        mock_repo.purge_older_than.side_effect = _capture

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session_factory = MagicMock(return_value=mock_session)

        before = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=90)
        with patch(_REPO_PATCH, return_value=mock_repo):
            await login_attempt_cleanup_job(
                session_factory=mock_session_factory,
                retention_days=90,
            )
        after = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=90)

        assert len(captured_cutoff) == 1
        # Allow a few seconds of drift
        assert before - timedelta(seconds=5) <= captured_cutoff[0] <= after + timedelta(seconds=5)

    async def test_예외_발생시_0을_반환한다(self) -> None:
        """Job must log the error and return 0 without propagating."""
        mock_session = AsyncMock()
        mock_session.__aenter__.side_effect = RuntimeError("DB down")
        mock_session.__aexit__.return_value = None
        mock_session_factory = MagicMock(return_value=mock_session)

        result = await login_attempt_cleanup_job(
            session_factory=mock_session_factory,
            retention_days=90,
        )

        assert result == 0

    async def test_cleanup_job이_스케줄러에_등록된다(self) -> None:
        """build_scheduler must register login_attempt_cleanup_daily job."""
        from app.adapters import AdapterRegistry  # noqa: PLC0415
        from app.main import _make_session_factory  # noqa: PLC0415
        from app.scheduler import build_scheduler  # noqa: PLC0415

        session_factory = _make_session_factory("sqlite+aiosqlite:///:memory:")
        mock_registry = MagicMock(spec=AdapterRegistry)

        scheduler = build_scheduler(session_factory, mock_registry, login_attempt_retention_days=90)
        job_ids = {j.id for j in scheduler.get_jobs()}

        assert "login_attempt_cleanup_daily" in job_ids
