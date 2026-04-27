"""Tests for CashAccountRepository — CRUD and sum_balance_by_currency."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cash_account import CashAccount
from app.repositories.cash_account import CashAccountRepository


async def _create_account(
    session: AsyncSession,
    label: str = "Test Account",
    currency: str = "KRW",
    balance: str = "1000000.0000",
) -> CashAccount:
    repo = CashAccountRepository(session)
    return await repo.create(label=label, currency=currency, balance=Decimal(balance))


class TestCashAccountRepositoryCreate:
    async def test_계정_생성_후_id_부여됨(self, db_session: AsyncSession) -> None:
        repo = CashAccountRepository(db_session)
        account = await repo.create(
            label="KRW Account", currency="KRW", balance=Decimal("500000.0000")
        )
        assert account.id is not None
        assert account.label == "KRW Account"
        assert account.currency == "KRW"
        assert account.balance == Decimal("500000.0000")

    async def test_생성된_계정_조회됨(self, db_session: AsyncSession) -> None:
        account = await _create_account(db_session)
        repo = CashAccountRepository(db_session)
        fetched = await repo.get_by_id(account.id)
        assert fetched is not None
        assert fetched.id == account.id


class TestCashAccountRepositoryGetById:
    async def test_존재하지_않는_id는_None_반환(self, db_session: AsyncSession) -> None:
        repo = CashAccountRepository(db_session)
        result = await repo.get_by_id(999999)
        assert result is None

    async def test_올바른_id_조회(self, db_session: AsyncSession) -> None:
        account = await _create_account(db_session, label="USD Account", currency="USD")
        repo = CashAccountRepository(db_session)
        result = await repo.get_by_id(account.id)
        assert result is not None
        assert result.label == "USD Account"


class TestCashAccountRepositoryListAll:
    async def test_빈_목록_반환(self, db_session: AsyncSession) -> None:
        repo = CashAccountRepository(db_session)
        results = await repo.list_all()
        assert list(results) == []

    async def test_여러_계정_전부_반환(self, db_session: AsyncSession) -> None:
        await _create_account(db_session, label="First", currency="KRW")
        await _create_account(db_session, label="Second", currency="USD")
        repo = CashAccountRepository(db_session)
        results = list(await repo.list_all())
        assert len(results) == 2

    async def test_두_계정_모두_반환됨(self, db_session: AsyncSession) -> None:
        first = await _create_account(db_session, label="First")
        second = await _create_account(db_session, label="Second")
        repo = CashAccountRepository(db_session)
        results = list(await repo.list_all())
        # Both accounts must be present (order is created_at desc)
        result_ids = {r.id for r in results}
        assert first.id in result_ids
        assert second.id in result_ids


class TestCashAccountRepositoryUpdate:
    async def test_label_변경(self, db_session: AsyncSession) -> None:
        account = await _create_account(db_session, label="Old Label")
        repo = CashAccountRepository(db_session)
        updated = await repo.update(account, label="New Label", balance=None)
        assert updated.label == "New Label"
        assert updated.balance == Decimal("1000000.0000")  # unchanged

    async def test_balance_변경(self, db_session: AsyncSession) -> None:
        account = await _create_account(db_session, balance="1000.0000")
        repo = CashAccountRepository(db_session)
        updated = await repo.update(account, label=None, balance=Decimal("2000.0000"))
        assert updated.balance == Decimal("2000.0000")
        assert updated.label == "Test Account"  # unchanged

    async def test_label_balance_동시_변경(self, db_session: AsyncSession) -> None:
        account = await _create_account(db_session, label="Old", balance="500.0000")
        repo = CashAccountRepository(db_session)
        updated = await repo.update(account, label="New", balance=Decimal("9999.0000"))
        assert updated.label == "New"
        assert updated.balance == Decimal("9999.0000")


class TestCashAccountRepositoryDelete:
    async def test_삭제_후_조회_불가(self, db_session: AsyncSession) -> None:
        account = await _create_account(db_session)
        repo = CashAccountRepository(db_session)
        await repo.delete(account)
        result = await repo.get_by_id(account.id)
        assert result is None


class TestCashAccountRepositorySumByCurrency:
    async def test_빈_상태_빈_dict_반환(self, db_session: AsyncSession) -> None:
        repo = CashAccountRepository(db_session)
        result = await repo.sum_balance_by_currency()
        assert result == {}

    async def test_단일_통화_합산(self, db_session: AsyncSession) -> None:
        await _create_account(db_session, currency="KRW", balance="1000000.0000")
        await _create_account(db_session, currency="KRW", balance="500000.0000")
        repo = CashAccountRepository(db_session)
        result = await repo.sum_balance_by_currency()
        assert result["KRW"] == Decimal("1500000.0000")

    async def test_다중_통화_분리_집계(self, db_session: AsyncSession) -> None:
        await _create_account(db_session, currency="KRW", balance="1000000.0000")
        await _create_account(db_session, currency="USD", balance="1000.0000")
        await _create_account(db_session, currency="KRW", balance="500000.0000")
        repo = CashAccountRepository(db_session)
        result = await repo.sum_balance_by_currency()
        assert result["KRW"] == Decimal("1500000.0000")
        assert result["USD"] == Decimal("1000.0000")

    async def test_단일_계정_합산(self, db_session: AsyncSession) -> None:
        await _create_account(db_session, currency="EUR", balance="2000.0000")
        repo = CashAccountRepository(db_session)
        result = await repo.sum_balance_by_currency()
        assert result["EUR"] == Decimal("2000.0000")


@pytest.mark.usefixtures("db_session")
class TestCashAccountModel:
    async def test_created_at_populated(self, db_session: AsyncSession) -> None:
        account = await _create_account(db_session)
        assert account.created_at is not None
        assert account.updated_at is not None
