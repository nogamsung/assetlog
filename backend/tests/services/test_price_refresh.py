"""Unit tests for PriceRefreshService — all adapters and repos are mocked."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.adapters import AdapterRegistry
from app.domain.asset_type import AssetType
from app.domain.price_refresh import (
    FetchBatchResult,
    FetchFailure,
    PriceQuote,
    SymbolRef,
)
from app.services.price_refresh import PriceRefreshService


def _make_ref(
    symbol: str,
    asset_type: AssetType = AssetType.KR_STOCK,
    exchange: str = "KRX",
    asset_symbol_id: int = 1,
) -> SymbolRef:
    return SymbolRef(
        asset_type=asset_type,
        symbol=symbol,
        exchange=exchange,
        asset_symbol_id=asset_symbol_id,
    )


def _make_quote(ref: SymbolRef, price: str = "10000") -> PriceQuote:
    return PriceQuote(
        ref=ref,
        price=Decimal(price),
        currency="KRW",
        fetched_at=datetime(2026, 4, 24, 9, 0, tzinfo=UTC),
    )


def _make_failure(ref: SymbolRef) -> FetchFailure:
    return FetchFailure(ref=ref, error_class="ValueError", error_msg="mock failure")


def _build_mock_adapter(
    asset_type: AssetType,
    result: FetchBatchResult,
) -> MagicMock:
    adapter = MagicMock()
    adapter.asset_type = asset_type
    adapter.fetch_batch = AsyncMock(return_value=result)
    return adapter


@pytest.fixture()
def fixed_clock() -> datetime:
    return datetime(2026, 4, 24, 9, 0, tzinfo=UTC)


class TestRefreshAllPrices:
    async def test_empty_targets_returns_zero_result(self) -> None:
        mock_as_repo = MagicMock()
        mock_as_repo.list_distinct_refresh_targets = AsyncMock(return_value=[])
        mock_pp_repo = MagicMock()
        mock_adapters = MagicMock(spec=AdapterRegistry)

        svc = PriceRefreshService(
            asset_symbol_repo=mock_as_repo,
            price_point_repo=mock_pp_repo,
            adapters=mock_adapters,
        )
        result = await svc.refresh_all_prices()

        assert result.total == 0
        assert result.success == 0
        assert result.failed == 0

    async def test_ten_symbols_seven_success_three_fail(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """10 symbols: 4 KR_STOCK (3 ok, 1 fail), 3 US_STOCK (2 ok, 1 fail),
        3 CRYPTO (2 ok, 1 fail) → success=7, failed=3."""
        import logging

        kr_refs = [_make_ref(f"00{i:04d}", AssetType.KR_STOCK, "KRX", i) for i in range(1, 5)]
        us_refs = [_make_ref(f"US{i}", AssetType.US_STOCK, "NASDAQ", i + 10) for i in range(1, 4)]
        cr_refs = [
            _make_ref(f"BTC/USDT{i}", AssetType.CRYPTO, "binance", i + 20) for i in range(1, 4)
        ]

        kr_result = FetchBatchResult(
            successes=[_make_quote(r) for r in kr_refs[:3]],
            failures=[_make_failure(kr_refs[3])],
        )
        us_result = FetchBatchResult(
            successes=[_make_quote(r, "200") for r in us_refs[:2]],
            failures=[_make_failure(us_refs[2])],
        )
        cr_result = FetchBatchResult(
            successes=[_make_quote(r, "60000") for r in cr_refs[:2]],
            failures=[_make_failure(cr_refs[2])],
        )

        kr_adapter = _build_mock_adapter(AssetType.KR_STOCK, kr_result)
        us_adapter = _build_mock_adapter(AssetType.US_STOCK, us_result)
        cr_adapter = _build_mock_adapter(AssetType.CRYPTO, cr_result)

        registry = AdapterRegistry(
            {
                AssetType.KR_STOCK: kr_adapter,
                AssetType.US_STOCK: us_adapter,
                AssetType.CRYPTO: cr_adapter,
            }
        )

        all_refs = kr_refs + us_refs + cr_refs

        mock_as_repo = MagicMock()
        mock_as_repo.list_distinct_refresh_targets = AsyncMock(return_value=all_refs)
        mock_as_repo.bulk_update_cache = AsyncMock(return_value=7)

        mock_pp_repo = MagicMock()
        mock_pp_repo.bulk_insert = AsyncMock(return_value=7)

        svc = PriceRefreshService(
            asset_symbol_repo=mock_as_repo,
            price_point_repo=mock_pp_repo,
            adapters=registry,
        )

        with caplog.at_level(logging.WARNING, logger="app.services.price_refresh"):
            result = await svc.refresh_all_prices()

        assert result.total == 10
        assert result.success == 7
        assert result.failed == 3
        assert len(result.failures) == 3

    async def test_bulk_insert_called_with_successes(self) -> None:
        ref = _make_ref("005930", AssetType.KR_STOCK, "KRX", 1)
        quote = _make_quote(ref)
        kr_result = FetchBatchResult(successes=[quote], failures=[])

        kr_adapter = _build_mock_adapter(AssetType.KR_STOCK, kr_result)
        registry = AdapterRegistry({AssetType.KR_STOCK: kr_adapter})

        mock_as_repo = MagicMock()
        mock_as_repo.list_distinct_refresh_targets = AsyncMock(return_value=[ref])
        mock_as_repo.bulk_update_cache = AsyncMock(return_value=1)

        mock_pp_repo = MagicMock()
        mock_pp_repo.bulk_insert = AsyncMock(return_value=1)

        svc = PriceRefreshService(
            asset_symbol_repo=mock_as_repo,
            price_point_repo=mock_pp_repo,
            adapters=registry,
        )
        await svc.refresh_all_prices()

        mock_pp_repo.bulk_insert.assert_awaited_once()
        inserted = mock_pp_repo.bulk_insert.call_args[0][0]
        assert len(inserted) == 1
        assert inserted[0] == quote

    async def test_bulk_update_cache_called_for_successes(self) -> None:
        ref = _make_ref("AAPL", AssetType.US_STOCK, "NASDAQ", 1)
        quote = _make_quote(ref, "190")
        us_result = FetchBatchResult(successes=[quote], failures=[])

        us_adapter = _build_mock_adapter(AssetType.US_STOCK, us_result)
        registry = AdapterRegistry({AssetType.US_STOCK: us_adapter})

        mock_as_repo = MagicMock()
        mock_as_repo.list_distinct_refresh_targets = AsyncMock(return_value=[ref])
        mock_as_repo.bulk_update_cache = AsyncMock(return_value=1)

        mock_pp_repo = MagicMock()
        mock_pp_repo.bulk_insert = AsyncMock(return_value=1)

        svc = PriceRefreshService(
            asset_symbol_repo=mock_as_repo,
            price_point_repo=mock_pp_repo,
            adapters=registry,
        )
        await svc.refresh_all_prices()

        mock_as_repo.bulk_update_cache.assert_awaited_once()
        rows = mock_as_repo.bulk_update_cache.call_args[0][0]
        assert len(rows) == 1
        asset_id, price, _fetched_at = rows[0]
        assert asset_id == 1
        assert price == Decimal("190")

    async def test_failed_symbols_not_in_bulk_update(self) -> None:
        ref_ok = _make_ref("005930", AssetType.KR_STOCK, "KRX", 1)
        ref_fail = _make_ref("999999", AssetType.KR_STOCK, "KRX", 2)

        kr_result = FetchBatchResult(
            successes=[_make_quote(ref_ok)],
            failures=[_make_failure(ref_fail)],
        )
        kr_adapter = _build_mock_adapter(AssetType.KR_STOCK, kr_result)
        registry = AdapterRegistry({AssetType.KR_STOCK: kr_adapter})

        mock_as_repo = MagicMock()
        mock_as_repo.list_distinct_refresh_targets = AsyncMock(return_value=[ref_ok, ref_fail])
        mock_as_repo.bulk_update_cache = AsyncMock(return_value=1)

        mock_pp_repo = MagicMock()
        mock_pp_repo.bulk_insert = AsyncMock(return_value=1)

        svc = PriceRefreshService(
            asset_symbol_repo=mock_as_repo,
            price_point_repo=mock_pp_repo,
            adapters=registry,
        )
        await svc.refresh_all_prices()

        rows = mock_as_repo.bulk_update_cache.call_args[0][0]
        updated_ids = {r[0] for r in rows}
        assert 2 not in updated_ids  # failed symbol must not be updated

    async def test_decimal_precision_preserved(self) -> None:
        ref = _make_ref("005930", AssetType.KR_STOCK, "KRX", 1)
        precise_price = Decimal("75000.123456")
        quote = PriceQuote(
            ref=ref,
            price=precise_price,
            currency="KRW",
            fetched_at=datetime(2026, 4, 24, 9, 0, tzinfo=UTC),
        )
        kr_result = FetchBatchResult(successes=[quote], failures=[])
        kr_adapter = _build_mock_adapter(AssetType.KR_STOCK, kr_result)
        registry = AdapterRegistry({AssetType.KR_STOCK: kr_adapter})

        mock_as_repo = MagicMock()
        mock_as_repo.list_distinct_refresh_targets = AsyncMock(return_value=[ref])
        mock_as_repo.bulk_update_cache = AsyncMock(return_value=1)

        mock_pp_repo = MagicMock()
        mock_pp_repo.bulk_insert = AsyncMock(return_value=1)

        svc = PriceRefreshService(
            asset_symbol_repo=mock_as_repo,
            price_point_repo=mock_pp_repo,
            adapters=registry,
        )
        await svc.refresh_all_prices()

        rows = mock_as_repo.bulk_update_cache.call_args[0][0]
        _, stored_price, _ = rows[0]
        # Price must remain Decimal — no float conversion
        assert isinstance(stored_price, Decimal)
        assert stored_price == precise_price

    async def test_adapter_crash_isolates_other_adapters(self) -> None:
        """If one adapter crashes, other asset types should still succeed."""
        kr_ref = _make_ref("005930", AssetType.KR_STOCK, "KRX", 1)
        us_ref = _make_ref("AAPL", AssetType.US_STOCK, "NASDAQ", 2)

        kr_adapter = MagicMock()
        kr_adapter.asset_type = AssetType.KR_STOCK
        kr_adapter.fetch_batch = AsyncMock(side_effect=RuntimeError("KR adapter crashed"))

        us_result = FetchBatchResult(successes=[_make_quote(us_ref, "190")], failures=[])
        us_adapter = _build_mock_adapter(AssetType.US_STOCK, us_result)

        registry = AdapterRegistry({AssetType.KR_STOCK: kr_adapter, AssetType.US_STOCK: us_adapter})

        mock_as_repo = MagicMock()
        mock_as_repo.list_distinct_refresh_targets = AsyncMock(return_value=[kr_ref, us_ref])
        mock_as_repo.bulk_update_cache = AsyncMock(return_value=1)

        mock_pp_repo = MagicMock()
        mock_pp_repo.bulk_insert = AsyncMock(return_value=1)

        svc = PriceRefreshService(
            asset_symbol_repo=mock_as_repo,
            price_point_repo=mock_pp_repo,
            adapters=registry,
        )
        result = await svc.refresh_all_prices()

        assert result.success == 1
        assert result.failed == 1

    async def test_refresh_result_has_correct_structure(self) -> None:
        ref = _make_ref("005930", AssetType.KR_STOCK, "KRX", 1)
        quote = _make_quote(ref)
        kr_result = FetchBatchResult(successes=[quote], failures=[])
        kr_adapter = _build_mock_adapter(AssetType.KR_STOCK, kr_result)
        registry = AdapterRegistry({AssetType.KR_STOCK: kr_adapter})

        mock_as_repo = MagicMock()
        mock_as_repo.list_distinct_refresh_targets = AsyncMock(return_value=[ref])
        mock_as_repo.bulk_update_cache = AsyncMock(return_value=1)

        mock_pp_repo = MagicMock()
        mock_pp_repo.bulk_insert = AsyncMock(return_value=1)

        svc = PriceRefreshService(
            asset_symbol_repo=mock_as_repo,
            price_point_repo=mock_pp_repo,
            adapters=registry,
        )
        result = await svc.refresh_all_prices()

        assert result.total == 1
        assert result.success == 1
        assert result.failed == 0
        assert result.elapsed_ms >= 0
        assert result.failures == []

    async def test_warning_logged_for_failures(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        ref = _make_ref("FAIL", AssetType.KR_STOCK, "KRX", 1)
        kr_result = FetchBatchResult(successes=[], failures=[_make_failure(ref)])
        kr_adapter = _build_mock_adapter(AssetType.KR_STOCK, kr_result)
        registry = AdapterRegistry({AssetType.KR_STOCK: kr_adapter})

        mock_as_repo = MagicMock()
        mock_as_repo.list_distinct_refresh_targets = AsyncMock(return_value=[ref])
        mock_as_repo.bulk_update_cache = AsyncMock(return_value=0)

        mock_pp_repo = MagicMock()
        mock_pp_repo.bulk_insert = AsyncMock(return_value=0)

        svc = PriceRefreshService(
            asset_symbol_repo=mock_as_repo,
            price_point_repo=mock_pp_repo,
            adapters=registry,
        )

        with caplog.at_level(logging.WARNING, logger="app.services.price_refresh"):
            await svc.refresh_all_prices()

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) >= 1
