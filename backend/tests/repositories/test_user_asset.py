"""Unit tests for UserAssetRepository — uses SQLite in-memory via conftest."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.asset_type import AssetType
from app.repositories.asset_symbol import AssetSymbolRepository
from app.repositories.user import UserRepository
from app.repositories.user_asset import UserAssetRepository


async def _seed(session: AsyncSession) -> tuple[int, int]:
    """Create one user and one asset_symbol, return (user_id, asset_symbol_id)."""
    user_repo = UserRepository(session)
    user = await user_repo.create(email="ua_test@example.com", password_hash="hashed")

    sym_repo = AssetSymbolRepository(session)
    sym = await sym_repo.create(
        asset_type=AssetType.CRYPTO,
        symbol="BTC",
        exchange="upbit",
        name="Bitcoin",
        currency="KRW",
    )
    return user.id, sym.id


class TestUserAssetCreate:
    async def test_생성하면_id가_할당된다(self, db_session: AsyncSession) -> None:
        user_id, sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        ua = await repo.create(user_id=user_id, asset_symbol_id=sym_id)
        assert ua.id is not None

    async def test_생성하면_asset_symbol이_로드된다(self, db_session: AsyncSession) -> None:
        user_id, sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        ua = await repo.create(user_id=user_id, asset_symbol_id=sym_id)
        assert ua.asset_symbol.symbol == "BTC"

    async def test_memo가_저장된다(self, db_session: AsyncSession) -> None:
        user_id, sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        ua = await repo.create(user_id=user_id, asset_symbol_id=sym_id, memo="long hold")
        assert ua.memo == "long hold"


class TestUserAssetGetByIdForUser:
    async def test_본인_소유면_반환된다(self, db_session: AsyncSession) -> None:
        user_id, sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        created = await repo.create(user_id=user_id, asset_symbol_id=sym_id)

        found = await repo.get_by_id_for_user(created.id, user_id)
        assert found is not None
        assert found.id == created.id

    async def test_타_사용자_id로_조회하면_None이_반환된다(self, db_session: AsyncSession) -> None:
        user_id, sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        created = await repo.create(user_id=user_id, asset_symbol_id=sym_id)

        # Use a different user_id
        found = await repo.get_by_id_for_user(created.id, user_id + 999)
        assert found is None


class TestUserAssetListForUser:
    async def test_사용자_보유_목록이_반환된다(self, db_session: AsyncSession) -> None:
        user_id, sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        await repo.create(user_id=user_id, asset_symbol_id=sym_id)

        results = await repo.list_for_user(user_id)
        assert len(results) >= 1
        assert all(r.user_id == user_id for r in results)

    async def test_다른_사용자_자산은_목록에_없다(self, db_session: AsyncSession) -> None:
        user_id, sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        await repo.create(user_id=user_id, asset_symbol_id=sym_id)

        other_results = await repo.list_for_user(user_id + 999)
        assert all(r.user_id != user_id for r in other_results)


class TestUserAssetDeleteByIdForUser:
    async def test_삭제하면_True를_반환하고_사라진다(self, db_session: AsyncSession) -> None:
        user_id, sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        ua = await repo.create(user_id=user_id, asset_symbol_id=sym_id)

        deleted = await repo.delete_by_id_for_user(ua.id, user_id)
        assert deleted is True

        found = await repo.get_by_id_for_user(ua.id, user_id)
        assert found is None

    async def test_타_사용자_자산_삭제하면_False를_반환한다(self, db_session: AsyncSession) -> None:
        user_id, sym_id = await _seed(db_session)
        repo = UserAssetRepository(db_session)
        ua = await repo.create(user_id=user_id, asset_symbol_id=sym_id)

        deleted = await repo.delete_by_id_for_user(ua.id, user_id + 999)
        assert deleted is False
