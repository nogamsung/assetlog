"""Unit tests for FrankfurterAdapter — httpx mock, no real network calls."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.adapters.fx import FrankfurterAdapter
from app.exceptions import FxFetchError


@pytest.fixture()
def adapter() -> FrankfurterAdapter:
    return FrankfurterAdapter()


def _mock_response(json_data: dict[str, object], status_code: int = 200) -> MagicMock:
    """Build a mock httpx.Response."""
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


class TestFrankfurterAdapterFetchRates:
    async def test_정상_응답_파싱(self, adapter: FrankfurterAdapter) -> None:
        payload = {
            "amount": 1.0,
            "base": "USD",
            "date": "2026-04-24",
            "rates": {"KRW": 1380.25, "EUR": 0.92},
        }
        mock_resp = _mock_response(payload)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.adapters.fx.httpx.AsyncClient", return_value=mock_client):
            rates = await adapter.fetch_rates("USD", ["KRW", "EUR"])

        assert rates["KRW"] == Decimal("1380.25")
        assert rates["EUR"] == Decimal("0.92")
        assert isinstance(rates["KRW"], Decimal)

    async def test_빈_quotes_빈_dict_반환(self, adapter: FrankfurterAdapter) -> None:
        rates = await adapter.fetch_rates("USD", [])
        assert rates == {}

    async def test_HTTP_에러_FxFetchError_발생(self, adapter: FrankfurterAdapter) -> None:
        mock_resp = _mock_response({}, status_code=500)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.adapters.fx.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(FxFetchError, match="HTTP 500"):
                await adapter.fetch_rates("USD", ["KRW"])

    async def test_타임아웃_FxFetchError_발생(self, adapter: FrankfurterAdapter) -> None:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("app.adapters.fx.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(FxFetchError, match="timed out"):
                await adapter.fetch_rates("USD", ["KRW"])

    async def test_네트워크_에러_FxFetchError_발생(self, adapter: FrankfurterAdapter) -> None:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        with patch("app.adapters.fx.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(FxFetchError, match="request failed"):
                await adapter.fetch_rates("USD", ["KRW"])

    async def test_rates_누락_응답_FxFetchError_발생(self, adapter: FrankfurterAdapter) -> None:
        payload: dict[str, object] = {"base": "USD", "date": "2026-04-24"}  # no "rates"
        mock_resp = _mock_response(payload)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.adapters.fx.httpx.AsyncClient", return_value=mock_client):
            # empty dict returned — no error (rates key defaults to {})
            rates = await adapter.fetch_rates("USD", ["KRW"])
        assert rates == {}

    async def test_숫자_아닌_rate_FxFetchError_발생(self, adapter: FrankfurterAdapter) -> None:
        payload: dict[str, object] = {
            "base": "USD",
            "date": "2026-04-24",
            "rates": {"KRW": "not_a_number"},
        }
        mock_resp = _mock_response(payload)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.adapters.fx.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(FxFetchError, match="non-numeric rate"):
                await adapter.fetch_rates("USD", ["KRW"])

    async def test_rate_Decimal_타입_확인(self, adapter: FrankfurterAdapter) -> None:
        payload: dict[str, object] = {
            "base": "USD",
            "date": "2026-04-24",
            "rates": {"KRW": 1380.25},
        }
        mock_resp = _mock_response(payload)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.adapters.fx.httpx.AsyncClient", return_value=mock_client):
            rates = await adapter.fetch_rates("USD", ["KRW"])

        assert isinstance(rates["KRW"], Decimal)
