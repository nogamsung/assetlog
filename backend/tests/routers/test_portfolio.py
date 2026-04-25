"""Router tests for /api/portfolio — 401, 200, empty portfolio, contract."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.core.deps import get_current_user, get_portfolio_service, get_tag_breakdown_service
from app.domain.asset_type import AssetType
from app.main import app
from app.models.user import User
from app.schemas.portfolio import (
    AllocationEntry,
    HoldingResponse,
    PnlEntry,
    PortfolioSummaryResponse,
    SymbolEmbedded,
)
from app.schemas.tag_breakdown import TagBreakdownEntry, TagBreakdownResponse
from app.services.portfolio import PortfolioService
from app.services.tag_breakdown import TagBreakdownService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: int = 1) -> User:
    user = User(email="test@example.com", password_hash="x")
    user.id = user_id
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def _make_symbol_embedded() -> SymbolEmbedded:
    return SymbolEmbedded(
        id=7,
        asset_type=AssetType.US_STOCK,
        symbol="AAPL",
        exchange="NASDAQ",
        name="Apple Inc.",
        currency="USD",
    )


def _make_holding() -> HoldingResponse:
    return HoldingResponse(
        user_asset_id=12,
        asset_symbol=_make_symbol_embedded(),
        quantity=Decimal("10.0000000000"),
        avg_cost=Decimal("170.500000"),
        cost_basis=Decimal("1705.00"),
        latest_price=Decimal("175.200000"),
        latest_value=Decimal("1752.00"),
        pnl_abs=Decimal("47.00"),
        pnl_pct=2.76,
        weight_pct=21.4,
        last_price_refreshed_at=datetime(2026, 4, 24, 9, 0, 0, tzinfo=UTC),
        is_stale=False,
        is_pending=False,
    )


def _make_summary() -> PortfolioSummaryResponse:
    return PortfolioSummaryResponse(
        total_value_by_currency={"KRW": "12500000.00", "USD": "8200.12"},
        total_cost_by_currency={"KRW": "11000000.00", "USD": "7500.00"},
        pnl_by_currency={
            "KRW": PnlEntry(abs=Decimal("1500000.00"), pct=13.64),
            "USD": PnlEntry(abs=Decimal("700.12"), pct=9.34),
        },
        allocation=[
            AllocationEntry(asset_type=AssetType.US_STOCK, pct=48.3),
            AllocationEntry(asset_type=AssetType.CRYPTO, pct=51.7),
        ],
        last_price_refreshed_at=datetime(2026, 4, 24, 9, 0, 0, tzinfo=UTC),
        pending_count=1,
        stale_count=0,
    )


# ---------------------------------------------------------------------------
# GET /api/portfolio/summary
# ---------------------------------------------------------------------------


class TestGetPortfolioSummary:
    async def test_미인증_401_반환(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/portfolio/summary")
        assert response.status_code == 401

    async def test_정상_200_반환(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_summary.return_value = _make_summary()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/summary")
            assert response.status_code == 200
            body = response.json()
            assert "total_value_by_currency" in body
            assert "pnl_by_currency" in body
            assert "allocation" in body
            assert "pending_count" in body
            assert "stale_count" in body
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_빈_포트폴리오_summary_0값_구조(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_summary.return_value = PortfolioSummaryResponse()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/summary")
            assert response.status_code == 200
            body = response.json()
            assert body["total_value_by_currency"] == {}
            assert body["pending_count"] == 0
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_contract_응답_키_일치(self, async_client: AsyncClient) -> None:
        """Contract test: response keys must match the OpenAPI schema."""
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_summary.return_value = _make_summary()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/summary")
            body = response.json()
            required_keys = {
                "total_value_by_currency",
                "total_cost_by_currency",
                "pnl_by_currency",
                "allocation",
                "last_price_refreshed_at",
                "pending_count",
                "stale_count",
            }
            assert required_keys.issubset(set(body.keys()))
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_service가_user_id로_호출됨(self, async_client: AsyncClient) -> None:
        user = _make_user(user_id=42)
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_summary.return_value = PortfolioSummaryResponse()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            await async_client.get("/api/portfolio/summary")
            mock_service.get_summary.assert_called_once_with(42, convert_to=None)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_convert_to_KRW_파라미터_전달(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_summary.return_value = PortfolioSummaryResponse(
            total_value_by_currency={"USD": "1000.00"},
            converted_total_value=Decimal("1380000.00"),
            converted_total_cost=Decimal("1100000.00"),
            converted_pnl_abs=Decimal("280000.00"),
            converted_realized_pnl=Decimal("50000.00"),
            display_currency="KRW",
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/summary?convert_to=krw")
            assert response.status_code == 200
            body = response.json()
            assert body["display_currency"] == "KRW"
            assert body["converted_total_value"] is not None
            mock_service.get_summary.assert_called_once_with(user.id, convert_to="KRW")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_convert_to_없으면_converted_필드_null(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_summary.return_value = PortfolioSummaryResponse()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/summary")
            assert response.status_code == 200
            body = response.json()
            assert body["converted_total_value"] is None
            assert body["display_currency"] is None
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_convert_to_너무_짧으면_422(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_summary.return_value = PortfolioSummaryResponse()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/summary?convert_to=K")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)


# ---------------------------------------------------------------------------
# GET /api/portfolio/holdings
# ---------------------------------------------------------------------------


class TestGetPortfolioHoldings:
    async def test_미인증_401_반환(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/portfolio/holdings")
        assert response.status_code == 401

    async def test_정상_200_반환(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_holdings.return_value = [_make_holding()]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/holdings")
            assert response.status_code == 200
            body = response.json()
            assert isinstance(body, list)
            assert len(body) == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_빈_포트폴리오_빈_배열_반환(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_holdings.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/holdings")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_contract_응답_키_일치(self, async_client: AsyncClient) -> None:
        """Contract test: holding row keys must match the OpenAPI HoldingResponse schema."""
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_holdings.return_value = [_make_holding()]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/holdings")
            item = response.json()[0]
            required_keys = {
                "user_asset_id",
                "asset_symbol",
                "quantity",
                "avg_cost",
                "cost_basis",
                "latest_price",
                "latest_value",
                "pnl_abs",
                "pnl_pct",
                "weight_pct",
                "last_price_refreshed_at",
                "is_stale",
                "is_pending",
            }
            assert required_keys.issubset(set(item.keys()))
            # Decimal fields must be strings
            assert isinstance(item["quantity"], str)
            assert isinstance(item["avg_cost"], str)
            assert isinstance(item["cost_basis"], str)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_asset_symbol_nested_키_존재(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_holdings.return_value = [_make_holding()]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/holdings")
            sym = response.json()[0]["asset_symbol"]
            assert "id" in sym
            assert "asset_type" in sym
            assert "symbol" in sym
            assert "exchange" in sym
            assert "name" in sym
            assert "currency" in sym
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_service가_user_id로_호출됨(self, async_client: AsyncClient) -> None:
        user = _make_user(user_id=7)
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_holdings.return_value = []

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            await async_client.get("/api/portfolio/holdings")
            mock_service.get_holdings.assert_called_once_with(7, convert_to=None)  # MODIFIED
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_convert_to_KRW_query_전달(self, async_client: AsyncClient) -> None:  # ADDED
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        holding = _make_holding()
        holding.converted_latest_value = Decimal("2418768.00")
        holding.converted_cost_basis = Decimal("2352900.00")
        holding.converted_pnl_abs = Decimal("64946.00")
        holding.converted_realized_pnl = Decimal("0")
        holding.display_currency = "KRW"
        mock_service.get_holdings.return_value = [holding]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/holdings?convert_to=krw")
            assert response.status_code == 200
            body = response.json()
            assert len(body) == 1
            item = body[0]
            assert item["display_currency"] == "KRW"
            assert item["converted_latest_value"] is not None
            assert item["converted_cost_basis"] is not None
            mock_service.get_holdings.assert_called_once_with(user.id, convert_to="KRW")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)

    async def test_convert_to_없으면_converted_필드_null(
        self, async_client: AsyncClient
    ) -> None:  # ADDED
        user = _make_user()
        mock_service = AsyncMock(spec=PortfolioService)
        mock_service.get_holdings.return_value = [_make_holding()]

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_portfolio_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/holdings")
            assert response.status_code == 200
            item = response.json()[0]
            assert item["converted_latest_value"] is None
            assert item["converted_cost_basis"] is None
            assert item["converted_pnl_abs"] is None
            assert item["converted_realized_pnl"] is None
            assert item["display_currency"] is None
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_portfolio_service, None)


# ---------------------------------------------------------------------------
# GET /api/portfolio/tags/breakdown
# ---------------------------------------------------------------------------


def _make_breakdown_response(
    tag: str | None = "DCA",
    buy_count: int = 10,
    sell_count: int = 2,
) -> TagBreakdownResponse:
    entry = TagBreakdownEntry(
        tag=tag,
        transaction_count=buy_count + sell_count,
        buy_count=buy_count,
        sell_count=sell_count,
        total_bought_value_by_currency={"USD": "1500.00", "KRW": "5000000.00"},
        total_sold_value_by_currency={"USD": "100.00"},
    )
    return TagBreakdownResponse(entries=[entry])


class TestGetTagBreakdown:
    async def test_미인증_401_반환(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/portfolio/tags/breakdown")
        assert response.status_code == 401

    async def test_정상_200_반환_schema_검증(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TagBreakdownService)
        mock_service.get_breakdown.return_value = _make_breakdown_response()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_tag_breakdown_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/tags/breakdown")
            assert response.status_code == 200
            body = response.json()
            assert "entries" in body
            assert isinstance(body["entries"], list)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_tag_breakdown_service, None)

    async def test_거래없음_빈_entries_반환(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TagBreakdownService)
        mock_service.get_breakdown.return_value = TagBreakdownResponse(entries=[])

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_tag_breakdown_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/tags/breakdown")
            assert response.status_code == 200
            assert response.json() == {"entries": []}
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_tag_breakdown_service, None)

    async def test_contract_응답_키_일치(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TagBreakdownService)
        mock_service.get_breakdown.return_value = _make_breakdown_response()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_tag_breakdown_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/tags/breakdown")
            entry = response.json()["entries"][0]
            required_keys = {
                "tag",
                "transaction_count",
                "buy_count",
                "sell_count",
                "total_bought_value_by_currency",
                "total_sold_value_by_currency",
            }
            assert required_keys.issubset(set(entry.keys()))
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_tag_breakdown_service, None)

    async def test_entry_통화별_금액_str_타입(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TagBreakdownService)
        mock_service.get_breakdown.return_value = _make_breakdown_response()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_tag_breakdown_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/tags/breakdown")
            entry = response.json()["entries"][0]
            for val in entry["total_bought_value_by_currency"].values():
                assert isinstance(val, str)
            for val in entry["total_sold_value_by_currency"].values():
                assert isinstance(val, str)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_tag_breakdown_service, None)

    async def test_untagged_entry_tag_null(self, async_client: AsyncClient) -> None:
        user = _make_user()
        mock_service = AsyncMock(spec=TagBreakdownService)
        mock_service.get_breakdown.return_value = TagBreakdownResponse(
            entries=[
                TagBreakdownEntry(
                    tag=None,
                    transaction_count=3,
                    buy_count=3,
                    sell_count=0,
                    total_bought_value_by_currency={"KRW": "1000000.00"},
                    total_sold_value_by_currency={},
                )
            ]
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_tag_breakdown_service] = lambda: mock_service

        try:
            response = await async_client.get("/api/portfolio/tags/breakdown")
            assert response.status_code == 200
            entry = response.json()["entries"][0]
            assert entry["tag"] is None
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_tag_breakdown_service, None)

    async def test_service가_user_id로_호출됨(self, async_client: AsyncClient) -> None:
        user = _make_user(user_id=99)
        mock_service = AsyncMock(spec=TagBreakdownService)
        mock_service.get_breakdown.return_value = TagBreakdownResponse(entries=[])

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_tag_breakdown_service] = lambda: mock_service

        try:
            await async_client.get("/api/portfolio/tags/breakdown")
            mock_service.get_breakdown.assert_called_once_with(99)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_tag_breakdown_service, None)
