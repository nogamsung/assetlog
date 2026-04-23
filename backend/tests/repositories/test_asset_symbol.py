"""Unit tests for AssetSymbolRepository — uses SQLite in-memory via conftest."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.asset_type import AssetType
from app.repositories.asset_symbol import AssetSymbolRepository


async def _create_btc(repo: AssetSymbolRepository) -> None:
    await repo.create(
        asset_type=AssetType.CRYPTO,
        symbol="BTC",
        exchange="upbit",
        name="Bitcoin",
        currency="KRW",
    )


class TestAssetSymbolCreate:
    async def test_생성하면_id가_할당된다(self, db_session: AsyncSession) -> None:
        repo = AssetSymbolRepository(db_session)
        asset = await repo.create(
            asset_type=AssetType.CRYPTO,
            symbol="ETH",
            exchange="upbit",
            name="Ethereum",
            currency="KRW",
        )
        assert asset.id is not None
        assert asset.symbol == "ETH"

    async def test_필드가_올바르게_저장된다(self, db_session: AsyncSession) -> None:
        repo = AssetSymbolRepository(db_session)
        asset = await repo.create(
            asset_type=AssetType.US_STOCK,
            symbol="AAPL",
            exchange="NASDAQ",
            name="Apple Inc.",
            currency="USD",
        )
        assert asset.asset_type == AssetType.US_STOCK
        assert asset.exchange == "NASDAQ"
        assert asset.name == "Apple Inc."
        assert asset.currency == "USD"


class TestAssetSymbolGetById:
    async def test_존재하는_id로_조회하면_반환된다(self, db_session: AsyncSession) -> None:
        repo = AssetSymbolRepository(db_session)
        created = await repo.create(
            asset_type=AssetType.KR_STOCK,
            symbol="005930",
            exchange="KOSPI",
            name="삼성전자",
            currency="KRW",
        )
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.symbol == "005930"

    async def test_없는_id로_조회하면_None이_반환된다(self, db_session: AsyncSession) -> None:
        repo = AssetSymbolRepository(db_session)
        result = await repo.get_by_id(99999)
        assert result is None


class TestAssetSymbolGetByTriple:
    async def test_존재하는_triple로_조회하면_반환된다(self, db_session: AsyncSession) -> None:
        repo = AssetSymbolRepository(db_session)
        await _create_btc(repo)
        found = await repo.get_by_triple(AssetType.CRYPTO, "BTC", "upbit")
        assert found is not None
        assert found.symbol == "BTC"

    async def test_없는_triple로_조회하면_None이_반환된다(self, db_session: AsyncSession) -> None:
        repo = AssetSymbolRepository(db_session)
        result = await repo.get_by_triple(AssetType.CRYPTO, "DOGE", "upbit")
        assert result is None

    async def test_exchange가_다르면_다른_row로_조회된다(self, db_session: AsyncSession) -> None:
        repo = AssetSymbolRepository(db_session)
        await _create_btc(repo)
        result = await repo.get_by_triple(AssetType.CRYPTO, "BTC", "binance")
        assert result is None


class TestAssetSymbolSearch:
    async def test_q검색이_symbol에_매칭된다(self, db_session: AsyncSession) -> None:
        repo = AssetSymbolRepository(db_session)
        await repo.create(
            asset_type=AssetType.CRYPTO,
            symbol="SOL",
            exchange="upbit",
            name="Solana",
            currency="KRW",
        )
        results = await repo.search(q="SOL")
        assert any(s.symbol == "SOL" for s in results)

    async def test_q검색이_name에_매칭된다(self, db_session: AsyncSession) -> None:
        repo = AssetSymbolRepository(db_session)
        await repo.create(
            asset_type=AssetType.CRYPTO,
            symbol="XRP",
            exchange="upbit",
            name="Ripple",
            currency="KRW",
        )
        results = await repo.search(q="ripple")
        assert any(s.symbol == "XRP" for s in results)

    async def test_asset_type_필터가_적용된다(self, db_session: AsyncSession) -> None:
        repo = AssetSymbolRepository(db_session)
        await repo.create(
            asset_type=AssetType.US_STOCK,
            symbol="TSLA",
            exchange="NASDAQ",
            name="Tesla Inc.",
            currency="USD",
        )
        results = await repo.search(asset_type=AssetType.US_STOCK)
        assert all(s.asset_type == AssetType.US_STOCK for s in results)

    async def test_exchange_필터가_적용된다(self, db_session: AsyncSession) -> None:
        repo = AssetSymbolRepository(db_session)
        await repo.create(
            asset_type=AssetType.CRYPTO,
            symbol="ADA",
            exchange="binance",
            name="Cardano",
            currency="USDT",
        )
        results = await repo.search(exchange="binance")
        assert all(s.exchange == "binance" for s in results)

    async def test_limit과_offset이_적용된다(self, db_session: AsyncSession) -> None:
        repo = AssetSymbolRepository(db_session)
        for i in range(5):
            await repo.create(
                asset_type=AssetType.CRYPTO,
                symbol=f"COIN{i}",
                exchange="test_ex",
                name=f"Coin {i}",
                currency="KRW",
            )
        results = await repo.search(exchange="test_ex", limit=2, offset=0)
        assert len(results) == 2
