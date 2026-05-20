"""add withholding tax on dividend + cash_account_transaction

Toss reports the gross dividend / interest in the 거래대금 column but the
balance shown in the 잔액 column already reflects the source withholding
(15.4% for KRW, ~15% for US dividends). Without a separate withholding
column the parser had to choose between recording gross (over-counts
cash) or net (loses the gross figure for tax reporting). Capture both.

Two columns, both ``NUMERIC(20, 8) NOT NULL DEFAULT 0``:

- ``dividends.withholding_tax``
- ``cash_account_transactions.withholding_tax`` (only meaningful when
  kind = 'interest')

Existing rows keep ``withholding_tax = 0`` — under-reports withholding
rather than over-reports, so net-worth stays conservative until the
user re-imports the Toss PDFs.

Revision ID: e2f8a91d4c67
Revises: d7f4b21e8c50
Create Date: 2026-05-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e2f8a91d4c67"
down_revision = "d7f4b21e8c50"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dividends",
        sa.Column(
            "withholding_tax",
            sa.Numeric(20, 8),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "cash_account_transactions",
        sa.Column(
            "withholding_tax",
            sa.Numeric(20, 8),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("cash_account_transactions", "withholding_tax")
    op.drop_column("dividends", "withholding_tax")
