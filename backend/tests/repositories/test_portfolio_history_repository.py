"""Integration tests for PortfolioHistoryRepository — real in-memory SQLite."""

from __future__ import annotations

import itertools
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType
from app.models.asset_symbol import AssetSymbol
from app.models.price_point import PricePoint
from app.models.transaction import Transaction
from app.models.user import User
from app.models.user_asset import UserAsset
from app.repositories.portfolio_history import PortfolioHistoryRepository

# ---------------------------------------------------------------------------
# Helpers — mirrors test_portfolio.py style
# ---------------------------------------------------------------------------

NOW = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)

# Monotonically-increasing ID generator for PricePoint (BigInteger + SQLite quirk)
_price_point_id_gen = itertools.count(1)


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
) -> AssetSymbol:
    from app.repositories.asset_symbol import AssetSymbolRepository

    repo = AssetSymbolRepository(session)
    return await repo.create(
        asset_type=asset_type,
        symbol=symbol,
        exchange="upbit",
        name=symbol,
        currency=currency,
    )


async def _create_user_asset(session: AsyncSession, user: User, symbol: AssetSymbol) -> UserAsset:
    from app.repositories.user_asset import UserAssetRepository

    repo = UserAssetRepository(session)
    return await repo.create(user_id=user.id, asset_symbol_id=symbol.id)


async def _add_buy_tx(
    session: AsyncSession,
    user_asset: UserAsset,
    qty: Decimal,
    price: Decimal,
    traded_at: datetime,
) -> Transaction:
    tx = Transaction(
        user_asset_id=user_asset.id,
        type=TransactionType.BUY,
        quantity=qty,
        price=price,
        traded_at=traded_at,
    )
    session.add(tx)
    await session.flush()
    return tx


async def _add_price_point(
    session: AsyncSession,
    symbol: AssetSymbol,
    price: Decimal,
    fetched_at: datetime,
    currency: str = "KRW",
) -> PricePoint:
    # SQLite does not support BigInteger autoincrement without explicit id.
    pp = PricePoint(
        id=next(_price_point_id_gen),
        asset_symbol_id=symbol.id,
        price=price,
        currency=currency,
        fetched_at=fetched_at,
    )
    session.add(pp)
    await session.flush()
    return pp


# ---------------------------------------------------------------------------
# list_user_transactions
# ---------------------------------------------------------------------------


class TestListUserTransactions:
    async def test_BUY_트랜잭션_반환(self, db_session: AsyncSession) -> None:
        user = await _create_user(db_session, "hist_tx_basic@example.com")
        sym = await _create_symbol(db_session, "BTC", "KRW")
        ua = await _create_user_asset(db_session, user, sym)
        await _add_buy_tx(db_session, ua, Decimal("1"), Decimal("50000000"), NOW)

        repo = PortfolioHistoryRepository(db_session)
        txs = await repo.list_user_transactions(user.id, "KRW")

        assert len(txs) == 1
        assert txs[0].symbol_id == sym.id
        assert txs[0].quantity == Decimal("1")
        assert txs[0].price == Decimal("50000000")

    async def test_traded_at_ASC_정렬(self, db_session: AsyncSession) -> None:
        user = await _create_user(db_session, "hist_tx_sort@example.com")
        sym = await _create_symbol(db_session, "SORT_BTC", "KRW")
        ua = await _create_user_asset(db_session, user, sym)

        t1 = NOW - timedelta(days=2)
        t2 = NOW - timedelta(days=1)
        await _add_buy_tx(db_session, ua, Decimal("2"), Decimal("1000"), t2)
        await _add_buy_tx(db_session, ua, Decimal("1"), Decimal("900"), t1)

        repo = PortfolioHistoryRepository(db_session)
        txs = await repo.list_user_transactions(user.id, "KRW")

        assert len(txs) == 2
        assert txs[0].traded_at <= txs[1].traded_at

    async def test_다른_currency_제외(self, db_session: AsyncSession) -> None:
        user = await _create_user(db_session, "hist_tx_cur@example.com")
        sym_krw = await _create_symbol(db_session, "CUR_BTC", "KRW")
        sym_usd = await _create_symbol(db_session, "CUR_AAPL", "USD", AssetType.US_STOCK)
        ua_krw = await _create_user_asset(db_session, user, sym_krw)
        ua_usd = await _create_user_asset(db_session, user, sym_usd)

        await _add_buy_tx(db_session, ua_krw, Decimal("1"), Decimal("50000000"), NOW)
        await _add_buy_tx(db_session, ua_usd, Decimal("5"), Decimal("170"), NOW)

        repo = PortfolioHistoryRepository(db_session)
        krw_txs = await repo.list_user_transactions(user.id, "KRW")
        usd_txs = await repo.list_user_transactions(user.id, "USD")

        assert len(krw_txs) == 1
        assert krw_txs[0].symbol_id == sym_krw.id
        assert len(usd_txs) == 1
        assert usd_txs[0].symbol_id == sym_usd.id

    async def test_다른_사용자_트랜잭션_제외(self, db_session: AsyncSession) -> None:
        user_a = await _create_user(db_session, "hist_tx_isoa@example.com")
        user_b = await _create_user(db_session, "hist_tx_isob@example.com")
        sym = await _create_symbol(db_session, "ISO_COIN", "KRW")

        ua_a = await _create_user_asset(db_session, user_a, sym)
        await _add_buy_tx(db_session, ua_a, Decimal("3"), Decimal("1000"), NOW)

        repo = PortfolioHistoryRepository(db_session)
        txs_b = await repo.list_user_transactions(user_b.id, "KRW")
        assert txs_b == []

    async def test_거래_없는_사용자_빈_리스트(self, db_session: AsyncSession) -> None:
        user = await _create_user(db_session, "hist_tx_empty@example.com")

        repo = PortfolioHistoryRepository(db_session)
        txs = await repo.list_user_transactions(user.id, "KRW")
        assert txs == []


# ---------------------------------------------------------------------------
# list_price_points_for_symbols
# ---------------------------------------------------------------------------


class TestListPricePointsForSymbols:
    async def test_since_이후_포인트_반환(self, db_session: AsyncSession) -> None:
        sym = await _create_symbol(db_session, "PP_BTC", "KRW")
        since = NOW - timedelta(hours=3)

        await _add_price_point(db_session, sym, Decimal("60000000"), since + timedelta(hours=1))
        await _add_price_point(db_session, sym, Decimal("61000000"), since + timedelta(hours=2))

        repo = PortfolioHistoryRepository(db_session)
        result = await repo.list_price_points_for_symbols([sym.id], since=since)

        assert sym.id in result
        # The two after-since points should be present
        ts_list = [ts for ts, _ in result[sym.id]]
        assert since + timedelta(hours=1) in ts_list
        assert since + timedelta(hours=2) in ts_list

    async def test_since_이전_최근_포인트_포함(self, db_session: AsyncSession) -> None:
        sym = await _create_symbol(db_session, "PP_SEED", "KRW")
        since = NOW - timedelta(hours=2)

        seed_ts = since - timedelta(hours=5)
        old_ts = since - timedelta(hours=10)
        after_ts = since + timedelta(hours=1)

        await _add_price_point(db_session, sym, Decimal("55000000"), old_ts)
        await _add_price_point(
            db_session, sym, Decimal("58000000"), seed_ts
        )  # most recent before since
        await _add_price_point(db_session, sym, Decimal("60000000"), after_ts)

        repo = PortfolioHistoryRepository(db_session)
        result = await repo.list_price_points_for_symbols([sym.id], since=since)

        prices = [p for _, p in result[sym.id]]
        # seed (58000000) must be included as rollforward start value
        assert Decimal("58000000") in prices
        # oldest point (55000000) must NOT be included (not the most recent before since)
        assert Decimal("55000000") not in prices

    async def test_결과가_fetched_at_ASC_정렬(self, db_session: AsyncSession) -> None:
        sym = await _create_symbol(db_session, "PP_SORT", "KRW")
        since = NOW - timedelta(hours=6)

        ts1 = since + timedelta(hours=1)
        ts2 = since + timedelta(hours=3)
        await _add_price_point(db_session, sym, Decimal("100"), ts1)
        await _add_price_point(db_session, sym, Decimal("200"), ts2)

        repo = PortfolioHistoryRepository(db_session)
        result = await repo.list_price_points_for_symbols([sym.id], since=since)

        timestamps = [ts for ts, _ in result[sym.id]]
        assert timestamps == sorted(timestamps)

    async def test_빈_symbol_ids_빈_dict_반환(self, db_session: AsyncSession) -> None:
        repo = PortfolioHistoryRepository(db_session)
        result = await repo.list_price_points_for_symbols([], since=NOW)
        assert result == {}

    async def test_여러_심볼_그룹핑(self, db_session: AsyncSession) -> None:
        sym1 = await _create_symbol(db_session, "PP_GRP1", "KRW")
        sym2 = await _create_symbol(db_session, "PP_GRP2", "KRW")
        since = NOW - timedelta(hours=1)

        await _add_price_point(db_session, sym1, Decimal("1000"), since + timedelta(minutes=10))
        await _add_price_point(db_session, sym2, Decimal("2000"), since + timedelta(minutes=20))

        repo = PortfolioHistoryRepository(db_session)
        result = await repo.list_price_points_for_symbols([sym1.id, sym2.id], since=since)

        assert sym1.id in result
        assert sym2.id in result
        assert result[sym1.id][0][1] == Decimal("1000")
        assert result[sym2.id][0][1] == Decimal("2000")
