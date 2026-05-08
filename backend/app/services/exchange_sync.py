"""ExchangeSyncService — convert ExternalTrade rows into Transactions.

The service is *adapter-agnostic*: it takes a pre-fetched list of
``ExternalTrade`` (the adapter handles auth + paging) and writes them to the
DB, deduping by ``(external_source, external_id)`` and auto-creating any
missing ``UserAsset`` / ``AssetSymbol`` rows for the discovered tickers.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.asset_type import AssetType
from app.domain.exchange_sync import ExchangeSource, ExternalTrade, SyncResult
from app.models.asset_symbol import AssetSymbol
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset

logger = logging.getLogger(__name__)


_UPBIT_EXCHANGE_LABEL = "UPBIT"


def _asset_type_for(source: ExchangeSource) -> AssetType:
    """Map an exchange source to the asset_type its symbols belong to."""
    if source in {ExchangeSource.UPBIT, ExchangeSource.BITHUMB, ExchangeSource.BINANCE}:
        return AssetType.CRYPTO
    if source == ExchangeSource.SHINHAN:
        return AssetType.KR_STOCK
    return AssetType.US_STOCK


def _exchange_label_for(source: ExchangeSource) -> str:
    """Return the AssetSymbol.exchange string for a given ExchangeSource."""
    return {
        ExchangeSource.UPBIT: _UPBIT_EXCHANGE_LABEL,
        ExchangeSource.BITHUMB: "BITHUMB",
        ExchangeSource.BINANCE: "BINANCE",
        ExchangeSource.SHINHAN: "KRX",
        ExchangeSource.KIS: "KRX",
    }[source]


class ExchangeSyncService:
    """Persist external trades as Transactions, auto-creating symbol/asset rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def import_trades(
        self,
        source: ExchangeSource,
        trades: Iterable[ExternalTrade],
    ) -> SyncResult:
        """Insert *trades* as Transactions; dedupe on (source, external_id)."""
        trade_list = list(trades)
        if not trade_list:
            return SyncResult(0, 0, 0, 0)

        existing_ids = await self._existing_external_ids(
            source.value,
            [t.external_id for t in trade_list],
        )

        symbol_cache: dict[str, AssetSymbol] = {}
        asset_cache: dict[int, UserAsset] = {}
        inserted = 0
        skipped_dup = 0

        for trade in trade_list:
            if trade.external_id in existing_ids:
                skipped_dup += 1
                continue

            symbol = symbol_cache.get(trade.symbol)
            if symbol is None:
                symbol = await self._get_or_create_symbol(source, trade)
                symbol_cache[trade.symbol] = symbol

            asset = asset_cache.get(symbol.id)
            if asset is None:
                asset = await self._get_or_create_user_asset(symbol.id)
                asset_cache[symbol.id] = asset

            self._session.add(
                Transaction(
                    user_asset_id=asset.id,
                    type=trade.side,
                    quantity=trade.quantity,
                    price=trade.price,
                    traded_at=trade.traded_at,
                    external_source=source.value,
                    external_id=trade.external_id,
                )
            )
            existing_ids.add(trade.external_id)
            inserted += 1

        if inserted > 0:
            await self._session.flush()
            logger.info(
                "exchange_sync inserted",
                extra={
                    "event": "exchange_sync_done",
                    "source": source.value,
                    "inserted": inserted,
                    "fetched": len(trade_list),
                },
            )
        return SyncResult(
            fetched=len(trade_list),
            inserted=inserted,
            skipped_duplicate=skipped_dup,
            skipped_no_symbol=0,
        )

    async def _existing_external_ids(
        self,
        source: str,
        external_ids: list[str],
    ) -> set[str]:
        if not external_ids:
            return set()
        stmt = select(Transaction.external_id).where(
            Transaction.external_source == source,
            Transaction.external_id.in_(external_ids),
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return {row for row in rows if row is not None}

    async def _get_or_create_symbol(
        self,
        source: ExchangeSource,
        trade: ExternalTrade,
    ) -> AssetSymbol:
        asset_type = _asset_type_for(source)
        exchange = _exchange_label_for(source)
        stmt = select(AssetSymbol).where(
            AssetSymbol.asset_type == asset_type,
            AssetSymbol.symbol == trade.symbol,
            AssetSymbol.exchange == exchange,
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return existing

        new_symbol = AssetSymbol(
            asset_type=asset_type,
            symbol=trade.symbol,
            exchange=exchange,
            name=trade.symbol,
            currency=trade.quote_currency,
        )
        self._session.add(new_symbol)
        await self._session.flush()
        return new_symbol

    async def _get_or_create_user_asset(self, asset_symbol_id: int) -> UserAsset:
        stmt = select(UserAsset).where(UserAsset.asset_symbol_id == asset_symbol_id)
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return existing

        new_asset = UserAsset(asset_symbol_id=asset_symbol_id)
        self._session.add(new_asset)
        await self._session.flush()
        return new_asset
