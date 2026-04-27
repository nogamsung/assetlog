"""Unit tests for PortfolioHistoryService — AsyncMock repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.domain.portfolio_history import HistoryBucket, HistoryPeriod
from app.domain.transaction_type import TransactionType  # ADDED
from app.repositories.portfolio_history import PortfolioHistoryRepository, TransactionRow
from app.services.portfolio_history import PortfolioHistoryService


def _now() -> datetime:
    """Current UTC time — used to build relative timestamps in tests."""
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tx(
    symbol_id: int,
    qty: str,
    price: str,
    traded_at: datetime,
    tx_type: TransactionType = TransactionType.BUY,  # ADDED
) -> TransactionRow:
    tx = MagicMock(spec=TransactionRow)
    tx.symbol_id = symbol_id
    tx.traded_at = traded_at
    tx.quantity = Decimal(qty)
    tx.price = Decimal(price)
    tx.tx_type = tx_type  # ADDED
    return tx


def _make_service(
    txs: list[TransactionRow],
    price_index: dict[int, list[tuple[datetime, Decimal]]],
) -> PortfolioHistoryService:
    mock_repo = AsyncMock(spec=PortfolioHistoryRepository)
    mock_repo.list_transactions.return_value = txs
    mock_repo.list_price_points_for_symbols.return_value = price_index
    return PortfolioHistoryService(mock_repo)


# ---------------------------------------------------------------------------
# Empty portfolio
# ---------------------------------------------------------------------------


class TestPortfolioHistoryServiceEmpty:
    async def test_거래_없으면_빈_points_반환(self) -> None:
        svc = _make_service([], {})
        result = await svc.get_history(period=HistoryPeriod.ONE_MONTH, currency="KRW")
        assert result.points == []
        assert result.currency == "KRW"
        assert result.period == HistoryPeriod.ONE_MONTH

    async def test_빈_결과의_bucket은_기본값(self) -> None:
        svc = _make_service([], {})
        result = await svc.get_history(period=HistoryPeriod.ONE_DAY, currency="KRW")
        assert result.bucket == HistoryBucket.FIVE_MIN
        assert result.points == []


# ---------------------------------------------------------------------------
# Single symbol, single BUY
# ---------------------------------------------------------------------------


class TestPortfolioHistoryServiceSingleSymbol:
    async def test_단일_BUY_이후_value_계산(self) -> None:
        now = _now()
        trade_time = now - timedelta(hours=2)
        # Price available before the end of history window
        price_ts = now - timedelta(hours=1)
        tx = _make_tx(1, "2", "1000", trade_time)
        price_index = {1: [(price_ts, Decimal("1200"))]}

        svc = _make_service([tx], price_index)
        result = await svc.get_history(HistoryPeriod.ONE_DAY, "KRW")

        # The last point should include the latest price
        assert any(p.value == Decimal("2400") for p in result.points)

    async def test_BUY_이전_버킷은_value_0(self) -> None:
        now = _now()
        trade_time = now - timedelta(hours=1)
        tx = _make_tx(1, "5", "1000", trade_time)

        price_index: dict[int, list[tuple[datetime, Decimal]]] = {}
        svc = _make_service([tx], price_index)
        result = await svc.get_history(HistoryPeriod.ONE_DAY, "KRW")

        # All points before (strictly) trade should have value = 0
        before_trade = [p for p in result.points if p.timestamp <= trade_time]
        assert all(p.value == Decimal("0") for p in before_trade)

    async def test_cost_basis_누적_계산(self) -> None:
        now = _now()
        t1 = now - timedelta(hours=3)
        t2 = now - timedelta(minutes=30)
        tx1 = _make_tx(1, "2", "1000", t1)  # cost = 2000
        tx2 = _make_tx(1, "3", "1500", t2)  # cost = 4500 → total = 6500

        price_ts = now - timedelta(minutes=10)
        price_index = {1: [(price_ts, Decimal("2000"))]}

        svc = _make_service([tx1, tx2], price_index)
        result = await svc.get_history(HistoryPeriod.ONE_DAY, "KRW")

        # Last point should reflect full cost basis 6500
        last = result.points[-1]
        assert last.cost_basis == Decimal("6500")


# ---------------------------------------------------------------------------
# Multiple symbols + rollforward
# ---------------------------------------------------------------------------


class TestPortfolioHistoryServiceMultiSymbol:
    async def test_여러_심볼_value_합산(self) -> None:
        now = _now()
        trade_time = now - timedelta(hours=2)
        tx1 = _make_tx(1, "1", "1000", trade_time)
        tx2 = _make_tx(2, "2", "500", trade_time)

        price_ts = now - timedelta(hours=1)
        price_index = {
            1: [(price_ts, Decimal("1100"))],
            2: [(price_ts, Decimal("600"))],
        }

        svc = _make_service([tx1, tx2], price_index)
        result = await svc.get_history(HistoryPeriod.ONE_DAY, "KRW")

        # value = 1*1100 + 2*600 = 2300
        assert any(p.value == Decimal("2300") for p in result.points)

    async def test_price_없는_구간은_value_0_기여(self) -> None:
        now = _now()
        trade_time = now - timedelta(hours=3)
        tx = _make_tx(1, "10", "1000", trade_time)

        # No price available at all
        price_index: dict[int, list[tuple[datetime, Decimal]]] = {}
        svc = _make_service([tx], price_index)
        result = await svc.get_history(HistoryPeriod.ONE_DAY, "KRW")

        # All value fields should be 0 (no price data)
        assert all(p.value == Decimal("0") for p in result.points)

    async def test_rollforward_직전값_사용(self) -> None:
        """A price point seeded before `since` should be used for rollforward."""
        now = _now()
        trade_time = now - timedelta(hours=5)
        tx = _make_tx(1, "1", "1000", trade_time)

        # Seed price was before `since` (ONE_DAY window start = now-24h)
        seed_ts = now - timedelta(hours=25)
        later_ts = now - timedelta(hours=10)
        price_index = {
            1: [
                # asc order: older first
                (seed_ts, Decimal("1200")),
                (later_ts, Decimal("1500")),
            ]
        }

        svc = _make_service([tx], price_index)
        result = await svc.get_history(HistoryPeriod.ONE_DAY, "KRW")

        # Points between seed_ts and later_ts where trade has occurred → value = 1 * 1200
        mid_points = [p for p in result.points if trade_time <= p.timestamp < later_ts]
        if mid_points:
            assert all(p.value == Decimal("1200") for p in mid_points)


# ---------------------------------------------------------------------------
# Period / bucket resolution
# ---------------------------------------------------------------------------


class TestPortfolioHistoryServicePeriodBucket:
    async def test_ONE_DAY_버킷은_FIVE_MIN(self) -> None:
        now = _now()
        tx = _make_tx(1, "1", "1000", now - timedelta(hours=1))
        svc = _make_service([tx], {})
        result = await svc.get_history(HistoryPeriod.ONE_DAY, "KRW")
        assert result.bucket == HistoryBucket.FIVE_MIN

    async def test_ONE_YEAR_버킷은_WEEK(self) -> None:
        now = _now()
        tx = _make_tx(1, "1", "1000", now - timedelta(days=10))
        svc = _make_service([tx], {})
        result = await svc.get_history(HistoryPeriod.ONE_YEAR, "KRW")
        assert result.bucket == HistoryBucket.WEEK

    async def test_ALL_버킷은_MONTH(self) -> None:
        now = _now()
        first_trade = now - timedelta(days=365)
        tx = _make_tx(1, "1", "1000", first_trade)
        svc = _make_service([tx], {})
        result = await svc.get_history(HistoryPeriod.ALL, "KRW")
        assert result.bucket == HistoryBucket.MONTH

    async def test_ALL_시작은_첫_거래일(self) -> None:
        now = _now()
        first_trade = now - timedelta(days=200)
        tx = _make_tx(1, "1", "1000", first_trade)
        svc = _make_service([tx], {})
        result = await svc.get_history(HistoryPeriod.ALL, "KRW")

        # First point timestamp should be at or near first_trade
        first_ts = result.points[0].timestamp
        assert first_ts <= first_trade + timedelta(days=31)  # within one MONTH bucket

    async def test_ONE_MONTH_포인트_수_약30개(self) -> None:
        now = _now()
        tx = _make_tx(1, "1", "1000", now - timedelta(days=35))
        price_ts = now - timedelta(hours=1)
        price_index = {1: [(price_ts, Decimal("2000"))]}
        svc = _make_service([tx], price_index)
        result = await svc.get_history(HistoryPeriod.ONE_MONTH, "KRW")

        # ONE_MONTH with DAY bucket → ~30 points (+1 for end clamp)
        assert 28 <= len(result.points) <= 32


# ---------------------------------------------------------------------------
# Currency filter — delegated to repo
# ---------------------------------------------------------------------------


class TestPortfolioHistoryServiceCurrencyFilter:
    async def test_repo가_올바른_currency로_호출됨(self) -> None:
        mock_repo = AsyncMock(spec=PortfolioHistoryRepository)
        mock_repo.list_transactions.return_value = []
        svc = PortfolioHistoryService(mock_repo)

        await svc.get_history(HistoryPeriod.ONE_MONTH, "USD")
        mock_repo.list_transactions.assert_awaited_once_with("USD")


# ---------------------------------------------------------------------------
# SELL 반영 — ADDED
# ---------------------------------------------------------------------------


class TestPortfolioHistoryServiceSell:
    async def test_BUY후_SELL하면_qty_감소(self) -> None:
        now = _now()
        buy_time = now - timedelta(hours=3)
        sell_time = now - timedelta(hours=1)
        price_ts = now - timedelta(minutes=10)

        buy_tx = _make_tx(1, "5", "1000", buy_time, TransactionType.BUY)
        sell_tx = _make_tx(1, "2", "1200", sell_time, TransactionType.SELL)
        price_index = {1: [(price_ts, Decimal("1300"))]}

        svc = _make_service([buy_tx, sell_tx], price_index)
        result = await svc.get_history(HistoryPeriod.ONE_DAY, "KRW")

        # Last point: qty=3, price=1300 → value=3900
        last = result.points[-1]
        assert last.value == Decimal("3900")

    async def test_BUY후_SELL하면_cost_basis_재계산(self) -> None:
        now = _now()
        buy_time = now - timedelta(hours=3)
        sell_time = now - timedelta(hours=1)
        price_ts = now - timedelta(minutes=10)

        # BUY 4 at 1000 → avg=1000, SELL 1 → remaining_cost = 1000 * 3 = 3000
        buy_tx = _make_tx(1, "4", "1000", buy_time, TransactionType.BUY)
        sell_tx = _make_tx(1, "1", "1200", sell_time, TransactionType.SELL)
        price_index = {1: [(price_ts, Decimal("1100"))]}

        svc = _make_service([buy_tx, sell_tx], price_index)
        result = await svc.get_history(HistoryPeriod.ONE_DAY, "KRW")

        last = result.points[-1]
        # cost_basis = avg_buy(1000) × remaining_qty(3) = 3000
        assert last.cost_basis == Decimal("3000")

    async def test_전량_SELL후_value_0(self) -> None:
        now = _now()
        buy_time = now - timedelta(hours=4)
        sell_time = now - timedelta(hours=2)
        price_ts = now - timedelta(minutes=10)

        buy_tx = _make_tx(1, "3", "1000", buy_time, TransactionType.BUY)
        sell_tx = _make_tx(1, "3", "1200", sell_time, TransactionType.SELL)
        price_index = {1: [(price_ts, Decimal("1300"))]}

        svc = _make_service([buy_tx, sell_tx], price_index)
        result = await svc.get_history(HistoryPeriod.ONE_DAY, "KRW")

        # After full sell, value should be 0
        after_sell = [p for p in result.points if p.timestamp >= sell_time]
        assert all(p.value == Decimal("0") for p in after_sell)
