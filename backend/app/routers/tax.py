"""Tax router — GET /api/tax/capital-gains."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, TaxKrServiceDep
from app.schemas.auth import ErrorResponse
from app.schemas.tax import (
    CapitalGainsTaxResponse,
    CostMethod,
    DividendTaxResponse,
)

router = APIRouter(prefix="/api/tax", tags=["tax"])


@router.get(
    "/capital-gains",
    response_model=CapitalGainsTaxResponse,
    status_code=status.HTTP_200_OK,
    summary="Korean foreign-stock capital gains tax estimate",
    description=(
        "Computes Korean residents' annual foreign-stock capital gains tax. "
        "All amounts in KRW: sell proceeds converted at sell-date FX, cost "
        "basis at buy-date FX(es). Default rate 22% (incl. 2% local), "
        "default deduction 2,500,000 KRW. Crypto + US stock symbols are "
        "included; KR_STOCK is outside this estimator's scope."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_capital_gains_tax(
    _current_user: CurrentUser,
    service: TaxKrServiceDep,
    year: int = Query(..., ge=2000, le=2100),
    method: CostMethod = Query(default="average"),
    deduction_krw: Decimal = Query(default=Decimal("2500000"), ge=0),
    tax_rate: Decimal = Query(default=Decimal("0.22"), ge=0, le=1),
) -> CapitalGainsTaxResponse:
    return await service.get_capital_gains(year, method, deduction_krw, tax_rate)


@router.get(
    "/dividend-income",
    response_model=DividendTaxResponse,
    status_code=status.HTTP_200_OK,
    summary="Korean dividend-income tax estimate",
    description=(
        "Sums all Dividend rows in *year*, converts each at the ex-date FX "
        "rate, applies the flat withholding rate (default 15.4% = 14% income "
        "+ 1.4% local). Flags when the total exceeds 20,000,000 KRW — "
        "comprehensive income tax then applies on the excess, computed "
        "outside this estimator (depends on user's other income)."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_dividend_income_tax(
    _current_user: CurrentUser,
    service: TaxKrServiceDep,
    year: int = Query(..., ge=2000, le=2100),
    withholding_rate: Decimal = Query(default=Decimal("0.154"), ge=0, le=1),
    comprehensive_threshold_krw: Decimal = Query(
        default=Decimal("20000000"),
        ge=0,
    ),
) -> DividendTaxResponse:
    return await service.get_dividend_income_tax(
        year, withholding_rate, comprehensive_threshold_krw
    )
