"""wipe upbit PDF-imported data for fee re-import

Pre-fix the Upbit PDF parser dropped the broker fee on every BUY/SELL
(``transactions.fee = 0``) and recorded only the principal amount —
not ``amount + 출금수수료`` — on every KRW 출금. Together these inflated
the on-screen Upbit KRW balance by every taker fee plus every withdrawal
fee, about ₩62,661 on one user's history.

Trade ext_ids and cash ext_ids are deterministic on PDF-row data that
hasn't changed (qty/unit_price for trades; raw amount column for cash),
so a plain re-import would dedup-skip every row and leave ``fee = 0`` /
short cash drains forever. Wipe ONLY the PDF-sourced rows so the next
file-import populates fee from line2 (amount − settle) and writes the
true ``amount + fee`` drain for withdrawals.

API-synced rows (no ``upbit-pdf-`` prefix) are NOT wiped — those are
either reconciled to the live balance by ``sync_upbit`` or about to be
replaced wholesale by the next ``replace_trades`` call.

Downgrade is a no-op — the wiped rows would need the user's PDFs to
restore. Re-import via the UI is the supported path.

Revision ID: 85fce37dac95
Revises: 22b139eb4686
Create Date: 2026-05-21
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "85fce37dac95"
down_revision = "22b139eb4686"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM transactions
        WHERE external_source = 'upbit'
          AND external_id LIKE 'upbit-pdf-trade-%'
        """
    )
    op.execute(
        """
        DELETE FROM cash_account_transactions
        WHERE external_source = 'upbit'
          AND external_id LIKE 'upbit-pdf-cash-%'
        """
    )


def downgrade() -> None:
    # Intentionally a no-op — the wiped rows would need the user's PDFs to
    # restore. Re-import via the UI is the supported path.
    pass
