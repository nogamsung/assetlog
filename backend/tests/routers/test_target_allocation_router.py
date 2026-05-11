"""Router tests for /api/target-allocation."""

from __future__ import annotations

from decimal import Decimal

from httpx import AsyncClient

from app.core.deps import get_current_user
from app.core.principal import OwnerPrincipal
from app.main import app


class TestGetTargetAllocation:
    async def test_미인증_401(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/target-allocation")
        assert response.status_code == 401

    async def test_초기_빈_entries(self, async_client: AsyncClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        try:
            response = await async_client.get("/api/target-allocation")
            assert response.status_code == 200
            assert response.json() == {"entries": []}
        finally:
            app.dependency_overrides.clear()


class TestPutTargetAllocation:
    async def test_미인증_401(self, async_client: AsyncClient) -> None:
        response = await async_client.put(
            "/api/target-allocation", json={"entries": []}
        )
        assert response.status_code == 401

    async def test_정상_저장_round_trip(self, async_client: AsyncClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        try:
            payload = {
                "entries": [
                    {"asset_type": "us_stock", "target_pct": "0.6"},
                    {"asset_type": "crypto", "target_pct": "0.2"},
                    {"asset_type": "cash", "target_pct": "0.2"},
                ]
            }
            put = await async_client.put("/api/target-allocation", json=payload)
            assert put.status_code == 200
            body = put.json()
            assert len(body["entries"]) == 3
            total = sum(Decimal(e["target_pct"]) for e in body["entries"])
            assert total == Decimal("1.0")

            get = await async_client.get("/api/target-allocation")
            assert get.status_code == 200
            assert len(get.json()["entries"]) == 3
        finally:
            app.dependency_overrides.clear()

    async def test_합계_초과_422(self, async_client: AsyncClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        try:
            payload = {
                "entries": [
                    {"asset_type": "us_stock", "target_pct": "0.7"},
                    {"asset_type": "kr_stock", "target_pct": "0.5"},
                ]
            }
            response = await async_client.put("/api/target-allocation", json=payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_빈_리스트_clear(self, async_client: AsyncClient) -> None:
        app.dependency_overrides[get_current_user] = lambda: OwnerPrincipal()
        try:
            await async_client.put(
                "/api/target-allocation",
                json={"entries": [{"asset_type": "us_stock", "target_pct": "0.5"}]},
            )
            response = await async_client.put(
                "/api/target-allocation", json={"entries": []}
            )
            assert response.status_code == 200
            assert response.json() == {"entries": []}
        finally:
            app.dependency_overrides.clear()
