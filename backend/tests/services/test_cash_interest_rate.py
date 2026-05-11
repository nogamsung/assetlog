"""Integration tests for CashAccount.interest_rate_annual field (#76)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.cash_account import CashAccountRepository
from app.schemas.cash_account import (
    CashAccountCreate,
    CashAccountResponse,
    CashAccountUpdate,
)
from app.services.cash_account import CashAccountService


@pytest.fixture()
def service(db_session: AsyncSession) -> CashAccountService:
    return CashAccountService(CashAccountRepository(db_session))


class TestCreateWithInterestRate:
    async def test_생성시_interest_rate_저장(self, service: CashAccountService) -> None:
        account = await service.create(
            CashAccountCreate(
                label="KRW Savings",
                currency="KRW",
                balance=Decimal("1000000"),
                interest_rate_annual=Decimal("0.0350"),
            )
        )
        assert account.interest_rate_annual == Decimal("0.0350")

    async def test_interest_rate_없으면_None(self, service: CashAccountService) -> None:
        account = await service.create(
            CashAccountCreate(
                label="USD Cash",
                currency="USD",
                balance=Decimal("500.0000"),
            )
        )
        assert account.interest_rate_annual is None


class TestUpdateInterestRate:
    async def test_interest_rate_갱신(self, service: CashAccountService) -> None:
        account = await service.create(
            CashAccountCreate(
                label="KRW Savings",
                currency="KRW",
                balance=Decimal("1000000"),
            )
        )
        updated = await service.update(
            account.id,
            CashAccountUpdate(interest_rate_annual=Decimal("0.0450")),
        )
        assert updated.interest_rate_annual == Decimal("0.0450")


class TestResponseSerialisation:
    async def test_response_serialisation(self, service: CashAccountService) -> None:
        account = await service.create(
            CashAccountCreate(
                label="KRW Savings",
                currency="KRW",
                balance=Decimal("1000000"),
                interest_rate_annual=Decimal("0.0350"),
            )
        )
        resp = CashAccountResponse.model_validate(account)
        body = resp.model_dump()
        assert body["interest_rate_annual"] == "0.0350"

    async def test_response_serialisation_none(self, service: CashAccountService) -> None:
        account = await service.create(
            CashAccountCreate(
                label="USD Cash",
                currency="USD",
                balance=Decimal("500"),
            )
        )
        resp = CashAccountResponse.model_validate(account)
        body = resp.model_dump()
        assert body["interest_rate_annual"] is None


class TestSchemaValidation:
    def test_interest_rate_range(self) -> None:
        # 0–1 fraction (0% to 100%) — values outside should 422
        with pytest.raises(ValueError):
            CashAccountCreate(
                label="x",
                currency="USD",
                balance=Decimal("100"),
                interest_rate_annual=Decimal("1.5"),
            )
        with pytest.raises(ValueError):
            CashAccountCreate(
                label="x",
                currency="USD",
                balance=Decimal("100"),
                interest_rate_annual=Decimal("-0.01"),
            )

    def test_update_빈_요청_거부(self) -> None:
        with pytest.raises(ValueError):
            CashAccountUpdate()
