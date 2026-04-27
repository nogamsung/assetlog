"""Unit tests for TransactionRepository — uses SQLite in-memory via conftest."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.transaction_type import TransactionType
from app.repositories.transaction import TransactionRepository
from app.schemas.transaction import TransactionCreate


def _buy(
    quantity: str = "1.0",
    price: str = "50000.0",
    hours_ago: int = 0,
    tag: str | None = None,
) -> TransactionCreate:
    traded_at = datetime.now(tz=UTC) - timedelta(hours=hours_ago)
    return TransactionCreate(
        type=TransactionType.BUY,
        quantity=Decimal(quantity),
        price=Decimal(price),
        traded_at=traded_at,
        memo=None,
        tag=tag,
    )


def _sell(
    quantity: str = "1.0",
    price: str = "55000.0",
    hours_ago: int = 0,
    tag: str | None = None,
) -> TransactionCreate:
    traded_at = datetime.now(tz=UTC) - timedelta(hours=hours_ago)
    return TransactionCreate(
        type=TransactionType.SELL,
        quantity=Decimal(quantity),
        price=Decimal(price),
        traded_at=traded_at,
        memo=None,
        tag=tag,
    )


class TestTransactionCreate:
    async def test_생성하면_id가_할당된다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory()
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        tx = await repo.create(ua.id, _buy())
        assert tx.id is not None

    async def test_생성하면_필드가_올바르게_저장된다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="ETH")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        data = _buy(quantity="2.5", price="3000.0")
        tx = await repo.create(ua.id, data)

        assert tx.user_asset_id == ua.id
        assert tx.type == TransactionType.BUY
        assert tx.quantity == Decimal("2.5")
        assert tx.price == Decimal("3000.0")

    async def test_memo가_저장된다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="MEMO_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        data = TransactionCreate(
            type=TransactionType.BUY,
            quantity=Decimal("1.0"),
            price=Decimal("100.0"),
            traded_at=datetime.now(tz=UTC),
            memo="DCA buy",
        )
        tx = await repo.create(ua.id, data)
        assert tx.memo == "DCA buy"


class TestTransactionListForUserAsset:
    async def test_traded_at_내림차순으로_반환된다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="LIST_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        await repo.create(ua.id, _buy(hours_ago=2))
        await repo.create(ua.id, _buy(hours_ago=1))
        await repo.create(ua.id, _buy(hours_ago=0))

        result = await repo.list_for_user_asset(ua.id)
        assert len(result) == 3
        assert result[0].traded_at >= result[1].traded_at >= result[2].traded_at

    async def test_다른_user_asset_거래는_포함되지_않는다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym1 = await asset_symbol_factory(symbol="COIN_A")
        sym2 = await asset_symbol_factory(symbol="COIN_B")
        ua1 = await user_asset_factory(asset_symbol=sym1)
        ua2 = await user_asset_factory(asset_symbol=sym2)

        repo = TransactionRepository(db_session)
        await repo.create(ua1.id, _buy())
        await repo.create(ua2.id, _buy())

        result = await repo.list_for_user_asset(ua1.id)
        assert all(tx.user_asset_id == ua1.id for tx in result)

    async def test_limit과_offset이_적용된다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="LIMIT_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        for i in range(5):
            await repo.create(ua.id, _buy(hours_ago=i))

        page1 = await repo.list_for_user_asset(ua.id, limit=2, offset=0)
        page2 = await repo.list_for_user_asset(ua.id, limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert {tx.id for tx in page1}.isdisjoint({tx.id for tx in page2})


class TestTransactionGetSummary:
    async def test_거래_없을때_0_반환(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="EMPTY_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        agg = await repo.get_summary(ua.id)

        assert agg.total_bought_qty == Decimal("0")
        assert agg.total_bought_cost == Decimal("0")
        assert agg.total_sold_qty == Decimal("0")
        assert agg.total_sold_value == Decimal("0")
        assert agg.tx_count == 0

    async def test_단건_매수_집계가_올바르다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="SINGLE_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        await repo.create(ua.id, _buy(quantity="2.0", price="1000.0"))

        agg = await repo.get_summary(ua.id)

        assert agg.total_bought_qty == Decimal("2.0")
        assert agg.total_bought_cost == Decimal("2000.0")
        assert agg.total_sold_qty == Decimal("0")
        assert agg.tx_count == 1

    async def test_다건_매수_가중평균이_올바르다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="MULTI_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        await repo.create(ua.id, _buy(quantity="1.0", price="1000.0"))
        await repo.create(ua.id, _buy(quantity="3.0", price="2000.0"))

        agg = await repo.get_summary(ua.id)

        assert agg.total_bought_qty == Decimal("4.0")
        assert agg.total_bought_cost == Decimal("7000.0")
        assert agg.total_sold_qty == Decimal("0")
        assert agg.tx_count == 2

    async def test_매수_후_매도_집계가_올바르다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="SELL_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        await repo.create(ua.id, _buy(quantity="5.0", price="1000.0"))
        await repo.create(ua.id, _sell(quantity="2.0", price="1200.0"))

        agg = await repo.get_summary(ua.id)

        assert agg.total_bought_qty == Decimal("5.0")
        assert agg.total_bought_cost == Decimal("5000.0")
        assert agg.total_sold_qty == Decimal("2.0")
        assert agg.total_sold_value == Decimal("2400.0")
        assert agg.tx_count == 2

    async def test_get_remaining_quantity가_올바르다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="REMAIN_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        await repo.create(ua.id, _buy(quantity="5.0", price="1000.0"))
        await repo.create(ua.id, _sell(quantity="2.0", price="1200.0"))

        remaining = await repo.get_remaining_quantity(ua.id)
        assert remaining == Decimal("3.0")


class TestTransactionUpdate:
    async def test_update_필드가_모두_반영된다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        from app.schemas.transaction import TransactionUpdate

        sym = await asset_symbol_factory(symbol="UPD_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        tx = await repo.create(ua.id, _buy(quantity="1.0", price="1000.0"))

        new_data = TransactionUpdate(
            type=TransactionType.BUY,
            quantity=Decimal("2.5"),
            price=Decimal("2000.0"),
            traded_at=datetime.now(tz=UTC),
            memo="updated memo",
        )
        updated = await repo.update(tx.id, ua.id, new_data)

        assert updated is not None
        assert updated.id == tx.id
        assert updated.quantity == Decimal("2.5")
        assert updated.price == Decimal("2000.0")
        assert updated.memo == "updated memo"

    async def test_update_다른_user_asset_id면_None_반환(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        from app.schemas.transaction import TransactionUpdate

        sym = await asset_symbol_factory(symbol="UPD_WRONG_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        tx = await repo.create(ua.id, _buy())

        new_data = TransactionUpdate(
            type=TransactionType.BUY,
            quantity=Decimal("1.0"),
            price=Decimal("1000.0"),
            traded_at=datetime.now(tz=UTC),
        )
        result = await repo.update(tx.id, ua.id + 9999, new_data)
        assert result is None

    async def test_update_존재하지_않는_tx면_None_반환(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        from app.schemas.transaction import TransactionUpdate

        sym = await asset_symbol_factory(symbol="UPD_MISS_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        new_data = TransactionUpdate(
            type=TransactionType.BUY,
            quantity=Decimal("1.0"),
            price=Decimal("1000.0"),
            traded_at=datetime.now(tz=UTC),
        )
        result = await repo.update(99999, ua.id, new_data)
        assert result is None


class TestListAllForUserAsset:
    async def test_traded_at_오름차순으로_반환된다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="ALL_ASC_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        await repo.create(ua.id, _buy(hours_ago=0))
        await repo.create(ua.id, _buy(hours_ago=2))
        await repo.create(ua.id, _buy(hours_ago=1))

        result = await repo.list_all_for_user_asset(ua.id)
        assert len(result) == 3
        assert result[0].traded_at <= result[1].traded_at <= result[2].traded_at

    async def test_다른_user_asset_거래는_포함되지_않는다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym1 = await asset_symbol_factory(symbol="ALL_ISO_COIN_A")
        sym2 = await asset_symbol_factory(symbol="ALL_ISO_COIN_B")
        ua1 = await user_asset_factory(asset_symbol=sym1)
        ua2 = await user_asset_factory(asset_symbol=sym2)

        repo = TransactionRepository(db_session)
        await repo.create(ua1.id, _buy())
        await repo.create(ua2.id, _buy())

        result = await repo.list_all_for_user_asset(ua1.id)
        assert all(tx.user_asset_id == ua1.id for tx in result)

    async def test_거래_없으면_빈_리스트(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="ALL_EMPTY_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        result = await repo.list_all_for_user_asset(ua.id)
        assert result == []


class TestTransactionTag:
    async def test_tag가_저장된다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="TAG_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        tx = await repo.create(ua.id, _buy(tag="DCA"))
        assert tx.tag == "DCA"

    async def test_tag_None이면_필터_없음(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="NOTAG_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        await repo.create(ua.id, _buy(tag="DCA"))
        await repo.create(ua.id, _buy(tag="장기보유"))
        await repo.create(ua.id, _buy(tag=None))

        result = await repo.list_for_user_asset(ua.id, tag=None)
        assert len(result) == 3

    async def test_tag_필터_적용된다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="FILTER_TAG_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        await repo.create(ua.id, _buy(tag="DCA"))
        await repo.create(ua.id, _buy(tag="DCA"))
        await repo.create(ua.id, _buy(tag="장기보유"))

        result = await repo.list_for_user_asset(ua.id, tag="DCA")
        assert len(result) == 2
        assert all(tx.tag == "DCA" for tx in result)

    async def test_list_distinct_tags_반환된다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="DISTINCT_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        await repo.create(ua.id, _buy(tag="DCA"))
        await repo.create(ua.id, _buy(tag="DCA"))
        await repo.create(ua.id, _buy(tag="장기보유"))
        await repo.create(ua.id, _buy(tag=None))

        tags = await repo.list_distinct_tags()
        assert tags == ["DCA", "장기보유"]

    async def test_list_distinct_tags_없으면_빈_리스트(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="EMPTY_TAG_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        await repo.create(ua.id, _buy(tag=None))

        tags = await repo.list_distinct_tags()
        assert tags == []

    async def test_update_tag가_반영된다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        from app.schemas.transaction import TransactionUpdate

        sym = await asset_symbol_factory(symbol="UPD_TAG_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        tx = await repo.create(ua.id, _buy(tag="DCA"))

        new_data = TransactionUpdate(
            type=TransactionType.BUY,
            quantity=Decimal("1.0"),
            price=Decimal("50000.0"),
            traded_at=datetime.now(tz=UTC),
            tag="장기보유",
        )
        updated = await repo.update(tx.id, ua.id, new_data)
        assert updated is not None
        assert updated.tag == "장기보유"

    async def test_공백_tag는_None으로_정규화(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="BLANK_TAG_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        data = TransactionCreate(
            type=TransactionType.BUY,
            quantity=Decimal("1.0"),
            price=Decimal("50000.0"),
            traded_at=datetime.now(tz=UTC),
            tag="   ",
        )
        tx = await repo.create(ua.id, data)
        assert tx.tag is None


class TestListAll:
    """Tests for TransactionRepository.list_all (export bulk query)."""

    async def test_단일_user_asset_모든_거래_반환(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="LAU_SINGLE_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        await repo.create(ua.id, _buy(hours_ago=3))
        await repo.create(ua.id, _buy(hours_ago=2))
        await repo.create(ua.id, _buy(hours_ago=1))

        result = await repo.list_all()
        assert len(result) == 3
        assert all(tx.user_asset_id == ua.id for tx in result)

    async def test_다건_user_asset_모든_거래_반환(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym_a = await asset_symbol_factory(symbol="LAU_MULTI_A")
        sym_b = await asset_symbol_factory(symbol="LAU_MULTI_B")
        ua_a = await user_asset_factory(asset_symbol=sym_a)
        ua_b = await user_asset_factory(asset_symbol=sym_b)

        repo = TransactionRepository(db_session)
        await repo.create(ua_a.id, _buy(hours_ago=2))
        await repo.create(ua_a.id, _buy(hours_ago=1))
        await repo.create(ua_b.id, _buy(hours_ago=1))

        result = await repo.list_all()
        assert len(result) == 3

    async def test_거래_없으면_빈_리스트(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="LAU_EMPTY_COIN")
        await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        result = await repo.list_all()
        assert result == []

    async def test_정렬_user_asset_id_ASC_then_traded_at_ASC(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym_x = await asset_symbol_factory(symbol="LAU_ORDER_X")
        sym_y = await asset_symbol_factory(symbol="LAU_ORDER_Y")
        ua_x = await user_asset_factory(asset_symbol=sym_x)
        ua_y = await user_asset_factory(asset_symbol=sym_y)

        repo = TransactionRepository(db_session)
        await repo.create(ua_y.id, _buy(hours_ago=1))
        await repo.create(ua_x.id, _buy(hours_ago=2))
        await repo.create(ua_x.id, _buy(hours_ago=1))

        result = await repo.list_all()

        ua_x_txs = [tx for tx in result if tx.user_asset_id == ua_x.id]
        assert len(ua_x_txs) == 2
        assert ua_x_txs[0].traded_at <= ua_x_txs[1].traded_at


class TestTransactionDelete:
    async def test_삭제하면_True_반환하고_사라진다(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="DEL_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        tx = await repo.create(ua.id, _buy())

        deleted = await repo.delete_by_id_for_user_asset(tx.id, ua.id)
        assert deleted is True

        result = await repo.get_by_id_for_user_asset(tx.id, ua.id)
        assert result is None

    async def test_다른_user_asset_id로_삭제시_False_반환(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="WRONG_DEL_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        tx = await repo.create(ua.id, _buy())

        deleted = await repo.delete_by_id_for_user_asset(tx.id, ua.id + 9999)
        assert deleted is False

    async def test_존재하지_않는_id_삭제시_False_반환(
        self,
        db_session: AsyncSession,
        user_asset_factory: Any,
        asset_symbol_factory: Any,
    ) -> None:
        sym = await asset_symbol_factory(symbol="MISS_DEL_COIN")
        ua = await user_asset_factory(asset_symbol=sym)

        repo = TransactionRepository(db_session)
        deleted = await repo.delete_by_id_for_user_asset(99999, ua.id)
        assert deleted is False
