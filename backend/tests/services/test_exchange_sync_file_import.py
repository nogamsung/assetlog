"""Tests for ExchangeSyncService file-import methods (dividends, cash_txs, import_records)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.parsers.base import (
    ParsedCashTx,
    ParsedCashTxKind,
    ParsedDividend,
    ParsedTrade,
    ParseResult,
)
from app.domain.asset_type import AssetType
from app.domain.exchange_sync import ExchangeSource
from app.domain.transaction_type import TransactionType
from app.models.cash_account_transaction import CashAccountTransaction
from app.models.dividend import Dividend
from app.models.transaction import Transaction
from app.services.exchange_sync import ExchangeSyncService


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, 15, 0, 0, tzinfo=UTC)


def _make_trade(ext_id: str = "trade001") -> ParsedTrade:
    return ParsedTrade(
        external_id=ext_id,
        symbol="US0079031078",
        asset_type=AssetType.US_STOCK,
        exchange="NYSE",
        side=TransactionType.BUY,
        quantity=Decimal("5"),
        price=Decimal("138.82"),
        currency="USD",
        traded_at=_utc(2025, 7, 11),
    )


def _make_dividend(ext_id: str = "div001") -> ParsedDividend:
    return ParsedDividend(
        external_id=ext_id,
        symbol="US0079031078",
        asset_type=AssetType.US_STOCK,
        exchange="NYSE",
        gross_amount=Decimal("3.58"),
        currency="USD",
        traded_at=_utc(2025, 7, 1),
    )


def _make_cash_tx(ext_id: str = "cash001") -> ParsedCashTx:
    return ParsedCashTx(
        external_id=ext_id,
        kind=ParsedCashTxKind.INTEREST,
        amount=Decimal("0.63"),
        currency="USD",
        traded_at=_utc(2026, 1, 30),
    )


class TestImportParsedTrades:
    async def test_insert_new_trade(self, db_session: AsyncSession) -> None:
        svc = ExchangeSyncService(db_session)
        parse_result = ParseResult(records=[_make_trade()])
        result = await svc.import_records(ExchangeSource.TOSS_SECURITIES, parse_result)
        assert result.inserted_trades == 1
        assert result.inserted_dividends == 0
        assert result.inserted_cash_txs == 0

    async def test_dedupe_trade(self, db_session: AsyncSession) -> None:
        svc = ExchangeSyncService(db_session)
        trade = _make_trade("dup_trade_001")
        pr = ParseResult(records=[trade])
        await svc.import_records(ExchangeSource.TOSS_SECURITIES, pr)
        # Second import with same ID
        result = await svc.import_records(ExchangeSource.TOSS_SECURITIES, pr)
        assert result.inserted_trades == 0


class TestImportParsedDividends:
    async def test_insert_new_dividend(self, db_session: AsyncSession) -> None:
        svc = ExchangeSyncService(db_session)
        pr = ParseResult(records=[_make_dividend("divtest001")])
        result = await svc.import_records(ExchangeSource.TOSS_SECURITIES, pr)
        assert result.inserted_dividends == 1

    async def test_dedupe_dividend(self, db_session: AsyncSession) -> None:
        svc = ExchangeSyncService(db_session)
        div = _make_dividend("divdup001")
        pr = ParseResult(records=[div])
        await svc.import_records(ExchangeSource.TOSS_SECURITIES, pr)
        result = await svc.import_records(ExchangeSource.TOSS_SECURITIES, pr)
        assert result.inserted_dividends == 0

    async def test_dedupe_dividend_by_symbol_and_ex_date(
        self, db_session: AsyncSession
    ) -> None:
        """Same (symbol, ex_date) from a *different* external_id must not crash.

        The dividends table has UNIQUE(asset_symbol_id, ex_date) in addition to
        UNIQUE(external_source, external_id), so two brokers reporting the same
        dividend with different external_ids would otherwise hit a duplicate
        key and abort the whole import session with PendingRollbackError.
        """
        svc = ExchangeSyncService(db_session)
        # First import: external_id="src_a"
        div_a = _make_dividend("src_a")
        await svc.import_records(
            ExchangeSource.TOSS_SECURITIES, ParseResult(records=[div_a])
        )
        # Second import: same symbol + same ex_date, different external_id
        div_b = _make_dividend("src_b")
        result = await svc.import_records(
            ExchangeSource.TOSS_SECURITIES, ParseResult(records=[div_b])
        )
        # Must be silently skipped, not crash
        assert result.inserted_dividends == 0


class TestImportParsedCashTxs:
    async def test_insert_new_cash_tx(self, db_session: AsyncSession) -> None:
        svc = ExchangeSyncService(db_session)
        pr = ParseResult(records=[_make_cash_tx("cashtest001")])
        result = await svc.import_records(ExchangeSource.TOSS_SECURITIES, pr)
        assert result.inserted_cash_txs == 1

    async def test_dedupe_cash_tx(self, db_session: AsyncSession) -> None:
        svc = ExchangeSyncService(db_session)
        ctx = _make_cash_tx("cashdup001")
        pr = ParseResult(records=[ctx])
        await svc.import_records(ExchangeSource.TOSS_SECURITIES, pr)
        result = await svc.import_records(ExchangeSource.TOSS_SECURITIES, pr)
        assert result.inserted_cash_txs == 0


class TestDryRun:
    async def test_dry_run_no_db_write(self, db_session: AsyncSession) -> None:
        from sqlalchemy import select

        svc = ExchangeSyncService(db_session)
        pr = ParseResult(
            records=[
                _make_trade("dry_trade_001"),
                _make_dividend("dry_div_001"),
                _make_cash_tx("dry_cash_001"),
            ]
        )
        result = await svc.import_records(ExchangeSource.TOSS_SECURITIES, pr, dry_run=True)

        # dry_run returns expected counts
        assert result.inserted_trades == 1
        assert result.inserted_dividends == 1
        assert result.inserted_cash_txs == 1

        # But nothing was written
        tx_count = (
            await db_session.execute(
                select(Transaction).where(Transaction.external_id == "dry_trade_001")
            )
        ).scalar_one_or_none()
        assert tx_count is None

        div_count = (
            await db_session.execute(select(Dividend).where(Dividend.external_id == "dry_div_001"))
        ).scalar_one_or_none()
        assert div_count is None

        cash_count = (
            await db_session.execute(
                select(CashAccountTransaction).where(
                    CashAccountTransaction.external_id == "dry_cash_001"
                )
            )
        ).scalar_one_or_none()
        assert cash_count is None
