"""Router tests for GET /api/fx/rates."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_fx_rate_service
from app.core.principal import OwnerPrincipal
from app.main import app
from app.models.fx_rate import FxRate
from app.services.fx_rate import FxRateService


def _make_owner() -> OwnerPrincipal:
    return OwnerPrincipal()


def _make_fx_rate(
    base: str = "USD",
    quote: str = "KRW",
    rate: str = "1380.25000000",
) -> FxRate:
    row = FxRate(
        base_currency=base,
        quote_currency=quote,
        rate=Decimal(rate),
        fetched_at=datetime(2026, 4, 24, 9, 0, 0, tzinfo=UTC),
    )
    return row


class TestGetFxRates:
    async def test_미인증_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/fx/rates")
        assert response.status_code == 401

    async def test_정상_200_반환(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_svc = AsyncMock(spec=FxRateService)
        mock_svc.list_all_rates.return_value = [
            _make_fx_rate("USD", "KRW", "1380.25000000"),
            _make_fx_rate("USD", "EUR", "0.92000000"),
        ]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_fx_rate_service] = lambda: mock_svc

        try:
            response = await async_client.get("/api/fx/rates")
            assert response.status_code == 200
            body = response.json()
            assert "rates" in body
            assert len(body["rates"]) == 2
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_fx_rate_service, None)

    async def test_빈_rates_빈_배열(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_svc = AsyncMock(spec=FxRateService)
        mock_svc.list_all_rates.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_fx_rate_service] = lambda: mock_svc

        try:
            response = await async_client.get("/api/fx/rates")
            assert response.status_code == 200
            assert response.json()["rates"] == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_fx_rate_service, None)

    async def test_contract_응답_키_일치(self, async_client: AsyncClient) -> None:
        """Each rate entry must contain base, quote, rate, fetched_at."""
        user = _make_owner()
        mock_svc = AsyncMock(spec=FxRateService)
        mock_svc.list_all_rates.return_value = [_make_fx_rate()]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_fx_rate_service] = lambda: mock_svc

        try:
            response = await async_client.get("/api/fx/rates")
            entry = response.json()["rates"][0]
            required_keys = {"base", "quote", "rate", "fetched_at"}
            assert required_keys.issubset(set(entry.keys()))
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_fx_rate_service, None)

    async def test_rate_필드_문자열_직렬화(self, async_client: AsyncClient) -> None:
        """rate must be serialised as a string (Decimal → str)."""
        user = _make_owner()
        mock_svc = AsyncMock(spec=FxRateService)
        mock_svc.list_all_rates.return_value = [_make_fx_rate("USD", "KRW", "1380.25000000")]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_fx_rate_service] = lambda: mock_svc

        try:
            response = await async_client.get("/api/fx/rates")
            entry = response.json()["rates"][0]
            assert isinstance(entry["rate"], str)
            assert entry["base"] == "USD"
            assert entry["quote"] == "KRW"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_fx_rate_service, None)
