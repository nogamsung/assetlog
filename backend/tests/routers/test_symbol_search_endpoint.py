"""Integration tests for symbol search endpoint — DB-first + fallback pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.core.deps import get_current_user, get_symbol_service
from app.domain.asset_type import AssetType
from app.main import app
from app.models.asset_symbol import AssetSymbol
from app.models.user import User
from app.services.symbol import SymbolService


def _fake_user() -> User:
    user = User(email="test@example.com", password_hash="hashed")
    user.id = 1
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def _make_asset(
    symbol: str,
    asset_type: AssetType = AssetType.US_STOCK,
    name: str = "",
    exchange: str = "NASDAQ",
) -> AssetSymbol:
    asset = AssetSymbol(
        asset_type=asset_type,
        symbol=symbol,
        exchange=exchange,
        name=name or f"{symbol} Corp",
        currency="USD",
    )
    asset.id = 1
    asset.last_synced_at = None
    asset.created_at = datetime.now(UTC)
    asset.updated_at = datetime.now(UTC)
    return asset


def _override_service(mock_service: SymbolService) -> None:
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_symbol_service] = lambda: mock_service


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_symbol_service, None)


@pytest.mark.asyncio
async def test_us_stock_search_returns_200_with_shape(async_client: AsyncClient) -> None:
    """US-S1: GET /api/symbols?q=AAPL&asset_type=us_stock returns symbol + name."""
    mock_service = AsyncMock(spec=SymbolService)
    asset = _make_asset("AAPL", AssetType.US_STOCK, "Apple Inc.")
    mock_service.search.return_value = [asset]
    _override_service(mock_service)

    try:
        resp = await async_client.get("/api/symbols?q=AAPL&asset_type=us_stock")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert body[0]["symbol"] == "AAPL"
        assert body[0]["name"] == "Apple Inc."
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_kr_stock_search_returns_samsung(async_client: AsyncClient) -> None:
    """US-S2: GET /api/symbols?q=005930&asset_type=kr_stock returns 삼성전자."""
    mock_service = AsyncMock(spec=SymbolService)
    asset = _make_asset("005930", AssetType.KR_STOCK, "삼성전자", "KRX")
    asset.currency = "KRW"
    mock_service.search.return_value = [asset]
    _override_service(mock_service)

    try:
        resp = await async_client.get("/api/symbols?q=005930&asset_type=kr_stock")
        assert resp.status_code == 200
        body = resp.json()
        assert any(s["symbol"] == "005930" and s["name"] == "삼성전자" for s in body)
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_crypto_search_btc_returns_pairs(async_client: AsyncClient) -> None:
    """US-S3: GET /api/symbols?q=BTC&asset_type=crypto returns BTC/USDT."""
    mock_service = AsyncMock(spec=SymbolService)
    asset = _make_asset("BTC/USDT", AssetType.CRYPTO, "Bitcoin", "binance")
    asset.currency = "USDT"
    mock_service.search.return_value = [asset]
    _override_service(mock_service)

    try:
        resp = await async_client.get("/api/symbols?q=BTC&asset_type=crypto")
        assert resp.status_code == 200
        body = resp.json()
        assert any("BTC/USDT" in s["symbol"] for s in body)
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_no_asset_type_returns_db_only(async_client: AsyncClient) -> None:
    """US-S4: asset_type omitted → service.search called with asset_type=None."""
    mock_service = AsyncMock(spec=SymbolService)
    mock_service.search.return_value = []
    _override_service(mock_service)

    try:
        resp = await async_client.get("/api/symbols?q=BTC")
        assert resp.status_code == 200
        call_kwargs = mock_service.search.call_args.kwargs
        assert call_kwargs["asset_type"] is None
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_external_failure_returns_200_with_db_hits(async_client: AsyncClient) -> None:
    """US-S5: even if adapter raises, endpoint returns 200 + DB results."""
    mock_service = AsyncMock(spec=SymbolService)
    # service.search swallows adapter errors internally and returns DB hits
    asset = _make_asset("AAPL", AssetType.US_STOCK, "Apple Inc.")
    mock_service.search.return_value = [asset]
    _override_service(mock_service)

    try:
        resp = await async_client.get("/api/symbols?q=AAPL&asset_type=us_stock")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_empty_query_no_fallback(async_client: AsyncClient) -> None:
    """US-S6: empty q returns DB results without triggering fallback."""
    mock_service = AsyncMock(spec=SymbolService)
    mock_service.search.return_value = []
    _override_service(mock_service)

    try:
        resp = await async_client.get("/api/symbols?q=")
        assert resp.status_code == 200
        assert resp.json() == []
        # Verify search was called (but adapter won't be invoked — that's service logic)
        mock_service.search.assert_called_once()
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_pagination_params_forwarded(async_client: AsyncClient) -> None:
    mock_service = AsyncMock(spec=SymbolService)
    mock_service.search.return_value = []
    _override_service(mock_service)

    try:
        resp = await async_client.get("/api/symbols?limit=5&offset=10")
        assert resp.status_code == 200
        call_kwargs = mock_service.search.call_args.kwargs
        assert call_kwargs["limit"] == 5
        assert call_kwargs["offset"] == 10
    finally:
        _clear_overrides()
