"""Integration tests for POST /api/transactions/bulk router."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.core.deps import get_bulk_transaction_service, get_current_user
from app.core.principal import OwnerPrincipal
from app.domain.transaction_type import TransactionType
from app.exceptions import CsvImportValidationError
from app.main import app
from app.models.transaction import Transaction
from app.services.bulk_transaction import BulkTransactionService

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_owner() -> OwnerPrincipal:
    return OwnerPrincipal()


def _make_transaction(
    tx_id: int = 1,
    user_asset_id: int = 1,
) -> Transaction:
    tx = Transaction(
        user_asset_id=user_asset_id,
        type=TransactionType.BUY,
        quantity=Decimal("1.0"),
        price=Decimal("50000.0"),
        traded_at=datetime.now(UTC),
    )
    tx.id = tx_id
    tx.memo = None
    tx.tag = None
    tx.created_at = datetime.now(UTC)
    tx.updated_at = datetime.now(UTC)
    return tx


_JSON_PAYLOAD = {
    "rows": [
        {
            "symbol": "BTC",
            "exchange": "UPBIT",
            "type": "buy",
            "quantity": "0.5",
            "price": "85000000",
            "traded_at": "2026-04-20T10:00:00+09:00",
        }
    ]
}

_VALID_CSV = (
    "symbol,exchange,type,quantity,price,traded_at\n"
    "BTC,UPBIT,buy,0.5,85000000,2026-04-20T10:00:00+09:00\n"
)


# ---------------------------------------------------------------------------
# 401 — unauthenticated
# ---------------------------------------------------------------------------


class TestBulkImportAuth:
    async def test_인증_없으면_401(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/transactions/bulk",
            json=_JSON_PAYLOAD,
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 200 — JSON mode
# ---------------------------------------------------------------------------


class TestBulkImportJsonMode:
    async def test_JSON_모드_정상_200(self, async_client: AsyncClient) -> None:
        owner = _make_owner()
        tx = _make_transaction()
        mock_service = AsyncMock(spec=BulkTransactionService)
        mock_service.import_json.return_value = (1, [tx])

        app.dependency_overrides[get_current_user] = lambda: owner
        app.dependency_overrides[get_bulk_transaction_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/transactions/bulk",
                json=_JSON_PAYLOAD,
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["imported_count"] == 1
            assert len(body["preview"]) == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_bulk_transaction_service, None)

    async def test_JSON_모드_잘못된_body_400(self, async_client: AsyncClient) -> None:
        owner = _make_owner()
        mock_service = AsyncMock(spec=BulkTransactionService)

        app.dependency_overrides[get_current_user] = lambda: owner
        app.dependency_overrides[get_bulk_transaction_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/transactions/bulk",
                content=b"not-json",
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 400
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_bulk_transaction_service, None)


# ---------------------------------------------------------------------------
# 200 — CSV mode
# ---------------------------------------------------------------------------


class TestBulkImportCsvMode:
    async def test_CSV_모드_정상_200(self, async_client: AsyncClient) -> None:
        owner = _make_owner()
        tx = _make_transaction()
        mock_service = AsyncMock(spec=BulkTransactionService)
        mock_service.import_csv.return_value = (1, [tx])

        app.dependency_overrides[get_current_user] = lambda: owner
        app.dependency_overrides[get_bulk_transaction_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/transactions/bulk",
                files={"file": ("txs.csv", io.BytesIO(_VALID_CSV.encode()), "text/csv")},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["imported_count"] == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_bulk_transaction_service, None)

    async def test_CSV_1MB_초과_413(self, async_client: AsyncClient) -> None:
        owner = _make_owner()
        mock_service = AsyncMock(spec=BulkTransactionService)

        app.dependency_overrides[get_current_user] = lambda: owner
        app.dependency_overrides[get_bulk_transaction_service] = lambda: mock_service

        try:
            large_content = b"x" * (1_048_576 + 1)
            response = await async_client.post(
                "/api/transactions/bulk",
                files={"file": ("big.csv", io.BytesIO(large_content), "text/csv")},
            )
            assert response.status_code == 413
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_bulk_transaction_service, None)


# ---------------------------------------------------------------------------
# 415 — wrong content-type
# ---------------------------------------------------------------------------


class TestBulkImportWrongContentType:
    async def test_잘못된_content_type_415(self, async_client: AsyncClient) -> None:
        owner = _make_owner()
        mock_service = AsyncMock(spec=BulkTransactionService)

        app.dependency_overrides[get_current_user] = lambda: owner
        app.dependency_overrides[get_bulk_transaction_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/transactions/bulk",
                content=b"some-data",
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 415
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_bulk_transaction_service, None)


# ---------------------------------------------------------------------------
# 422 — validation errors from service
# ---------------------------------------------------------------------------


class TestBulkImportValidationError:
    async def test_행_검증_실패_422_errors_포함(self, async_client: AsyncClient) -> None:
        owner = _make_owner()
        mock_service = AsyncMock(spec=BulkTransactionService)
        mock_service.import_json.side_effect = CsvImportValidationError(
            [{"row": 1, "field": "symbol", "message": "Unknown (symbol, exchange)"}]
        )

        app.dependency_overrides[get_current_user] = lambda: owner
        app.dependency_overrides[get_bulk_transaction_service] = lambda: mock_service

        try:
            response = await async_client.post(
                "/api/transactions/bulk",
                json=_JSON_PAYLOAD,
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 422
            body = response.json()
            assert "errors" in body
            assert body["errors"][0]["row"] == 1
            assert body["errors"][0]["field"] == "symbol"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_bulk_transaction_service, None)

    async def test_CSV_헤더_누락_422(self, async_client: AsyncClient) -> None:
        owner = _make_owner()
        mock_service = AsyncMock(spec=BulkTransactionService)
        mock_service.import_csv.side_effect = CsvImportValidationError(
            [{"row": 0, "field": None, "message": "Missing required CSV columns: exchange"}]
        )

        app.dependency_overrides[get_current_user] = lambda: owner
        app.dependency_overrides[get_bulk_transaction_service] = lambda: mock_service

        try:
            bad_csv = (
                "symbol,type,quantity,price,traded_at\nBTC,buy,1.0,50000,2026-04-20T10:00:00+09:00"
            )
            response = await async_client.post(
                "/api/transactions/bulk",
                files={"file": ("txs.csv", io.BytesIO(bad_csv.encode()), "text/csv")},
            )
            assert response.status_code == 422
            body = response.json()
            assert body["errors"][0]["row"] == 0
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_bulk_transaction_service, None)
