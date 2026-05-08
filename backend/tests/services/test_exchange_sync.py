"""Integration tests for ExchangeSyncService — SQLite in-memory DB."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.asset_type import AssetType
from app.domain.exchange_sync import ExchangeSource, ExternalTrade
from app.domain.transaction_type import TransactionType
from app.models.asset_symbol import AssetSymbol
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset
from app.services.exchange_sync import ExchangeSyncService


@pytest.fixture()
def service(db_session: AsyncSession) -> ExchangeSyncService:
    return ExchangeSyncService(db_session)


def _trade(
    *,
    external_id: str = "tx-1",
    symbol: str = "BTC",
    side: TransactionType = TransactionType.BUY,
    quantity: str = "0.5",
    price: str = "50000000",
    minute: int = 0,
) -> ExternalTrade:
    return ExternalTrade(
        external_id=external_id,
        symbol=symbol,
        quote_currency="KRW",
        side=side,
        quantity=Decimal(quantity),
        price=Decimal(price),
        traded_at=datetime(2026, 5, 1, 12, minute, tzinfo=UTC),
    )


class TestImportTrades:
    async def test_빈_입력_무동작(
        self, service: ExchangeSyncService
    ) -> None:
        result = await service.import_trades(ExchangeSource.UPBIT, [])
        assert result.fetched == 0
        assert result.inserted == 0

    async def test_심볼_자동_생성(
        self, service: ExchangeSyncService, db_session: AsyncSession
    ) -> None:
        result = await service.import_trades(ExchangeSource.UPBIT, [_trade()])
        assert result.inserted == 1

        symbols = (
            await db_session.execute(select(AssetSymbol).where(AssetSymbol.symbol == "BTC"))
        ).scalars().all()
        assert len(symbols) == 1
        assert symbols[0].asset_type == AssetType.CRYPTO
        assert symbols[0].exchange == "UPBIT"
        assert symbols[0].currency == "KRW"

    async def test_user_asset_자동_생성(
        self, service: ExchangeSyncService, db_session: AsyncSession
    ) -> None:
        await service.import_trades(ExchangeSource.UPBIT, [_trade()])
        assets = (await db_session.execute(select(UserAsset))).scalars().all()
        assert len(assets) == 1

    async def test_transaction_external_ref(
        self, service: ExchangeSyncService, db_session: AsyncSession
    ) -> None:
        await service.import_trades(ExchangeSource.UPBIT, [_trade(external_id="abc-123")])
        rows = (await db_session.execute(select(Transaction))).scalars().all()
        assert len(rows) == 1
        assert rows[0].external_source == "upbit"
        assert rows[0].external_id == "abc-123"
        assert rows[0].type == TransactionType.BUY

    async def test_재실행_시_dedupe(
        self, service: ExchangeSyncService, db_session: AsyncSession
    ) -> None:
        trades = [
            _trade(external_id="tx-1", minute=0),
            _trade(external_id="tx-2", minute=5),
        ]
        first = await service.import_trades(ExchangeSource.UPBIT, trades)
        assert first.inserted == 2

        # Re-import same trades + 1 new
        again = trades + [_trade(external_id="tx-3", minute=10)]
        second = await service.import_trades(ExchangeSource.UPBIT, again)
        assert second.inserted == 1
        assert second.skipped_duplicate == 2

        rows = (await db_session.execute(select(Transaction))).scalars().all()
        assert len(rows) == 3

    async def test_같은_심볼_여러_거래는_같은_user_asset(
        self, service: ExchangeSyncService, db_session: AsyncSession
    ) -> None:
        trades = [
            _trade(external_id="tx-1", minute=0),
            _trade(external_id="tx-2", minute=5, side=TransactionType.SELL),
        ]
        await service.import_trades(ExchangeSource.UPBIT, trades)
        assets = (await db_session.execute(select(UserAsset))).scalars().all()
        assert len(assets) == 1

    async def test_다른_심볼_각자_user_asset(
        self, service: ExchangeSyncService, db_session: AsyncSession
    ) -> None:
        trades = [
            _trade(external_id="tx-1", symbol="BTC"),
            _trade(external_id="tx-2", symbol="ETH"),
        ]
        await service.import_trades(ExchangeSource.UPBIT, trades)
        assets = (await db_session.execute(select(UserAsset))).scalars().all()
        assert len(assets) == 2


class TestAssetTypeMapping:
    async def test_shinhan_은_kr_stock(
        self, service: ExchangeSyncService, db_session: AsyncSession
    ) -> None:
        trade = ExternalTrade(
            external_id="ord-1",
            symbol="005930",
            quote_currency="KRW",
            side=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("70000"),
            traded_at=datetime(2026, 5, 1, tzinfo=UTC),
        )
        await service.import_trades(ExchangeSource.SHINHAN, [trade])
        sym = (
            await db_session.execute(select(AssetSymbol).where(AssetSymbol.symbol == "005930"))
        ).scalar_one()
        assert sym.asset_type == AssetType.KR_STOCK
        assert sym.exchange == "KRX"
