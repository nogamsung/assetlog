"""Unit tests for CashAccountService — mocked repository, pure logic."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.exceptions import NotFoundError
from app.models.cash_account import CashAccount
from app.repositories.cash_account import CashAccountRepository
from app.schemas.cash_account import CashAccountCreate, CashAccountUpdate
from app.services.cash_account import CashAccountService


def _make_account(
    id_: int = 1,
    label: str = "Test Account",
    currency: str = "KRW",
    balance: str = "1000000.0000",
) -> CashAccount:
    from datetime import UTC, datetime

    account = CashAccount(label=label, currency=currency, balance=Decimal(balance))
    account.id = id_
    account.created_at = datetime.now(UTC)
    account.updated_at = datetime.now(UTC)
    return account


def _make_service(mock_repo: CashAccountRepository) -> CashAccountService:
    return CashAccountService(mock_repo)


class TestCashAccountServiceList:
    async def test_빈_목록_반환(self) -> None:
        repo = AsyncMock(spec=CashAccountRepository)
        repo.list_all.return_value = []
        svc = _make_service(repo)
        result = await svc.list()
        assert list(result) == []
        repo.list_all.assert_called_once()

    async def test_계정_목록_반환(self) -> None:
        repo = AsyncMock(spec=CashAccountRepository)
        accounts = [_make_account(1), _make_account(2, label="USD Account", currency="USD")]
        repo.list_all.return_value = accounts
        svc = _make_service(repo)
        result = await svc.list()
        assert list(result) == accounts


class TestCashAccountServiceCreate:
    async def test_정상_생성(self) -> None:
        repo = AsyncMock(spec=CashAccountRepository)
        account = _make_account()
        repo.create.return_value = account

        svc = _make_service(repo)
        data = CashAccountCreate(label="Test Account", currency="KRW", balance=Decimal("1000000"))
        result = await svc.create(data)

        assert result == account
        repo.create.assert_called_once_with(
            label="Test Account",
            currency="KRW",
            balance=Decimal("1000000"),
        )

    async def test_생성된_계정_반환(self) -> None:
        repo = AsyncMock(spec=CashAccountRepository)
        account = _make_account(id_=42, label="My Account", currency="USD")
        repo.create.return_value = account

        svc = _make_service(repo)
        data = CashAccountCreate(label="My Account", currency="USD", balance=Decimal("500"))
        result = await svc.create(data)

        assert result.id == 42
        assert result.currency == "USD"


class TestCashAccountServiceUpdate:
    async def test_없는_id_NotFoundError_발생(self) -> None:
        repo = AsyncMock(spec=CashAccountRepository)
        repo.get_by_id.return_value = None

        svc = _make_service(repo)
        data = CashAccountUpdate(label="New Label")
        with pytest.raises(NotFoundError, match="CashAccount 999 not found"):
            await svc.update(999, data)

    async def test_label만_업데이트(self) -> None:
        repo = AsyncMock(spec=CashAccountRepository)
        original = _make_account(label="Old Label")
        updated = _make_account(label="New Label")
        repo.get_by_id.return_value = original
        repo.update.return_value = updated

        svc = _make_service(repo)
        data = CashAccountUpdate(label="New Label")
        result = await svc.update(1, data)

        repo.update.assert_called_once_with(original, label="New Label", balance=None)
        assert result.label == "New Label"

    async def test_balance만_업데이트(self) -> None:
        repo = AsyncMock(spec=CashAccountRepository)
        original = _make_account()
        updated = _make_account(balance="9999.0000")
        repo.get_by_id.return_value = original
        repo.update.return_value = updated

        svc = _make_service(repo)
        data = CashAccountUpdate(balance=Decimal("9999"))
        result = await svc.update(1, data)

        repo.update.assert_called_once_with(original, label=None, balance=Decimal("9999"))
        assert result.balance == Decimal("9999.0000")

    async def test_둘_다_업데이트(self) -> None:
        repo = AsyncMock(spec=CashAccountRepository)
        original = _make_account()
        updated = _make_account(label="New", balance="500.0000")
        repo.get_by_id.return_value = original
        repo.update.return_value = updated

        svc = _make_service(repo)
        data = CashAccountUpdate(label="New", balance=Decimal("500"))
        result = await svc.update(1, data)

        repo.update.assert_called_once_with(original, label="New", balance=Decimal("500"))
        assert result.label == "New"


class TestCashAccountServiceDelete:
    async def test_없는_id_NotFoundError_발생(self) -> None:
        repo = AsyncMock(spec=CashAccountRepository)
        repo.get_by_id.return_value = None

        svc = _make_service(repo)
        with pytest.raises(NotFoundError, match="CashAccount 99 not found"):
            await svc.delete(99)

    async def test_정상_삭제(self) -> None:
        repo = AsyncMock(spec=CashAccountRepository)
        account = _make_account()
        repo.get_by_id.return_value = account
        repo.delete.return_value = None

        svc = _make_service(repo)
        await svc.delete(1)

        repo.delete.assert_called_once_with(account)
