"""Unit tests for MarketIndexService — TTL cache behavior with stub fetcher."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.schemas.market_index import IndexQuote
from app.services.market_index import IndexSpec, MarketIndexService

pytestmark = pytest.mark.asyncio


def _quote(symbol: str, price: str = "100.00") -> IndexQuote:
    return IndexQuote(
        symbol=symbol,
        name=symbol,
        currency="USD",
        price=Decimal(price),
        change=Decimal("0.00"),
        change_pct=Decimal("0.00"),
        fetched_at=datetime.now(UTC),
    )


def _make_service(
    fetcher_calls: list[int],
    quotes: list[IndexQuote] | None = None,
    raises: Exception | None = None,
    ttl_seconds: int = 300,
) -> MarketIndexService:
    """Build a service with a counting stub fetcher.

    fetcher_calls is a list whose length is incremented on each fetch — used
    by tests to assert call counts without unittest.mock.
    """

    async def _stub(specs: Sequence[IndexSpec]) -> list[IndexQuote]:
        fetcher_calls.append(1)
        if raises is not None:
            raise raises
        return list(quotes or [])

    return MarketIndexService(
        fetcher=_stub,
        specs=[("^TEST", "Test", "USD")],
        ttl_seconds=ttl_seconds,
    )


class TestMarketIndexServiceCache:
    async def test_첫_호출은_fetcher_실행(self) -> None:
        calls: list[int] = []
        svc = _make_service(calls, quotes=[_quote("^TEST")])
        result = await svc.list_indices()
        assert len(result) == 1
        assert len(calls) == 1

    async def test_TTL_안이면_캐시_재사용(self) -> None:
        calls: list[int] = []
        svc = _make_service(calls, quotes=[_quote("^TEST")], ttl_seconds=300)
        await svc.list_indices()
        await svc.list_indices()
        await svc.list_indices()
        assert len(calls) == 1

    async def test_TTL_0이면_매번_재요청(self) -> None:
        calls: list[int] = []
        svc = _make_service(calls, quotes=[_quote("^TEST")], ttl_seconds=0)
        await svc.list_indices()
        await svc.list_indices()
        assert len(calls) == 2

    async def test_fetcher_예외시_빈_리스트(self) -> None:
        calls: list[int] = []
        svc = _make_service(calls, raises=RuntimeError("network down"))
        result = await svc.list_indices()
        assert result == []
        assert len(calls) == 1

    async def test_fetcher_예외여도_이전_캐시_있으면_stale_반환(self) -> None:
        calls: list[int] = []
        # First, prime the cache.
        svc = _make_service(calls, quotes=[_quote("^TEST", "111.00")], ttl_seconds=0)
        primed = await svc.list_indices()
        assert primed[0].price == Decimal("111.00")

        # Now swap the fetcher to raise — service should fall back to cache.
        async def _failing(specs: Sequence[IndexSpec]) -> list[IndexQuote]:
            calls.append(1)
            raise RuntimeError("flaky")

        svc._fetcher = _failing  # type: ignore[assignment]  # test-only override
        result = await svc.list_indices()
        assert result[0].price == Decimal("111.00")
