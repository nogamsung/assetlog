"""Integration tests for /api/user-assets/{user_asset_id}/transactions router."""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_transaction_service
from app.domain.transaction_type import TransactionType
from app.exceptions import (  # MODIFIED
    CsvImportValidationError,
    InsufficientHoldingError,
    NotFoundError,
)
from app.main import app
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import UserAssetSummaryResponse
from app.services.transaction import TransactionService


def _make_user(user_id: int = 1, email: str = "test@example.com") -> User:
    user = User(email=email, password_hash="hashed")
    user.id = user_id
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def _make_transaction(tx_id: int = 1, user_asset_id: int = 1) -> Transaction:
    tx = Transaction(
        user_asset_id=user_asset_id,
        type=TransactionType.BUY,
        quantity=Decimal("1.5"),
        price=Decimal("50000.0"),
        traded_at=datetime.now(UTC),
    )
    tx.id = tx_id
    tx.memo = None
    tx.created_at = datetime.now(UTC)
    tx.updated_at = datetime.now(UTC)
    return tx


def _make_summary(user_asset_id: int = 1, currency: str = "KRW") -> UserAssetSummaryResponse:
    return UserAssetSummaryResponse(  # MODIFIED — new schema fields
        user_asset_id=user_asset_id,
        total_bought_quantity=Decimal("3.0"),
        total_sold_quantity=Decimal("0.0"),
        remaining_quantity=Decimal("3.0"),
        avg_buy_price=Decimal("50000.0"),
        total_invested=Decimal("150000.0"),
        total_sold_value=Decimal("0.0"),
        realized_pnl=Decimal("0.0"),
        transaction_count=2,
        currency=currency,
    )


_BUY_PAYLOAD = {
    "type": "buy",
    "quantity": "1.5",
    "price": "50000.0",
    "traded_at": "2026-04-23T10:00:00+00:00",
}


class TestAddTransaction:
    async def test_인증_없이_접근하면_401(self, async_client: AsyncClient) -> None:
        response = await async_client.post("/api/user-assets/1/transactions", json=_BUY_PAYLOAD)
        assert response.status_code == 401

    async def test_매수_성공하면_201_반환(self, async_client: AsyncClient) -> None:
        user = _make_user()
        tx = _make_transaction()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.add.return_value = tx

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.post("/api/user-assets/1/transactions", json=_BUY_PAYLOAD)
            assert response.status_code == 201
            body = response.json()
            assert body["id"] == tx.id
            assert body["type"] == "buy"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_소유하지_않은_user_asset이면_404(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.add.side_effect = NotFoundError("not found")

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/user-assets/999/transactions", json=_BUY_PAYLOAD
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_잔여수량_초과_매도시_409(self, async_client: AsyncClient) -> None:  # ADDED
        user = _make_user()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.add.side_effect = InsufficientHoldingError(
            "Cannot sell 5 units: only 2 units held."
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        sell_payload = {
            "type": "sell",
            "quantity": "5.0",
            "price": "55000.0",
            "traded_at": "2026-04-23T10:00:00+00:00",
        }
        try:
            response = await async_client.post("/api/user-assets/1/transactions", json=sell_payload)
            assert response.status_code == 409
            body = response.json()
            assert "detail" in body
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_user_asset_id가_0이면_422(self, async_client: AsyncClient) -> None:
        user = _make_user()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.post("/api/user-assets/0/transactions", json=_BUY_PAYLOAD)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_quantity가_0이면_422(self, async_client: AsyncClient) -> None:
        user = _make_user()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            bad_payload = {**_BUY_PAYLOAD, "quantity": "0"}
            response = await async_client.post("/api/user-assets/1/transactions", json=bad_payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_naive_traded_at이면_422(self, async_client: AsyncClient) -> None:
        user = _make_user()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            bad_payload = {**_BUY_PAYLOAD, "traded_at": "2026-04-23T10:00:00"}  # no tz
            response = await async_client.post("/api/user-assets/1/transactions", json=bad_payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_미래_traded_at이면_422(self, async_client: AsyncClient) -> None:
        user = _make_user()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            bad_payload = {**_BUY_PAYLOAD, "traded_at": "2099-01-01T00:00:00+00:00"}
            response = await async_client.post("/api/user-assets/1/transactions", json=bad_payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestListTransactions:
    async def test_인증_없이_접근하면_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/user-assets/1/transactions")
        assert response.status_code == 401

    async def test_목록_조회_성공(self, async_client: AsyncClient) -> None:
        user = _make_user()
        txs = [_make_transaction(tx_id=1), _make_transaction(tx_id=2)]
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.list.return_value = txs

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets/1/transactions")
            assert response.status_code == 200
            body = response.json()
            assert isinstance(body, list)
            assert len(body) == 2
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_타_사용자_user_asset_조회시_404(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.list.side_effect = NotFoundError("not found")

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets/999/transactions")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_limit_offset_쿼리_파라미터_전달(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.list.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets/1/transactions?limit=10&offset=20")
            assert response.status_code == 200
            mock_service.list.assert_called_once_with(
                current_user_id := user.id,  # noqa: F841
                1,
                limit=10,
                offset=20,
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)


class TestDeleteTransaction:
    async def test_인증_없이_삭제하면_401(self, async_client: AsyncClient) -> None:
        response = await async_client.delete("/api/user-assets/1/transactions/1")
        assert response.status_code == 401

    async def test_삭제_성공하면_204(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.remove.return_value = None

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.delete("/api/user-assets/1/transactions/1")
            assert response.status_code == 204
            mock_service.remove.assert_called_once_with(user.id, 1, 1)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_없는_transaction_삭제시_404(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.remove.side_effect = NotFoundError("not found")

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.delete("/api/user-assets/1/transactions/9999")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_타_사용자_user_asset_트랜잭션_삭제시_404(
        self, async_client: AsyncClient
    ) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.remove.side_effect = NotFoundError("user asset not found")

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.delete("/api/user-assets/999/transactions/1")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_transaction_id가_0이면_422(self, async_client: AsyncClient) -> None:
        user = _make_user()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.delete("/api/user-assets/1/transactions/0")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestGetSummary:
    async def test_인증_없이_접근하면_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/user-assets/1/summary")
        assert response.status_code == 401

    async def test_요약_조회_성공(self, async_client: AsyncClient) -> None:
        user = _make_user()
        summary = _make_summary()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.summary.return_value = summary

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets/1/summary")
            assert response.status_code == 200
            body = response.json()
            assert body["user_asset_id"] == 1
            assert body["currency"] == "KRW"
            assert body["transaction_count"] == 2
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_소유하지_않은_user_asset이면_404(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.summary.side_effect = NotFoundError("not found")

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets/999/summary")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)


_UPDATE_PAYLOAD = {  # ADDED
    "type": "buy",
    "quantity": "2.0",
    "price": "55000.0",
    "traded_at": "2026-04-23T10:00:00+00:00",
}


class TestUpdateTransaction:  # ADDED
    async def test_인증_없이_접근하면_401(self, async_client: AsyncClient) -> None:
        response = await async_client.put("/api/user-assets/1/transactions/1", json=_UPDATE_PAYLOAD)
        assert response.status_code == 401

    async def test_수정_성공하면_200_반환(self, async_client: AsyncClient) -> None:
        user = _make_user()
        tx = _make_transaction()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.edit.return_value = tx

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.put(
                "/api/user-assets/1/transactions/1", json=_UPDATE_PAYLOAD
            )
            assert response.status_code == 200
            body = response.json()
            assert body["id"] == tx.id
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_없는_transaction이면_404(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.edit.side_effect = NotFoundError("not found")

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.put(
                "/api/user-assets/1/transactions/9999", json=_UPDATE_PAYLOAD
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_보유_부족_SELL이면_409(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.edit.side_effect = InsufficientHoldingError(
            "Edit would leave negative holding."
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        sell_update = {**_UPDATE_PAYLOAD, "type": "sell", "quantity": "999.0"}
        try:
            response = await async_client.put("/api/user-assets/1/transactions/1", json=sell_update)
            assert response.status_code == 409
            body = response.json()
            assert "detail" in body
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_quantity가_0이면_422(self, async_client: AsyncClient) -> None:
        user = _make_user()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            bad_payload = {**_UPDATE_PAYLOAD, "quantity": "0"}
            response = await async_client.put("/api/user-assets/1/transactions/1", json=bad_payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_naive_traded_at이면_422(self, async_client: AsyncClient) -> None:
        user = _make_user()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            bad_payload = {**_UPDATE_PAYLOAD, "traded_at": "2026-04-23T10:00:00"}
            response = await async_client.put("/api/user-assets/1/transactions/1", json=bad_payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_미래_traded_at이면_422(self, async_client: AsyncClient) -> None:
        user = _make_user()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            bad_payload = {**_UPDATE_PAYLOAD, "traded_at": "2099-01-01T00:00:00+00:00"}
            response = await async_client.put("/api/user-assets/1/transactions/1", json=bad_payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_transaction_id가_0이면_422(self, async_client: AsyncClient) -> None:
        user = _make_user()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.put(
                "/api/user-assets/1/transactions/0", json=_UPDATE_PAYLOAD
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)


def _make_import_tx(tx_id: int = 1, user_asset_id: int = 1) -> Transaction:
    """Build a Transaction row as returned after import."""
    tx = Transaction(
        user_asset_id=user_asset_id,
        type=TransactionType.BUY,
        quantity=Decimal("1.0"),
        price=Decimal("50000.0"),
        traded_at=datetime.now(UTC) - timedelta(hours=1),
    )
    tx.id = tx_id
    tx.memo = None
    tx.created_at = datetime.now(UTC)
    tx.updated_at = datetime.now(UTC)
    return tx


def _csv_bytes(
    rows: list[str],
    header: str = "type,quantity,price,traded_at,memo",
) -> bytes:
    """Build CSV bytes suitable for UploadFile in tests."""
    content = "\n".join([header] + rows)
    return content.encode("utf-8")


def _past_iso(hours_ago: int = 1) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()


class TestImportTransactionsCsv:
    async def test_200_happy_path(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TransactionService)
        imported_tx = _make_import_tx()
        mock_service.import_csv.return_value = (1, [imported_tx])

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        csv_content = _csv_bytes([f"buy,1.0,50000,{_past_iso()},"])
        try:
            response = await async_client.post(
                "/api/user-assets/1/transactions/import",
                files={"file": ("trades.csv", io.BytesIO(csv_content), "text/csv")},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["imported_count"] == 1
            assert isinstance(body["preview"], list)
            assert len(body["preview"]) == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_401_unauthenticated(self, async_client: AsyncClient) -> None:
        csv_content = _csv_bytes([f"buy,1.0,50000,{_past_iso()},"])
        response = await async_client.post(
            "/api/user-assets/1/transactions/import",
            files={"file": ("trades.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert response.status_code == 401

    async def test_404_user_asset_없음(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.import_csv.side_effect = NotFoundError("not found")

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        csv_content = _csv_bytes([f"buy,1.0,50000,{_past_iso()},"])
        try:
            response = await async_client.post(
                "/api/user-assets/999/transactions/import",
                files={"file": ("trades.csv", io.BytesIO(csv_content), "text/csv")},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_413_1MB_초과(self, async_client: AsyncClient) -> None:
        user = _make_user()
        app.dependency_overrides[get_current_user] = lambda: user

        # Slightly over 1 MB
        oversized = b"x" * (1_048_576 + 1)
        try:
            response = await async_client.post(
                "/api/user-assets/1/transactions/import",
                files={"file": ("big.csv", io.BytesIO(oversized), "text/csv")},
            )
            assert response.status_code == 413
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_422_row_errors(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.import_csv.side_effect = CsvImportValidationError(
            [{"row": 1, "field": "type", "message": "Invalid transaction type."}]
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        csv_content = _csv_bytes([f"INVALID,1.0,50000,{_past_iso()},"])
        try:
            response = await async_client.post(
                "/api/user-assets/1/transactions/import",
                files={"file": ("trades.csv", io.BytesIO(csv_content), "text/csv")},
            )
            assert response.status_code == 422
            body = response.json()
            assert "errors" in body
            assert len(body["errors"]) == 1
            assert body["errors"][0]["row"] == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_빈_CSV_200_imported_count_0(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.import_csv.return_value = (0, [])

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        csv_content = b"type,quantity,price,traded_at,memo\n"
        try:
            response = await async_client.post(
                "/api/user-assets/1/transactions/import",
                files={"file": ("empty.csv", io.BytesIO(csv_content), "text/csv")},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["imported_count"] == 0
            assert body["preview"] == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_user_asset_id_0이면_422(self, async_client: AsyncClient) -> None:
        user = _make_user()
        app.dependency_overrides[get_current_user] = lambda: user

        csv_content = _csv_bytes([f"buy,1.0,50000,{_past_iso()},"])
        try:
            response = await async_client.post(
                "/api/user-assets/0/transactions/import",
                files={"file": ("trades.csv", io.BytesIO(csv_content), "text/csv")},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestTransactionUserIsolation:
    """Full integration test: user A's transactions must not be accessible by user B."""

    async def test_사용자_격리_통합_테스트(
        self, async_client: AsyncClient, user_factory: Any, asset_symbol_factory: Any
    ) -> None:
        from app.core.security import create_access_token
        from app.db.base import AsyncSessionLocal
        from app.repositories.transaction import TransactionRepository
        from app.repositories.user_asset import UserAssetRepository
        from app.schemas.transaction import TransactionCreate

        user_a = await user_factory(email="txiso_a@example.com")
        user_b = await user_factory(email="txiso_b@example.com")

        async with AsyncSessionLocal() as session:
            sym = (
                await asset_symbol_factory.__wrapped__(session)
                if hasattr(asset_symbol_factory, "__wrapped__")
                else None
            )  # type: ignore[attr-defined]  # runtime factory access
            if sym is None:
                from app.domain.asset_type import AssetType
                from app.repositories.asset_symbol import AssetSymbolRepository

                sym_repo = AssetSymbolRepository(session)
                sym = await sym_repo.create(
                    asset_type=AssetType.CRYPTO,
                    symbol="TXISO_COIN",
                    exchange="test",
                    name="Isolation Test Coin",
                    currency="KRW",
                )
            await session.commit()
            sym_id = sym.id

        async with AsyncSessionLocal() as session:
            ua_repo = UserAssetRepository(session)
            ua_a = await ua_repo.create(user_id=user_a.id, asset_symbol_id=sym_id)
            await session.commit()
            ua_a_id = ua_a.id

        async with AsyncSessionLocal() as session:
            tx_repo = TransactionRepository(session)
            from datetime import UTC, datetime

            await tx_repo.create(
                ua_a_id,
                TransactionCreate(
                    type=TransactionType.BUY,
                    quantity=Decimal("1.0"),
                    price=Decimal("1000.0"),
                    traded_at=datetime.now(UTC),
                ),
            )
            await session.commit()

        # User A can access their transaction list
        token_a = create_access_token(subject=user_a.id)
        resp_a = await async_client.get(
            f"/api/user-assets/{ua_a_id}/transactions",
            cookies={"access_token": token_a},
        )
        assert resp_a.status_code == 200
        assert len(resp_a.json()) >= 1

        # User B gets 404 when trying to access User A's user_asset
        token_b = create_access_token(subject=user_b.id)
        resp_b = await async_client.get(
            f"/api/user-assets/{ua_a_id}/transactions",
            cookies={"access_token": token_b},
        )
        assert resp_b.status_code == 404
