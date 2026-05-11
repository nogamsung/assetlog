"""Router tests for GET /api/tax/dividend-income."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_tax_kr_service
from app.core.principal import OwnerPrincipal
from app.main import app
from app.schemas.tax import DividendTaxResponse
from app.services.tax_kr import TaxKrService


def _make_response() -> DividendTaxResponse:
    return DividendTaxResponse(
        year=2025,
        entries=[],
        total_dividend_krw=Decimal("637"),
        withholding_rate=Decimal("0.154"),
        withholding_tax_krw=Decimal("98.098"),
        comprehensive_threshold_krw=Decimal("20000000"),
        comprehensive_threshold_breach=False,
        warnings=[],
    )


class TestDividendTaxEndpoint:
    async def test_미인증_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/tax/dividend-income?year=2025")
        assert response.status_code == 401

    async def test_year_누락_422(self, async_client: AsyncClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        try:
            response = await async_client.get("/api/tax/dividend-income")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_정상_200(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=TaxKrService)
        mock_svc.get_dividend_income_tax.return_value = _make_response()

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_tax_kr_service] = lambda: mock_svc
        try:
            response = await async_client.get(
                "/api/tax/dividend-income?year=2025&withholding_rate=0.154"
            )
            assert response.status_code == 200
            body = response.json()
            assert body["year"] == 2025
            assert body["total_dividend_krw"] == "637"
            assert body["withholding_rate"] == "0.154"
            assert body["comprehensive_threshold_breach"] is False
        finally:
            app.dependency_overrides.clear()

    async def test_custom_threshold_passed(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=TaxKrService)
        mock_svc.get_dividend_income_tax.return_value = _make_response()

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_tax_kr_service] = lambda: mock_svc
        try:
            await async_client.get(
                "/api/tax/dividend-income?year=2025"
                "&withholding_rate=0.20&comprehensive_threshold_krw=10000000"
            )
            mock_svc.get_dividend_income_tax.assert_awaited_once_with(
                2025, Decimal("0.20"), Decimal("10000000")
            )
        finally:
            app.dependency_overrides.clear()
