"""Diagnostic — print every KODEX 레버리지 transaction the way the cost-basis walker sees it.

Run with the same DB the API uses:

    uv run python backend/scripts/diagnose_kodex_leverage.py

Prints (1) every row in the DB for symbol 122630, (2) the ORDER BY produced
by the post-#184 query, and (3) what list_holdings_with_aggregates reports
as total_qty / total_cost. If total_qty is non-zero you'll see exactly why.
"""

from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import case, select

from app.db.session import AsyncSessionLocal
from app.domain.transaction_type import TransactionType
from app.models.asset_symbol import AssetSymbol
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset
from app.repositories.portfolio import PortfolioRepository

KODEX_LEV_SYMBOL = "122630"


async def main() -> None:
    async with AsyncSessionLocal() as session:
        sym = (
            await session.execute(
                select(AssetSymbol).where(AssetSymbol.symbol == KODEX_LEV_SYMBOL)
            )
        ).scalar_one_or_none()
        if sym is None:
            print(f"AssetSymbol with symbol={KODEX_LEV_SYMBOL} not found.")
            return

        ua = (
            await session.execute(
                select(UserAsset).where(UserAsset.asset_symbol_id == sym.id)
            )
        ).scalar_one_or_none()
        if ua is None:
            print(f"UserAsset for symbol {KODEX_LEV_SYMBOL} not found.")
            return

        print(f"AssetSymbol id={sym.id} name={sym.name!r}")
        print(f"UserAsset id={ua.id}")
        print()

        # Raw rows ordered by id (DB insertion order)
        rows_by_id = (
            await session.execute(
                select(Transaction)
                .where(Transaction.user_asset_id == ua.id)
                .order_by(Transaction.id.asc())
            )
        ).scalars().all()

        print("=== Raw rows (by id ASC) ===")
        for r in rows_by_id:
            print(
                f"id={r.id:>6}  {r.traded_at}  {r.type.value:<4}  "
                f"qty={r.quantity}  price={r.price}  external_id={r.external_id}"
            )
        print()

        # Rows as the cost-basis walker now sees them
        ordered_stmt = (
            select(Transaction)
            .where(Transaction.user_asset_id == ua.id)
            .order_by(
                Transaction.traded_at.asc(),
                case((Transaction.type == TransactionType.BUY, 0), else_=1),
                Transaction.id.asc(),
            )
        )
        rows_walked = (await session.execute(ordered_stmt)).scalars().all()
        print("=== Rows as the cost-basis walker now sorts them ===")
        for r in rows_walked:
            print(
                f"id={r.id:>6}  {r.traded_at}  {r.type.value:<4}  "
                f"qty={r.quantity}  price={r.price}"
            )
        print()

        # Replay the walker
        running_qty = Decimal("0")
        running_cost = Decimal("0")
        for r in rows_walked:
            if r.type == TransactionType.BUY:
                running_cost += r.quantity * r.price
                running_qty += r.quantity
            else:
                if running_qty > Decimal("0"):
                    avg = running_cost / running_qty
                    sold = r.quantity if r.quantity <= running_qty else running_qty
                    running_cost -= sold * avg
                    running_qty -= sold

        print("=== Replayed walk ===")
        print(f"running_qty  = {running_qty}")
        print(f"running_cost = {running_cost}")
        print()

        # Repo result
        repo = PortfolioRepository(session)
        agg = await repo.list_holdings_with_aggregates()
        row = next((r for r in agg if r.user_asset_id == ua.id), None)
        print("=== PortfolioRepository.list_holdings_with_aggregates ===")
        if row is None:
            print("(no row returned)")
        else:
            print(f"total_qty    = {row.total_qty}")
            print(f"total_cost   = {row.total_cost}")
            print(f"realized_pnl = {row.realized_pnl}")


if __name__ == "__main__":
    asyncio.run(main())
