"""wipe shinhan trades for fee re-import

Pre-fix the Shinhan parser dropped 수수료/거래세 on every BUY/SELL, so the
recorded ``transactions.fee`` was always 0 and `cash_flow` inflated the
Shinhan KRW balance by exactly the total broker deductions — about
₩651,874 over one user's 2-year history.

Trade ext_ids are deterministic on ``(date, side, name, qty, price)`` and
weren't changed by the fix, so re-importing the same PDFs would simply
dedup-skip every row, leaving ``fee = 0`` forever. Wipe Shinhan-sourced
``transactions`` so the next file-import populates the column from
``line3 정산금액 − gross``.

Dividends and cash_account_transactions are untouched: the parser already
records those correctly via 정산금액.

The companion symbol-resolution fix routes the Shinhan-reported name
through ``KrNameResolver`` for ANY non-6-digit symbol (was previously
gated on having Hangul, so ASCII tickers like ``NAVER`` slipped through
and ended up as ``AssetSymbol.symbol = 'NAVER'`` — the price refresher
couldn't reach Yahoo / pykrx with that). Re-import after this wipe
creates the canonical ``035420`` row and links new transactions to it.

Downgrade is a no-op — the wiped rows would need the user's PDFs to
restore. Re-import via the UI is the supported path.

Revision ID: 22b139eb4686
Revises: e2f8a91d4c67
Create Date: 2026-05-21
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "22b139eb4686"
down_revision = "e2f8a91d4c67"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM transactions
        WHERE external_source = 'shinhan_investment'
        """
    )


def downgrade() -> None:
    # Intentionally a no-op — the wiped rows would need the user's PDFs to
    # restore. Re-import via the UI is the supported path.
    pass
