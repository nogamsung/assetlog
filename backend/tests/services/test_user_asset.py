"""Unit tests for UserAssetService."""

from unittest.mock import AsyncMock

import pytest

from app.domain.asset_type import AssetType
from app.exceptions import ConflictError, NotFoundError
from app.models.asset_symbol import AssetSymbol
from app.models.user_asset import UserAsset
from app.repositories.user_asset import UserAssetRepository
from app.schemas.asset import UserAssetCreate
from app.services.user_asset import UserAssetService


def _make_symbol(sym_id: int = 1) -> AssetSymbol:
    sym = AssetSymbol(
        asset_type=AssetType.CRYPTO,
        symbol="BTC",
        exchange="upbit",
        name="Bitcoin",
        currency="KRW",
    )
    sym.id = sym_id
    return sym


def _make_user_asset(ua_id: int = 1, sym_id: int = 1) -> UserAsset:
    sym = _make_symbol(sym_id)
    ua = UserAsset(asset_symbol_id=sym_id)
    ua.id = ua_id
    ua.asset_symbol = sym  # type: ignore[assignment]  # mock relationship
    return ua


class TestUserAssetServiceList:
    async def test_보유_목록을_반환한다(self) -> None:
        mock_repo = AsyncMock(spec=UserAssetRepository)
        mock_repo.list_all.return_value = [_make_user_asset()]
        service = UserAssetService(mock_repo)

        results = await service.list()
        mock_repo.list_all.assert_awaited_once()
        assert len(results) == 1

    async def test_빈_목록을_반환한다(self) -> None:
        mock_repo = AsyncMock(spec=UserAssetRepository)
        mock_repo.list_all.return_value = []
        service = UserAssetService(mock_repo)

        results = await service.list()
        assert results == []


class TestUserAssetServiceAdd:
    async def test_신규_보유_선언에_성공한다(self) -> None:
        mock_repo = AsyncMock(spec=UserAssetRepository)
        mock_repo.get_asset_symbol.return_value = _make_symbol()
        mock_repo.get_by_symbol.return_value = None
        mock_repo.create.return_value = _make_user_asset()
        service = UserAssetService(mock_repo)

        data = UserAssetCreate(asset_symbol_id=1)
        result = await service.add(data=data)

        mock_repo.create.assert_awaited_once_with(asset_symbol_id=1, memo=None)
        assert result.id == 1

    async def test_존재하지_않는_심볼이면_NotFoundError를_발생시킨다(self) -> None:
        mock_repo = AsyncMock(spec=UserAssetRepository)
        mock_repo.get_asset_symbol.return_value = None
        service = UserAssetService(mock_repo)

        data = UserAssetCreate(asset_symbol_id=9999)
        with pytest.raises(NotFoundError):
            await service.add(data=data)

        mock_repo.create.assert_not_called()

    async def test_이미_보유_중이면_ConflictError를_발생시킨다(self) -> None:
        mock_repo = AsyncMock(spec=UserAssetRepository)
        mock_repo.get_asset_symbol.return_value = _make_symbol()
        mock_repo.get_by_symbol.return_value = _make_user_asset()
        service = UserAssetService(mock_repo)

        data = UserAssetCreate(asset_symbol_id=1)
        with pytest.raises(ConflictError):
            await service.add(data=data)

        mock_repo.create.assert_not_called()


class TestUserAssetServiceRemove:
    async def test_삭제에_성공한다(self) -> None:
        mock_repo = AsyncMock(spec=UserAssetRepository)
        mock_repo.delete_by_id.return_value = True
        service = UserAssetService(mock_repo)

        await service.remove(user_asset_id=1)
        mock_repo.delete_by_id.assert_awaited_once()

    async def test_없는_자산이면_NotFoundError를_발생시킨다(self) -> None:
        mock_repo = AsyncMock(spec=UserAssetRepository)
        mock_repo.delete_by_id.return_value = False
        service = UserAssetService(mock_repo)

        with pytest.raises(NotFoundError):
            await service.remove(user_asset_id=9999)

    async def test_없는_자산은_NotFoundError를_발생시킨다(self) -> None:
        mock_repo = AsyncMock(spec=UserAssetRepository)
        mock_repo.delete_by_id.return_value = False
        service = UserAssetService(mock_repo)

        with pytest.raises(NotFoundError):
            await service.remove(user_asset_id=1)
