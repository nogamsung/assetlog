"""Unit tests for FawazCurrencyApiAdapter and ChainedFxAdapter — httpx mocked."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.adapters.fx import (
    ChainedFxAdapter,
    FawazCurrencyApiAdapter,
    FrankfurterAdapter,
)
from app.exceptions import FxFetchError


def _mock_response(json_data: dict[str, object], status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    return resp


def _mock_client(*responses: MagicMock | Exception) -> AsyncMock:
    """Build a mock AsyncClient that yields *responses* in sequence on .get()."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    side_effect: list[MagicMock | Exception] = list(responses)
    client.get = AsyncMock(side_effect=side_effect)
    return client


class TestFawazCurrencyApiAdapterFetchRates:
    @pytest.fixture()
    def adapter(self) -> FawazCurrencyApiAdapter:
        return FawazCurrencyApiAdapter()

    async def test_정상_응답_파싱_및_KRW_대문자_키(self, adapter: FawazCurrencyApiAdapter) -> None:
        payload = {"date": "2026-04-27", "usd": {"krw": 1470.31, "eur": 0.92}}
        client = _mock_client(_mock_response(payload))

        with patch("app.adapters.fx.httpx.AsyncClient", return_value=client):
            rates = await adapter.fetch_rates("USD", ["KRW", "EUR"])

        assert rates["KRW"] == Decimal("1470.31")
        assert rates["EUR"] == Decimal("0.92")
        assert isinstance(rates["KRW"], Decimal)

    async def test_빈_quotes_빈_dict_반환(self, adapter: FawazCurrencyApiAdapter) -> None:
        rates = await adapter.fetch_rates("USD", [])
        assert rates == {}

    async def test_jsdelivr_실패_시_pages_dev_미러로_폴백(
        self, adapter: FawazCurrencyApiAdapter
    ) -> None:
        payload = {"date": "2026-04-27", "usd": {"krw": 1470.31}}
        client = _mock_client(
            httpx.RequestError("jsDelivr down"),
            _mock_response(payload),
        )

        with patch("app.adapters.fx.httpx.AsyncClient", return_value=client):
            rates = await adapter.fetch_rates("USD", ["KRW"])

        assert rates == {"KRW": Decimal("1470.31")}
        assert client.get.await_count == 2

    async def test_두_미러_모두_실패_시_FxFetchError(
        self, adapter: FawazCurrencyApiAdapter
    ) -> None:
        client = _mock_client(
            httpx.RequestError("jsDelivr down"),
            httpx.RequestError("Cloudflare down"),
        )

        with patch("app.adapters.fx.httpx.AsyncClient", return_value=client):
            with pytest.raises(FxFetchError, match="unavailable on all mirrors"):
                await adapter.fetch_rates("USD", ["KRW"])

    async def test_누락된_quote_는_조용히_제외(self, adapter: FawazCurrencyApiAdapter) -> None:
        payload = {"date": "2026-04-27", "usd": {"krw": 1470.31}}  # no EUR
        client = _mock_client(_mock_response(payload))

        with patch("app.adapters.fx.httpx.AsyncClient", return_value=client):
            rates = await adapter.fetch_rates("USD", ["KRW", "EUR"])

        assert rates == {"KRW": Decimal("1470.31")}

    async def test_base_키_누락_시_미러로_재시도_후_실패(
        self, adapter: FawazCurrencyApiAdapter
    ) -> None:
        payload = {"date": "2026-04-27"}  # no "usd" key
        client = _mock_client(_mock_response(payload), _mock_response(payload))

        with patch("app.adapters.fx.httpx.AsyncClient", return_value=client):
            with pytest.raises(FxFetchError):
                await adapter.fetch_rates("USD", ["KRW"])

    async def test_숫자_아닌_rate_FxFetchError(self, adapter: FawazCurrencyApiAdapter) -> None:
        payload = {"date": "2026-04-27", "usd": {"krw": "not_a_number"}}
        client = _mock_client(_mock_response(payload))

        with patch("app.adapters.fx.httpx.AsyncClient", return_value=client):
            with pytest.raises(FxFetchError, match="non-numeric rate"):
                await adapter.fetch_rates("USD", ["KRW"])

    async def test_HTTP_500_은_미러로_폴백(self, adapter: FawazCurrencyApiAdapter) -> None:
        payload = {"date": "2026-04-27", "usd": {"krw": 1470.31}}
        client = _mock_client(
            _mock_response({}, status_code=500),
            _mock_response(payload),
        )

        with patch("app.adapters.fx.httpx.AsyncClient", return_value=client):
            rates = await adapter.fetch_rates("USD", ["KRW"])

        assert rates == {"KRW": Decimal("1470.31")}


class TestChainedFxAdapter:
    async def test_빈_어댑터_리스트는_생성_시_거부(self) -> None:
        with pytest.raises(ValueError, match="at least one adapter"):
            ChainedFxAdapter([])

    async def test_1차_어댑터_성공_시_2차_미호출(self) -> None:
        primary = AsyncMock(spec=FrankfurterAdapter)
        primary.fetch_rates = AsyncMock(return_value={"KRW": Decimal("1380.25")})
        secondary = AsyncMock(spec=FawazCurrencyApiAdapter)
        secondary.fetch_rates = AsyncMock()

        chained = ChainedFxAdapter([primary, secondary])
        rates = await chained.fetch_rates("USD", ["KRW"])

        assert rates == {"KRW": Decimal("1380.25")}
        primary.fetch_rates.assert_awaited_once_with("USD", ["KRW"])
        secondary.fetch_rates.assert_not_awaited()

    async def test_1차_FxFetchError_시_2차로_폴백(self) -> None:
        primary = AsyncMock(spec=FrankfurterAdapter)
        primary.fetch_rates = AsyncMock(side_effect=FxFetchError("Frankfurter down"))
        secondary = AsyncMock(spec=FawazCurrencyApiAdapter)
        secondary.fetch_rates = AsyncMock(return_value={"KRW": Decimal("1470.31")})

        chained = ChainedFxAdapter([primary, secondary])
        rates = await chained.fetch_rates("USD", ["KRW"])

        assert rates == {"KRW": Decimal("1470.31")}
        primary.fetch_rates.assert_awaited_once()
        secondary.fetch_rates.assert_awaited_once()

    async def test_모든_어댑터_실패_시_마지막_에러_전파(self) -> None:
        primary = AsyncMock(spec=FrankfurterAdapter)
        primary.fetch_rates = AsyncMock(side_effect=FxFetchError("Frankfurter down"))
        secondary = AsyncMock(spec=FawazCurrencyApiAdapter)
        secondary.fetch_rates = AsyncMock(side_effect=FxFetchError("fawaz down"))

        chained = ChainedFxAdapter([primary, secondary])
        with pytest.raises(FxFetchError, match="fawaz down"):
            await chained.fetch_rates("USD", ["KRW"])

    async def test_FxFetchError_가_아닌_예외는_즉시_전파(self) -> None:
        """체인은 FxFetchError만 폴백 트리거 — 그 외는 버그로 간주하고 즉시 raise."""
        primary = AsyncMock(spec=FrankfurterAdapter)
        primary.fetch_rates = AsyncMock(side_effect=RuntimeError("bug"))
        secondary = AsyncMock(spec=FawazCurrencyApiAdapter)
        secondary.fetch_rates = AsyncMock(return_value={"KRW": Decimal("1470.31")})

        chained = ChainedFxAdapter([primary, secondary])
        with pytest.raises(RuntimeError, match="bug"):
            await chained.fetch_rates("USD", ["KRW"])

        secondary.fetch_rates.assert_not_awaited()
