"""Unit tests for IsinResolver — three-tier lookup with mocked OpenFIGI."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.isin_resolver import IsinResolver, looks_like_isin


class TestLooksLikeIsin:
    def test_us_isin_matches(self) -> None:
        assert looks_like_isin("US0079031078") is True

    def test_cayman_isin_matches(self) -> None:
        assert looks_like_isin("KYG651631007") is True

    def test_plain_ticker_does_not_match(self) -> None:
        assert looks_like_isin("AMD") is False
        assert looks_like_isin("GOOGL") is False

    def test_wrong_length_does_not_match(self) -> None:
        assert looks_like_isin("US007903") is False
        assert looks_like_isin("US00790310789") is False


class TestIsinResolver:
    @pytest.mark.asyncio
    async def test_static_map_hit_skips_db_and_openfigi(self) -> None:
        session = AsyncMock()
        resolver = IsinResolver(session)
        with patch(
            "app.services.isin_resolver.fetch_ticker_from_openfigi",
            new=AsyncMock(),
        ) as mocked_fetch:
            result = await resolver.resolve("US0079031078")  # AMD in static map
        assert result == "AMD"
        session.get.assert_not_called()
        mocked_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_db_cache_hit_skips_openfigi(self) -> None:
        from app.models.isin_ticker_cache import IsinTickerCache

        session = AsyncMock()
        session.get.return_value = IsinTickerCache(
            isin="US0000000099", ticker="FOO", source="openfigi"
        )
        resolver = IsinResolver(session)
        with patch(
            "app.services.isin_resolver.fetch_ticker_from_openfigi",
            new=AsyncMock(),
        ) as mocked_fetch:
            result = await resolver.resolve("US0000000099")
        assert result == "FOO"
        mocked_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_openfigi_hit_persists_to_cache(self) -> None:
        session = AsyncMock()
        session.get.return_value = None  # cache miss
        resolver = IsinResolver(session)
        with patch(
            "app.services.isin_resolver.fetch_ticker_from_openfigi",
            new=AsyncMock(return_value="NEWX"),
        ) as mocked_fetch:
            result = await resolver.resolve("US0000000099")
        assert result == "NEWX"
        mocked_fetch.assert_called_once_with("US0000000099")
        # cache row added
        session.add.assert_called_once()
        added = session.add.call_args.args[0]
        assert added.isin == "US0000000099"
        assert added.ticker == "NEWX"

    @pytest.mark.asyncio
    async def test_openfigi_miss_persists_negative_to_cache(self) -> None:
        """Unknown ISINs are remembered as (ticker=None) so we don't re-hit the API."""
        session = AsyncMock()
        session.get.return_value = None
        resolver = IsinResolver(session)
        with patch(
            "app.services.isin_resolver.fetch_ticker_from_openfigi",
            new=AsyncMock(return_value=None),
        ):
            result = await resolver.resolve("US9999999999")
        assert result is None
        added = session.add.call_args.args[0]
        assert added.ticker is None

    @pytest.mark.asyncio
    async def test_db_cache_negative_skips_openfigi(self) -> None:
        from app.models.isin_ticker_cache import IsinTickerCache

        session = AsyncMock()
        session.get.return_value = IsinTickerCache(
            isin="US9999999999", ticker=None, source="openfigi"
        )
        resolver = IsinResolver(session)
        with patch(
            "app.services.isin_resolver.fetch_ticker_from_openfigi",
            new=AsyncMock(),
        ) as mocked_fetch:
            result = await resolver.resolve("US9999999999")
        assert result is None
        mocked_fetch.assert_not_called()
