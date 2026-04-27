"""Unit tests for BulkTransactionService — mocked repositories."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType
from app.exceptions import CsvImportValidationError
from app.models.asset_symbol import AssetSymbol
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset
from app.repositories.transaction import TransactionRepository
from app.repositories.user_asset import UserAssetRepository
from app.schemas.bulk_transaction import BulkTransactionRow
from app.services.bulk_transaction import BulkTransactionService

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_asset_symbol(
    symbol: str = "BTC",
    exchange: str = "UPBIT",
    currency: str = "KRW",
) -> AssetSymbol:
    sym = AssetSymbol(
        asset_type=AssetType.CRYPTO,
        symbol=symbol,
        exchange=exchange,
        name=symbol,
        currency=currency,
    )
    sym.id = 1
    sym.created_at = datetime.now(UTC)
    sym.updated_at = datetime.now(UTC)
    return sym


def _make_user_asset(user_asset_id: int = 1) -> UserAsset:
    ua = UserAsset(asset_symbol_id=1)
    ua.id = user_asset_id
    ua.asset_symbol = _make_asset_symbol()  # type: ignore[assignment]
    ua.memo = None
    ua.created_at = datetime.now(UTC)
    ua.updated_at = datetime.now(UTC)
    return ua


def _make_transaction(
    tx_id: int = 1,
    user_asset_id: int = 1,
    tx_type: TransactionType = TransactionType.BUY,
    quantity: str = "1.0",
    traded_at: datetime | None = None,
) -> Transaction:
    tx = Transaction(
        user_asset_id=user_asset_id,
        type=tx_type,
        quantity=Decimal(quantity),
        price=Decimal("50000.0"),
        traded_at=traded_at or datetime.now(UTC),
    )
    tx.id = tx_id
    tx.memo = None
    tx.tag = None
    tx.created_at = datetime.now(UTC)
    tx.updated_at = datetime.now(UTC)
    return tx


def _make_bulk_row(
    symbol: str = "BTC",
    exchange: str = "UPBIT",
    tx_type: TransactionType = TransactionType.BUY,
    quantity: str = "1.0",
    price: str = "50000.0",
    traded_at: datetime | None = None,
    memo: str | None = None,
    tag: str | None = None,
) -> BulkTransactionRow:
    return BulkTransactionRow(
        symbol=symbol,
        exchange=exchange,
        type=tx_type,
        quantity=Decimal(quantity),
        price=Decimal(price),
        traded_at=traded_at or datetime.now(UTC),
        memo=memo,
        tag=tag,
    )


def _make_service(
    symbol_map: dict[tuple[str, str], int] | None = None,
    existing_by_ua: dict[int, list[Transaction]] | None = None,
    created_tx: Transaction | None = None,
    flush_side_effect: Exception | None = None,
) -> BulkTransactionService:
    """Build a BulkTransactionService with mocked repositories.

    Args:
        symbol_map: Mapping returned by get_user_asset_ids_by_symbol_exchange.
        existing_by_ua: Mapping returned by list_all_for_user_assets.
        created_tx: A Transaction instance returned per row (same obj, id patched below).
        flush_side_effect: If set, session.flush raises this exception.
    """
    ua_repo = AsyncMock(spec=UserAssetRepository)
    ua_repo.get_user_asset_ids_by_symbol_exchange.return_value = symbol_map or {}

    tx_repo = AsyncMock(spec=TransactionRepository)
    tx_repo.list_all_for_user_assets.return_value = existing_by_ua or {}

    # Mock the session used by the service (add_all + flush + refresh).
    session = AsyncMock()
    if flush_side_effect is not None:
        session.flush.side_effect = flush_side_effect
    tx_repo._session = session

    return BulkTransactionService(transaction_repo=tx_repo, user_asset_repo=ua_repo)


# ---------------------------------------------------------------------------
# import_json — happy path
# ---------------------------------------------------------------------------


class TestImportJsonSuccess:
    async def test_두_종목_각_1건_BUY_정상_등록(self) -> None:
        """Two different assets, one BUY each → imported=2."""
        symbol_map = {("BTC", "UPBIT"): 1, ("AAPL", "NASDAQ"): 2}
        rows = [
            _make_bulk_row("BTC", "UPBIT"),
            _make_bulk_row("AAPL", "NASDAQ", price="200.0"),
        ]
        svc = _make_service(symbol_map=symbol_map)

        count, preview = await svc.import_json(rows)

        assert count == 2
        assert len(preview) <= 10

    async def test_한_종목_BUY_후_SELL_잔고_정상(self) -> None:
        """BUY then SELL with quantity that keeps balance non-negative."""
        symbol_map = {("BTC", "UPBIT"): 1}
        now = datetime.now(UTC)
        rows = [
            _make_bulk_row(
                "BTC", "UPBIT", TransactionType.BUY, "2.0", traded_at=now - timedelta(hours=2)
            ),
            _make_bulk_row(
                "BTC", "UPBIT", TransactionType.SELL, "1.0", traded_at=now - timedelta(hours=1)
            ),
        ]
        svc = _make_service(symbol_map=symbol_map)

        count, preview = await svc.import_json(rows)

        assert count == 2


# ---------------------------------------------------------------------------
# import_json — validation failures
# ---------------------------------------------------------------------------


class TestImportJsonValidationFailures:
    async def test_빈_rows_422(self) -> None:
        svc = _make_service()
        with pytest.raises(CsvImportValidationError) as exc_info:
            await svc.import_json([])
        assert len(exc_info.value.errors) > 0

    async def test_501행_초과_422(self) -> None:
        svc = _make_service()
        rows = [_make_bulk_row() for _ in range(501)]
        with pytest.raises(CsvImportValidationError) as exc_info:
            await svc.import_json(rows)
        assert "Too many rows" in str(exc_info.value.errors[0]["message"])

    async def test_알_수_없는_symbol_exchange_422(self) -> None:
        """Unknown (symbol, exchange) pair → errors[].field == 'symbol'."""
        svc = _make_service(symbol_map={})  # nothing mapped
        rows = [_make_bulk_row("UNKNOWN", "NOWHERE")]

        with pytest.raises(CsvImportValidationError) as exc_info:
            await svc.import_json(rows)

        errors = exc_info.value.errors
        assert len(errors) == 1
        assert errors[0]["field"] == "symbol"
        assert errors[0]["row"] == 1

    async def test_AssetSymbol_있으나_UserAsset_미선언_422(self) -> None:
        """AssetSymbol exists but no UserAsset → symbol not in symbol_map → same 422."""
        svc = _make_service(symbol_map={})  # no user_asset for BTC/UPBIT
        rows = [_make_bulk_row("BTC", "UPBIT")]

        with pytest.raises(CsvImportValidationError) as exc_info:
            await svc.import_json(rows)

        assert exc_info.value.errors[0]["field"] == "symbol"

    async def test_SELL_잔고_음수_422(self) -> None:
        """SELL > existing holding → 'running balance' error message."""
        symbol_map = {("BTC", "UPBIT"): 1}
        # No existing transactions, SELL 1.0 → negative
        svc = _make_service(symbol_map=symbol_map, existing_by_ua={1: []})
        rows = [_make_bulk_row("BTC", "UPBIT", TransactionType.SELL, "1.0")]

        with pytest.raises(CsvImportValidationError) as exc_info:
            await svc.import_json(rows)

        errors = exc_info.value.errors
        assert any("running balance" in str(e["message"]).lower() for e in errors)

    async def test_트랜잭션_롤백_add_all_에러_시_0건_삽입(self) -> None:
        """If flush raises, CsvImportValidationError is NOT raised by service;
        the exception propagates to the caller (session dependency handles rollback)."""
        symbol_map = {("BTC", "UPBIT"): 1}
        rows = [_make_bulk_row("BTC", "UPBIT")]
        svc = _make_service(
            symbol_map=symbol_map,
            flush_side_effect=RuntimeError("DB error"),
        )

        with pytest.raises(RuntimeError, match="DB error"):
            await svc.import_json(rows)

        # Verify add_all was called (rows were built) but flush failed.
        svc._tx_repo._session.add_all.assert_called_once()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# import_csv — header and normalisation tests
# ---------------------------------------------------------------------------


class TestImportCsv:
    def _csv(self, header: str, *data_rows: str) -> str:
        return "\n".join([header, *data_rows])

    async def test_헤더_누락_row0_422(self) -> None:
        csv_text = self._csv(
            "symbol,type,quantity,price,traded_at",  # 'exchange' missing
            "BTC,buy,1.0,50000,2026-04-20T10:00:00+09:00",
        )
        svc = _make_service()
        with pytest.raises(CsvImportValidationError) as exc_info:
            await svc.import_csv(csv_text)
        assert exc_info.value.errors[0]["row"] == 0
        assert "exchange" in str(exc_info.value.errors[0]["message"])

    async def test_type_한글_정규화_OK(self) -> None:
        """매수 → buy / 매도 → sell normalisation."""
        symbol_map = {("BTC", "UPBIT"): 1}
        csv_text = self._csv(
            "symbol,exchange,type,quantity,price,traded_at",
            "BTC,UPBIT,매수,1.0,50000000,2026-04-20T10:00:00+09:00",
        )
        svc = _make_service(symbol_map=symbol_map)

        count, _ = await svc.import_csv(csv_text)
        assert count == 1

    async def test_빈_데이터_행_422(self) -> None:
        """CSV with header but no data rows → error."""
        csv_text = "symbol,exchange,type,quantity,price,traded_at\n"
        svc = _make_service()
        with pytest.raises(CsvImportValidationError) as exc_info:
            await svc.import_csv(csv_text)
        assert len(exc_info.value.errors) > 0
