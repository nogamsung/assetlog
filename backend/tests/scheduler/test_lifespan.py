"""Tests for scheduler lifespan integration — no real cron waiting."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import AdapterRegistry
from app.core.config import Settings
from app.main import _make_session_factory, lifespan
from app.scheduler import build_scheduler


def _make_test_settings(enable_scheduler: bool) -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        jwt_secret_key="test-secret",
        enable_scheduler=enable_scheduler,
    )


class TestSchedulerLifespan:
    async def test_scheduler_started_when_enabled(
        self,
        db_session: AsyncSession,
    ) -> None:
        """When enable_scheduler=True, lifespan must call scheduler.start()."""
        started = False
        stopped = False

        class FakeScheduler:
            def add_job(self, *args: object, **kwargs: object) -> None:
                pass

            def start(self) -> None:
                nonlocal started
                started = True

            def shutdown(self, wait: bool = True) -> None:
                nonlocal stopped
                stopped = True

            def get_jobs(self) -> list[object]:
                return []

        fake = FakeScheduler()
        test_settings = _make_test_settings(enable_scheduler=True)

        from fastapi import FastAPI

        dummy_app = FastAPI()
        with (
            patch("app.main.settings", test_settings),
            patch("app.main.build_scheduler", return_value=fake),
            patch("app.main.build_default_adapter_registry", return_value=MagicMock()),
        ):
            async with lifespan(dummy_app):
                assert started, "scheduler.start() was not called during lifespan startup"

        assert stopped, "scheduler.shutdown() was not called during lifespan teardown"

    async def test_scheduler_not_started_when_disabled(
        self,
        db_session: AsyncSession,
    ) -> None:
        """When enable_scheduler=False, scheduler must not be started."""
        start_called = False

        class FakeScheduler:
            def add_job(self, *args: object, **kwargs: object) -> None:
                pass

            def start(self) -> None:
                nonlocal start_called
                start_called = True

            def shutdown(self, wait: bool = True) -> None:
                pass

        fake = FakeScheduler()
        test_settings = _make_test_settings(enable_scheduler=False)

        from fastapi import FastAPI

        dummy_app = FastAPI()
        with (
            patch("app.main.settings", test_settings),
            patch("app.main.build_scheduler", return_value=fake),
            patch("app.main.build_default_adapter_registry", return_value=MagicMock()),
        ):
            async with lifespan(dummy_app):
                pass

        assert not start_called, (
            "scheduler.start() should NOT be called when enable_scheduler=False"
        )

    async def test_job_registered_with_correct_id(
        self,
        db_session: AsyncSession,
    ) -> None:
        """build_scheduler must register both price_refresh and fx_refresh jobs."""
        session_factory = _make_session_factory("sqlite+aiosqlite:///:memory:")
        mock_registry = MagicMock(spec=AdapterRegistry)

        scheduler = build_scheduler(session_factory, mock_registry)
        jobs = scheduler.get_jobs()

        assert len(jobs) == 2  # price_refresh_hourly + fx_refresh_hourly
        job_ids = {j.id for j in jobs}
        assert "price_refresh_hourly" in job_ids
        assert "fx_refresh_hourly" in job_ids
        # Verify scheduler is not running yet — start() has not been called
        assert not scheduler.running

    async def test_scheduler_builds_with_all_required_kwargs(
        self,
        db_session: AsyncSession,
    ) -> None:
        """build_scheduler must configure max_instances=1 and coalesce=True for both jobs."""
        session_factory = _make_session_factory("sqlite+aiosqlite:///:memory:")
        mock_registry = MagicMock(spec=AdapterRegistry)

        scheduler = build_scheduler(session_factory, mock_registry)
        jobs = scheduler.get_jobs()

        assert len(jobs) == 2
        for job in jobs:
            assert job.max_instances == 1
            assert job.coalesce is True

    async def test_build_scheduler_called_when_enabled(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Lifespan must call build_scheduler when enable_scheduler=True."""
        test_settings = _make_test_settings(enable_scheduler=True)

        mock_scheduler = MagicMock()
        mock_scheduler.start = MagicMock()
        mock_scheduler.shutdown = MagicMock()

        from fastapi import FastAPI

        dummy_app = FastAPI()
        with (
            patch("app.main.settings", test_settings),
            patch("app.main.build_scheduler", return_value=mock_scheduler) as mock_build,
            patch("app.main.build_default_adapter_registry", return_value=MagicMock()),
        ):
            async with lifespan(dummy_app):
                mock_build.assert_called_once()
                mock_scheduler.start.assert_called_once()

        mock_scheduler.shutdown.assert_called_once_with(wait=False)

    async def test_build_scheduler_not_called_when_disabled(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Lifespan must NOT call build_scheduler when enable_scheduler=False."""
        test_settings = _make_test_settings(enable_scheduler=False)

        from fastapi import FastAPI

        dummy_app = FastAPI()
        with (
            patch("app.main.settings", test_settings),
            patch("app.main.build_scheduler") as mock_build,
            patch("app.main.build_default_adapter_registry", return_value=MagicMock()),
        ):
            async with lifespan(dummy_app):
                mock_build.assert_not_called()
