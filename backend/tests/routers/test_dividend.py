"""Router tests for GET /api/dividends."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_dividend_service
from app.core.principal import OwnerPrincipal
from app.main import app
from app.schemas.dividend import (
    DividendListResponse,
    DividendResponse,
    DividendSummaryEntry,
)
from app.services.dividend import DividendService


def _make_owner() -> OwnerPrincipal:
    return OwnerPrincipal()


def _make_response() -> DividendListResponse:
    return DividendListResponse(
        items=[
            DividendResponse(
                id=1,
                asset_symbol_id=7,
                ex_date=date(2026, 2, 7),
                amount=Decimal("0.24"),
                currency="USD",
                source="yfinance",  # type: ignore[arg-type]  # StrEnum value
                created_at=date(2026, 2, 8),  # type: ignore[arg-type]  # accepts date
            )
        ],
        summary_by_symbol=[
            DividendSummaryEntry(
                asset_symbol_id=7,
                total_amount=Decimal("0.24"),
                currency="USD",
            )
        ],
    )


class TestListDividendsEndpoint:
    async def test_미인증_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/dividends")
        assert response.status_code == 401

    async def test_정상_200_응답_구조(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=DividendService)
        mock_svc.list_dividends.return_value = _make_response()

        app.dependency_overrides[get_current_user] = lambda: _make_owner()
        app.dependency_overrides[get_dividend_service] = lambda: mock_svc
        try:
            response = await async_client.get("/api/dividends")
            assert response.status_code == 200
            body = response.json()
            assert "items" in body
            assert "summary_by_symbol" in body
            assert body["items"][0]["amount"] == "0.24"
            assert body["summary_by_symbol"][0]["asset_symbol_id"] == 7
        finally:
            app.dependency_overrides.clear()

    async def test_쿼리_파라미터_전달(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=DividendService)
        mock_svc.list_dividends.return_value = DividendListResponse()

        app.dependency_overrides[get_current_user] = lambda: _make_owner()
        app.dependency_overrides[get_dividend_service] = lambda: mock_svc
        try:
            response = await async_client.get(
                "/api/dividends?asset_symbol_id=7&from=2026-01-01&to=2026-12-31"
            )
            assert response.status_code == 200
            mock_svc.list_dividends.assert_awaited_once_with(
                asset_symbol_id=7,
                date_from=date(2026, 1, 1),
                date_to=date(2026, 12, 31),
            )
        finally:
            app.dependency_overrides.clear()

    async def test_잘못된_param_422(self, async_client: AsyncClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: _make_owner()
        try:
            response = await async_client.get("/api/dividends?asset_symbol_id=0")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()
