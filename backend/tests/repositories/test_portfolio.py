"""Tests for PortfolioRepository — multi-user isolation + BUY-aggregate accuracy."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.asset_type import AssetType
from app.domain.portfolio import HoldingRow
from app.domain.transaction_type import TransactionType
from app.models.asset_symbol import AssetSymbol
from app.models.transaction import Transaction
from app.models.user import User
from app.models.user_asset import UserAsset
from app.repositories.portfolio import PortfolioRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(session: AsyncSession, email: str) -> User:
    from app.core.security import hash_password
    from app.repositories.user import UserRepository

    repo = UserRepository(session)
    return await repo.create(email=email, password_hash=hash_password("Pass1234"))


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


async def _create_user_asset(session: AsyncSession, user: User, symbol: AssetSymbol) -> UserAsset:
    from app.repositories.user_asset import UserAssetRepository

    repo = UserAssetRepository(session)
    return await repo.create(user_id=user.id, asset_symbol_id=symbol.id)


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


class TestPortfolioRepositoryIsolation:
    async def test_다른_사용자_자산이_섞이지_않는다(self, db_session: AsyncSession) -> None:
        user_a = await _create_user(db_session, "repo_a@example.com")
        user_b = await _create_user(db_session, "repo_b@example.com")
        sym = await _create_symbol(db_session, "AAPL", "USD", AssetType.US_STOCK)

        ua_a = await _create_user_asset(db_session, user_a, sym)
        await _add_buy_tx(db_session, ua_a, Decimal("5"), Decimal("100"))

        repo = PortfolioRepository(db_session)
        rows_a = await repo.list_user_holdings_with_aggregates(user_a.id)
        rows_b = await repo.list_user_holdings_with_aggregates(user_b.id)

        assert len(rows_a) == 1
        assert rows_b == []

    async def test_사용자_B_는_사용자_A_자산_아이디를_볼_수_없다(
        self, db_session: AsyncSession
    ) -> None:
        user_a = await _create_user(db_session, "repo_iso_a@example.com")
        user_b = await _create_user(db_session, "repo_iso_b@example.com")
        sym = await _create_symbol(db_session, "ISOCOIN", "KRW")

        ua_a = await _create_user_asset(db_session, user_a, sym)
        await _add_buy_tx(db_session, ua_a, Decimal("1"), Decimal("1000"))

        repo = PortfolioRepository(db_session)
        rows_b = await repo.list_user_holdings_with_aggregates(user_b.id)
        ua_ids_b = {r.user_asset_id for r in rows_b}
        assert ua_a.id not in ua_ids_b


class TestPortfolioRepositoryZeroTx:
    async def test_거래_0건인_UserAsset도_포함된다(self, db_session: AsyncSession) -> None:
        user = await _create_user(db_session, "repo_zero@example.com")
        sym = await _create_symbol(db_session, "EMPTY", "KRW")
        await _create_user_asset(db_session, user, sym)

        repo = PortfolioRepository(db_session)
        rows = await repo.list_user_holdings_with_aggregates(user.id)

        assert len(rows) == 1
        assert rows[0].total_qty == Decimal("0")
        assert rows[0].total_cost == Decimal("0")

    async def test_거래_0건_여러_자산(self, db_session: AsyncSession) -> None:
        user = await _create_user(db_session, "repo_zero_multi@example.com")
        sym1 = await _create_symbol(db_session, "ZERO1", "KRW")
        sym2 = await _create_symbol(db_session, "ZERO2", "USD", AssetType.US_STOCK)
        await _create_user_asset(db_session, user, sym1)
        await _create_user_asset(db_session, user, sym2)

        repo = PortfolioRepository(db_session)
        rows = await repo.list_user_holdings_with_aggregates(user.id)
        assert len(rows) == 2
        for r in rows:
            assert r.total_qty == Decimal("0")


class TestPortfolioRepositoryAggregates:
    async def test_BUY_N건_집계_정확성(self, db_session: AsyncSession) -> None:
        user = await _create_user(db_session, "repo_agg@example.com")
        sym = await _create_symbol(db_session, "AGG", "KRW")
        ua = await _create_user_asset(db_session, user, sym)

        await _add_buy_tx(db_session, ua, Decimal("2"), Decimal("1000"))
        await _add_buy_tx(db_session, ua, Decimal("3"), Decimal("2000"))

        repo = PortfolioRepository(db_session)
        rows = await repo.list_user_holdings_with_aggregates(user.id)

        assert len(rows) == 1
        row = rows[0]
        assert row.total_qty == Decimal("5")
        assert row.total_cost == Decimal("8000")  # 2*1000 + 3*2000

    async def test_반환_타입이_HoldingRow이다(self, db_session: AsyncSession) -> None:
        user = await _create_user(db_session, "repo_type@example.com")
        sym = await _create_symbol(db_session, "TYPECHECK", "KRW")
        await _create_user_asset(db_session, user, sym)

        repo = PortfolioRepository(db_session)
        rows = await repo.list_user_holdings_with_aggregates(user.id)

        assert all(isinstance(r, HoldingRow) for r in rows)

    async def test_AssetSymbol이_eager_load된다(self, db_session: AsyncSession) -> None:
        user = await _create_user(db_session, "repo_eager@example.com")
        sym = await _create_symbol(db_session, "EAGER", "USD", AssetType.US_STOCK)
        await _create_user_asset(db_session, user, sym)

        repo = PortfolioRepository(db_session)
        rows = await repo.list_user_holdings_with_aggregates(user.id)

        # Should not raise — relationship must be already loaded.
        assert rows[0].asset_symbol.symbol == "EAGER"
        assert rows[0].asset_symbol.currency == "USD"
