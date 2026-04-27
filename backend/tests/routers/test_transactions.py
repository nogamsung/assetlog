"""Integration tests for /api/user-assets/{user_asset_id}/transactions router."""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_transaction_service
from app.core.principal import OwnerPrincipal
from app.domain.transaction_type import TransactionType
from app.exceptions import (  # MODIFIED
    CsvImportValidationError,
    InsufficientHoldingError,
    NotFoundError,
)
from app.main import app
from app.models.transaction import Transaction
from app.schemas.transaction import UserAssetSummaryResponse
from app.services.transaction import TransactionService


def _make_owner() -> OwnerPrincipal:
    return OwnerPrincipal()


def _make_transaction(
    tx_id: int = 1,
    user_asset_id: int = 1,
    tag: str | None = None,
) -> Transaction:
    tx = Transaction(
        user_asset_id=user_asset_id,
        type=TransactionType.BUY,
        quantity=Decimal("1.5"),
        price=Decimal("50000.0"),
        traded_at=datetime.now(UTC),
    )
    tx.id = tx_id
    tx.memo = None
    tx.tag = tag
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
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            response = await async_client.post("/api/user-assets/0/transactions", json=_BUY_PAYLOAD)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_quantity가_0이면_422(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            bad_payload = {**_BUY_PAYLOAD, "quantity": "0"}
            response = await async_client.post("/api/user-assets/1/transactions", json=bad_payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_naive_traded_at이면_422(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            bad_payload = {**_BUY_PAYLOAD, "traded_at": "2026-04-23T10:00:00"}  # no tz
            response = await async_client.post("/api/user-assets/1/transactions", json=bad_payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_미래_traded_at이면_422(self, async_client: AsyncClient) -> None:
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.list.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets/1/transactions?limit=10&offset=20")
            assert response.status_code == 200
            mock_service.list.assert_called_once_with(
                1,
                limit=10,
                offset=20,
                tag=None,
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)


class TestDeleteTransaction:
    async def test_인증_없이_삭제하면_401(self, async_client: AsyncClient) -> None:
        response = await async_client.delete("/api/user-assets/1/transactions/1")
        assert response.status_code == 401

    async def test_삭제_성공하면_204(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.remove.return_value = None

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.delete("/api/user-assets/1/transactions/1")
            assert response.status_code == 204
            mock_service.remove.assert_called_once_with(1, 1)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_없는_transaction_삭제시_404(self, async_client: AsyncClient) -> None:
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            bad_payload = {**_UPDATE_PAYLOAD, "quantity": "0"}
            response = await async_client.put("/api/user-assets/1/transactions/1", json=bad_payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_naive_traded_at이면_422(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            bad_payload = {**_UPDATE_PAYLOAD, "traded_at": "2026-04-23T10:00:00"}
            response = await async_client.put("/api/user-assets/1/transactions/1", json=bad_payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_미래_traded_at이면_422(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            bad_payload = {**_UPDATE_PAYLOAD, "traded_at": "2099-01-01T00:00:00+00:00"}
            response = await async_client.put("/api/user-assets/1/transactions/1", json=bad_payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_transaction_id가_0이면_422(self, async_client: AsyncClient) -> None:
        user = _make_owner()
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
    tx.tag = None
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
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
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
        user = _make_owner()
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


class TestListTransactionsTagFilter:
    async def test_tag_쿼리파라미터_전달된다(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.list.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets/1/transactions?tag=DCA")
            assert response.status_code == 200
            mock_service.list.assert_called_once_with(
                1,
                limit=100,
                offset=0,
                tag="DCA",
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_tag_없으면_None_전달된다(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.list.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets/1/transactions")
            assert response.status_code == 200
            mock_service.list.assert_called_once_with(
                1,
                limit=100,
                offset=0,
                tag=None,
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_tag_50자_초과면_422(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        app.dependency_overrides[get_current_user] = lambda: user

        try:
            long_tag = "A" * 51
            response = await async_client.get(f"/api/user-assets/1/transactions?tag={long_tag}")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_response에_tag_포함된다(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        tx = _make_transaction(tag="DCA")
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.list.return_value = [tx]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets/1/transactions?tag=DCA")
            assert response.status_code == 200
            body = response.json()
            assert body[0]["tag"] == "DCA"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_tag_None인_response는_null(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        tx = _make_transaction(tag=None)
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.list.return_value = [tx]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets/1/transactions")
            assert response.status_code == 200
            body = response.json()
            assert body[0]["tag"] is None
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)


class TestListUserTags:
    async def test_인증_없이_접근하면_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/user-assets/transactions/tags")
        assert response.status_code == 401

    async def test_태그_목록_200_반환(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.list_distinct_tags.return_value = ["DCA", "장기보유"]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets/transactions/tags")
            assert response.status_code == 200
            body = response.json()
            assert body == ["DCA", "장기보유"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_태그_없으면_빈_배열(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.list_distinct_tags.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets/transactions/tags")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)

    async def test_service_호출된다(self, async_client: AsyncClient) -> None:
        user = _make_owner()
        mock_service = AsyncMock(spec=TransactionService)
        mock_service.list_distinct_tags.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_transaction_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/user-assets/transactions/tags")
            assert response.status_code == 200
            mock_service.list_distinct_tags.assert_called_once_with()
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_transaction_service, None)
