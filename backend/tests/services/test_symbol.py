"""Unit tests for SymbolService."""

from unittest.mock import AsyncMock

import pytest

from app.domain.asset_type import AssetType
from app.exceptions import ConflictError
from app.models.asset_symbol import AssetSymbol
from app.repositories.asset_symbol import AssetSymbolRepository
from app.schemas.asset import AssetSymbolCreate
from app.services.symbol import SymbolService


def _make_asset(
    asset_id: int = 1,
    symbol: str = "BTC",
    exchange: str = "upbit",
    asset_type: AssetType = AssetType.CRYPTO,
) -> AssetSymbol:
    asset = AssetSymbol(
        asset_type=asset_type,
        symbol=symbol,
        exchange=exchange,
        name="Bitcoin",
        currency="KRW",
    )
    asset.id = asset_id
    return asset


class TestSymbolServiceSearch:
    async def test_검색_결과를_반환한다(self) -> None:
        mock_repo = AsyncMock(spec=AssetSymbolRepository)
        mock_repo.search.return_value = [_make_asset()]
        service = SymbolService(mock_repo)

        results = await service.search(q="BTC")

        mock_repo.search.assert_called_once_with(
            q="BTC",
            asset_type=None,
            exchange=None,
            limit=20,
            offset=0,
        )
        assert len(results) == 1

    async def test_빈_결과를_반환한다(self) -> None:
        mock_repo = AsyncMock(spec=AssetSymbolRepository)
        mock_repo.search.return_value = []
        service = SymbolService(mock_repo)

        results = await service.search(q="UNKNOWN")
        assert results == []


class TestSymbolServiceRegister:
    async def test_신규_심볼을_등록한다(self) -> None:
        mock_repo = AsyncMock(spec=AssetSymbolRepository)
        mock_repo.get_by_triple.return_value = None
        created = _make_asset()
        mock_repo.create.return_value = created
        service = SymbolService(mock_repo)

        data = AssetSymbolCreate(
            asset_type=AssetType.CRYPTO,
            symbol="BTC",
            exchange="upbit",
            name="Bitcoin",
            currency="KRW",
        )
        result = await service.register(data)

        mock_repo.create.assert_called_once()
        assert result.symbol == "BTC"

    async def test_중복_심볼이면_ConflictError를_발생시킨다(self) -> None:
        mock_repo = AsyncMock(spec=AssetSymbolRepository)
        mock_repo.get_by_triple.return_value = _make_asset()
        service = SymbolService(mock_repo)

        data = AssetSymbolCreate(
            asset_type=AssetType.CRYPTO,
            symbol="BTC",
            exchange="upbit",
            name="Bitcoin",
            currency="KRW",
        )
        with pytest.raises(ConflictError):
            await service.register(data)

        mock_repo.create.assert_not_called()

    async def test_다른_exchange면_중복_아님(self) -> None:
        mock_repo = AsyncMock(spec=AssetSymbolRepository)
        mock_repo.get_by_triple.return_value = None
        mock_repo.create.return_value = _make_asset(exchange="binance")
        service = SymbolService(mock_repo)

        data = AssetSymbolCreate(
            asset_type=AssetType.CRYPTO,
            symbol="BTC",
            exchange="binance",
            name="Bitcoin",
            currency="USDT",
        )
        result = await service.register(data)
        assert result is not None
        mock_repo.create.assert_called_once()
