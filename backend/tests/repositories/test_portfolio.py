"""Tests for PortfolioRepository — holding aggregation accuracy."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.asset_type import AssetType
from app.domain.portfolio import HoldingRow
from app.domain.transaction_type import TransactionType
from app.models.asset_symbol import AssetSymbol
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset
from app.repositories.portfolio import PortfolioRepository


async def _create_symbol(
    session: AsyncSession,
    symbol: str = "BTC",
    currency: str = "KRW",
    asset_type: AssetType = AssetType.CRYPTO,
    last_price: Decimal | None = None,
) -> AssetSymbol:
    from app.repositories.asset_symbol import AssetSymbolRepository

    repo = AssetSymbolRepository(session)
    sym = await repo.create(
        asset_type=asset_type,
        symbol=symbol,
        exchange="upbit",
        name=symbol,
        currency=currency,
    )
    if last_price is not None:
        sym.last_price = last_price
        sym.last_price_refreshed_at = datetime.now(UTC)
        await session.flush()
    return sym


async def _create_user_asset(session: AsyncSession, symbol: AssetSymbol) -> UserAsset:
    from app.repositories.user_asset import UserAssetRepository

    repo = UserAssetRepository(session)
    return await repo.create(asset_symbol_id=symbol.id)


async def _add_buy_tx(
    session: AsyncSession,
    user_asset: UserAsset,
    qty: Decimal,
    price: Decimal,
) -> None:
    tx = Transaction(
        user_asset_id=user_asset.id,
        type=TransactionType.BUY,
        quantity=qty,
        price=price,
        traded_at=datetime.now(UTC),
    )
    session.add(tx)
    await session.flush()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPortfolioRepositoryZeroTx:
    async def test_거래_0건인_UserAsset도_포함된다(self, db_session: AsyncSession) -> None:
        sym = await _create_symbol(db_session, "EMPTY", "KRW")
        ua = await _create_user_asset(db_session, sym)

        repo = PortfolioRepository(db_session)
        rows = await repo.list_holdings_with_aggregates()

        assert len(rows) >= 1
        assert any(r.user_asset_id == ua.id for r in rows)
        empty_row = next(r for r in rows if r.user_asset_id == ua.id)
        assert empty_row.total_qty == Decimal("0")
        assert empty_row.total_cost == Decimal("0")

    async def test_거래_0건_여러_자산(self, db_session: AsyncSession) -> None:
        sym1 = await _create_symbol(db_session, "ZERO1", "KRW")
        sym2 = await _create_symbol(db_session, "ZERO2", "USD", AssetType.US_STOCK)
        ua1 = await _create_user_asset(db_session, sym1)
        ua2 = await _create_user_asset(db_session, sym2)

        repo = PortfolioRepository(db_session)
        rows = await repo.list_holdings_with_aggregates()

        assert len(rows) >= 2
        ua_ids = {r.user_asset_id for r in rows}
        assert ua1.id in ua_ids
        assert ua2.id in ua_ids


class TestPortfolioRepositoryAggregates:
    async def test_BUY_N건_집계_정확성(self, db_session: AsyncSession) -> None:
        sym = await _create_symbol(db_session, "AGG", "KRW")
        ua = await _create_user_asset(db_session, sym)

        await _add_buy_tx(db_session, ua, Decimal("2"), Decimal("1000"))
        await _add_buy_tx(db_session, ua, Decimal("3"), Decimal("2000"))

        repo = PortfolioRepository(db_session)
        rows = await repo.list_holdings_with_aggregates()

        row = next(r for r in rows if r.user_asset_id == ua.id)
        assert row.total_qty == Decimal("5")
        assert row.total_cost == Decimal("8000")  # 2*1000 + 3*2000

    async def test_반환_타입이_HoldingRow이다(self, db_session: AsyncSession) -> None:
        sym = await _create_symbol(db_session, "TYPECHECK", "KRW")
        await _create_user_asset(db_session, sym)

        repo = PortfolioRepository(db_session)
        rows = await repo.list_holdings_with_aggregates()

        assert all(isinstance(r, HoldingRow) for r in rows)

    async def test_AssetSymbol이_eager_load된다(self, db_session: AsyncSession) -> None:
        sym = await _create_symbol(db_session, "EAGER", "USD", AssetType.US_STOCK)
        ua = await _create_user_asset(db_session, sym)

        repo = PortfolioRepository(db_session)
        rows = await repo.list_holdings_with_aggregates()

        # Should not raise — relationship must be already loaded.
        row = next(r for r in rows if r.user_asset_id == ua.id)
        assert row.asset_symbol.symbol == "EAGER"
