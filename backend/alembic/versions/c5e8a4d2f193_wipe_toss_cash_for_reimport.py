"""wipe toss cash for reimport

Pre-#182 the Toss parser recorded the FX rate (~1,500) instead of the
principal (~10⁶–10⁷) as the moved KRW amount on every 환전원화* row, and
also miscounted any 이체*/이벤트/배당세출금 row that happened to share the
same numeric layout. Because external_id is hashed from
(date, kind, amount, currency), the corrected parser produces a *different*
external_id for the same physical row — so re-import without a wipe
double-counts the cash side.

This migration deletes every CashAccountTransaction with
``external_source = 'toss_investment'`` so the user can re-upload the
Toss PDFs through the UI and have the cash ledger rebuilt cleanly with
the post-#182 amounts. Trades and dividends are untouched (their
external_ids didn't change between parser versions, so the dedup logic
already protects them on re-import).

Downgrade is a no-op — there's no way to faithfully restore the deleted
rows. The PDFs are the source of truth.

Revision ID: c5e8a4d2f193
Revises: a1c8b3e64d92
Create Date: 2026-05-19
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "c5e8a4d2f193"
down_revision = "a1c8b3e64d92"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM cash_account_transactions
        WHERE external_source = 'toss_investment'
        """
    )


def downgrade() -> None:
    # Intentionally a no-op — the wiped rows would need the user's PDFs to
    # restore. Re-import via the UI is the supported path.
    pass
