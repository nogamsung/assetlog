"""Unit tests for KrNameResolver."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.kr_name_resolver import KrNameResolver, looks_like_kr_name


def _async_session_mock() -> AsyncMock:
    """An ``AsyncMock`` session whose ``begin_nested`` works as a savepoint."""
    session = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=None)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.begin_nested = MagicMock(return_value=ctx)
    return session


class TestLooksLikeKrName:
    def test_hangul_string_matches(self) -> None:
        assert looks_like_kr_name("삼성전자") is True

    def test_etf_with_mixed_chars_matches(self) -> None:
        assert looks_like_kr_name("TIGER 미국S&P500배당귀족") is True

    def test_six_digit_code_does_not_match(self) -> None:
        assert looks_like_kr_name("005930") is False

    def test_ascii_only_does_not_match(self) -> None:
        assert looks_like_kr_name("AMD") is False


class TestKrNameResolver:
    @pytest.mark.asyncio
    async def test_db_cache_hit_skips_network(self) -> None:
        from app.models.kr_name_cache import KrNameCache

        session = _async_session_mock()
        session.get.return_value = KrNameCache(name="삼성전자", code="005930", source="naver")
        resolver = KrNameResolver(session)
        with patch(
            "app.services.kr_name_resolver.fetch_kr_code_from_naver",
            new=AsyncMock(),
        ) as mocked:
            result = await resolver.resolve("삼성전자")
        assert result == "005930"
        mocked.assert_not_called()

    @pytest.mark.asyncio
    async def test_naver_hit_persists_to_cache(self) -> None:
        session = _async_session_mock()
        session.get.return_value = None
        resolver = KrNameResolver(session)
        with patch(
            "app.services.kr_name_resolver.fetch_kr_code_from_naver",
            new=AsyncMock(return_value="005930"),
        ):
            result = await resolver.resolve("삼성전자")
        assert result == "005930"
        added = session.add.call_args.args[0]
        assert added.name == "삼성전자"
        assert added.code == "005930"

    @pytest.mark.asyncio
    async def test_naver_miss_persists_negative(self) -> None:
        session = _async_session_mock()
        session.get.return_value = None
        resolver = KrNameResolver(session)
        with patch(
            "app.services.kr_name_resolver.fetch_kr_code_from_naver",
            new=AsyncMock(return_value=None),
        ):
            result = await resolver.resolve("존재하지않는종목명")
        assert result is None
        added = session.add.call_args.args[0]
        assert added.code is None

    @pytest.mark.asyncio
    async def test_db_negative_cache_skips_network(self) -> None:
        from app.models.kr_name_cache import KrNameCache

        session = _async_session_mock()
        session.get.return_value = KrNameCache(name="없는종목", code=None, source="naver")
        resolver = KrNameResolver(session)
        with patch(
            "app.services.kr_name_resolver.fetch_kr_code_from_naver",
            new=AsyncMock(),
        ) as mocked:
            result = await resolver.resolve("없는종목")
        assert result is None
        mocked.assert_not_called()
