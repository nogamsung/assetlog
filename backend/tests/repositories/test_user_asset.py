"""Unit tests for UserAssetRepository — uses SQLite in-memory via conftest."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.asset_type import AssetType
from app.repositories.asset_symbol import AssetSymbolRepository
from app.repositories.user_asset import UserAssetRepository


async def _seed(session: AsyncSession) -> int:
    """Create one asset_symbol, return asset_symbol_id."""
    sym_repo = AssetSymbolRepository(session)
    sym = await sym_repo.create(
        asset_type=AssetType.CRYPTO,
        symbol="BTC",
        exchange="upbit",
        name="Bitcoin",
        currency="KRW",
    )
    return sym.id


class TestUserAssetCreate:
    async def test_생성하면_id가_할당된다(self, db_session: AsyncSession) -> None:
        sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        ua = await repo.create(asset_symbol_id=sym_id)
        assert ua.id is not None

    async def test_생성하면_asset_symbol이_로드된다(self, db_session: AsyncSession) -> None:
        sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        ua = await repo.create(asset_symbol_id=sym_id)
        assert ua.asset_symbol.symbol == "BTC"

    async def test_memo가_저장된다(self, db_session: AsyncSession) -> None:
        sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        ua = await repo.create(asset_symbol_id=sym_id, memo="long hold")
        assert ua.memo == "long hold"


class TestUserAssetGetById:
    async def test_조회하면_반환된다(self, db_session: AsyncSession) -> None:
        sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        created = await repo.create(asset_symbol_id=sym_id)

        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.id == created.id

    async def test_없는_id면_None이_반환된다(self, db_session: AsyncSession) -> None:
        sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        created = await repo.create(asset_symbol_id=sym_id)

        # Query non-existent ID
        found = await repo.get_by_id(created.id + 999)
        assert found is None


class TestUserAssetListAll:
    async def test_보유_목록이_반환된다(self, db_session: AsyncSession) -> None:
        sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        await repo.create(asset_symbol_id=sym_id)

        results = await repo.list_all()
        assert len(results) >= 1

    async def test_여러_자산을_반환한다(self, db_session: AsyncSession) -> None:
        sym_repo = AssetSymbolRepository(db_session)
        sym_a = await sym_repo.create(
            asset_type=AssetType.CRYPTO,
            symbol="BTC",
            exchange="upbit",
            name="Bitcoin",
            currency="KRW",
        )
        sym_b = await sym_repo.create(
            asset_type=AssetType.CRYPTO,
            symbol="ETH",
            exchange="upbit",
            name="Ethereum",
            currency="KRW",
        )
        repo = UserAssetRepository(db_session)
        await repo.create(asset_symbol_id=sym_a.id)
        await repo.create(asset_symbol_id=sym_b.id)

        results = await repo.list_all()
        assert len(results) >= 2


class TestUserAssetDeleteById:
    async def test_삭제하면_True를_반환하고_사라진다(self, db_session: AsyncSession) -> None:
        sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        ua = await repo.create(asset_symbol_id=sym_id)

        deleted = await repo.delete_by_id(ua.id)
        assert deleted is True

        found = await repo.get_by_id(ua.id)
        assert found is None

    async def test_없는_id_삭제하면_False를_반환한다(self, db_session: AsyncSession) -> None:
        sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        ua = await repo.create(asset_symbol_id=sym_id)

        deleted = await repo.delete_by_id(ua.id + 999)
        assert deleted is False
