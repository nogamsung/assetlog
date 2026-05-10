"""Router tests for /api/dividends/calendar and /api/dividends/yield-on-cost."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_dividend_service
from app.core.principal import OwnerPrincipal
from app.main import app
from app.schemas.dividend import (
    DividendCalendarEntry,
    DividendCalendarResponse,
    YieldOnCostEntry,
    YieldOnCostResponse,
)
from app.services.dividend import DividendService


def _make_calendar() -> DividendCalendarResponse:
    return DividendCalendarResponse(
        entries=[
            DividendCalendarEntry(
                asset_symbol_id=7,
                symbol="AAPL",
                name="Apple Inc.",
                ex_date=date(2026, 5, 9),
                amount=Decimal("0.25"),
                currency="USD",
            )
        ]
    )


def _make_yoc() -> YieldOnCostResponse:
    return YieldOnCostResponse(
        entries=[
            YieldOnCostEntry(
                asset_symbol_id=7,
                symbol="AAPL",
                name="Apple Inc.",
                currency="USD",
                cost_basis=Decimal("1705"),
                total_dividend=Decimal("49.20"),
                yield_on_cost_pct=Decimal("0.0289"),
            )
        ]
    )


class TestCalendarEndpoint:
    async def test_미인증_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/dividends/calendar")
        assert response.status_code == 401

    async def test_정상_200(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=DividendService)
        mock_svc.get_calendar.return_value = _make_calendar()

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_dividend_service] = lambda: mock_svc
        try:
            response = await async_client.get(
                "/api/dividends/calendar?from=2026-01-01&to=2026-12-31"
            )
            assert response.status_code == 200
            body = response.json()
            assert body["entries"][0]["symbol"] == "AAPL"
            assert body["entries"][0]["amount"] == "0.25"
            mock_svc.get_calendar.assert_awaited_once_with(
                date_from=date(2026, 1, 1),
                date_to=date(2026, 12, 31),
            )
        finally:
            app.dependency_overrides.clear()

    async def test_필터_없으면_None_전달(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=DividendService)
        mock_svc.get_calendar.return_value = DividendCalendarResponse()

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_dividend_service] = lambda: mock_svc
        try:
            response = await async_client.get("/api/dividends/calendar")
            assert response.status_code == 200
            mock_svc.get_calendar.assert_awaited_once_with(
                date_from=None,
                date_to=None,
            )
        finally:
            app.dependency_overrides.clear()


class TestYieldOnCostEndpoint:
    async def test_미인증_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/dividends/yield-on-cost")
        assert response.status_code == 401

    async def test_정상_200_응답구조(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=DividendService)
        mock_svc.get_yield_on_cost.return_value = _make_yoc()

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_dividend_service] = lambda: mock_svc
        try:
            response = await async_client.get("/api/dividends/yield-on-cost")
            assert response.status_code == 200
            body = response.json()
            entry = body["entries"][0]
            assert entry["symbol"] == "AAPL"
            assert entry["cost_basis"] == "1705"
            assert entry["total_dividend"] == "49.20"
            assert entry["yield_on_cost_pct"] == "0.0289"
        finally:
            app.dependency_overrides.clear()

    async def test_null_yoc_직렬화(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=DividendService)
        mock_svc.get_yield_on_cost.return_value = YieldOnCostResponse(
            entries=[
                YieldOnCostEntry(
                    asset_symbol_id=1,
                    symbol="X",
                    name="X Corp",
                    currency="USD",
                    cost_basis=Decimal("0"),
                    total_dividend=Decimal("0"),
                    yield_on_cost_pct=None,
                )
            ]
        )

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_dividend_service] = lambda: mock_svc
        try:
            response = await async_client.get("/api/dividends/yield-on-cost")
            assert response.status_code == 200
            assert response.json()["entries"][0]["yield_on_cost_pct"] is None
        finally:
            app.dependency_overrides.clear()
