"""Unit tests for RebalanceService — pure helpers + mocked dependencies."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from app.schemas.portfolio import (
    AllocationEntry,
    PnlEntry,
    PortfolioSummaryResponse,
)
from app.schemas.target_allocation import (
    TargetAllocationEntry,
    TargetAllocationListResponse,
)
from app.services.portfolio import PortfolioService
from app.services.rebalance import RebalanceService, _decide_action
from app.services.target_allocation import TargetAllocationService


class TestDecideAction:
    def test_under_threshold_buy(self) -> None:
        # drift -0.08 ≤ -0.05 → buy
        assert _decide_action(Decimal("-0.08"), Decimal("0.05")) == "buy"

    def test_over_threshold_sell(self) -> None:
        assert _decide_action(Decimal("0.07"), Decimal("0.05")) == "sell"

    def test_within_threshold_hold(self) -> None:
        assert _decide_action(Decimal("0.03"), Decimal("0.05")) == "hold"
        assert _decide_action(Decimal("-0.04"), Decimal("0.05")) == "hold"

    def test_경계값_정확(self) -> None:
        # exact threshold counts as buy/sell
        assert _decide_action(Decimal("-0.05"), Decimal("0.05")) == "buy"
        assert _decide_action(Decimal("0.05"), Decimal("0.05")) == "sell"


def _make_summary(
    *,
    converted_total: Decimal | None = Decimal("10000000"),
    allocation: list[AllocationEntry] | None = None,
) -> PortfolioSummaryResponse:
    return PortfolioSummaryResponse(
        total_value_by_currency={},
        total_cost_by_currency={},
        pnl_by_currency={"KRW": PnlEntry(abs=Decimal("0"), pct=0.0)},
        realized_pnl_by_currency={},
        cash_total_by_currency={},
        allocation=allocation or [],
        last_price_refreshed_at=datetime.now(UTC),
        pending_count=0,
        stale_count=0,
        converted_total_value=converted_total,
        converted_total_cost=None,
        converted_pnl_abs=None,
        converted_realized_pnl=None,
        display_currency="KRW",
    )


def _make_targets(
    pairs: list[tuple[str, str]],
) -> TargetAllocationListResponse:
    return TargetAllocationListResponse(
        entries=[
            TargetAllocationEntry(asset_type=at, target_pct=Decimal(p))  # type: ignore[arg-type]
            for at, p in pairs
        ]
    )


def _make_service(
    *,
    targets: TargetAllocationListResponse | None = None,
    summary: PortfolioSummaryResponse | None = None,
) -> RebalanceService:
    target_svc = AsyncMock(spec=TargetAllocationService)
    target_svc.list_targets.return_value = (
        targets if targets is not None else TargetAllocationListResponse(entries=[])
    )

    portfolio_svc = AsyncMock(spec=PortfolioService)
    portfolio_svc.get_summary.return_value = (
        summary if summary is not None else _make_summary()
    )

    return RebalanceService(target_svc, portfolio_svc)


class TestSuggest:
    async def test_no_target_warning(self) -> None:
        svc = _make_service()
        result = await svc.suggest("KRW")
        assert "no_target_configured" in result.warnings

    async def test_no_portfolio_value_warning(self) -> None:
        svc = _make_service(
            targets=_make_targets([("us_stock", "0.6")]),
            summary=_make_summary(converted_total=None),
        )
        result = await svc.suggest("KRW")
        assert "no_portfolio_value" in result.warnings
        assert result.total_value == Decimal("0")

    async def test_under_allocated_buy_action(self) -> None:
        # target us_stock=60%, current 50% → drift -10%, buy
        svc = _make_service(
            targets=_make_targets([("us_stock", "0.6")]),
            summary=_make_summary(
                converted_total=Decimal("10000000"),
                allocation=[AllocationEntry(asset_type="us_stock", pct=50.0)],
            ),
        )
        result = await svc.suggest("KRW", threshold_pct=Decimal("0.05"))
        us = next(e for e in result.entries if str(e.asset_type) == "us_stock")
        assert us.action == "buy"
        # delta = (0.6 - 0.5) * 10_000_000 = 1_000_000
        assert us.delta_amount == Decimal("1000000.0")

    async def test_over_allocated_sell(self) -> None:
        svc = _make_service(
            targets=_make_targets([("us_stock", "0.4")]),
            summary=_make_summary(
                converted_total=Decimal("10000000"),
                allocation=[AllocationEntry(asset_type="us_stock", pct=55.0)],
            ),
        )
        result = await svc.suggest("KRW")
        us = next(e for e in result.entries if str(e.asset_type) == "us_stock")
        assert us.action == "sell"
        assert us.delta_amount == Decimal("-1500000.0")

    async def test_within_threshold_hold(self) -> None:
        svc = _make_service(
            targets=_make_targets([("us_stock", "0.5")]),
            summary=_make_summary(
                converted_total=Decimal("10000000"),
                allocation=[AllocationEntry(asset_type="us_stock", pct=52.0)],
            ),
        )
        result = await svc.suggest("KRW", threshold_pct=Decimal("0.05"))
        us = next(e for e in result.entries if str(e.asset_type) == "us_stock")
        assert us.action == "hold"

    async def test_missing_in_current_treated_as_0(self) -> None:
        # target bucket exists but portfolio has no holdings of that type
        svc = _make_service(
            targets=_make_targets([("crypto", "0.2")]),
            summary=_make_summary(allocation=[]),
        )
        result = await svc.suggest("KRW")
        crypto = next(e for e in result.entries if str(e.asset_type) == "crypto")
        assert crypto.current_pct == Decimal("0")
        assert crypto.action == "buy"

    async def test_missing_in_target_treated_as_0(self) -> None:
        # portfolio has crypto but no target → should suggest sell
        svc = _make_service(
            targets=_make_targets([("us_stock", "0.6")]),
            summary=_make_summary(
                allocation=[
                    AllocationEntry(asset_type="us_stock", pct=60.0),
                    AllocationEntry(asset_type="crypto", pct=20.0),
                ]
            ),
        )
        result = await svc.suggest("KRW")
        crypto = next(e for e in result.entries if str(e.asset_type) == "crypto")
        assert crypto.target_pct == Decimal("0")
        assert crypto.action == "sell"

    async def test_currency_uppercase_보존(self) -> None:
        svc = _make_service()
        result = await svc.suggest("usd")
        assert result.currency == "usd"  # service receives already-uppercased str
