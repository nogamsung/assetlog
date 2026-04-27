"""Unit tests for TagBreakdownService — mocked repository, pure logic."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

from app.repositories.portfolio import PortfolioRepository
from app.services.tag_breakdown import TagBreakdownService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RawRow = tuple[str | None, str, str, Decimal, int]


def _make_service(rows: list[RawRow]) -> TagBreakdownService:
    mock_repo = AsyncMock(spec=PortfolioRepository)
    mock_repo.list_tag_breakdown_rows.return_value = rows
    return TagBreakdownService(repo=mock_repo)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestTagBreakdownServiceEmpty:
    async def test_거래없음_빈_entries(self) -> None:
        svc = _make_service([])
        result = await svc.get_breakdown()
        assert result.entries == []

    async def test_repo가_user_id로_호출됨(self) -> None:
        mock_repo = AsyncMock(spec=PortfolioRepository)
        mock_repo.list_tag_breakdown_rows.return_value = []
        svc = TagBreakdownService(repo=mock_repo)

        await svc.get_breakdown()
        mock_repo.list_tag_breakdown_rows.assert_awaited_once()


# ---------------------------------------------------------------------------
# Single tag scenarios
# ---------------------------------------------------------------------------


class TestTagBreakdownServiceSingleTag:
    async def test_단일태그_BUY_1건_카운트_정확(self) -> None:
        rows: list[RawRow] = [
            ("DCA", "USD", "buy", Decimal("150.00"), 1),
        ]
        svc = _make_service(rows)
        result = await svc.get_breakdown()

        assert len(result.entries) == 1
        entry = result.entries[0]
        assert entry.tag == "DCA"
        assert entry.transaction_count == 1
        assert entry.buy_count == 1
        assert entry.sell_count == 0
        assert entry.total_bought_value_by_currency == {"USD": "150.00"}
        assert entry.total_sold_value_by_currency == {}

    async def test_단일태그_SELL_1건_카운트_정확(self) -> None:
        rows: list[RawRow] = [
            ("DCA", "USD", "sell", Decimal("200.00"), 1),
        ]
        svc = _make_service(rows)
        result = await svc.get_breakdown()

        entry = result.entries[0]
        assert entry.buy_count == 0
        assert entry.sell_count == 1
        assert entry.total_bought_value_by_currency == {}
        assert entry.total_sold_value_by_currency == {"USD": "200.00"}

    async def test_BUY_SELL_혼합_태그_카운트_금액_정확(self) -> None:
        rows: list[RawRow] = [
            ("DCA", "USD", "buy", Decimal("1500.00"), 10),
            ("DCA", "USD", "sell", Decimal("100.00"), 2),
        ]
        svc = _make_service(rows)
        result = await svc.get_breakdown()

        assert len(result.entries) == 1
        entry = result.entries[0]
        assert entry.transaction_count == 12
        assert entry.buy_count == 10
        assert entry.sell_count == 2
        assert entry.total_bought_value_by_currency == {"USD": "1500.00"}
        assert entry.total_sold_value_by_currency == {"USD": "100.00"}


# ---------------------------------------------------------------------------
# Multi-currency
# ---------------------------------------------------------------------------


class TestTagBreakdownServiceMultiCurrency:
    async def test_다중통화_USD_KRW_분리(self) -> None:
        rows: list[RawRow] = [
            ("DCA", "USD", "buy", Decimal("1500.00"), 10),
            ("DCA", "KRW", "buy", Decimal("5000000.00"), 2),
            ("DCA", "USD", "sell", Decimal("100.00"), 2),
        ]
        svc = _make_service(rows)
        result = await svc.get_breakdown()

        assert len(result.entries) == 1
        entry = result.entries[0]
        assert entry.transaction_count == 14
        assert entry.buy_count == 12
        assert entry.sell_count == 2
        assert entry.total_bought_value_by_currency["USD"] == "1500.00"
        assert entry.total_bought_value_by_currency["KRW"] == "5000000.00"
        assert entry.total_sold_value_by_currency["USD"] == "100.00"
        assert "KRW" not in entry.total_sold_value_by_currency

    async def test_sold_KRW_0인_경우_sold_dict에_없음(self) -> None:
        """If there are no KRW SELL rows, the dict key is absent (not '0.00')."""
        rows: list[RawRow] = [
            ("DCA", "USD", "buy", Decimal("1500.00"), 10),
            ("DCA", "KRW", "buy", Decimal("5000000.00"), 2),
            ("DCA", "USD", "sell", Decimal("100.00"), 2),
        ]
        svc = _make_service(rows)
        result = await svc.get_breakdown()

        entry = result.entries[0]
        # KRW has no SELL rows — key must not exist
        assert "KRW" not in entry.total_sold_value_by_currency


# ---------------------------------------------------------------------------
# Untagged transactions
# ---------------------------------------------------------------------------


class TestTagBreakdownServiceUntagged:
    async def test_untagged_거래_tag_None_entry(self) -> None:
        rows: list[RawRow] = [
            (None, "KRW", "buy", Decimal("1000000.00"), 3),
        ]
        svc = _make_service(rows)
        result = await svc.get_breakdown()

        assert len(result.entries) == 1
        entry = result.entries[0]
        assert entry.tag is None
        assert entry.buy_count == 3

    async def test_untagged_정렬_항상_마지막(self) -> None:
        rows: list[RawRow] = [
            (None, "KRW", "buy", Decimal("1000000.00"), 5),
            ("DCA", "USD", "buy", Decimal("500.00"), 3),
            ("Swing", "USD", "sell", Decimal("200.00"), 2),
        ]
        svc = _make_service(rows)
        result = await svc.get_breakdown()

        # untagged (count=5) has more than tagged entries BUT must still be last
        assert result.entries[-1].tag is None

    async def test_untagged_단독일때_entries_하나(self) -> None:
        rows: list[RawRow] = [
            (None, "USD", "buy", Decimal("300.00"), 2),
        ]
        svc = _make_service(rows)
        result = await svc.get_breakdown()

        assert len(result.entries) == 1
        assert result.entries[0].tag is None


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------


class TestTagBreakdownServiceSort:
    async def test_정렬_transaction_count_DESC(self) -> None:
        rows: list[RawRow] = [
            ("Low", "USD", "buy", Decimal("100.00"), 1),
            ("High", "USD", "buy", Decimal("500.00"), 5),
            ("Mid", "USD", "buy", Decimal("300.00"), 3),
        ]
        svc = _make_service(rows)
        result = await svc.get_breakdown()

        counts = [e.transaction_count for e in result.entries]
        assert counts == [5, 3, 1]

    async def test_정렬_동률시_tag_ASC(self) -> None:
        rows: list[RawRow] = [
            ("Zebra", "USD", "buy", Decimal("100.00"), 2),
            ("Alpha", "USD", "buy", Decimal("100.00"), 2),
            ("Mid", "USD", "buy", Decimal("100.00"), 2),
        ]
        svc = _make_service(rows)
        result = await svc.get_breakdown()

        tags = [e.tag for e in result.entries]
        assert tags == ["Alpha", "Mid", "Zebra"]

    async def test_정렬_null_항상_마지막_count무관(self) -> None:
        rows: list[RawRow] = [
            (None, "USD", "buy", Decimal("100.00"), 100),  # highest count
            ("A", "USD", "buy", Decimal("10.00"), 1),
        ]
        svc = _make_service(rows)
        result = await svc.get_breakdown()

        # null wins on count but must be last
        assert result.entries[0].tag == "A"
        assert result.entries[1].tag is None

    async def test_복합_정렬_count_DESC_tag_ASC_null_last(self) -> None:
        rows: list[RawRow] = [
            (None, "KRW", "buy", Decimal("1000000.00"), 5),
            ("DCA", "USD", "buy", Decimal("1500.00"), 10),
            ("Swing", "USD", "sell", Decimal("100.00"), 2),
            ("HODL", "KRW", "buy", Decimal("2000000.00"), 10),
        ]
        svc = _make_service(rows)
        result = await svc.get_breakdown()

        tags = [e.tag for e in result.entries]
        # DCA and HODL both have 10 → alphabetical → DCA first
        assert tags[0] == "DCA"
        assert tags[1] == "HODL"
        assert tags[2] == "Swing"
        assert tags[-1] is None

    async def test_Decimal_str_직렬화(self) -> None:
        rows: list[RawRow] = [
            ("DCA", "USD", "buy", Decimal("1500.123456"), 1),
        ]
        svc = _make_service(rows)
        result = await svc.get_breakdown()

        val = result.entries[0].total_bought_value_by_currency["USD"]
        assert isinstance(val, str)
        assert val == "1500.123456"

    async def test_다중태그_멀티통화_currency_누적(self) -> None:
        """Same tag+currency with multiple rows (e.g. BUY and SELL) are merged."""
        rows: list[RawRow] = [
            ("DCA", "USD", "buy", Decimal("700.00"), 7),
            ("DCA", "USD", "buy", Decimal("300.00"), 3),  # same tag+currency+type
        ]
        svc = _make_service(rows)
        result = await svc.get_breakdown()

        entry = result.entries[0]
        # In practice the DB GROUP BY collapses these, but the service must
        # handle the same (tag, currency, type) appearing in two raw rows too.
        assert entry.buy_count == 10
        assert entry.total_bought_value_by_currency["USD"] == "1000.00"
