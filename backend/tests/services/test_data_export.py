"""Unit tests for DataExportService — uses AsyncMock repositories."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType
from app.models.asset_symbol import AssetSymbol
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset
from app.repositories.transaction import TransactionRepository
from app.repositories.user_asset import UserAssetRepository
from app.services.data_export import DataExportService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_symbol(
    sym_id: int = 7,
    symbol: str = "BTC",
    asset_type: AssetType = AssetType.CRYPTO,
    exchange: str = "upbit",
    name: str = "Bitcoin",
    currency: str = "KRW",
    last_price: Decimal | None = Decimal("50000.000000"),
) -> AssetSymbol:
    s = AssetSymbol(
        asset_type=asset_type,
        symbol=symbol,
        exchange=exchange,
        name=name,
        currency=currency,
    )
    s.id = sym_id
    s.last_price = last_price
    s.last_price_refreshed_at = None
    s.last_synced_at = None
    s.created_at = datetime.now(UTC)
    s.updated_at = datetime.now(UTC)
    return s


def _make_user_asset(
    ua_id: int = 1,
    asset_symbol: AssetSymbol | None = None,
    memo: str | None = None,
) -> UserAsset:
    sym = asset_symbol if asset_symbol is not None else _make_symbol()
    ua = UserAsset(
        asset_symbol_id=sym.id,
        memo=memo,
    )
    ua.id = ua_id
    ua.asset_symbol = sym  # manually attach eager-loaded relationship
    ua.created_at = datetime.now(UTC)
    ua.updated_at = datetime.now(UTC)
    return ua


def _make_transaction(
    tx_id: int = 1,
    user_asset_id: int = 1,
    tx_type: TransactionType = TransactionType.BUY,
    quantity: str = "1.5",
    price: str = "50000.0",
    memo: str | None = None,
    tag: str | None = None,
    hours_ago: int = 1,
) -> Transaction:
    tx = Transaction(
        user_asset_id=user_asset_id,
        type=tx_type,
        quantity=Decimal(quantity),
        price=Decimal(price),
        traded_at=datetime.now(UTC) - timedelta(hours=hours_ago),
        memo=memo,
        tag=tag,
    )
    tx.id = tx_id
    tx.created_at = datetime.now(UTC)
    tx.updated_at = datetime.now(UTC)
    return tx


def _make_service(
    user_assets: list[UserAsset],
    transactions: list[Transaction],
) -> DataExportService:
    ua_repo = AsyncMock(spec=UserAssetRepository)
    tx_repo = AsyncMock(spec=TransactionRepository)
    ua_repo.list_all.return_value = user_assets
    tx_repo.list_all.return_value = transactions
    return DataExportService(user_asset_repo=ua_repo, transaction_repo=tx_repo)


# ---------------------------------------------------------------------------
# export_json tests
# ---------------------------------------------------------------------------


class TestExportJson:
    async def test_빈_사용자_빈_배열_반환(self) -> None:
        service = _make_service(user_assets=[], transactions=[])
        envelope = await service.export_json()

        assert envelope.user_assets == []
        assert envelope.transactions == []
        assert envelope.exported_at.tzinfo is not None

    async def test_자산과_거래_있는_사용자_정확한_카운트(self) -> None:
        sym = _make_symbol()
        ua = _make_user_asset(ua_id=1, asset_symbol=sym)
        txs = [
            _make_transaction(tx_id=1, user_asset_id=1),
            _make_transaction(tx_id=2, user_asset_id=1, hours_ago=2),
        ]
        service = _make_service(user_assets=[ua], transactions=txs)
        envelope = await service.export_json()

        assert len(envelope.user_assets) == 1
        assert len(envelope.transactions) == 2

    async def test_user_asset에_asset_symbol이_포함된다(self) -> None:
        sym = _make_symbol(sym_id=7, symbol="ETH", currency="KRW")
        ua = _make_user_asset(ua_id=2, asset_symbol=sym)
        service = _make_service(user_assets=[ua], transactions=[])
        envelope = await service.export_json()

        export_ua = envelope.user_assets[0]
        assert export_ua.asset_symbol.symbol == "ETH"
        assert export_ua.asset_symbol.id == 7
        assert export_ua.asset_symbol.currency == "KRW"

    async def test_last_price_스냅샷_포함(self) -> None:
        sym = _make_symbol(last_price=Decimal("65000.000000"))
        ua = _make_user_asset(asset_symbol=sym)
        service = _make_service(user_assets=[ua], transactions=[])
        envelope = await service.export_json()

        assert envelope.user_assets[0].asset_symbol.last_price == Decimal("65000.000000")

    async def test_last_price_None_허용(self) -> None:
        sym = _make_symbol(last_price=None)
        ua = _make_user_asset(asset_symbol=sym)
        service = _make_service(user_assets=[ua], transactions=[])
        envelope = await service.export_json()

        assert envelope.user_assets[0].asset_symbol.last_price is None

    async def test_transaction_구조가_올바르다(self) -> None:
        sym = _make_symbol()
        ua = _make_user_asset(ua_id=1, asset_symbol=sym)
        tx = _make_transaction(
            tx_id=5,
            user_asset_id=1,
            tx_type=TransactionType.BUY,
            quantity="2.0",
            price="48000.0",
            memo="DCA",
            tag="monthly",
        )
        service = _make_service(user_assets=[ua], transactions=[tx])
        envelope = await service.export_json()

        export_tx = envelope.transactions[0]
        assert export_tx.id == 5
        assert export_tx.user_asset_id == 1
        assert export_tx.type == TransactionType.BUY
        assert export_tx.quantity == Decimal("2.0")
        assert export_tx.price == Decimal("48000.0")
        assert export_tx.memo == "DCA"
        assert export_tx.tag == "monthly"

    async def test_memo_tag_null_처리(self) -> None:
        sym = _make_symbol()
        ua = _make_user_asset(asset_symbol=sym, memo=None)
        tx = _make_transaction(memo=None, tag=None)
        service = _make_service(user_assets=[ua], transactions=[tx])
        envelope = await service.export_json()

        assert envelope.user_assets[0].memo is None
        assert envelope.transactions[0].memo is None
        assert envelope.transactions[0].tag is None

    async def test_exported_at이_UTC_timezone_aware(self) -> None:
        service = _make_service(user_assets=[], transactions=[])
        envelope = await service.export_json()

        assert envelope.exported_at.tzinfo is not None
        # UTC offset must be zero
        assert envelope.exported_at.utcoffset().total_seconds() == 0  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# export_csv_zip tests
# ---------------------------------------------------------------------------


class TestExportCsvZip:
    async def test_빈_사용자_두_csv_존재(self) -> None:
        service = _make_service(user_assets=[], transactions=[])
        zip_bytes = await service.export_csv_zip()

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
        assert "user_assets.csv" in names
        assert "transactions.csv" in names

    async def test_유효한_zip_파일(self) -> None:
        service = _make_service(user_assets=[], transactions=[])
        zip_bytes = await service.export_csv_zip()

        assert zipfile.is_zipfile(io.BytesIO(zip_bytes))

    async def test_user_assets_csv_헤더(self) -> None:
        service = _make_service(user_assets=[], transactions=[])
        zip_bytes = await service.export_csv_zip()

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            content = zf.read("user_assets.csv").decode("utf-8")

        reader = csv.DictReader(io.StringIO(content))
        assert reader.fieldnames == [
            "id",
            "asset_type",
            "symbol",
            "exchange",
            "name",
            "currency",
            "memo",
            "created_at",
        ]

    async def test_transactions_csv_헤더(self) -> None:
        service = _make_service(user_assets=[], transactions=[])
        zip_bytes = await service.export_csv_zip()

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            content = zf.read("transactions.csv").decode("utf-8")

        reader = csv.DictReader(io.StringIO(content))
        assert reader.fieldnames == [
            "id",
            "user_asset_id",
            "asset_symbol",
            "type",
            "quantity",
            "price",
            "traded_at",
            "memo",
            "tag",
            "created_at",
        ]

    async def test_user_assets_행_검증(self) -> None:
        sym = _make_symbol(symbol="BTC", exchange="upbit", name="Bitcoin", currency="KRW")
        ua = _make_user_asset(ua_id=1, asset_symbol=sym, memo="hodl")
        service = _make_service(user_assets=[ua], transactions=[])
        zip_bytes = await service.export_csv_zip()

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            content = zf.read("user_assets.csv").decode("utf-8")

        rows = list(csv.DictReader(io.StringIO(content)))
        assert len(rows) == 1
        assert rows[0]["symbol"] == "BTC"
        assert rows[0]["exchange"] == "upbit"
        assert rows[0]["currency"] == "KRW"
        assert rows[0]["memo"] == "hodl"

    async def test_transactions_행_검증(self) -> None:
        sym = _make_symbol(symbol="ETH")
        ua = _make_user_asset(ua_id=1, asset_symbol=sym)
        tx = _make_transaction(
            tx_id=3,
            user_asset_id=1,
            quantity="2.5",
            price="3000.0",
            memo="DCA",
            tag="monthly",
        )
        service = _make_service(user_assets=[ua], transactions=[tx])
        zip_bytes = await service.export_csv_zip()

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            content = zf.read("transactions.csv").decode("utf-8")

        rows = list(csv.DictReader(io.StringIO(content)))
        assert len(rows) == 1
        assert rows[0]["asset_symbol"] == "ETH"
        assert rows[0]["type"] == "buy"
        assert rows[0]["quantity"] == "2.5"
        assert rows[0]["memo"] == "DCA"
        assert rows[0]["tag"] == "monthly"

    async def test_memo_tag_null이_빈문자열로_직렬화(self) -> None:
        sym = _make_symbol()
        ua = _make_user_asset(asset_symbol=sym, memo=None)
        tx = _make_transaction(memo=None, tag=None)
        service = _make_service(user_assets=[ua], transactions=[tx])
        zip_bytes = await service.export_csv_zip()

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            ua_content = zf.read("user_assets.csv").decode("utf-8")
            tx_content = zf.read("transactions.csv").decode("utf-8")

        ua_rows = list(csv.DictReader(io.StringIO(ua_content)))
        tx_rows = list(csv.DictReader(io.StringIO(tx_content)))

        assert ua_rows[0]["memo"] == ""
        assert tx_rows[0]["memo"] == ""
        assert tx_rows[0]["tag"] == ""

    async def test_다건_자산_카운트(self) -> None:
        sym_a = _make_symbol(sym_id=1, symbol="BTC")
        sym_b = _make_symbol(sym_id=2, symbol="ETH")
        ua_a = _make_user_asset(ua_id=1, asset_symbol=sym_a)
        ua_b = _make_user_asset(ua_id=2, asset_symbol=sym_b)
        txs = [
            _make_transaction(tx_id=1, user_asset_id=1),
            _make_transaction(tx_id=2, user_asset_id=1, hours_ago=2),
            _make_transaction(tx_id=3, user_asset_id=2),
        ]
        service = _make_service(user_assets=[ua_a, ua_b], transactions=txs)
        zip_bytes = await service.export_csv_zip()

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            ua_content = zf.read("user_assets.csv").decode("utf-8")
            tx_content = zf.read("transactions.csv").decode("utf-8")

        ua_rows = list(csv.DictReader(io.StringIO(ua_content)))
        tx_rows = list(csv.DictReader(io.StringIO(tx_content)))

        assert len(ua_rows) == 2
        assert len(tx_rows) == 3
