"""Unit tests for TransactionService — mocked repositories."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType
from app.exceptions import NotFoundError
from app.models.asset_symbol import AssetSymbol
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset
from app.repositories.transaction import TransactionRepository
from app.repositories.user_asset import UserAssetRepository
from app.schemas.transaction import TransactionCreate
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


def _make_service(
    ua: UserAsset | None = None,
    tx: Transaction | None = None,
    summary: tuple[Decimal, Decimal, Decimal, int] | None = None,
    transactions: list[Transaction] | None = None,
    delete_result: bool = True,
) -> TransactionService:
    ua_repo = AsyncMock(spec=UserAssetRepository)
    ua_repo.get_by_id_for_user.return_value = ua

    tx_repo = AsyncMock(spec=TransactionRepository)
    if tx is not None:
        tx_repo.create.return_value = tx
    if summary is not None:
        tx_repo.get_summary.return_value = summary
    if transactions is not None:
        tx_repo.list_for_user_asset.return_value = transactions
    tx_repo.delete_by_id_for_user_asset.return_value = delete_result

    return TransactionService(transaction_repo=tx_repo, user_asset_repo=ua_repo)


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


class TestTransactionServiceSummary:
    async def test_요약이_올바르게_반환된다(self) -> None:
        ua = _make_user_asset(currency="KRW")
        summary_data = (Decimal("3.0"), Decimal("1750.0"), Decimal("5250.0"), 2)
        svc = _make_service(ua=ua, summary=summary_data)

        result = await svc.summary(user_id=1, user_asset_id=1)
        assert result.total_quantity == Decimal("3.0")
        assert result.avg_buy_price == Decimal("1750.0")
        assert result.total_invested == Decimal("5250.0")
        assert result.transaction_count == 2
        assert result.currency == "KRW"

    async def test_currency가_AssetSymbol에서_정확히_매핑된다(self) -> None:
        ua = _make_user_asset(currency="USD")
        summary_data = (Decimal("1.0"), Decimal("50000.0"), Decimal("50000.0"), 1)
        svc = _make_service(ua=ua, summary=summary_data)

        result = await svc.summary(user_id=1, user_asset_id=1)
        assert result.currency == "USD"

    async def test_소유하지_않은_user_asset이면_NotFoundError(self) -> None:
        svc = _make_service(ua=None)

        with pytest.raises(NotFoundError):
            await svc.summary(user_id=1, user_asset_id=999)

    async def test_거래_없을때_0값_반환(self) -> None:
        ua = _make_user_asset(currency="KRW")
        summary_data = (Decimal("0"), Decimal("0"), Decimal("0"), 0)
        svc = _make_service(ua=ua, summary=summary_data)

        result = await svc.summary(user_id=1, user_asset_id=1)
        assert result.total_quantity == Decimal("0")
        assert result.avg_buy_price == Decimal("0")
        assert result.transaction_count == 0


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
