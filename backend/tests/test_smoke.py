"""Smoke tests — verify app boots and /health responds correctly."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(async_client: AsyncClient) -> None:
    """GET /health should return 200 with {"status": "ok"}."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "ok"


@pytest.mark.asyncio
async def test_app_boots_without_error(async_client: AsyncClient) -> None:
    """Lifespan context should complete without raising exceptions.

    A successful response to any endpoint implies the lifespan ran cleanly.
    """
    response = await async_client.get("/health")
    # As long as the app is reachable, lifespan did not crash.
    assert response.status_code < 500
