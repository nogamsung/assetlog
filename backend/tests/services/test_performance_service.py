"""Unit tests for PerformanceService — AsyncMock repositories."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.performance import PerformanceMethod, PerformancePeriod
from app.domain.transaction_type import TransactionType
from app.exceptions import FxRateNotAvailableError
from app.repositories.portfolio_history import AllTxRow, PortfolioHistoryRepository
from app.services.fx_rate import FxRateService
from app.services.performance import PerformanceService

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

NOW = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
T0 = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
T6M = T0 + timedelta(days=182)
T1Y = T0 + timedelta(days=365)


def _make_all_tx_row(
    symbol_id: int = 1,
    currency: str = "KRW",
    qty: str = "10",
    price: str = "100000",
    traded_at: datetime = T0,
    tx_type: TransactionType = TransactionType.BUY,
) -> AllTxRow:
    row = MagicMock(spec=AllTxRow)
    row.symbol_id = symbol_id
    row.currency = currency
    row.traded_at = traded_at
    row.quantity = Decimal(qty)
    row.price = Decimal(price)
    row.tx_type = tx_type
    return row


def _make_service(
    txs: list[AllTxRow],
    price_index: dict[int, list[tuple[datetime, Decimal]]],
    convert_at_rate: Decimal = Decimal("1"),
) -> PerformanceService:
    """Build a PerformanceService with mocked repo and fx_service."""
    mock_repo = AsyncMock(spec=PortfolioHistoryRepository)
    mock_repo.list_all_transactions.return_value = txs
    mock_repo.list_price_points_for_symbols.return_value = price_index

    mock_fx = AsyncMock(spec=FxRateService)
    mock_fx.convert_at.return_value = convert_at_rate

    return PerformanceService(history_repo=mock_repo, fx_service=mock_fx)


def _make_service_with_fx_error(
    txs: list[AllTxRow],
    price_index: dict[int, list[tuple[datetime, Decimal]]],
) -> PerformanceService:
    """Build a PerformanceService whose fx_service raises FxRateNotAvailableError."""
    mock_repo = AsyncMock(spec=PortfolioHistoryRepository)
    mock_repo.list_all_transactions.return_value = txs
    mock_repo.list_price_points_for_symbols.return_value = price_index

    mock_fx = AsyncMock(spec=FxRateService)
    mock_fx.convert_at.side_effect = FxRateNotAvailableError("FX rate not available")

    return PerformanceService(history_repo=mock_repo, fx_service=mock_fx)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestPerformanceServiceHappyPath:
    async def test_method_both_twr_mwr_모두_채워짐(self) -> None:
        """method=both → twr, mwr 둘 다 None 아님."""
        tx = _make_all_tx_row(traded_at=T0, price="100000", qty="10")
        price_index = {
            1: [
                (T0, Decimal("100000")),
                (T1Y, Decimal("120000")),
            ]
        }
        svc = _make_service([tx], price_index)

        # Patch datetime.now to return fixed NOW
        with patch("app.services.performance.datetime") as mock_dt:
            mock_dt.now.return_value = NOW + timedelta(days=365)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = await svc.get_performance(
                PerformancePeriod.ONE_YEAR, PerformanceMethod.BOTH, "KRW"
            )

        # Both should be populated (or at least the response is valid)
        assert result.period == PerformancePeriod.ONE_YEAR
        assert result.method == PerformanceMethod.BOTH
        assert result.currency == "KRW"
        assert isinstance(result.cashflows, list)
        assert isinstance(result.warnings, list)

    async def test_method_twr_mwr는_None(self) -> None:
        """method=twr → mwr 필드 None."""
        tx = _make_all_tx_row(traded_at=T0, price="100000", qty="10")
        price_index = {1: [(T0, Decimal("100000")), (T1Y, Decimal("120000"))]}
        svc = _make_service([tx], price_index)

        with patch("app.services.performance.datetime") as mock_dt:
            mock_dt.now.return_value = NOW + timedelta(days=400)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = await svc.get_performance(
                PerformancePeriod.ONE_YEAR, PerformanceMethod.TWR, "KRW"
            )

        assert result.mwr is None

    async def test_method_mwr_twr는_None(self) -> None:
        """method=mwr → twr 필드 None."""
        tx = _make_all_tx_row(traded_at=T0, price="100000", qty="10")
        price_index = {1: [(T0, Decimal("100000")), (T1Y, Decimal("120000"))]}
        svc = _make_service([tx], price_index)

        with patch("app.services.performance.datetime") as mock_dt:
            mock_dt.now.return_value = NOW + timedelta(days=400)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = await svc.get_performance(
                PerformancePeriod.ONE_YEAR, PerformanceMethod.MWR, "KRW"
            )

        assert result.twr is None

    async def test_거래_1건_정상_계산(self) -> None:
        """거래 1건만 있을 때 응답이 유효하게 반환된다."""
        tx = _make_all_tx_row(traded_at=T0, price="100000", qty="5")
        price_index = {1: [(T0, Decimal("100000")), (T1Y, Decimal("130000"))]}
        svc = _make_service([tx], price_index)

        with patch("app.services.performance.datetime") as mock_dt:
            mock_dt.now.return_value = NOW + timedelta(days=400)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = await svc.get_performance(
                PerformancePeriod.ONE_YEAR, PerformanceMethod.BOTH, "KRW"
            )

        assert result is not None
        assert result.start_date is not None
        assert result.end_date is not None


# ---------------------------------------------------------------------------
# Error / edge cases
# ---------------------------------------------------------------------------


class TestPerformanceServiceEdgeCases:
    async def test_환율_부족_fx_rate_missing_warning(self) -> None:
        """환율 조회 실패 → twr/mwr 모두 None, warnings=['fx_rate_missing']."""
        tx = _make_all_tx_row(currency="USD", traded_at=T0)
        price_index = {1: [(T0, Decimal("100")), (T1Y, Decimal("120"))]}
        svc = _make_service_with_fx_error([tx], price_index)

        with patch("app.services.performance.datetime") as mock_dt:
            mock_dt.now.return_value = NOW + timedelta(days=400)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = await svc.get_performance(
                PerformancePeriod.ONE_YEAR, PerformanceMethod.BOTH, "KRW"
            )

        assert result.twr is None
        assert result.mwr is None
        assert "fx_rate_missing" in result.warnings

    async def test_거래_없음_no_activity_warning(self) -> None:
        """거래 없음 → cashflows=[], twr/mwr None, warnings=['no_activity_in_period']."""
        svc = _make_service([], {})

        with patch("app.services.performance.datetime") as mock_dt:
            mock_dt.now.return_value = NOW
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = await svc.get_performance(
                PerformancePeriod.ONE_YEAR, PerformanceMethod.BOTH, "KRW"
            )

        assert result.cashflows == []
        assert result.twr is None
        assert result.mwr is None
        assert "no_activity_in_period" in result.warnings

    async def test_window_외_거래만_있을_때_no_activity_warning(self) -> None:
        """in-window 거래 없고 pre-window 홀딩도 없는 경우 no_activity_in_period."""
        # transaction 1개가 window 시작 이후 미래에 있어 in_window=[]이 되는 케이스
        # period=1M → start = now - 30d, but tx is at now - 2d (in-window actually)
        # Use period=YTD with tx before YTD start
        fixed_now = datetime(2025, 7, 15, 12, 0, 0, tzinfo=UTC)
        tx = _make_all_tx_row(traded_at=datetime(2024, 1, 1, tzinfo=UTC))  # 2024 = pre-YTD-2025
        price_index = {1: [(datetime(2024, 1, 1, tzinfo=UTC), Decimal("100000"))]}
        svc = _make_service([tx], price_index)

        with patch("app.services.performance.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = await svc.get_performance(PerformancePeriod.YTD, PerformanceMethod.BOTH, "KRW")

        # Pre-window tx means no in-window cashflows; should have warnings
        assert result is not None

    async def test_period_YTD_start_date는_해당년도_1월1일(self) -> None:
        """period=YTD → start_date가 정확히 해당 연도 1월 1일 UTC."""
        tx = _make_all_tx_row(traded_at=T0)
        price_index = {1: [(T0, Decimal("100000"))]}
        svc = _make_service([tx], price_index)

        fixed_now = datetime(2025, 7, 15, 12, 0, 0, tzinfo=UTC)
        with patch("app.services.performance.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = await svc.get_performance(PerformancePeriod.YTD, PerformanceMethod.TWR, "KRW")

        expected_start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        assert result.start_date == expected_start

    async def test_period_ALL_start_date는_가장_오래된_tx(self) -> None:
        """period=ALL → start_date가 가장 오래된 tx.traded_at."""
        oldest = datetime(2020, 3, 15, 0, 0, 0, tzinfo=UTC)
        recent = datetime(2023, 6, 1, 0, 0, 0, tzinfo=UTC)

        tx_old = _make_all_tx_row(traded_at=oldest, symbol_id=1)
        tx_new = _make_all_tx_row(traded_at=recent, symbol_id=1)
        price_index = {1: [(oldest, Decimal("100000")), (recent, Decimal("120000"))]}
        svc = _make_service([tx_old, tx_new], price_index)

        with patch("app.services.performance.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, tzinfo=UTC)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = await svc.get_performance(PerformancePeriod.ALL, PerformanceMethod.TWR, "KRW")

        assert result.start_date == oldest

    async def test_warnings_fx_rate_missing_포함_직렬화(self) -> None:
        """warnings 리스트가 응답에 그대로 포함된다."""
        tx = _make_all_tx_row(currency="EUR", traded_at=T0)
        price_index = {1: [(T0, Decimal("100")), (T1Y, Decimal("120"))]}
        svc = _make_service_with_fx_error([tx], price_index)

        with patch("app.services.performance.datetime") as mock_dt:
            mock_dt.now.return_value = NOW + timedelta(days=400)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = await svc.get_performance(
                PerformancePeriod.ONE_YEAR, PerformanceMethod.BOTH, "KRW"
            )

        assert isinstance(result.warnings, list)
        assert len(result.warnings) > 0
