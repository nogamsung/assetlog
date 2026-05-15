"""CashFlowService — compute the user's available cash balance per currency.

Pieces the balance together from three sources that already live in the DB:

1. ``cash_account_transactions`` (DEPOSIT / INTEREST / TRANSFER_IN add cash;
   WITHDRAW / INTEREST_TAX / TRANSFER_OUT subtract).
2. ``transactions`` (BUY drains the broker cash account; SELL refills it,
   in the security's quote currency).
3. ``dividends`` (gross_amount adds cash, in the dividend currency).

Combined with portfolio holdings valuation this gives net worth.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.transaction_type import TransactionType
from app.models.asset_symbol import AssetSymbol
from app.models.cash_account_transaction import CashAccountTransaction, CashTxKind
from app.models.dividend import Dividend
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")

_POSITIVE_KINDS = frozenset(
    {CashTxKind.DEPOSIT, CashTxKind.INTEREST, CashTxKind.TRANSFER_IN}
)
_NEGATIVE_KINDS = frozenset(
    {CashTxKind.WITHDRAW, CashTxKind.INTEREST_TAX, CashTxKind.TRANSFER_OUT}
)


class CashFlowService:
    """Aggregates DB-level cash-flow signals into a per-currency balance."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def net_cash_by_currency(self) -> dict[str, Decimal]:
        """Return a {currency: balance} map summing every cash-flow signal."""
        balances: dict[str, Decimal] = {}

        # 1) cash_account_transactions
        cash_rows = (
            await self._session.execute(
                select(
                    CashAccountTransaction.kind,
                    CashAccountTransaction.amount,
                    CashAccountTransaction.currency,
                )
            )
        ).all()
        for kind, amount, currency in cash_rows:
            if kind in _POSITIVE_KINDS:
                balances[currency] = balances.get(currency, _ZERO) + amount
            elif kind in _NEGATIVE_KINDS:
                balances[currency] = balances.get(currency, _ZERO) - amount

        # 2) transactions (BUY drains, SELL refills) — in symbol's currency
        trade_rows = (
            await self._session.execute(
                select(
                    Transaction.type,
                    Transaction.quantity,
                    Transaction.price,
                    AssetSymbol.currency,
                )
                .join(UserAsset, UserAsset.id == Transaction.user_asset_id)
                .join(AssetSymbol, AssetSymbol.id == UserAsset.asset_symbol_id)
            )
        ).all()
        for tx_type, qty, price, currency in trade_rows:
            gross = qty * price
            if tx_type == TransactionType.BUY:
                balances[currency] = balances.get(currency, _ZERO) - gross
            elif tx_type == TransactionType.SELL:
                balances[currency] = balances.get(currency, _ZERO) + gross

        # 3) dividends (always positive)
        div_rows = (
            await self._session.execute(
                select(Dividend.amount, Dividend.currency)
            )
        ).all()
        for amount, currency in div_rows:
            balances[currency] = balances.get(currency, _ZERO) + amount

        return balances

    async def net_cash_by_source_and_currency(self) -> dict[str, dict[str, Decimal]]:
        """Return ``{source: {currency: balance}}`` — per-broker cash balance.

        Source identifiers (``toss_securities``, ``shinhan``, ``upbit``, …)
        come from ``cash_account_transactions.external_source`` for cash-flow
        events and from ``transactions.external_source`` / ``dividends.external_source``
        for trade-driven balance changes. Rows with no source (manually added)
        are grouped under ``"manual"``.
        """
        result: dict[str, dict[str, Decimal]] = {}

        def _bump(src: str | None, ccy: str, delta: Decimal) -> None:
            s = src or "manual"
            by_cur = result.setdefault(s, {})
            by_cur[ccy] = by_cur.get(ccy, _ZERO) + delta

        cash_rows = (
            await self._session.execute(
                select(
                    CashAccountTransaction.kind,
                    CashAccountTransaction.amount,
                    CashAccountTransaction.currency,
                    CashAccountTransaction.external_source,
                )
            )
        ).all()
        for kind, amount, currency, source in cash_rows:
            if kind in _POSITIVE_KINDS:
                _bump(source, currency, amount)
            elif kind in _NEGATIVE_KINDS:
                _bump(source, currency, -amount)

        trade_rows = (
            await self._session.execute(
                select(
                    Transaction.type,
                    Transaction.quantity,
                    Transaction.price,
                    AssetSymbol.currency,
                    Transaction.external_source,
                )
                .join(UserAsset, UserAsset.id == Transaction.user_asset_id)
                .join(AssetSymbol, AssetSymbol.id == UserAsset.asset_symbol_id)
            )
        ).all()
        for tx_type, qty, price, currency, source in trade_rows:
            gross = qty * price
            if tx_type == TransactionType.BUY:
                _bump(source, currency, -gross)
            elif tx_type == TransactionType.SELL:
                _bump(source, currency, gross)

        div_rows = (
            await self._session.execute(
                select(Dividend.amount, Dividend.currency, Dividend.external_source)
            )
        ).all()
        for amount, currency, source in div_rows:
            _bump(source, currency, amount)

        return result
