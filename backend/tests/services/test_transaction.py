"""Unit tests for TransactionService — mocked repositories."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType
from app.exceptions import InsufficientHoldingError, NotFoundError  # MODIFIED
from app.models.asset_symbol import AssetSymbol
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset
from app.repositories.transaction import SummaryAggregates, TransactionRepository  # MODIFIED
from app.repositories.user_asset import UserAssetRepository
from app.schemas.transaction import TransactionCreate, TransactionUpdate  # MODIFIED
from app.services.transaction import TransactionService


def _make_asset_symbol(currency: str = "KRW") -> AssetSymbol:
    sym = AssetSymbol(
        asset_type=AssetType.CRYPTO,
        symbol="BTC",
        exchange="upbit",
        name="Bitcoin",
        currency=currency,
    )
    sym.id = 1
    sym.created_at = datetime.now(UTC)
    sym.updated_at = datetime.now(UTC)
    return sym


def _make_user_asset(user_asset_id: int = 1, user_id: int = 1, currency: str = "KRW") -> UserAsset:
    ua = UserAsset(user_id=user_id, asset_symbol_id=1)
    ua.id = user_asset_id
    ua.asset_symbol = _make_asset_symbol(currency=currency)  # type: ignore[assignment]  # mock relationship
    ua.memo = None
    ua.created_at = datetime.now(UTC)
    ua.updated_at = datetime.now(UTC)
    return ua


def _make_transaction(tx_id: int = 1, user_asset_id: int = 1) -> Transaction:
    tx = Transaction(
        user_asset_id=user_asset_id,
        type=TransactionType.BUY,
        quantity=Decimal("1.0"),
        price=Decimal("50000.0"),
        traded_at=datetime.now(UTC),
    )
    tx.id = tx_id
    tx.memo = None
    tx.created_at = datetime.now(UTC)
    tx.updated_at = datetime.now(UTC)
    return tx


def _buy_data(
    quantity: str = "1.0",
    price: str = "50000.0",
) -> TransactionCreate:
    return TransactionCreate(
        type=TransactionType.BUY,
        quantity=Decimal(quantity),
        price=Decimal(price),
        traded_at=datetime.now(UTC),
    )


def _sell_data(  # ADDED
    quantity: str = "1.0",
    price: str = "55000.0",
) -> TransactionCreate:
    return TransactionCreate(
        type=TransactionType.SELL,
        quantity=Decimal(quantity),
        price=Decimal(price),
        traded_at=datetime.now(UTC),
    )


def _make_aggregates(  # ADDED — helper to build SummaryAggregates
    bought_qty: str = "0",
    bought_cost: str = "0",
    sold_qty: str = "0",
    sold_value: str = "0",
    tx_count: int = 0,
) -> SummaryAggregates:
    return SummaryAggregates(
        total_bought_qty=Decimal(bought_qty),
        total_bought_cost=Decimal(bought_cost),
        total_sold_qty=Decimal(sold_qty),
        total_sold_value=Decimal(sold_value),
        tx_count=tx_count,
    )


def _update_data(
    tx_type: TransactionType = TransactionType.BUY,
    quantity: str = "1.0",
    price: str = "50000.0",
) -> TransactionUpdate:  # ADDED
    return TransactionUpdate(
        type=tx_type,
        quantity=Decimal(quantity),
        price=Decimal(price),
        traded_at=datetime.now(UTC),
    )


def _make_service(
    ua: UserAsset | None = None,
    tx: Transaction | None = None,
    summary: SummaryAggregates | None = None,  # MODIFIED — SummaryAggregates
    remaining_quantity: Decimal | None = None,  # ADDED
    transactions: list[Transaction] | None = None,
    delete_result: bool = True,
    update_result: Transaction | None = None,  # ADDED
) -> TransactionService:
    ua_repo = AsyncMock(spec=UserAssetRepository)
    ua_repo.get_by_id_for_user.return_value = ua

    tx_repo = AsyncMock(spec=TransactionRepository)
    if tx is not None:
        tx_repo.create.return_value = tx
        tx_repo.get_by_id_for_user_asset.return_value = tx
    if summary is not None:
        tx_repo.get_summary.return_value = summary
    if remaining_quantity is not None:  # ADDED
        tx_repo.get_remaining_quantity.return_value = remaining_quantity
    if transactions is not None:
        tx_repo.list_for_user_asset.return_value = transactions
    tx_repo.delete_by_id_for_user_asset.return_value = delete_result
    if update_result is not None:  # ADDED
        tx_repo.update.return_value = update_result

    return TransactionService(transaction_repo=tx_repo, user_asset_repo=ua_repo)


class TestTransactionServiceList:
    async def test_정상_조회(self) -> None:
        ua = _make_user_asset()
        txs = [_make_transaction(tx_id=1), _make_transaction(tx_id=2)]
        svc = _make_service(ua=ua, transactions=txs)

        result = await svc.list(user_id=1, user_asset_id=1)
        assert len(result) == 2

    async def test_소유하지_않은_user_asset이면_NotFoundError(self) -> None:
        svc = _make_service(ua=None)

        with pytest.raises(NotFoundError):
            await svc.list(user_id=1, user_asset_id=999)


class TestTransactionServiceAdd:
    async def test_매수_성공(self) -> None:
        ua = _make_user_asset()
        tx = _make_transaction()
        svc = _make_service(ua=ua, tx=tx)

        result = await svc.add(user_id=1, user_asset_id=1, data=_buy_data())
        assert result.id == tx.id

    async def test_소유하지_않은_user_asset이면_NotFoundError(self) -> None:
        svc = _make_service(ua=None)

        with pytest.raises(NotFoundError):
            await svc.add(user_id=1, user_asset_id=999, data=_buy_data())

    async def test_타_사용자_user_asset이면_NotFoundError(self) -> None:
        # ua_repo returns None because user_id does not match
        svc = _make_service(ua=None)

        with pytest.raises(NotFoundError):
            await svc.add(user_id=2, user_asset_id=1, data=_buy_data())

    async def test_매도_성공_잔여수량_충분(self) -> None:  # ADDED
        ua = _make_user_asset()
        tx = _make_transaction()
        svc = _make_service(ua=ua, tx=tx, remaining_quantity=Decimal("5.0"))

        result = await svc.add(user_id=1, user_asset_id=1, data=_sell_data(quantity="3.0"))
        assert result.id == tx.id

    async def test_매도_잔여수량_초과시_InsufficientHoldingError(self) -> None:  # ADDED
        ua = _make_user_asset()
        svc = _make_service(ua=ua, remaining_quantity=Decimal("2.0"))

        with pytest.raises(InsufficientHoldingError):
            await svc.add(user_id=1, user_asset_id=1, data=_sell_data(quantity="5.0"))

    async def test_매도_잔여수량이_0일때_InsufficientHoldingError(self) -> None:  # ADDED
        ua = _make_user_asset()
        svc = _make_service(ua=ua, remaining_quantity=Decimal("0"))

        with pytest.raises(InsufficientHoldingError):
            await svc.add(user_id=1, user_asset_id=1, data=_sell_data(quantity="1.0"))


class TestTransactionServiceSummary:
    async def test_요약이_올바르게_반환된다(self) -> None:  # MODIFIED — SummaryAggregates
        ua = _make_user_asset(currency="KRW")
        # BUY 3 at 1750 avg, SELL 1 at 2000
        agg = _make_aggregates(
            bought_qty="3.0",
            bought_cost="5250.0",
            sold_qty="1.0",
            sold_value="2000.0",
            tx_count=3,
        )
        svc = _make_service(ua=ua, summary=agg)

        result = await svc.summary(user_id=1, user_asset_id=1)
        assert result.total_bought_quantity == Decimal("3.0")
        assert result.total_sold_quantity == Decimal("1.0")
        assert result.remaining_quantity == Decimal("2.0")
        assert result.avg_buy_price == Decimal("1750.0")
        assert result.total_invested == Decimal("5250.0")
        assert result.total_sold_value == Decimal("2000.0")
        # realized_pnl = 2000 - 1 * 1750 = 250
        assert result.realized_pnl == Decimal("250.0")
        assert result.transaction_count == 3
        assert result.currency == "KRW"

    async def test_currency가_AssetSymbol에서_정확히_매핑된다(self) -> None:
        ua = _make_user_asset(currency="USD")
        agg = _make_aggregates(bought_qty="1.0", bought_cost="50000.0", tx_count=1)
        svc = _make_service(ua=ua, summary=agg)

        result = await svc.summary(user_id=1, user_asset_id=1)
        assert result.currency == "USD"

    async def test_소유하지_않은_user_asset이면_NotFoundError(self) -> None:
        svc = _make_service(ua=None)

        with pytest.raises(NotFoundError):
            await svc.summary(user_id=1, user_asset_id=999)

    async def test_거래_없을때_0값_반환(self) -> None:
        ua = _make_user_asset(currency="KRW")
        agg = _make_aggregates()  # all zeros
        svc = _make_service(ua=ua, summary=agg)

        result = await svc.summary(user_id=1, user_asset_id=1)
        assert result.total_bought_quantity == Decimal("0")
        assert result.remaining_quantity == Decimal("0")
        assert result.avg_buy_price == Decimal("0")
        assert result.realized_pnl == Decimal("0")
        assert result.transaction_count == 0

    async def test_sell만_있을때_realized_pnl_정확(self) -> None:  # ADDED — edge case
        # theoretically impossible via valid flow, but test aggregates math
        ua = _make_user_asset(currency="KRW")
        agg = _make_aggregates(
            bought_qty="5.0",
            bought_cost="10000.0",
            sold_qty="2.0",
            sold_value="4500.0",
            tx_count=2,
        )
        svc = _make_service(ua=ua, summary=agg)

        result = await svc.summary(user_id=1, user_asset_id=1)
        # avg_buy = 10000/5 = 2000, realized = 4500 - 2*2000 = 500
        assert result.avg_buy_price == Decimal("2000.0")
        assert result.realized_pnl == Decimal("500.0")
        assert result.remaining_quantity == Decimal("3.0")


class TestTransactionServiceRemove:
    async def test_정상_삭제(self) -> None:
        ua = _make_user_asset()
        svc = _make_service(ua=ua, delete_result=True)

        # Should not raise
        await svc.remove(user_id=1, user_asset_id=1, transaction_id=1)

    async def test_소유하지_않은_user_asset이면_NotFoundError(self) -> None:
        svc = _make_service(ua=None)

        with pytest.raises(NotFoundError):
            await svc.remove(user_id=1, user_asset_id=999, transaction_id=1)

    async def test_존재하지_않는_transaction이면_NotFoundError(self) -> None:
        ua = _make_user_asset()
        svc = _make_service(ua=ua, delete_result=False)

        with pytest.raises(NotFoundError):
            await svc.remove(user_id=1, user_asset_id=1, transaction_id=9999)

    async def test_타_사용자_transaction_삭제시_NotFoundError(self) -> None:
        # The ua_repo returns None when user_id doesn't own the user_asset
        svc = _make_service(ua=None)

        with pytest.raises(NotFoundError):
            await svc.remove(user_id=2, user_asset_id=1, transaction_id=1)


class TestTransactionServiceEdit:  # ADDED
    async def test_edit_성공_BUY_수정(self) -> None:
        ua = _make_user_asset()
        tx = _make_transaction()
        updated_tx = _make_transaction()
        updated_tx.quantity = Decimal("2.0")

        # 기존 tx 는 BUY 1.0 → 수정 후 BUY 2.0, 전체 집계는 bought=1.0
        agg = _make_aggregates(bought_qty="1.0", bought_cost="50000.0", tx_count=1)
        svc = _make_service(ua=ua, tx=tx, summary=agg, update_result=updated_tx)

        result = await svc.edit(
            user_id=1,
            user_asset_id=1,
            transaction_id=1,
            data=_update_data(tx_type=TransactionType.BUY, quantity="2.0"),
        )
        assert result.quantity == Decimal("2.0")

    async def test_edit_성공_SELL_수정_보유_충분(self) -> None:
        ua = _make_user_asset()
        # 기존 tx: BUY 1.0, 다른 tx: BUY 5.0 → total bought=6.0, sold=0
        tx = _make_transaction()
        updated_tx = _make_transaction()
        updated_tx.type = TransactionType.SELL
        updated_tx.quantity = Decimal("3.0")

        agg = _make_aggregates(bought_qty="6.0", bought_cost="300000.0", tx_count=2)
        svc = _make_service(ua=ua, tx=tx, summary=agg, update_result=updated_tx)

        result = await svc.edit(
            user_id=1,
            user_asset_id=1,
            transaction_id=1,
            data=_update_data(tx_type=TransactionType.SELL, quantity="3.0"),
        )
        assert result.type == TransactionType.SELL

    async def test_edit_ua_없으면_NotFoundError(self) -> None:
        svc = _make_service(ua=None)

        with pytest.raises(NotFoundError):
            await svc.edit(
                user_id=1,
                user_asset_id=999,
                transaction_id=1,
                data=_update_data(),
            )

    async def test_edit_tx_없으면_NotFoundError(self) -> None:
        ua = _make_user_asset()
        # tx_repo.get_by_id_for_user_asset returns None (tx not found)
        ua_repo = AsyncMock(spec=UserAssetRepository)
        ua_repo.get_by_id_for_user.return_value = ua
        tx_repo = AsyncMock(spec=TransactionRepository)
        tx_repo.get_by_id_for_user_asset.return_value = None
        svc = TransactionService(transaction_repo=tx_repo, user_asset_repo=ua_repo)

        with pytest.raises(NotFoundError):
            await svc.edit(
                user_id=1,
                user_asset_id=1,
                transaction_id=9999,
                data=_update_data(),
            )

    async def test_edit_SELL로_변경_보유_부족시_InsufficientHoldingError(self) -> None:
        ua = _make_user_asset()
        # 기존 tx: BUY 1.0, 전체 집계 bought=1.0 sold=0
        # 수정: BUY→SELL 5.0 → hypothetical = (1-1) - 5 = -5 < 0
        tx = _make_transaction()  # BUY 1.0
        agg = _make_aggregates(bought_qty="1.0", bought_cost="50000.0", tx_count=1)
        svc = _make_service(ua=ua, tx=tx, summary=agg)

        with pytest.raises(InsufficientHoldingError):
            await svc.edit(
                user_id=1,
                user_asset_id=1,
                transaction_id=1,
                data=_update_data(tx_type=TransactionType.SELL, quantity="5.0"),
            )

    async def test_edit_BUY_수량_변경_정상(self) -> None:
        ua = _make_user_asset()
        # 기존 BUY 1.0, 전체 bought=3.0 sold=1.0 → other_bought=2.0 other_sold=1.0
        # 수정 후 BUY 4.0 → hypothetical = 2+4-1 = 5 ≥ 0 → OK
        tx = _make_transaction()
        updated_tx = _make_transaction()
        updated_tx.quantity = Decimal("4.0")

        agg = _make_aggregates(
            bought_qty="3.0",
            bought_cost="150000.0",
            sold_qty="1.0",
            sold_value="55000.0",
            tx_count=3,
        )
        svc = _make_service(ua=ua, tx=tx, summary=agg, update_result=updated_tx)

        result = await svc.edit(
            user_id=1,
            user_asset_id=1,
            transaction_id=1,
            data=_update_data(tx_type=TransactionType.BUY, quantity="4.0"),
        )
        assert result.quantity == Decimal("4.0")


class TestTransactionServiceListPagination:
    async def test_limit과_offset이_repo로_전달된다(self) -> None:
        ua = _make_user_asset()
        ua_repo = AsyncMock(spec=UserAssetRepository)
        ua_repo.get_by_id_for_user.return_value = ua

        tx_repo = AsyncMock(spec=TransactionRepository)
        tx_repo.list_for_user_asset.return_value = []

        svc = TransactionService(transaction_repo=tx_repo, user_asset_repo=ua_repo)
        await svc.list(user_id=1, user_asset_id=1, limit=10, offset=20)

        tx_repo.list_for_user_asset.assert_called_once_with(1, limit=10, offset=20)


# Helper for type-checking — ensure service does not use Any from mock
def _check_types(data: Any) -> None:  # noqa: ANN401
    pass
