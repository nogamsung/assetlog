"""Router tests for GET /api/tax/capital-gains."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_tax_kr_service
from app.core.principal import OwnerPrincipal
from app.main import app
from app.schemas.tax import CapitalGainsTaxResponse
from app.services.tax_kr import TaxKrService


def _make_response() -> CapitalGainsTaxResponse:
    return CapitalGainsTaxResponse(
        year=2025,
        method="average",
        sales=[],
        gross_gain_krw=Decimal("5700000"),
        deduction_krw=Decimal("2500000"),
        taxable_gain_krw=Decimal("3200000"),
        tax_rate=Decimal("0.22"),
        estimated_tax_krw=Decimal("704000"),
        warnings=[],
    )


class TestCapitalGainsEndpoint:
    async def test_미인증_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/tax/capital-gains?year=2025")
        assert response.status_code == 401

    async def test_year_파라미터_누락_422(self, async_client: AsyncClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        try:
            response = await async_client.get("/api/tax/capital-gains")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_정상_200(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=TaxKrService)
        mock_svc.get_capital_gains.return_value = _make_response()

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_tax_kr_service] = lambda: mock_svc
        try:
            response = await async_client.get("/api/tax/capital-gains?year=2025&method=average")
            assert response.status_code == 200
            body = response.json()
            assert body["year"] == 2025
            assert body["method"] == "average"
            assert body["taxable_gain_krw"] == "3200000"
            assert body["estimated_tax_krw"] == "704000"
        finally:
            app.dependency_overrides.clear()

    async def test_method_fifo_passed(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=TaxKrService)
        mock_svc.get_capital_gains.return_value = _make_response()

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_tax_kr_service] = lambda: mock_svc
        try:
            await async_client.get("/api/tax/capital-gains?year=2025&method=fifo")
            mock_svc.get_capital_gains.assert_awaited_once()
            args = mock_svc.get_capital_gains.await_args
            assert args is not None
            assert args.args[1] == "fifo"
        finally:
            app.dependency_overrides.clear()

    async def test_invalid_method_422(self, async_client: AsyncClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        try:
            response = await async_client.get("/api/tax/capital-gains?year=2025&method=lifo")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()
