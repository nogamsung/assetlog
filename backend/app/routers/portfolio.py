"""Portfolio router — aggregated summary, per-holding, and history endpoints."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Query, Request, status

from app.core.deps import (
    BenchmarkServiceDep,
    CashFlowServiceDep,
    CurrentUser,
    FxRateServiceDep,
    HeatmapServiceDep,
    PerformanceServiceDep,
    PortfolioHistoryServiceDep,
    PortfolioServiceDep,
    RiskServiceDep,
    TagBreakdownServiceDep,
)
from app.domain.performance import PerformanceMethod, PerformancePeriod
from app.domain.portfolio_history import HistoryPeriod
from app.schemas.auth import ErrorResponse
from app.schemas.benchmark import BenchmarkComparisonResponse
from app.schemas.heatmap import HeatmapResponse
from app.schemas.performance import PerformanceResponse
from app.schemas.portfolio import (
    HoldingResponse,
    PortfolioHistoryResponse,
    PortfolioSummaryResponse,
)
from app.schemas.risk import RiskMetricsResponse
from app.schemas.tag_breakdown import TagBreakdownResponse

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get(
    "/summary",
    response_model=PortfolioSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get currency-bucketed portfolio summary",
    description=(
        "Returns total market value, cost basis, P&L, and asset-class allocation "
        "grouped by currency. Holdings whose last_price is NULL are excluded from "
        "value/P&L totals but counted in ``pending_count``. "
        "Pass ``convert_to`` (e.g. ``KRW``) to receive converted totals in addition to "
        "the per-currency breakdown. Converted fields are null if any required FX rate "
        "is unavailable — no partial conversion is performed."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        503: {
            "model": ErrorResponse,
            "description": "FX rate not yet available — retry after scheduler runs",
        },
    },
)
async def get_portfolio_summary(
    _current_user: CurrentUser,
    portfolio_service: PortfolioServiceDep,
    convert_to: str | None = Query(
        default=None,
        min_length=3,
        max_length=10,
        description="Target currency for conversion (e.g. KRW, USD, EUR)",
        examples=["KRW"],
    ),
) -> PortfolioSummaryResponse:
    """Return aggregated portfolio summary."""
    target = convert_to.upper() if convert_to else None
    return await portfolio_service.get_summary(convert_to=target)


@router.get(
    "/holdings",
    response_model=list[HoldingResponse],
    status_code=status.HTTP_200_OK,
    summary="List per-holding valuation rows",
    description=(
        "Returns one row per UserAsset with derived fields: latest_price, "
        "latest_value, pnl_abs, pnl_pct, weight_pct, is_stale, is_pending. "
        "Decimal fields are serialised as strings. "
        "Pass ``convert_to`` (e.g. ``KRW``) to receive per-row converted_* fields. "
        "If the FX rate for a holding's currency is unavailable, that holding's "
        "converted_* fields are null while others remain converted (partial conversion allowed)."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_portfolio_holdings(
    _current_user: CurrentUser,
    portfolio_service: PortfolioServiceDep,
    convert_to: str | None = Query(
        default=None,
        min_length=3,
        max_length=10,
        description="Target currency for per-row conversion (e.g. KRW, USD, EUR)",
        examples=["KRW"],
    ),
) -> list[HoldingResponse]:
    """Return per-holding valuation rows."""
    return await portfolio_service.get_holdings(
        convert_to=convert_to.upper() if convert_to else None,
    )


@router.get(
    "/history",
    response_model=PortfolioHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get portfolio value time series",
    description=(
        "Returns a bucketed time series of portfolio value and cost basis. "
        "Bucket granularity is determined by the requested period: "
        "1D → 5MIN, 1W → HOUR, 1M → DAY, 1Y → WEEK, ALL → MONTH. "
        "Points where no price data is available contribute 0 to value."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {
            "model": ErrorResponse,
            "description": "Validation error (invalid period or missing currency)",
        },
    },
)
async def get_portfolio_history(
    _current_user: CurrentUser,
    history_service: PortfolioHistoryServiceDep,
    period: HistoryPeriod = Query(default=HistoryPeriod.ONE_MONTH, description="Time window"),
    currency: str = Query(
        ...,
        min_length=1,
        max_length=10,
        description="Quote currency (e.g. KRW, USD)",
    ),
) -> PortfolioHistoryResponse:
    """Return portfolio value time series."""
    return await history_service.get_history(period, currency.upper())


async def _run_backfill_in_background(session_factory: Any) -> None:
    """Run a one-shot price-history back-fill in a fresh session.

    Used as a fire-and-forget background task so the HTTP request returns
    immediately and the rest of the API stays responsive while yfinance is
    pulling several years of daily closes per symbol.
    """
    from app.repositories.price_point import PricePointRepository  # noqa: PLC0415
    from app.services.price_history_backfill import (  # noqa: PLC0415
        PriceHistoryBackfillService,
    )

    logger = logging.getLogger("app.routers.portfolio.backfill")
    try:
        async with session_factory() as session:
            svc = PriceHistoryBackfillService(
                session=session,
                price_point_repo=PricePointRepository(session),
            )
            result = await svc.backfill_all()
            await session.commit()
            logger.info(
                "history backfill done",
                extra={
                    "event": "history_backfill_done",
                    "attempted": result.symbols_attempted,
                    "skipped": result.symbols_skipped,
                    "inserted": result.points_inserted,
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("history backfill failed: %s", exc)


@router.post(
    "/history/backfill",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Schedule a back-fill of historical daily prices",
    description=(
        "Schedules a background job that pulls daily closing prices from "
        "yfinance back to each symbol's earliest trade date and writes them "
        "to price_points. Returns 202 immediately — actual completion is "
        "asynchronous, which keeps the API responsive while yfinance is busy."
    ),
    responses={401: {"model": ErrorResponse, "description": "Not authenticated"}},
)
async def backfill_portfolio_history(
    _current_user: CurrentUser,
    request: Request,
) -> dict[str, str]:
    """Schedule the backfill and return immediately."""
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        return {"status": "unavailable"}
    asyncio.create_task(_run_backfill_in_background(session_factory))
    return {"status": "scheduled"}


@router.get(
    "/tags/breakdown",
    response_model=TagBreakdownResponse,
    status_code=status.HTTP_200_OK,
    summary="Per-tag transaction flow breakdown",
    description=(
        "Groups transactions by tag and returns per-tag buy/sell counts and "
        "currency-bucketed value totals. "
        "Untagged transactions are grouped under tag=null and always appear last. "
        "Returns entries=[] when there are no transactions."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_tag_breakdown(
    _current_user: CurrentUser,
    service: TagBreakdownServiceDep,
) -> TagBreakdownResponse:
    """Return per-tag transaction flow breakdown."""
    return await service.get_breakdown()


@router.get(
    "/performance",
    response_model=PerformanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get TWR / MWR(IRR) portfolio performance over a period",
    description=(
        "Returns time-weighted return (TWR) and money-weighted return / IRR "
        "(MWR) over the requested period in the requested report currency. "
        "Cashflows are signed (BUY=-, SELL=+) and converted at trade-date FX "
        "rates. If FX rates are missing for any required pair, twr/mwr are "
        "null and a 'fx_rate_missing' warning is returned (HTTP 200)."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_portfolio_performance(
    _current_user: CurrentUser,
    perf_service: PerformanceServiceDep,
    period: PerformancePeriod = Query(default=PerformancePeriod.ONE_YEAR),
    method: PerformanceMethod = Query(default=PerformanceMethod.BOTH),
    currency: str = Query(default="KRW", min_length=3, max_length=10),
) -> PerformanceResponse:
    """Return TWR / MWR portfolio performance metrics."""
    return await perf_service.get_performance(period, method, currency.upper())


@router.get(
    "/performance/benchmark",
    response_model=BenchmarkComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare portfolio cumulative return against market benchmarks",
    description=(
        "Returns the user portfolio's cumulative return time series alongside "
        "one series per requested benchmark symbol (default: KOSPI / S&P 500 / BTC). "
        "Each series is anchored at 0% on the window start. The response also "
        "includes per-symbol alpha = portfolio_final_return − benchmark_final_return."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_portfolio_benchmark(
    _current_user: CurrentUser,
    bench_service: BenchmarkServiceDep,
    period: PerformancePeriod = Query(default=PerformancePeriod.ONE_YEAR),
    currency: str = Query(default="KRW", min_length=3, max_length=10),
    symbols: str = Query(
        default="^KS11,^GSPC,BTC-USD",
        description="Comma-separated list of yfinance ticker symbols",
    ),
) -> BenchmarkComparisonResponse:
    """Return cumulative-return comparison vs market indices."""
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    return await bench_service.compare(period, currency.upper(), symbol_list)


@router.get(
    "/performance/risk",
    response_model=RiskMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get annualised return / volatility / Sharpe / max drawdown",
    description=(
        "Computes risk-adjusted performance metrics from the same daily value "
        "series used by /performance and /performance/benchmark. Volatility "
        "uses 252 trading days for annualisation; Sharpe uses the configured "
        "risk_free_rate (env: RISK_FREE_RATE, default 0.03)."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_portfolio_risk(
    _current_user: CurrentUser,
    risk_service: RiskServiceDep,
    period: PerformancePeriod = Query(default=PerformancePeriod.ONE_YEAR),
    currency: str = Query(default="KRW", min_length=3, max_length=10),
) -> RiskMetricsResponse:
    """Return Sharpe / volatility / MDD / annualised-return metrics."""
    return await risk_service.get_risk_metrics(period, currency.upper())


@router.get(
    "/performance/heatmap",
    response_model=HeatmapResponse,
    status_code=status.HTTP_200_OK,
    summary="Monthly returns heatmap (year × month matrix)",
    description=(
        "Returns per-month portfolio returns over the most recent N calendar "
        "years, computed by sampling portfolio value at month-end and taking "
        "(v_i / v_{i-1}) - 1. Yearly aggregates compound the months "
        "geometrically. Default years=5."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_portfolio_heatmap(
    _current_user: CurrentUser,
    heatmap_service: HeatmapServiceDep,
    currency: str = Query(default="KRW", min_length=3, max_length=10),
    years: int = Query(default=5, ge=1, le=20),
) -> HeatmapResponse:
    """Return monthly returns matrix."""
    return await heatmap_service.get_heatmap(currency.upper(), years)


@router.get(
    "/net-worth",
    status_code=status.HTTP_200_OK,
    summary="Total net worth (holdings value + cash) per currency + converted total",
    description=(
        "Combines per-currency holdings valuation with the user's available "
        "cash balance derived from imported cash-flow records (deposits, "
        "withdrawals, FX transfers, dividends, buys, sells, interest, taxes). "
        "Returns each currency's cash + assets, plus an optional sum "
        "converted into the requested display currency."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_portfolio_net_worth(
    _current_user: CurrentUser,
    portfolio_service: PortfolioServiceDep,
    cash_flow_service: CashFlowServiceDep,
    fx_service: FxRateServiceDep,
    display_currency: str | None = Query(
        default=None,
        description="ISO 4217 code to express the total in (e.g. KRW). "
        "Per-currency breakdown is always native.",
    ),
) -> dict[str, object]:
    """Return per-currency net worth + optional converted grand total."""
    from decimal import Decimal  # noqa: PLC0415

    holdings = await portfolio_service.get_holdings()
    cash_by_currency = await cash_flow_service.net_cash_by_currency()
    cash_by_source = await cash_flow_service.net_cash_by_source_and_currency()

    holdings_by_currency: dict[str, Decimal] = {}
    for h in holdings:
        if h.latest_value is None:
            continue
        cur = h.asset_symbol.currency
        holdings_by_currency[cur] = holdings_by_currency.get(cur, Decimal("0")) + h.latest_value

    currencies = set(cash_by_currency.keys()) | set(holdings_by_currency.keys())
    breakdown: dict[str, dict[str, str]] = {}
    for cur in sorted(currencies):
        cash = cash_by_currency.get(cur, Decimal("0"))
        assets = holdings_by_currency.get(cur, Decimal("0"))
        breakdown[cur] = {
            "cash": str(cash),
            "assets": str(assets),
            "total": str(cash + assets),
        }

    by_account: dict[str, dict[str, str]] = {}
    for source, ccy_map in cash_by_source.items():
        by_account[source] = {c: str(v) for c, v in ccy_map.items()}

    converted_total: str | None = None
    if display_currency is not None:
        target = display_currency.upper()
        from app.exceptions import FxRateNotAvailableError  # noqa: PLC0415

        grand_total = Decimal("0")
        for cur, entry in breakdown.items():
            try:
                converted = await fx_service.convert(Decimal(entry["total"]), cur, target)
                grand_total += converted
            except FxRateNotAvailableError:
                continue
        converted_total = str(grand_total)

    return {
        "by_currency": breakdown,
        "by_account": by_account,
        "display_currency": display_currency.upper() if display_currency else None,
        "converted_total": converted_total,
    }
