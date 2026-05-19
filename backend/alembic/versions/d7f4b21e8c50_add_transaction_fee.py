"""add transaction fee

Adds a broker-commission column on Transaction so cash_flow can subtract
the fee from the trade's quote currency. Without it, parser-imported
trades inflated cash by exactly the sum of fees (every BUY drained less
cash than reality, every SELL refilled more) — for Toss that's roughly
$240 / ₩1,700 on a single user's 2-year history.

The column is non-null with a 0 default so existing rows keep working
as "fee unknown / treat as zero" until the user re-imports.

Revision ID: d7f4b21e8c50
Revises: c5e8a4d2f193
Create Date: 2026-05-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d7f4b21e8c50"
down_revision = "c5e8a4d2f193"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column(
            "fee",
            sa.Numeric(20, 6),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("transactions", "fee")
