"""Integration tests for /api/cash-accounts router."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_cash_account_service, get_current_user
from app.core.principal import OwnerPrincipal
from app.exceptions import NotFoundError
from app.main import app
from app.models.cash_account import CashAccount
from app.services.cash_account import CashAccountService


def _make_account(
    id_: int = 1,
    label: str = "Test Account",
    currency: str = "KRW",
    balance: str = "1000000.0000",
) -> CashAccount:
    account = CashAccount(label=label, currency=currency, balance=Decimal(balance))
    account.id = id_
    account.created_at = datetime.now(UTC)
    account.updated_at = datetime.now(UTC)
    return account


class TestListCashAccounts:
    async def test_인증_없이_접근하면_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/cash-accounts")
        assert response.status_code == 401

    async def test_빈_목록_반환(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        mock_service = AsyncMock(spec=CashAccountService)
        mock_service.list.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_cash_account_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/cash-accounts")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_cash_account_service, None)

    async def test_계정_목록_반환(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        accounts = [
            _make_account(1, "KRW Account", "KRW", "1000000.0000"),
            _make_account(2, "USD Account", "USD", "500.0000"),
        ]
        mock_service = AsyncMock(spec=CashAccountService)
        mock_service.list.return_value = accounts

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_cash_account_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/cash-accounts")
            assert response.status_code == 200
            body = response.json()
            assert len(body) == 2
            assert body[0]["label"] == "KRW Account"
            assert body[0]["currency"] == "KRW"
            assert body[1]["label"] == "USD Account"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_cash_account_service, None)


class TestCreateCashAccount:
    async def test_인증_없이_생성하면_401(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/cash-accounts",
            json={"label": "Test", "currency": "KRW", "balance": "1000"},
        )
        assert response.status_code == 401

    async def test_정상_생성_201(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        account = _make_account(label="My Account", currency="KRW", balance="1000000.0000")
        mock_service = AsyncMock(spec=CashAccountService)
        mock_service.create.return_value = account

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_cash_account_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/cash-accounts",
                json={"label": "My Account", "currency": "KRW", "balance": "1000000"},
            )
            assert response.status_code == 201
            body = response.json()
            assert body["label"] == "My Account"
            assert body["currency"] == "KRW"
            assert body["balance"] == "1000000.0000"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_cash_account_service, None)

    async def test_음수_balance_422(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.post(
                "/api/cash-accounts",
                json={"label": "Test", "currency": "KRW", "balance": "-100"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_소문자_currency_자동_대문자_정규화_201(self, async_client: AsyncClient) -> None:
        # validator strips and uppercases: "krw" → "KRW" (valid 3-letter code)
        user = OwnerPrincipal()
        account = _make_account(currency="KRW", balance="1000.0000")
        mock_service = AsyncMock(spec=CashAccountService)
        mock_service.create.return_value = account

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_cash_account_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/cash-accounts",
                json={"label": "Test", "currency": "krw", "balance": "1000"},
            )
            assert response.status_code == 201
            assert response.json()["currency"] == "KRW"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_cash_account_service, None)

    async def test_2자리_currency_422(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.post(
                "/api/cash-accounts",
                json={"label": "Test", "currency": "KR", "balance": "1000"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_5자리_currency_422(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.post(
                "/api/cash-accounts",
                json={"label": "Test", "currency": "ABCDE", "balance": "1000"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_label_미제공_422(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.post(
                "/api/cash-accounts",
                json={"currency": "KRW", "balance": "1000"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_USDT_4자리_currency_허용(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        account = _make_account(currency="USDT", balance="500.0000")
        mock_service = AsyncMock(spec=CashAccountService)
        mock_service.create.return_value = account

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_cash_account_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/cash-accounts",
                json={"label": "USDT Wallet", "currency": "USDT", "balance": "500"},
            )
            assert response.status_code == 201
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_cash_account_service, None)


class TestUpdateCashAccount:
    async def test_인증_없이_수정하면_401(self, async_client: AsyncClient) -> None:
        response = await async_client.patch(
            "/api/cash-accounts/1",
            json={"label": "New Label"},
        )
        assert response.status_code == 401

    async def test_balance만_업데이트_200(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        account = _make_account(balance="2000000.0000")
        mock_service = AsyncMock(spec=CashAccountService)
        mock_service.update.return_value = account

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_cash_account_service] = lambda: mock_service

        try:
            response = await async_client.patch(
                "/api/cash-accounts/1",
                json={"balance": "2000000"},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["balance"] == "2000000.0000"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_cash_account_service, None)

    async def test_label만_업데이트_200(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        account = _make_account(label="New Label")
        mock_service = AsyncMock(spec=CashAccountService)
        mock_service.update.return_value = account

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_cash_account_service] = lambda: mock_service

        try:
            response = await async_client.patch(
                "/api/cash-accounts/1",
                json={"label": "New Label"},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_cash_account_service, None)

    async def test_둘_다_업데이트_200(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        account = _make_account(label="New", balance="500.0000")
        mock_service = AsyncMock(spec=CashAccountService)
        mock_service.update.return_value = account

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_cash_account_service] = lambda: mock_service

        try:
            response = await async_client.patch(
                "/api/cash-accounts/1",
                json={"label": "New", "balance": "500"},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_cash_account_service, None)

    async def test_빈_객체_전송_422(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.patch(
                "/api/cash-accounts/1",
                json={},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_currency_포함_422(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.patch(
                "/api/cash-accounts/1",
                json={"currency": "USD", "balance": "1000"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_없는_id_404(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        mock_service = AsyncMock(spec=CashAccountService)
        mock_service.update.side_effect = NotFoundError("CashAccount 9999 not found")

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_cash_account_service] = lambda: mock_service

        try:
            response = await async_client.patch(
                "/api/cash-accounts/9999",
                json={"balance": "1000"},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_cash_account_service, None)

    async def test_id_0이면_422(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.patch(
                "/api/cash-accounts/0",
                json={"balance": "1000"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestDeleteCashAccount:
    async def test_인증_없이_삭제하면_401(self, async_client: AsyncClient) -> None:
        response = await async_client.delete("/api/cash-accounts/1")
        assert response.status_code == 401

    async def test_정상_삭제_204(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        mock_service = AsyncMock(spec=CashAccountService)
        mock_service.delete.return_value = None

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_cash_account_service] = lambda: mock_service

        try:
            response = await async_client.delete("/api/cash-accounts/1")
            assert response.status_code == 204
            mock_service.delete.assert_called_once_with(1)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_cash_account_service, None)

    async def test_없는_id_404(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        mock_service = AsyncMock(spec=CashAccountService)
        mock_service.delete.side_effect = NotFoundError("CashAccount 9999 not found")

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_cash_account_service] = lambda: mock_service

        try:
            response = await async_client.delete("/api/cash-accounts/9999")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_cash_account_service, None)

    async def test_id_0이면_422(self, async_client: AsyncClient) -> None:
        user = OwnerPrincipal()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.delete("/api/cash-accounts/0")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)
