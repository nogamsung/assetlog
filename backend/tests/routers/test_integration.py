"""Router tests for POST /api/integrations/upbit/sync."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.core.deps import get_current_user, get_exchange_sync_service
from app.core.principal import OwnerPrincipal
from app.domain.exchange_sync import ExternalTrade, SyncResult
from app.domain.transaction_type import TransactionType
from app.main import app
from app.services.exchange_sync import ExchangeSyncService


class TestUpbitSyncEndpoint:
    async def test_미인증_401(self, async_client: AsyncClient) -> None:
        response = await async_client.post("/api/integrations/upbit/sync")
        assert response.status_code == 401

    async def test_키_미설정_502(self, async_client: AsyncClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        try:
            with patch("app.routers.integration.settings") as fake_settings:
                fake_settings.upbit_access_key = None
                fake_settings.upbit_secret_key = None
                response = await async_client.post("/api/integrations/upbit/sync")
                assert response.status_code == 502
                assert "Upbit" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    async def test_정상_200_결과_반환(self, async_client: AsyncClient) -> None:
        mock_svc = AsyncMock(spec=ExchangeSyncService)
        mock_svc.replace_trades.return_value = SyncResult(
            fetched=2, inserted=1, skipped_duplicate=1, skipped_no_symbol=0
        )
        fake_trades = [
            ExternalTrade(
                external_id="tx-1",
                symbol="BTC",
                quote_currency="KRW",
                side=TransactionType.BUY,
                quantity=Decimal("0.5"),
                price=Decimal("50000000"),
                traded_at=datetime(2026, 5, 1, tzinfo=UTC),
            )
        ]

        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        app.dependency_overrides[get_exchange_sync_service] = lambda: mock_svc
        try:
            with (
                patch("app.routers.integration.settings") as fake_settings,
                patch(
                    "app.adapters.upbit_account.UpbitAccountAdapter.fetch_trades",
                    return_value=fake_trades,
                ),
            ):
                fake_settings.upbit_access_key = "test-key"
                fake_settings.upbit_secret_key = "test-secret"
                response = await async_client.post("/api/integrations/upbit/sync")

            assert response.status_code == 200
            body = response.json()
            assert body["fetched"] == 2
            assert body["inserted"] == 1
            assert body["skipped_duplicate"] == 1
        finally:
            app.dependency_overrides.clear()
