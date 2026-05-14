"""ExchangeSyncService — convert ExternalTrade rows into Transactions.

The service is *adapter-agnostic*: it takes a pre-fetched list of
``ExternalTrade`` (the adapter handles auth + paging) and writes them to the
DB, deduping by ``(external_source, external_id)`` and auto-creating any
missing ``UserAsset`` / ``AssetSymbol`` rows for the discovered tickers.

For file-based imports (Toss Securities, etc.), ``import_records`` is the
unified entry point — it delegates to ``import_trades``, ``import_dividends``,
and ``import_cash_txs`` internally.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.parsers.base import (
    ParsedCashTx,
    ParsedDividend,
    ParsedTrade,
    ParseResult,
)
from app.domain.asset_type import AssetType
from app.domain.dividend import DividendSource
from app.domain.exchange_sync import ExchangeSource, ExternalTrade, SyncResult
from app.models.asset_symbol import AssetSymbol
from app.models.cash_account_transaction import CashAccountTransaction, CashTxKind
from app.models.dividend import Dividend
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset

logger = logging.getLogger(__name__)

_KST = ZoneInfo("Asia/Seoul")


_UPBIT_EXCHANGE_LABEL = "UPBIT"


@dataclass(frozen=True)
class ImportResult:
    """Aggregate counters returned by a file import run."""

    inserted_trades: int
    inserted_dividends: int
    inserted_cash_txs: int
    skipped_duplicate: int
    skipped_unsupported: int
    skipped_breakdown: dict[str, int]


def _asset_type_for(source: ExchangeSource) -> AssetType:
    """Map an exchange source to the asset_type its symbols belong to."""
    if source in {ExchangeSource.UPBIT, ExchangeSource.BITHUMB, ExchangeSource.BINANCE}:
        return AssetType.CRYPTO
    if source in {ExchangeSource.SHINHAN, ExchangeSource.TOSS_SECURITIES}:
        return AssetType.KR_STOCK
    return AssetType.US_STOCK


def _exchange_label_for(source: ExchangeSource) -> str:
    """Return the AssetSymbol.exchange string for a given ExchangeSource."""
    mapping = {
        ExchangeSource.UPBIT: _UPBIT_EXCHANGE_LABEL,
        ExchangeSource.BITHUMB: "BITHUMB",
        ExchangeSource.BINANCE: "BINANCE",
        ExchangeSource.SHINHAN: "KRX",
        ExchangeSource.KIS: "KRX",
        ExchangeSource.TOSS_SECURITIES: "",  # asset_type per-record for Toss
    }
    return mapping.get(source, "NYSE")


class ExchangeSyncService:
    """Persist external trades as Transactions, auto-creating symbol/asset rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        # Lazy-imported to avoid a hard dependency for callers that don't need resolution
        from app.services.isin_resolver import IsinResolver  # noqa: PLC0415
        from app.services.kr_name_resolver import KrNameResolver  # noqa: PLC0415

        self._isin_resolver = IsinResolver(session)
        self._kr_name_resolver = KrNameResolver(session)

    # ------------------------------------------------------------------
    # Public API — ExternalTrade (Upbit / brokerage OpenAPI)
    # ------------------------------------------------------------------

    async def import_trades(
        self,
        source: ExchangeSource,
        trades: Iterable[ExternalTrade],
    ) -> SyncResult:
        """Insert *trades* as Transactions; dedupe on (source, external_id)."""
        trade_list = list(trades)
        if not trade_list:
            return SyncResult(0, 0, 0, 0)

        existing_ids = await self._existing_tx_external_ids(
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

    async def replace_trades(
        self,
        source: ExchangeSource,
        trades: Iterable[ExternalTrade],
    ) -> SyncResult:
        """Delete all transactions for ``source`` then insert ``trades`` fresh.

        Used by Upbit sync so that re-running the sync always produces holdings
        that match the exchange's live balance, even when:
          - the upstream history has gaps (airdrops, external deposits, ...)
          - the user previously synced an out-of-date snapshot

        User-entered transactions (``external_source IS NULL``) are NOT touched.
        """
        from sqlalchemy import delete  # noqa: PLC0415

        trade_list = list(trades)

        await self._session.execute(
            delete(Transaction).where(Transaction.external_source == source.value)
        )
        await self._session.flush()

        if not trade_list:
            return SyncResult(0, 0, 0, 0)

        symbol_cache: dict[str, AssetSymbol] = {}
        asset_cache: dict[int, UserAsset] = {}
        inserted = 0
        for trade in trade_list:
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
            inserted += 1
        await self._session.flush()
        logger.info(
            "exchange_sync replaced",
            extra={
                "event": "exchange_sync_replaced",
                "source": source.value,
                "inserted": inserted,
                "fetched": len(trade_list),
            },
        )
        return SyncResult(
            fetched=len(trade_list),
            inserted=inserted,
            skipped_duplicate=0,
            skipped_no_symbol=0,
        )

    # ------------------------------------------------------------------
    # Public API — file-based import (Toss Securities, etc.)
    # ------------------------------------------------------------------

    async def import_records(
        self,
        source: ExchangeSource,
        parse_result: ParseResult,
        *,
        dry_run: bool = False,
    ) -> ImportResult:
        """Import a ParseResult into the DB; skips duplicates.

        Args:
            source: The exchange source identifier.
            parse_result: Output from a parser (toss_securities, etc.).
            dry_run: If True, validate and count without writing to DB.

        Returns:
            ImportResult with per-category insertion counters.
        """
        trades = [r for r in parse_result.records if isinstance(r, ParsedTrade)]
        dividends = [r for r in parse_result.records if isinstance(r, ParsedDividend)]
        cash_txs = [r for r in parse_result.records if isinstance(r, ParsedCashTx)]

        breakdown: dict[str, int] = {}
        for skip in parse_result.skipped:
            breakdown[skip.raw_kind] = breakdown.get(skip.raw_kind, 0) + 1

        if dry_run:
            return ImportResult(
                inserted_trades=len(trades),
                inserted_dividends=len(dividends),
                inserted_cash_txs=len(cash_txs),
                skipped_duplicate=0,
                skipped_unsupported=len(parse_result.skipped),
                skipped_breakdown=breakdown,
            )

        ins_trades = await self._import_parsed_trades(source, trades)
        ins_divs = await self._import_parsed_dividends(source, dividends)
        ins_cash = await self._import_parsed_cash_txs(source, cash_txs)

        return ImportResult(
            inserted_trades=ins_trades,
            inserted_dividends=ins_divs,
            inserted_cash_txs=ins_cash,
            skipped_duplicate=0,
            skipped_unsupported=len(parse_result.skipped),
            skipped_breakdown=breakdown,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _import_parsed_trades(
        self,
        source: ExchangeSource,
        trades: list[ParsedTrade],
    ) -> int:
        if not trades:
            return 0

        existing_ids = await self._existing_tx_external_ids(
            source.value, [t.external_id for t in trades]
        )

        symbol_cache: dict[tuple[str, AssetType, str], AssetSymbol] = {}
        asset_cache: dict[int, UserAsset] = {}
        inserted = 0
        skipped_dup = 0

        for trade in trades:
            if trade.external_id in existing_ids:
                skipped_dup += 1
                continue

            cache_key = (trade.symbol, trade.asset_type, trade.exchange)
            symbol = symbol_cache.get(cache_key)
            if symbol is None:
                symbol = await self._get_or_create_symbol_by_attrs(
                    trade.symbol,
                    trade.asset_type,
                    trade.exchange,
                    trade.currency,
                    name=trade.name or None,
                )
                symbol_cache[cache_key] = symbol

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
                "file_import trades inserted",
                extra={
                    "event": "file_import_trades",
                    "source": source.value,
                    "inserted": inserted,
                    "skipped_dup": skipped_dup,
                },
            )
        return inserted

    async def _import_parsed_dividends(
        self,
        source: ExchangeSource,
        dividends: list[ParsedDividend],
    ) -> int:
        if not dividends:
            return 0

        existing_ids = await self._existing_dividend_external_ids(
            source.value, [d.external_id for d in dividends]
        )

        symbol_cache: dict[tuple[str, AssetType, str], AssetSymbol] = {}
        inserted = 0
        skipped_dup = 0

        for div in dividends:
            if div.external_id in existing_ids:
                skipped_dup += 1
                continue

            cache_key = (div.symbol, div.asset_type, div.exchange)
            symbol = symbol_cache.get(cache_key)
            if symbol is None:
                symbol = await self._get_or_create_symbol_by_attrs(
                    div.symbol,
                    div.asset_type,
                    div.exchange,
                    div.currency,
                    name=div.name or None,
                )
                symbol_cache[cache_key] = symbol

            self._session.add(
                Dividend(
                    asset_symbol_id=symbol.id,
                    ex_date=div.traded_at.astimezone(_KST).date(),
                    amount=div.gross_amount,
                    currency=div.currency,
                    source=DividendSource.TOSS_SECURITIES,
                    external_source=source.value,
                    external_id=div.external_id,
                )
            )
            existing_ids.add(div.external_id)
            inserted += 1

        if inserted > 0:
            await self._session.flush()
            logger.info(
                "file_import dividends inserted",
                extra={
                    "event": "file_import_dividends",
                    "source": source.value,
                    "inserted": inserted,
                    "skipped_dup": skipped_dup,
                },
            )
        return inserted

    async def _import_parsed_cash_txs(
        self,
        source: ExchangeSource,
        cash_txs: list[ParsedCashTx],
    ) -> int:
        if not cash_txs:
            return 0

        existing_ids = await self._existing_cash_tx_external_ids(
            source.value, [c.external_id for c in cash_txs]
        )

        inserted = 0
        skipped_dup = 0

        for ctx in cash_txs:
            if ctx.external_id in existing_ids:
                skipped_dup += 1
                continue

            kind_map = {
                "interest": CashTxKind.INTEREST,
                "interest_tax": CashTxKind.INTEREST_TAX,
                "deposit": CashTxKind.DEPOSIT,
                "withdraw": CashTxKind.WITHDRAW,
            }
            kind = kind_map.get(ctx.kind.value, CashTxKind.INTEREST)

            self._session.add(
                CashAccountTransaction(
                    cash_account_id=None,
                    kind=kind,
                    amount=ctx.amount,
                    currency=ctx.currency,
                    traded_at=ctx.traded_at,
                    external_source=source.value,
                    external_id=ctx.external_id,
                )
            )
            existing_ids.add(ctx.external_id)
            inserted += 1

        if inserted > 0:
            await self._session.flush()
            logger.info(
                "file_import cash_txs inserted",
                extra={
                    "event": "file_import_cash_txs",
                    "source": source.value,
                    "inserted": inserted,
                    "skipped_dup": skipped_dup,
                },
            )
        return inserted

    # ------------------------------------------------------------------
    # Private: existing-IDs lookups for deduplication
    # ------------------------------------------------------------------

    async def _existing_tx_external_ids(
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

    async def _existing_dividend_external_ids(
        self,
        source: str,
        external_ids: list[str],
    ) -> set[str]:
        if not external_ids:
            return set()
        stmt = select(Dividend.external_id).where(
            Dividend.external_source == source,
            Dividend.external_id.in_(external_ids),
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return {row for row in rows if row is not None}

    async def _existing_cash_tx_external_ids(
        self,
        source: str,
        external_ids: list[str],
    ) -> set[str]:
        if not external_ids:
            return set()
        stmt = select(CashAccountTransaction.external_id).where(
            CashAccountTransaction.external_source == source,
            CashAccountTransaction.external_id.in_(external_ids),
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return {row for row in rows if row is not None}

    # ------------------------------------------------------------------
    # Private: symbol / asset helpers
    # ------------------------------------------------------------------

    async def _get_or_create_symbol(
        self,
        source: ExchangeSource,
        trade: ExternalTrade,
    ) -> AssetSymbol:
        asset_type = _asset_type_for(source)
        exchange = _exchange_label_for(source)
        return await self._get_or_create_symbol_by_attrs(
            trade.symbol, asset_type, exchange, trade.quote_currency
        )

    async def _get_or_create_symbol_by_attrs(
        self,
        symbol: str,
        asset_type: AssetType,
        exchange: str,
        currency: str,
        name: str | None = None,
    ) -> AssetSymbol:
        # If the symbol still looks like a raw ISIN (parser couldn't map it),
        # try the resolver chain (static map → DB cache → OpenFIGI) before
        # creating an AssetSymbol row that would otherwise carry the ISIN.
        from app.services.isin_resolver import looks_like_isin  # noqa: PLC0415
        from app.services.kr_name_resolver import looks_like_kr_name  # noqa: PLC0415

        if asset_type == AssetType.US_STOCK and looks_like_isin(symbol):
            resolved = await self._isin_resolver.resolve(symbol)
            if resolved:
                symbol = resolved
        elif asset_type == AssetType.KR_STOCK and looks_like_kr_name(symbol):
            # Shinhan rows carry a Korean security name as symbol — translate
            # to the canonical KRX 6-digit code via Naver autocomplete + cache.
            resolved_kr = await self._kr_name_resolver.resolve(symbol)
            if resolved_kr:
                symbol = resolved_kr

        # Crypto trade payloads (Upbit etc.) only carry the ticker, so we look
        # up a human display name so AssetSymbol.name doesn't fall back to the
        # ticker itself.
        if asset_type == AssetType.CRYPTO and not name:
            from app.adapters.crypto_name_map import lookup_crypto_name  # noqa: PLC0415

            base = symbol.split("/", maxsplit=1)[0] if "/" in symbol else symbol
            mapped = lookup_crypto_name(base)
            if mapped:
                name = mapped

        stmt = select(AssetSymbol).where(
            AssetSymbol.asset_type == asset_type,
            AssetSymbol.symbol == symbol,
            AssetSymbol.exchange == exchange,
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            # Upgrade fallback name (name == symbol) once we learn the real one
            # from a parser. Don't overwrite a non-fallback display name.
            if name and existing.name == existing.symbol and name != existing.symbol:
                existing.name = name
            return existing

        new_symbol = AssetSymbol(
            asset_type=asset_type,
            symbol=symbol,
            exchange=exchange,
            name=name or symbol,
            currency=currency,
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
