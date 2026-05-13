"""Unit tests for PriceHistoryBackfillService.

The yfinance call is mocked so we test ticker selection, idempotency, and
the per-symbol guard against re-inserting data that's already covered.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.asset_type import AssetType
from app.models.asset_symbol import AssetSymbol
from app.services.price_history_backfill import (
    PriceHistoryBackfillService,
    _yfinance_ticker_for,
)


def _symbol(
    id_: int,
    symbol: str,
    asset_type: AssetType = AssetType.US_STOCK,
    name: str = "",
    exchange: str = "NYSE",
    currency: str = "USD",
) -> AssetSymbol:
    s = AssetSymbol(
        symbol=symbol,
        name=name or symbol,
        asset_type=asset_type,
        exchange=exchange,
        currency=currency,
    )
    s.id = id_
    return s


class TestTickerMapping:
    def test_us_stock_with_ticker_passes_through(self) -> None:
        assert _yfinance_ticker_for(_symbol(1, "AMD")) == "AMD"

    def test_us_stock_raw_isin_is_unmappable(self) -> None:
        assert _yfinance_ticker_for(_symbol(1, "US0079031078")) is None

    def test_kr_stock_six_digit_gets_ks_suffix(self) -> None:
        s = _symbol(1, "005930", asset_type=AssetType.KR_STOCK, exchange="KRX", currency="KRW")
        assert _yfinance_ticker_for(s) == "005930.KS"

    def test_kr_stock_korean_name_is_unmappable(self) -> None:
        s = _symbol(1, "삼성전자", asset_type=AssetType.KR_STOCK, exchange="KRX", currency="KRW")
        assert _yfinance_ticker_for(s) is None

    def test_crypto_is_unmappable(self) -> None:
        s = _symbol(1, "BTC", asset_type=AssetType.CRYPTO, exchange="UPBIT", currency="KRW")
        assert _yfinance_ticker_for(s) is None


class TestBackfillAll:
    @pytest.mark.asyncio
    async def test_skip_count_when_no_symbols_mappable(self) -> None:
        """If every symbol is unmappable (ISIN/korean name), nothing is inserted."""
        session = AsyncMock()
        # earliest-trade query returns two unmappable symbols
        execute_result = MagicMock()
        execute_result.all.return_value = [
            (_symbol(1, "US0079031078"), datetime(2025, 1, 1, tzinfo=UTC)),
            (_symbol(2, "삼성전자", asset_type=AssetType.KR_STOCK, exchange="KRX", currency="KRW"),
             datetime(2025, 1, 1, tzinfo=UTC)),
        ]
        session.execute.return_value = execute_result

        repo = AsyncMock()
        repo.bulk_insert = AsyncMock(return_value=0)

        svc = PriceHistoryBackfillService(session=session, price_point_repo=repo)
        result = await svc.backfill_all()

        assert result.symbols_attempted == 0
        assert result.symbols_skipped == 2
        assert result.points_inserted == 0
        repo.bulk_insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_inserts_history_for_mappable_symbol(self) -> None:
        """A mappable symbol with no existing price_points triggers a bulk insert."""
        session = AsyncMock()

        # First call: earliest-trade query
        earliest_result = MagicMock()
        earliest_result.all.return_value = [
            (_symbol(1, "AMD"), datetime(2025, 1, 5, tzinfo=UTC)),
        ]
        # Second call: existing-oldest price_point query → None (no data yet)
        existing_oldest_result = MagicMock()
        existing_oldest_result.scalar_one_or_none.return_value = None

        session.execute = AsyncMock(side_effect=[earliest_result, existing_oldest_result])

        repo = AsyncMock()
        repo.bulk_insert = AsyncMock(return_value=2)

        svc = PriceHistoryBackfillService(session=session, price_point_repo=repo)

        with patch(
            "app.services.price_history_backfill._fetch_history_sync",
            return_value=[
                (date(2025, 1, 6), Decimal("120.50")),
                (date(2025, 1, 7), Decimal("121.00")),
            ],
        ):
            result = await svc.backfill_all()

        assert result.symbols_attempted == 1
        assert result.symbols_skipped == 0
        assert result.points_inserted == 2
        repo.bulk_insert.assert_called_once()
        quotes = repo.bulk_insert.call_args.args[0]
        assert {str(q.price) for q in quotes} == {"120.50", "121.00"}

    @pytest.mark.asyncio
    async def test_idempotent_when_existing_data_covers_range(self) -> None:
        """yfinance rows on/after the existing oldest fetched_at are dropped."""
        session = AsyncMock()
        earliest_result = MagicMock()
        earliest_result.all.return_value = [
            (_symbol(1, "AMD"), datetime(2025, 1, 1, tzinfo=UTC)),
        ]
        existing_oldest_result = MagicMock()
        existing_oldest_result.scalar_one_or_none.return_value = datetime(
            2025, 1, 5, 16, 0, tzinfo=UTC
        )
        session.execute = AsyncMock(side_effect=[earliest_result, existing_oldest_result])

        repo = AsyncMock()
        repo.bulk_insert = AsyncMock(return_value=2)

        svc = PriceHistoryBackfillService(session=session, price_point_repo=repo)

        with patch(
            "app.services.price_history_backfill._fetch_history_sync",
            return_value=[
                (date(2025, 1, 2), Decimal("100")),  # before existing → insert
                (date(2025, 1, 3), Decimal("101")),  # before existing → insert
                (date(2025, 1, 5), Decimal("105")),  # at existing → skip
                (date(2025, 1, 6), Decimal("106")),  # after existing → skip
            ],
        ):
            result = await svc.backfill_all()

        assert result.symbols_attempted == 1
        quotes = repo.bulk_insert.call_args.args[0]
        assert len(quotes) == 2  # only the two pre-existing-oldest rows
