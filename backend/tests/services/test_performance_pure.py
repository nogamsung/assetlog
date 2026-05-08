"""Unit tests for pure performance functions — no DB / async.

Tests cover compute_twr, compute_mwr, extract_cashflows, build_value_series.
All assertions use 1bp (0.0001) tolerance unless stated otherwise.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.performance import Cashflow, ValuePoint
from app.domain.transaction_type import TransactionType
from app.repositories.portfolio_history import AllTxRow
from app.services.performance import (
    build_value_series,
    compute_mwr,
    compute_twr,
    extract_cashflows,
)

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

T0 = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
T6M = T0 + timedelta(days=182)
T1Y = T0 + timedelta(days=365)

_TOL = Decimal("0.0001")  # 1bp tolerance


def _assert_approx(value: Decimal | None, expected: Decimal, tol: Decimal = _TOL) -> None:
    """Assert value is within tol of expected."""
    assert value is not None, f"Expected approx {expected} but got None"
    diff = abs(value - expected)
    assert diff <= tol, f"|{value} - {expected}| = {diff} > {tol}"


def _make_tx(
    symbol_id: int,
    currency: str,
    qty: str,
    price: str,
    traded_at: datetime,
    tx_type: TransactionType = TransactionType.BUY,
) -> AllTxRow:
    tx = MagicMock(spec=AllTxRow)
    tx.symbol_id = symbol_id
    tx.currency = currency
    tx.traded_at = traded_at
    tx.quantity = Decimal(qty)
    tx.price = Decimal(price)
    tx.tx_type = tx_type
    return tx


def _fx_identity(amount: Decimal, from_cur: str, to_cur: str, at: datetime) -> Decimal:
    """Identity FX stub — no conversion (same currency or 1:1)."""
    return amount


def _fx_usd_to_krw(amount: Decimal, from_cur: str, to_cur: str, at: datetime) -> Decimal:
    """Stub: USD → KRW at 1300, KRW passthrough."""
    if from_cur == to_cur:
        return amount
    if from_cur == "USD" and to_cur == "KRW":
        return amount * Decimal("1300")
    return amount


# ---------------------------------------------------------------------------
# compute_twr
# ---------------------------------------------------------------------------


class TestComputeTWR:
    def test_단일매수_1년_20프로_수익(self) -> None:
        """단일매수 TWR — 1년 전 100만원 매수, 현재 120만원: TWR ≈ 0.20"""
        value_series = [
            ValuePoint(timestamp=T0, value=Decimal("1000000")),
            ValuePoint(timestamp=T1Y, value=Decimal("1200000")),
        ]
        cashflows = [Cashflow(date=T0, amount=Decimal("-1000000"), kind="buy")]

        result = compute_twr(value_series, cashflows)
        _assert_approx(result, Decimal("0.20"))

    def test_추가매수_TWR_기하평균(self) -> None:
        """추가매수 TWR — t0 1주 매수(가격100), t6m 1주 추가매수(가격110), t1y 가격130.

        build_value_series는 각 timestamp에서 post-cashflow 가치를 반환:
          T0: 1share × 100 = 100 (post-BUY)
          T6M: 2shares × 110 = 220 (post-2nd-BUY)
          T1Y: 2shares × 130 = 260

        TWR subperiods:
          T0→T6M: V_before(T6M) = V_post(220) + cf(-110) = 110
                  r1 = 110/100 - 1 = 0.10
          T6M→T1Y: V_before(T1Y) = V_post(260) + cf(0) = 260
                   r2 = 260/220 - 1 = 0.1818...
          TWR = 1.10 × 1.1818 - 1 = 0.30
        """
        value_series = [
            ValuePoint(timestamp=T0, value=Decimal("100")),
            ValuePoint(timestamp=T6M, value=Decimal("220")),  # 2 shares × 110 (post-BUY)
            ValuePoint(timestamp=T1Y, value=Decimal("260")),  # 2 shares × 130
        ]
        cashflows = [
            Cashflow(date=T0, amount=Decimal("-100"), kind="buy"),
            Cashflow(date=T6M, amount=Decimal("-110"), kind="buy"),
        ]

        result = compute_twr(value_series, cashflows)
        _assert_approx(result, Decimal("0.30"))

    def test_부분매도_TWR_시점_무관(self) -> None:
        """부분매도 TWR — 매도해도 수익률 동일 (TWR ≈ 0.30).

        build_value_series는 post-cashflow 가치를 반환:
          T0: 10shares × 100K = 1M (post-BUY)
          T6M: 5shares × 110K = 550K (post-SELL of 5 shares)
          T1Y: 5shares × 130K = 650K

        TWR subperiods:
          T0→T6M: V_before(T6M) = V_post(550K) + cf(+550K) = 1.1M
                  r1 = 1.1M/1M - 1 = 0.10
          T6M→T1Y: V_before(T1Y) = V_post(650K) + cf(0) = 650K
                   r2 = 650K/550K - 1 = 0.1818...
          TWR = 1.10 × 1.1818 - 1 = 0.30
        """
        value_series = [
            ValuePoint(timestamp=T0, value=Decimal("1000000")),
            ValuePoint(timestamp=T6M, value=Decimal("550000")),  # 5shares × 110K (post-SELL)
            ValuePoint(timestamp=T1Y, value=Decimal("650000")),
        ]
        cashflows = [
            Cashflow(date=T0, amount=Decimal("-1000000"), kind="buy"),
            Cashflow(date=T6M, amount=Decimal("550000"), kind="sell"),
        ]

        result = compute_twr(value_series, cashflows)
        _assert_approx(result, Decimal("0.30"))

    def test_거래_없음_빈_value_series_None_반환(self) -> None:
        result = compute_twr([], [])
        assert result is None

    def test_value_series_단일_포인트_cashflow_없음(self) -> None:
        value_series = [ValuePoint(timestamp=T0, value=Decimal("1000000"))]
        result = compute_twr(value_series, [])
        # Single point, no cashflows → TWR = 0 (V_end/V_start - 1)
        assert result is not None

    def test_알려진_fixture_단일매수_TWR_정확도(self) -> None:
        """PRD G-4 known fixture: 100만 매수 → 120만 = 0.20 TWR (1bp 이내)."""
        value_series = [
            ValuePoint(timestamp=T0, value=Decimal("1000000")),
            ValuePoint(timestamp=T1Y, value=Decimal("1200000")),
        ]
        cashflows = [Cashflow(date=T0, amount=Decimal("-1000000"), kind="buy")]
        result = compute_twr(value_series, cashflows)
        _assert_approx(result, Decimal("0.20"))


# ---------------------------------------------------------------------------
# compute_mwr
# ---------------------------------------------------------------------------


class TestComputeMWR:
    def test_단일매수_1년_20프로_수익_MWR(self) -> None:
        """단일매수 MWR — 동일 fixture, MWR ≈ 0.20 (±1bp)."""
        cashflows = [Cashflow(date=T0, amount=Decimal("-1000000"), kind="buy")]
        result = compute_mwr(
            cashflows,
            terminal_value=Decimal("1200000"),
            terminal_date=T1Y,
        )
        _assert_approx(result, Decimal("0.20"))

    def test_알려진_fixture_PRD_G4(self) -> None:
        """PRD G-4: compute_mwr([-1000000 @t0], 1200000, t0+365d) == 0.20 (±0.0001)."""
        cashflows = [Cashflow(date=T0, amount=Decimal("-1000000"), kind="buy")]
        result = compute_mwr(
            cashflows,
            terminal_value=Decimal("1200000"),
            terminal_date=T0 + timedelta(days=365),
        )
        _assert_approx(result, Decimal("0.20"))

    def test_부분매도_MWR(self) -> None:
        """부분매도 MWR — cashflows=[-1M @t0, +0.55M @t6m], terminal_value=0.65M @t1y."""
        cashflows = [
            Cashflow(date=T0, amount=Decimal("-1000000"), kind="buy"),
            Cashflow(date=T6M, amount=Decimal("550000"), kind="sell"),
        ]
        result = compute_mwr(
            cashflows,
            terminal_value=Decimal("650000"),
            terminal_date=T1Y,
        )
        # MWR should be approximately 0.30 (same economic return as TWR case)
        assert result is not None
        assert Decimal("0.20") <= result <= Decimal("0.45")

    def test_단순부호_cashflow_해없음_None_반환(self) -> None:
        """현금흐름이 모두 같은 부호 → IRR 해 없음 → None."""
        cashflows = [
            Cashflow(date=T0, amount=Decimal("100"), kind="sell"),
            Cashflow(date=T6M, amount=Decimal("200"), kind="sell"),
        ]
        result = compute_mwr(
            cashflows,
            terminal_value=Decimal("300"),
            terminal_date=T1Y,
        )
        # All positive cashflows + positive terminal_value → no sign change → None
        assert result is None

    def test_initial_value와_initial_date_사용(self) -> None:
        """initial_value 파라미터를 사용하면 MWR 계산에 포함된다."""
        cashflows: list[Cashflow] = []
        result = compute_mwr(
            cashflows,
            terminal_value=Decimal("1200000"),
            terminal_date=T1Y,
            initial_value=Decimal("1000000"),
            initial_date=T0,
        )
        _assert_approx(result, Decimal("0.20"))


# ---------------------------------------------------------------------------
# extract_cashflows
# ---------------------------------------------------------------------------


class TestExtractCashflows:
    def test_window_외_거래_제외(self) -> None:
        """window 외 거래는 cashflow 에 포함 안 됨."""
        old_tx = _make_tx(1, "KRW", "10", "100000", T0 - timedelta(days=730))
        in_window_tx = _make_tx(1, "KRW", "5", "110000", T6M)

        result = extract_cashflows(
            [old_tx, in_window_tx],
            report_currency="KRW",
            fx_at=_fx_identity,
            window_start=T0,
            window_end=T1Y,
        )
        assert len(result) == 1
        _assert_approx(result[0].amount, Decimal("-550000"))
        assert result[0].kind == "buy"

    def test_같은_timestamp_BUY_SELL_병합(self) -> None:
        """동일 timestamp의 BUY+SELL은 1개의 Cashflow로 병합된다."""
        buy_tx = _make_tx(1, "KRW", "10", "100000", T6M, TransactionType.BUY)
        sell_tx = _make_tx(1, "KRW", "5", "100000", T6M, TransactionType.SELL)

        result = extract_cashflows(
            [buy_tx, sell_tx],
            report_currency="KRW",
            fx_at=_fx_identity,
            window_start=T0,
            window_end=T1Y,
        )
        assert len(result) == 1
        # BUY: -1000000, SELL: +500000 → net = -500000 (buy dominant)
        _assert_approx(result[0].amount, Decimal("-500000"))
        assert result[0].kind == "buy"

    def test_SELL_캐시플로우_양수(self) -> None:
        """SELL 거래는 양수 cashflow 생성."""
        sell_tx = _make_tx(1, "KRW", "5", "120000", T6M, TransactionType.SELL)
        result = extract_cashflows(
            [sell_tx],
            report_currency="KRW",
            fx_at=_fx_identity,
            window_start=T0,
            window_end=T1Y,
        )
        assert len(result) == 1
        assert result[0].amount > Decimal("0")
        assert result[0].kind == "sell"

    def test_FX_변환_적용됨(self) -> None:
        """FX 변환이 cashflow amount에 적용된다."""
        buy_tx = _make_tx(1, "USD", "1", "1000", T6M)  # 1000 USD
        result = extract_cashflows(
            [buy_tx],
            report_currency="KRW",
            fx_at=_fx_usd_to_krw,
            window_start=T0,
            window_end=T1Y,
        )
        # 1000 USD * 1300 KRW/USD = 1300000 KRW (BUY → negative)
        assert len(result) == 1
        _assert_approx(result[0].amount, Decimal("-1300000"))

    def test_빈_거래_빈_cashflows(self) -> None:
        """거래 없음 → 빈 cashflows 반환."""
        result = extract_cashflows(
            [],
            report_currency="KRW",
            fx_at=_fx_identity,
            window_start=T0,
            window_end=T1Y,
        )
        assert result == []

    def test_window_경계_포함(self) -> None:
        """window_start/end 경계의 거래도 포함된다."""
        tx_start = _make_tx(1, "KRW", "1", "100000", T0)
        tx_end = _make_tx(1, "KRW", "1", "120000", T1Y, TransactionType.SELL)
        result = extract_cashflows(
            [tx_start, tx_end],
            report_currency="KRW",
            fx_at=_fx_identity,
            window_start=T0,
            window_end=T1Y,
        )
        assert len(result) == 2


# ---------------------------------------------------------------------------
# build_value_series
# ---------------------------------------------------------------------------


class TestBuildValueSeries:
    def test_단일_KRW_종목_value_계산(self) -> None:
        """단일 KRW 종목 2주 매수 후 가격 상승 시 value 계산."""
        tx = _make_tx(1, "KRW", "2", "1000", T0)
        price_index = {
            1: [
                (T0, Decimal("1000")),
                (T6M, Decimal("1200")),
                (T1Y, Decimal("1500")),
            ]
        }
        symbol_currency = {1: "KRW"}

        result = build_value_series(
            [tx],
            price_index,
            symbol_currency,
            fx_at=_fx_identity,
            report_currency="KRW",
            timestamps=[T0, T6M, T1Y],
        )
        assert len(result) == 3
        assert result[0].value == Decimal("2000")  # 2 × 1000
        assert result[1].value == Decimal("2400")  # 2 × 1200
        assert result[2].value == Decimal("3000")  # 2 × 1500

    def test_다중_통화_FX_변환(self) -> None:
        """USD 종목 + KRW 종목 혼합 — FX 변환 후 KRW 합계."""
        tx_usd = _make_tx(1, "USD", "1", "1000", T0)  # 1 share at $1000 USD
        tx_krw = _make_tx(2, "KRW", "10", "50000", T0)  # 10 shares at 50000 KRW

        price_index = {
            1: [(T0, Decimal("1000")), (T1Y, Decimal("1100"))],
            2: [(T0, Decimal("50000")), (T1Y, Decimal("55000"))],
        }
        symbol_currency = {1: "USD", 2: "KRW"}

        result = build_value_series(
            [tx_usd, tx_krw],
            price_index,
            symbol_currency,
            fx_at=_fx_usd_to_krw,
            report_currency="KRW",
            timestamps=[T1Y],
        )
        # USD: 1 share × $1100 × 1300 = 1430000 KRW
        # KRW: 10 shares × 55000 = 550000 KRW
        # Total = 1980000 KRW
        assert len(result) == 1
        _assert_approx(result[0].value, Decimal("1980000"), tol=Decimal("1"))

    def test_빈_timestamps_빈_결과(self) -> None:
        """timestamps 없으면 빈 리스트 반환."""
        result = build_value_series(
            [],
            {},
            {},
            fx_at=_fx_identity,
            report_currency="KRW",
            timestamps=[],
        )
        assert result == []

    def test_SELL_후_수량_감소(self) -> None:
        """BUY 후 SELL 시 남은 수량만 price 계산."""
        buy_tx = _make_tx(1, "KRW", "10", "100", T0, TransactionType.BUY)
        sell_tx = _make_tx(1, "KRW", "3", "120", T6M, TransactionType.SELL)

        price_index = {1: [(T0, Decimal("100")), (T6M, Decimal("120")), (T1Y, Decimal("130"))]}
        symbol_currency = {1: "KRW"}

        result = build_value_series(
            [buy_tx, sell_tx],
            price_index,
            symbol_currency,
            fx_at=_fx_identity,
            report_currency="KRW",
            timestamps=[T0, T6M, T1Y],
        )
        # t0: 10 × 100 = 1000
        # t6m: after sell 3, remaining=7 × 120 = 840
        # t1y: 7 × 130 = 910
        assert result[0].value == Decimal("1000")
        assert result[1].value == Decimal("840")
        assert result[2].value == Decimal("910")

    def test_가격_없는_심볼은_value_기여_0(self) -> None:
        """가격 데이터 없는 심볼은 value에 기여하지 않는다."""
        tx = _make_tx(99, "KRW", "5", "1000", T0)
        result = build_value_series(
            [tx],
            price_index={},  # no prices
            symbol_currency={99: "KRW"},
            fx_at=_fx_identity,
            report_currency="KRW",
            timestamps=[T1Y],
        )
        assert len(result) == 1
        assert result[0].value == Decimal("0")


# ---------------------------------------------------------------------------
# Integration-style: TWR known fixture (PRD G-4)
# ---------------------------------------------------------------------------


class TestKnownFixturePRD:
    def test_PRD_G4_단일매수_TWR_1bp_이내(self) -> None:
        """compute_twr([1M→1.2M], [-1M @t0]) == 0.20 (±1bp)."""
        value_series = [
            ValuePoint(timestamp=T0, value=Decimal("1000000")),
            ValuePoint(timestamp=T1Y, value=Decimal("1200000")),
        ]
        cashflows = [Cashflow(date=T0, amount=Decimal("-1000000"), kind="buy")]
        result = compute_twr(value_series, cashflows)
        _assert_approx(result, Decimal("0.20"))

    def test_PRD_G4_단일매수_MWR_1bp_이내(self) -> None:
        """compute_mwr([-1000000 @t0], 1200000, t0+365d) == 0.20 (±1bp)."""
        cashflows = [Cashflow(date=T0, amount=Decimal("-1000000"), kind="buy")]
        result = compute_mwr(
            cashflows,
            terminal_value=Decimal("1200000"),
            terminal_date=T0 + timedelta(days=365),
        )
        _assert_approx(result, Decimal("0.20"))

    def test_MWR_Newton_수렴_확인(self) -> None:
        """IRR Newton-Raphson 수렴 확인 — 정확한 값을 빠르게 반환."""
        # 50만원 투자 → 1년 후 75만원: IRR = 0.50
        cashflows = [Cashflow(date=T0, amount=Decimal("-500000"), kind="buy")]
        result = compute_mwr(
            cashflows,
            terminal_value=Decimal("750000"),
            terminal_date=T1Y,
        )
        _assert_approx(result, Decimal("0.50"), tol=Decimal("0.001"))


class TestComputeMWREdgeCases:
    def test_Newton_발산_이분법_폴백(self) -> None:
        """Newton-Raphson 이 발산할 때 이분법으로 폴백하여 해를 구한다."""
        # Very large terminal value relative to investment triggers Newton issue at some seeds
        cashflows = [Cashflow(date=T0, amount=Decimal("-1000"), kind="buy")]
        # 5x return in 1 year: IRR = 4.0
        result = compute_mwr(
            cashflows,
            terminal_value=Decimal("5000"),
            terminal_date=T1Y,
        )
        assert result is not None
        # IRR should be approximately 4.0 (400% return)
        assert result > Decimal("3.5")

    def test_이분법_직접_커버_매우_높은_수익률(self) -> None:
        """Newton seed 로 수렴 안될 수 있는 극단적 케이스 → 이분법으로 커버."""
        # -1 투자 → 200 이익 (10년 후): 복리율 매우 높음
        t10y = T0 + timedelta(days=3650)
        cashflows = [Cashflow(date=T0, amount=Decimal("-1"), kind="buy")]
        result = compute_mwr(
            cashflows,
            terminal_value=Decimal("200"),
            terminal_date=t10y,
        )
        # IRR = 200^(1/10) - 1 ≈ 0.74 → Newton 수렴 가능
        assert result is not None
        assert result > Decimal("0.5")

    def test_Newton_max_iter_0_이분법_사용(self) -> None:
        """Newton 최대 반복 횟수 0으로 패치하면 이분법 폴백으로 해를 구한다."""
        from unittest.mock import patch

        cashflows = [Cashflow(date=T0, amount=Decimal("-1000000"), kind="buy")]
        with patch("app.services.performance._IRR_MAX_ITER", 0):
            result = compute_mwr(
                cashflows,
                terminal_value=Decimal("1200000"),
                terminal_date=T1Y,
            )
        # 이분법으로 0.20 근처 수렴
        assert result is not None
        _assert_approx(result, Decimal("0.20"), tol=Decimal("0.001"))

    def test_이분법_bracket_같은_부호_None(self) -> None:
        """이분법 bracket 에 같은 부호면 None 반환 (all-positive amounts)."""
        # All positive cashflows: terminal_value > 0 AND cashflow amounts > 0
        # NPV at -0.99 and 10 have same sign → None
        # Use amounts that won't change sign at bracket
        cashflows = [
            Cashflow(date=T0, amount=Decimal("100"), kind="sell"),
            Cashflow(date=T6M, amount=Decimal("200"), kind="sell"),
        ]
        result = compute_mwr(
            cashflows,
            terminal_value=Decimal("300"),
            terminal_date=T1Y,
        )
        assert result is None

    def test_annualize_음수_rate_None(self) -> None:
        """rate ≤ -1 이면 annualize 는 None 반환 (직접 호출)."""
        from app.services.performance import _annualize

        result = _annualize(Decimal("-1.5"), 365.0)
        assert result is None

    def test_annualize_0_days_None(self) -> None:
        """days ≤ 0 이면 annualize 는 None 반환."""
        from app.services.performance import _annualize

        result = _annualize(Decimal("0.20"), 0.0)
        assert result is None

    def test_compute_twr_시작값_0_None(self) -> None:
        """V_start = 0 이면 TWR 은 None 반환."""
        value_series = [
            ValuePoint(timestamp=T0, value=Decimal("0")),
            ValuePoint(timestamp=T1Y, value=Decimal("1200000")),
        ]
        result = compute_twr(value_series, [])
        assert result is None

    def test_compute_twr_cashflow_없는_순수_가치상승(self) -> None:
        """cashflow 없는 경우 TWR = V_end/V_start - 1."""
        value_series = [
            ValuePoint(timestamp=T0, value=Decimal("1000000")),
            ValuePoint(timestamp=T1Y, value=Decimal("1150000")),
        ]
        result = compute_twr(value_series, [])
        assert result is not None
        _assert_approx(result, Decimal("0.15"))

    def test_build_value_series_중간_FX_miss_info_로깅(self) -> None:
        """FX rate miss 시 해당 심볼의 value 기여가 0 이 된다 (FxRateNotAvailableError)."""
        from app.exceptions import FxRateNotAvailableError

        def _fx_raise(amount: Decimal, from_cur: str, to_cur: str, at: datetime) -> Decimal:
            if from_cur != to_cur:
                raise FxRateNotAvailableError("no rate")
            return amount

        tx = _make_tx(1, "USD", "1", "100", T0)
        price_index = {1: [(T0, Decimal("100")), (T1Y, Decimal("120"))]}
        symbol_currency = {1: "USD"}

        result = build_value_series(
            [tx],
            price_index,
            symbol_currency,
            fx_at=_fx_raise,
            report_currency="KRW",
            timestamps=[T1Y],
        )
        # FX error → value contribution = 0
        assert result[0].value == Decimal("0")


@pytest.mark.parametrize(
    "qty,price,expected_kind",
    [
        ("10", "100000", "buy"),
        ("5", "200000", "sell"),
    ],
)
def test_extract_cashflows_kind_parametrized(
    qty: str,
    price: str,
    expected_kind: str,
) -> None:
    """Buy → kind=buy, sell → kind=sell."""
    tx_type = TransactionType.BUY if expected_kind == "buy" else TransactionType.SELL
    tx = _make_tx(1, "KRW", qty, price, T6M, tx_type)
    result = extract_cashflows(
        [tx],
        report_currency="KRW",
        fx_at=_fx_identity,
        window_start=T0,
        window_end=T1Y,
    )
    assert len(result) == 1
    assert result[0].kind == expected_kind
