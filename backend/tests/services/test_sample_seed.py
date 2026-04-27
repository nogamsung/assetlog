"""Unit tests for SampleSeedService."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType
from app.models.asset_symbol import AssetSymbol
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset
from app.repositories.asset_symbol import AssetSymbolRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.user_asset import UserAssetRepository
from app.services.sample_seed import _SAMPLE_SYMBOLS, SampleSeedService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_asset_symbol(sym_id: int = 1, symbol: str = "BTC") -> AssetSymbol:
    sym = AssetSymbol(
        asset_type=AssetType.CRYPTO,
        symbol=symbol,
        exchange="BINANCE",
        name="Bitcoin",
        currency="USD",
    )
    sym.id = sym_id
    sym.last_price = None
    sym.last_price_refreshed_at = None
    sym.created_at = datetime.now(UTC)
    sym.updated_at = datetime.now(UTC)
    return sym


def _make_user_asset(ua_id: int = 1, sym_id: int = 1) -> UserAsset:
    sym = _make_asset_symbol(sym_id)
    ua = UserAsset(asset_symbol_id=sym_id)
    ua.id = ua_id
    ua.asset_symbol = sym  # type: ignore[assignment]  # mock relationship
    ua.memo = None
    ua.created_at = datetime.now(UTC)
    ua.updated_at = datetime.now(UTC)
    return ua


def _make_transaction(tx_id: int = 1, ua_id: int = 1) -> Transaction:
    tx = Transaction(
        user_asset_id=ua_id,
        type=TransactionType.BUY,
        quantity=Decimal("1.0"),
        price=Decimal("65000.0"),
        traded_at=datetime.now(UTC),
    )
    tx.id = tx_id
    tx.memo = "sample"
    tx.tag = "seed"
    tx.created_at = datetime.now(UTC)
    tx.updated_at = datetime.now(UTC)
    return tx


def _build_service(
    *,
    existing_assets: list[UserAsset] | None = None,
    symbol_exists: bool = False,
) -> tuple[SampleSeedService, AsyncMock, AsyncMock, AsyncMock]:
    """Return (service, symbol_repo_mock, ua_repo_mock, tx_repo_mock)."""
    symbol_repo = AsyncMock(spec=AssetSymbolRepository)
    ua_repo = AsyncMock(spec=UserAssetRepository)
    tx_repo = AsyncMock(spec=TransactionRepository)

    ua_repo.list_all.return_value = existing_assets or []

    if symbol_exists:
        # Return a pre-existing symbol for every get_by_triple call.
        def _symbol_side_effect(**kwargs: Any) -> AssetSymbol:
            sym = _make_asset_symbol()
            sym.symbol = kwargs.get("symbol", "BTC")
            return sym

        symbol_repo.get_by_triple.side_effect = _symbol_side_effect
    else:
        # No pre-existing symbols — create path.
        call_count: list[int] = [0]

        async def _create_side_effect(**kwargs: Any) -> AssetSymbol:
            call_count[0] += 1
            sym = _make_asset_symbol(sym_id=call_count[0], symbol=kwargs.get("symbol", "BTC"))
            return sym

        symbol_repo.get_by_triple.return_value = None
        symbol_repo.create.side_effect = _create_side_effect

    ua_call_count: list[int] = [0]

    async def _ua_create_side_effect(
        asset_symbol_id: int, memo: Any = None
    ) -> UserAsset:
        ua_call_count[0] += 1
        return _make_user_asset(ua_id=ua_call_count[0], sym_id=asset_symbol_id)

    ua_repo.create.side_effect = _ua_create_side_effect

    tx_call_count: list[int] = [0]

    async def _tx_create_side_effect(user_asset_id: int, data: Any) -> Transaction:
        tx_call_count[0] += 1
        return _make_transaction(tx_id=tx_call_count[0], ua_id=user_asset_id)

    tx_repo.create.side_effect = _tx_create_side_effect

    service = SampleSeedService(
        asset_symbol_repo=symbol_repo,
        user_asset_repo=ua_repo,
        transaction_repo=tx_repo,
    )
    return service, symbol_repo, ua_repo, tx_repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSampleSeedServiceSkip:
    async def test_이미_자산이_있는_사용자는_스킵된다(self) -> None:
        existing = [_make_user_asset()]
        service, _, ua_repo, tx_repo = _build_service(existing_assets=existing)

        result = await service.seed()

        assert result.seeded is False
        assert result.reason == "user_already_has_assets"
        assert result.user_assets_created == 0
        assert result.transactions_created == 0
        tx_repo.create.assert_not_called()

    async def test_두_번_호출_시_두_번째는_스킵된다(self) -> None:
        """First call succeeds, second returns seeded=False (simulated via mock state)."""
        # First call: no existing assets.
        service, _, ua_repo, tx_repo = _build_service(existing_assets=[])
        result_first = await service.seed()
        assert result_first.seeded is True

        # Second call: simulate existing assets returned.
        ua_repo.list_all.return_value = [_make_user_asset()]
        result_second = await service.seed()
        assert result_second.seeded is False
        assert result_second.reason == "user_already_has_assets"


class TestSampleSeedServiceSuccess:
    async def test_신규_사용자는_5개_자산이_생성된다(self) -> None:
        service, symbol_repo, ua_repo, tx_repo = _build_service()

        result = await service.seed()

        assert result.seeded is True
        assert result.user_assets_created == 5
        assert result.symbols_created == 5
        assert result.symbols_reused == 0
        assert result.transactions_created >= 10  # at least 2 per symbol
        assert result.transactions_created <= 20  # at most 4 per symbol

    async def test_기존_심볼이_있으면_재사용된다(self) -> None:
        service, symbol_repo, ua_repo, tx_repo = _build_service(symbol_exists=True)

        result = await service.seed()

        assert result.seeded is True
        assert result.symbols_reused == 5
        assert result.symbols_created == 0
        symbol_repo.create.assert_not_called()

    async def test_생성된_user_asset_수는_샘플_심볼_수와_같다(self) -> None:
        service, _, ua_repo, _ = _build_service()
        result = await service.seed()
        assert ua_repo.create.call_count == len(_SAMPLE_SYMBOLS)
        assert result.user_assets_created == len(_SAMPLE_SYMBOLS)

    async def test_거래_수는_각_자산당_2에서_4_사이이다(self) -> None:
        service, _, _, tx_repo = _build_service()
        result = await service.seed()
        n_symbols = len(_SAMPLE_SYMBOLS)
        assert result.transactions_created == tx_repo.create.call_count
        assert n_symbols * 2 <= result.transactions_created <= n_symbols * 4


class TestSampleSeedServiceDeterminism:
    async def test_같은_user_id는_같은_거래_수를_생성한다(self) -> None:
        """Two fresh seeds with the same user_id must produce identical tx count."""
        service_a, _, _, tx_repo_a = _build_service()
        result_a = await service_a.seed()

        service_b, _, _, tx_repo_b = _build_service()
        result_b = await service_b.seed()

        assert result_a.transactions_created == result_b.transactions_created

    async def test_owner_한_명이므로_항상_같은_결과(self) -> None:
        """Single-owner mode: all seeds produce the same result."""
        results: set[int] = set()
        for _ in range(5):
            service, _, _, _ = _build_service()
            result = await service.seed()
            results.add(result.transactions_created)
        # Only one distinct count (deterministic for single owner).
        assert len(results) == 1

    async def test_결정론적_거래는_BUY_타입만_포함한다(self) -> None:
        service, _, _, tx_repo = _build_service()
        await service.seed()

        for create_call in tx_repo.create.call_args_list:
            _, kwargs = create_call
            tx_data = kwargs.get("data") or create_call.args[1]
            assert tx_data.type == TransactionType.BUY


class TestSampleSeedResponseSchema:
    async def test_seed_false_시_counts는_0이다(self) -> None:
        existing = [_make_user_asset()]
        service, _, _, _ = _build_service(existing_assets=existing)
        result = await service.seed()

        assert result.user_assets_created == 0
        assert result.transactions_created == 0
        assert result.symbols_created == 0
        assert result.symbols_reused == 0

    async def test_seed_true_시_reason은_None이다(self) -> None:
        service, _, _, _ = _build_service()
        result = await service.seed()

        assert result.seeded is True
        assert result.reason is None
