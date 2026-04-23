"""Decimal precision tests for TransactionRepository.get_summary.

Validates that large-scale quantities and prices with many decimal places
do not lose precision when aggregated via SQLAlchemy + SQLite (aiosqlite).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.transaction_type import TransactionType
from app.repositories.transaction import TransactionRepository
from app.schemas.transaction import TransactionCreate


def _buy(quantity: str, price: str) -> TransactionCreate:
    return TransactionCreate(
        type=TransactionType.BUY,
        quantity=Decimal(quantity),
        price=Decimal(price),
        traded_at=datetime.now(tz=UTC),
    )


class TestSummaryDecimalPrecision:
    async def test_소수점_많은_수량과_가격의_가중평균(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        user_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        user = await user_factory(email="math_precision@example.com")
        sym = await asset_symbol_factory(symbol="PRECISION_COIN")
        ua = await user_asset_factory(user=user, asset_symbol=sym)

        repo = TransactionRepository(db_session)

        # qty1 * price1 = 1000.1234567890 * 1 = 1000.1234567890
        # qty2 * price2 = 2000.9876543210 * 1 = 2000.9876543210
        # total_cost = 3001.1111111100
        # total_qty  = 3001.1111111100
        # avg_price  = 1.0  (since price is 1.0 for both)
        await repo.create(ua.id, _buy(quantity="1000.1234567890", price="1.0"))
        await repo.create(ua.id, _buy(quantity="2000.9876543210", price="1.0"))

        total_qty, avg_price, total_cost, count = await repo.get_summary(ua.id)

        expected_qty = Decimal("1000.1234567890") + Decimal("2000.9876543210")
        assert total_qty == expected_qty
        assert count == 2
        # price is 1.0 for both, so avg = total_cost / total_qty = 1.0
        # allow tiny floating drift when SQLite returns REAL
        assert abs(avg_price - Decimal("1.0")) < Decimal("0.000001")

    async def test_두_거래_가중평균_정밀도(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        user_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        user = await user_factory(email="math_weighted@example.com")
        sym = await asset_symbol_factory(symbol="WEIGHTED_COIN")
        ua = await user_asset_factory(user=user, asset_symbol=sym)

        repo = TransactionRepository(db_session)

        # Buy 1 unit at 60000 and 2 units at 30000
        # avg = (1*60000 + 2*30000) / 3 = 120000/3 = 40000
        await repo.create(ua.id, _buy(quantity="1.0", price="60000.0"))
        await repo.create(ua.id, _buy(quantity="2.0", price="30000.0"))

        total_qty, avg_price, total_cost, count = await repo.get_summary(ua.id)

        assert total_qty == Decimal("3.0")
        assert total_cost == Decimal("120000.0")
        assert abs(avg_price - Decimal("40000.0")) < Decimal("0.000001")
        assert count == 2

    async def test_큰_금액의_합계가_정확하다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        user_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        user = await user_factory(email="math_large@example.com")
        sym = await asset_symbol_factory(symbol="LARGE_COIN")
        ua = await user_asset_factory(user=user, asset_symbol=sym)

        repo = TransactionRepository(db_session)

        # 10 BTC at 99999999.999999 KRW each
        await repo.create(ua.id, _buy(quantity="10.0", price="99999999.999999"))

        total_qty, avg_price, total_cost, count = await repo.get_summary(ua.id)

        assert total_qty == Decimal("10.0")
        expected_cost = Decimal("10.0") * Decimal("99999999.999999")
        assert abs(total_cost - expected_cost) < Decimal("0.001")
