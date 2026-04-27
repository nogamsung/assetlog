"""create_cash_accounts_table

Add the ``cash_accounts`` table for single-owner cash balance tracking.

Columns:
- id        INT PK AUTO_INCREMENT
- label     VARCHAR(100) NOT NULL
- currency  VARCHAR(4) NOT NULL  (indexed)
- balance   NUMERIC(20,4) NOT NULL  CHECK(balance >= 0)
- created_at / updated_at  DATETIME(tz) NOT NULL

Revision ID: 6c7b2345d068
Revises: c8a4f1e927b3
Create Date: 2026-04-27 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6c7b2345d068"
down_revision: str | None = "c8a4f1e927b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cash_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=4), nullable=False),
        sa.Column(
            "balance",
            sa.Numeric(precision=20, scale=4),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("balance >= 0", name="ck_cash_accounts_balance_non_negative"),
    )
    op.create_index("ix_cash_accounts_currency", "cash_accounts", ["currency"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cash_accounts_currency", table_name="cash_accounts")
    op.drop_table("cash_accounts")
