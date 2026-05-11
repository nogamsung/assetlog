"""Unit tests for TaxKrService — mocked repos + FX."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType
from app.exceptions import FxRateNotAvailableError
from app.models.asset_symbol import AssetSymbol
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset
from app.repositories.asset_symbol import AssetSymbolRepository
from app.repositories.portfolio_history import PortfolioHistoryRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.user_asset import UserAssetRepository
from app.services.fx_rate import FxRateService
from app.services.tax_kr import TaxKrService


def _make_symbol(
    sym_id: int = 1,
    symbol: str = "AAPL",
    currency: str = "USD",
    asset_type: AssetType = AssetType.US_STOCK,
) -> AssetSymbol:
    sym = AssetSymbol(
        asset_type=asset_type,
        symbol=symbol,
        exchange="NASDAQ",
        name=symbol,
        currency=currency,
    )
    sym.id = sym_id
    return sym


def _make_tx(
    tx_type: TransactionType,
    quantity: str,
    price: str,
    traded_at: datetime,
    user_asset_id: int = 1,
) -> Transaction:
    tx = Transaction(
        user_asset_id=user_asset_id,
        type=tx_type,
        quantity=Decimal(quantity),
        price=Decimal(price),
        traded_at=traded_at,
    )
    return tx


def _make_service(
    *,
    symbols: list[AssetSymbol] | None = None,
    txs_by_symbol_id: dict[int, list[Transaction]] | None = None,
    fx_rates: dict[tuple[str, str, str], Decimal] | None = None,
) -> TaxKrService:
    """Build a TaxKrService with everything mocked.

    *fx_rates* keys are (from, to, isoformat_date) → Decimal rate.
    """
    sym_repo = AsyncMock(spec=AssetSymbolRepository)
    sym_repo.search.side_effect = lambda asset_type=None, **_: [
        s for s in (symbols or []) if s.asset_type == asset_type
    ]

    ua_repo = AsyncMock(spec=UserAssetRepository)

    def _ua_by_symbol(sid: int) -> UserAsset | None:
        if not symbols:
            return None
        ua = UserAsset(asset_symbol_id=sid)
        ua.id = sid  # 1:1 sym_id ↔ ua_id for tests
        return ua

    ua_repo.get_by_symbol.side_effect = _ua_by_symbol

    tx_repo = AsyncMock(spec=TransactionRepository)
    tx_repo.list_all_for_user_asset.side_effect = lambda ua_id: (
        (txs_by_symbol_id or {}).get(ua_id, [])
    )

    fx = AsyncMock(spec=FxRateService)

    async def _convert_at(
        amount: Decimal, frm: str, to: str, at: datetime
    ) -> Decimal:
        if frm == to:
            return amount
        rate = (fx_rates or {}).get((frm, to, at.date().isoformat()))
        if rate is None:
            raise FxRateNotAvailableError()
        return amount * rate

    async def _convert(amount: Decimal, frm: str, to: str) -> Decimal:
        if frm == to:
            return amount
        raise FxRateNotAvailableError()

    fx.convert_at.side_effect = _convert_at
    fx.convert.side_effect = _convert

    history_repo = AsyncMock(spec=PortfolioHistoryRepository)

    return TaxKrService(
        history_repo=history_repo,
        symbol_repo=sym_repo,
        tx_repo=tx_repo,
        user_asset_repo=ua_repo,
        fx_service=fx,
    )


class TestEmptyAndDefaults:
    async def test_심볼_없으면_0(self) -> None:
        svc = _make_service(symbols=[])
        result = await svc.get_capital_gains(2025)
        assert result.gross_gain_krw == Decimal("0")
        assert result.estimated_tax_krw == Decimal("0")
        assert result.sales == []

    async def test_default_deduction_2_5M(self) -> None:
        svc = _make_service(symbols=[])
        result = await svc.get_capital_gains(2025)
        assert result.deduction_krw == Decimal("2500000")
        assert result.tax_rate == Decimal("0.22")


class TestAverageMethod:
    async def test_정상_평균_손익(self) -> None:
        sym = _make_symbol()
        # BUY 10 @ $100 (2024-01-01), FX 1300 → cost basis 1_300_000 KRW
        # SELL 10 @ $150 (2025-06-01), FX 1400 → proceeds 2_100_000 KRW
        # gain = 800_000 KRW
        txs = [
            _make_tx(
                TransactionType.BUY,
                "10",
                "100",
                datetime(2024, 1, 1, tzinfo=UTC),
            ),
            _make_tx(
                TransactionType.SELL,
                "10",
                "150",
                datetime(2025, 6, 1, tzinfo=UTC),
            ),
        ]
        svc = _make_service(
            symbols=[sym],
            txs_by_symbol_id={1: txs},
            fx_rates={
                ("USD", "KRW", "2024-01-01"): Decimal("1300"),
                ("USD", "KRW", "2025-06-01"): Decimal("1400"),
            },
        )
        result = await svc.get_capital_gains(2025, method="average")
        assert len(result.sales) == 1
        s = result.sales[0]
        assert s.sell_value_krw == Decimal("2100000")
        assert s.cost_basis_krw == Decimal("1300000")
        assert s.realized_gain_krw == Decimal("800000")
        # 800_000 < 2_500_000 deduction → no taxable
        assert result.taxable_gain_krw == Decimal("0")
        assert result.estimated_tax_krw == Decimal("0")

    async def test_큰_차익_세금_발생(self) -> None:
        sym = _make_symbol()
        txs = [
            _make_tx(
                TransactionType.BUY,
                "10",
                "100",
                datetime(2024, 1, 1, tzinfo=UTC),
            ),
            _make_tx(
                TransactionType.SELL,
                "10",
                "200",
                datetime(2025, 6, 1, tzinfo=UTC),
            ),
        ]
        # cost 1_300_000, proceeds 2_800_000 → gain 1_500_000 KRW × 2 SELLs equiv
        # Actually just one SELL — gain = 2_800_000 - 1_300_000 = 1_500_000 KRW
        svc = _make_service(
            symbols=[sym],
            txs_by_symbol_id={1: txs},
            fx_rates={
                ("USD", "KRW", "2024-01-01"): Decimal("1300"),
                ("USD", "KRW", "2025-06-01"): Decimal("1400"),
            },
        )
        # Bump qty to push above deduction:
        # buy 10 @ 100, FX 1300 = 1_300_000 cost
        # sell 10 @ 500, FX 1400 = 7_000_000 proceeds → gain 5_700_000 KRW
        sym2 = _make_symbol(sym_id=2, symbol="MSFT")
        txs2 = [
            _make_tx(
                TransactionType.BUY,
                "10",
                "100",
                datetime(2024, 1, 1, tzinfo=UTC),
                user_asset_id=2,
            ),
            _make_tx(
                TransactionType.SELL,
                "10",
                "500",
                datetime(2025, 6, 1, tzinfo=UTC),
                user_asset_id=2,
            ),
        ]
        svc = _make_service(
            symbols=[sym2],
            txs_by_symbol_id={2: txs2},
            fx_rates={
                ("USD", "KRW", "2024-01-01"): Decimal("1300"),
                ("USD", "KRW", "2025-06-01"): Decimal("1400"),
            },
        )
        result = await svc.get_capital_gains(2025, method="average")
        # gain = 5_700_000 - 0 deduction effect after 2_500_000 = taxable 3_200_000
        assert result.gross_gain_krw == Decimal("5700000")
        assert result.taxable_gain_krw == Decimal("3200000")
        # estimated = 3_200_000 × 0.22 = 704_000
        assert result.estimated_tax_krw == Decimal("704000.00")

    async def test_연도_밖_sell_제외(self) -> None:
        sym = _make_symbol()
        txs = [
            _make_tx(
                TransactionType.BUY,
                "10",
                "100",
                datetime(2024, 1, 1, tzinfo=UTC),
            ),
            _make_tx(
                TransactionType.SELL,
                "5",
                "150",
                datetime(2024, 6, 1, tzinfo=UTC),
            ),
        ]
        svc = _make_service(
            symbols=[sym],
            txs_by_symbol_id={1: txs},
            fx_rates={
                ("USD", "KRW", "2024-01-01"): Decimal("1300"),
                ("USD", "KRW", "2024-06-01"): Decimal("1400"),
            },
        )
        result = await svc.get_capital_gains(2025, method="average")
        assert result.sales == []


class TestFifoMethod:
    async def test_fifo_여러_lot_매칭(self) -> None:
        sym = _make_symbol()
        # BUY 5 @ 100 (2023-01), BUY 5 @ 200 (2024-01), SELL 7 @ 250 (2025-06)
        # FIFO: first 5 @ 100 + next 2 @ 200 = cost local 5*100 + 2*200 = 900
        # All BUY FX 1300, SELL FX 1400
        # cost_basis_krw = 900 × 1300 = 1_170_000
        # sell_value_krw = 7 × 250 × 1400 = 2_450_000
        # gain = 1_280_000
        txs = [
            _make_tx(
                TransactionType.BUY,
                "5",
                "100",
                datetime(2023, 1, 1, tzinfo=UTC),
            ),
            _make_tx(
                TransactionType.BUY,
                "5",
                "200",
                datetime(2024, 1, 1, tzinfo=UTC),
            ),
            _make_tx(
                TransactionType.SELL,
                "7",
                "250",
                datetime(2025, 6, 1, tzinfo=UTC),
            ),
        ]
        svc = _make_service(
            symbols=[sym],
            txs_by_symbol_id={1: txs},
            fx_rates={
                ("USD", "KRW", "2023-01-01"): Decimal("1300"),
                ("USD", "KRW", "2024-01-01"): Decimal("1300"),
                ("USD", "KRW", "2025-06-01"): Decimal("1400"),
            },
        )
        result = await svc.get_capital_gains(2025, method="fifo")
        s = result.sales[0]
        assert s.cost_basis_krw == Decimal("1170000")
        assert s.sell_value_krw == Decimal("2450000")
        assert s.realized_gain_krw == Decimal("1280000")

    async def test_fifo_oversold_warning(self) -> None:
        sym = _make_symbol()
        # SELL more than was bought
        txs = [
            _make_tx(
                TransactionType.BUY,
                "5",
                "100",
                datetime(2023, 1, 1, tzinfo=UTC),
            ),
            _make_tx(
                TransactionType.SELL,
                "10",
                "150",
                datetime(2025, 6, 1, tzinfo=UTC),
            ),
        ]
        svc = _make_service(
            symbols=[sym],
            txs_by_symbol_id={1: txs},
            fx_rates={
                ("USD", "KRW", "2023-01-01"): Decimal("1300"),
                ("USD", "KRW", "2025-06-01"): Decimal("1400"),
            },
        )
        result = await svc.get_capital_gains(2025, method="fifo")
        assert any(w.startswith("oversold:") for w in result.warnings)


class TestFxFallback:
    async def test_missing_historical_warning(self) -> None:
        sym = _make_symbol()
        txs = [
            _make_tx(
                TransactionType.BUY,
                "10",
                "100",
                datetime(2024, 1, 1, tzinfo=UTC),
            ),
            _make_tx(
                TransactionType.SELL,
                "10",
                "150",
                datetime(2025, 6, 1, tzinfo=UTC),
            ),
        ]
        # No FX rates at all
        svc = _make_service(symbols=[sym], txs_by_symbol_id={1: txs}, fx_rates={})
        result = await svc.get_capital_gains(2025, method="average")
        assert any(w.startswith("fx_rate_missing:") for w in result.warnings)
