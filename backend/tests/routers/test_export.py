"""Integration tests for GET /api/export router."""

from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from app.core.deps import get_current_user, get_data_export_service
from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType
from app.main import app
from app.models.user import User
from app.schemas.export import (
    ExportAssetSymbol,
    ExportEnvelope,
    ExportTransaction,
    ExportUserAsset,
)
from app.services.data_export import DataExportService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: int = 1) -> User:
    user = User(email="export@example.com", password_hash="hashed")
    user.id = user_id
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def _make_envelope(
    user_assets: list[ExportUserAsset] | None = None,
    transactions: list[ExportTransaction] | None = None,
) -> ExportEnvelope:
    sym = ExportAssetSymbol(
        id=7,
        asset_type=AssetType.CRYPTO,
        symbol="BTC",
        exchange="upbit",
        name="Bitcoin",
        currency="KRW",
        last_price=Decimal("50000.000000"),
    )
    ua = ExportUserAsset(
        id=1,
        asset_symbol_id=7,
        memo=None,
        created_at=datetime.now(UTC),
        asset_symbol=sym,
    )
    tx = ExportTransaction(
        id=1,
        user_asset_id=1,
        type=TransactionType.BUY,
        quantity=Decimal("1.5"),
        price=Decimal("50000.0"),
        traded_at=datetime.now(UTC),
        memo=None,
        tag="DCA",
        created_at=datetime.now(UTC),
    )
    return ExportEnvelope(
        exported_at=datetime.now(UTC),
        user_assets=user_assets if user_assets is not None else [ua],
        transactions=transactions if transactions is not None else [tx],
    )


# ---------------------------------------------------------------------------
# 401 미인증
# ---------------------------------------------------------------------------


class TestExportUnauthorized:
    async def test_미인증_401_반환(self, async_client: object) -> None:
        from httpx import AsyncClient

        client: AsyncClient = async_client  # type: ignore[assignment]
        response = await client.get("/api/export")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 200 JSON
# ---------------------------------------------------------------------------


class TestExportJson:
    async def test_json_format_200_반환(self, async_client: object) -> None:
        from httpx import AsyncClient

        client: AsyncClient = async_client  # type: ignore[assignment]

        user = _make_user()
        envelope = _make_envelope()

        mock_service = AsyncMock(spec=DataExportService)
        mock_service.export_json.return_value = envelope

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_data_export_service] = lambda: mock_service

        try:
            response = await client.get("/api/export?format=json")
        finally:
            del app.dependency_overrides[get_current_user]
            del app.dependency_overrides[get_data_export_service]

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")

    async def test_json_content_disposition_헤더(self, async_client: object) -> None:
        from httpx import AsyncClient

        client: AsyncClient = async_client  # type: ignore[assignment]

        user = _make_user()
        envelope = _make_envelope()

        mock_service = AsyncMock(spec=DataExportService)
        mock_service.export_json.return_value = envelope

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_data_export_service] = lambda: mock_service

        try:
            response = await client.get("/api/export?format=json")
        finally:
            del app.dependency_overrides[get_current_user]
            del app.dependency_overrides[get_data_export_service]

        disposition = response.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert "assetlog-export-" in disposition
        assert ".json" in disposition

    async def test_json_파싱_가능(self, async_client: object) -> None:
        from httpx import AsyncClient

        client: AsyncClient = async_client  # type: ignore[assignment]

        user = _make_user()
        envelope = _make_envelope()

        mock_service = AsyncMock(spec=DataExportService)
        mock_service.export_json.return_value = envelope

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_data_export_service] = lambda: mock_service

        try:
            response = await client.get("/api/export")  # default format=json
        finally:
            del app.dependency_overrides[get_current_user]
            del app.dependency_overrides[get_data_export_service]

        body = response.json()
        assert "exported_at" in body
        assert "user_assets" in body
        assert "transactions" in body

    async def test_json_기본_format_json(self, async_client: object) -> None:
        """format 파라미터 생략 시 JSON 반환."""
        from httpx import AsyncClient

        client: AsyncClient = async_client  # type: ignore[assignment]

        user = _make_user()
        envelope = _make_envelope()

        mock_service = AsyncMock(spec=DataExportService)
        mock_service.export_json.return_value = envelope

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_data_export_service] = lambda: mock_service

        try:
            response = await client.get("/api/export")
        finally:
            del app.dependency_overrides[get_current_user]
            del app.dependency_overrides[get_data_export_service]

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")

    async def test_json_decimal_str_직렬화(self, async_client: object) -> None:
        from httpx import AsyncClient

        client: AsyncClient = async_client  # type: ignore[assignment]

        user = _make_user()
        envelope = _make_envelope()

        mock_service = AsyncMock(spec=DataExportService)
        mock_service.export_json.return_value = envelope

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_data_export_service] = lambda: mock_service

        try:
            response = await client.get("/api/export?format=json")
        finally:
            del app.dependency_overrides[get_current_user]
            del app.dependency_overrides[get_data_export_service]

        body = response.json()
        # Decimal fields must be serialised as strings, not floats
        if body["transactions"]:
            qty = body["transactions"][0]["quantity"]
            assert isinstance(qty, str), f"quantity should be str, got {type(qty)}"


# ---------------------------------------------------------------------------
# 200 CSV
# ---------------------------------------------------------------------------


class TestExportCsv:
    async def test_csv_format_200_반환(self, async_client: object) -> None:
        from httpx import AsyncClient

        client: AsyncClient = async_client  # type: ignore[assignment]

        user = _make_user()
        mock_service = AsyncMock(spec=DataExportService)
        mock_service.export_csv_zip.return_value = _make_minimal_zip()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_data_export_service] = lambda: mock_service

        try:
            response = await client.get("/api/export?format=csv")
        finally:
            del app.dependency_overrides[get_current_user]
            del app.dependency_overrides[get_data_export_service]

        assert response.status_code == 200

    async def test_csv_content_type_zip(self, async_client: object) -> None:
        from httpx import AsyncClient

        client: AsyncClient = async_client  # type: ignore[assignment]

        user = _make_user()
        mock_service = AsyncMock(spec=DataExportService)
        mock_service.export_csv_zip.return_value = _make_minimal_zip()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_data_export_service] = lambda: mock_service

        try:
            response = await client.get("/api/export?format=csv")
        finally:
            del app.dependency_overrides[get_current_user]
            del app.dependency_overrides[get_data_export_service]

        assert response.headers["content-type"] == "application/zip"

    async def test_csv_content_disposition_zip_파일명(self, async_client: object) -> None:
        from httpx import AsyncClient

        client: AsyncClient = async_client  # type: ignore[assignment]

        user = _make_user()
        mock_service = AsyncMock(spec=DataExportService)
        mock_service.export_csv_zip.return_value = _make_minimal_zip()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_data_export_service] = lambda: mock_service

        try:
            response = await client.get("/api/export?format=csv")
        finally:
            del app.dependency_overrides[get_current_user]
            del app.dependency_overrides[get_data_export_service]

        disposition = response.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert "assetlog-export-" in disposition
        assert ".zip" in disposition

    async def test_csv_유효한_zip_반환(self, async_client: object) -> None:
        from httpx import AsyncClient

        client: AsyncClient = async_client  # type: ignore[assignment]

        user = _make_user()
        mock_service = AsyncMock(spec=DataExportService)
        mock_service.export_csv_zip.return_value = _make_minimal_zip()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_data_export_service] = lambda: mock_service

        try:
            response = await client.get("/api/export?format=csv")
        finally:
            del app.dependency_overrides[get_current_user]
            del app.dependency_overrides[get_data_export_service]

        assert zipfile.is_zipfile(io.BytesIO(response.content))


# ---------------------------------------------------------------------------
# 422 invalid format
# ---------------------------------------------------------------------------


class TestExportInvalidFormat:
    async def test_invalid_format_422(self, async_client: object) -> None:
        from httpx import AsyncClient

        client: AsyncClient = async_client  # type: ignore[assignment]

        user = _make_user()
        mock_service = AsyncMock(spec=DataExportService)

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_data_export_service] = lambda: mock_service

        try:
            response = await client.get("/api/export?format=xml")
        finally:
            del app.dependency_overrides[get_current_user]
            del app.dependency_overrides[get_data_export_service]

        assert response.status_code == 422

    async def test_empty_format_422(self, async_client: object) -> None:
        from httpx import AsyncClient

        client: AsyncClient = async_client  # type: ignore[assignment]

        user = _make_user()
        mock_service = AsyncMock(spec=DataExportService)

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_data_export_service] = lambda: mock_service

        try:
            response = await client.get("/api/export?format=")
        finally:
            del app.dependency_overrides[get_current_user]
            del app.dependency_overrides[get_data_export_service]

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_minimal_zip() -> bytes:
    """Return minimal valid ZIP bytes with two CSV stub files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "user_assets.csv", "id,asset_type,symbol,exchange,name,currency,memo,created_at\n"
        )
        zf.writestr(
            "transactions.csv",
            "id,user_asset_id,asset_symbol,type,quantity,price,traded_at,memo,tag,created_at\n",
        )
    return buf.getvalue()
