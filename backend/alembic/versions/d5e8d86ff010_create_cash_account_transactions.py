"""create cash_account_transactions table

Revision ID: d5e8d86ff010
Revises: b4d3bc99048f
Create Date: 2026-05-12 00:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5e8d86ff010"
down_revision: str | tuple[str, ...] | None = "b4d3bc99048f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cash_account_transactions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("cash_account_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "deposit",
                "withdraw",
                "interest",
                "interest_tax",
                "transfer_in",
                "transfer_out",
                name="cashtxkind",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("traded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("external_source", sa.String(32), nullable=True),
        sa.Column("external_id", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["cash_account_id"],
            ["cash_accounts.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_source", "external_id", name="uq_cash_tx_external"),
    )
    op.create_index(
        "ix_cash_tx_traded_at", "cash_account_transactions", ["traded_at"], unique=False
    )
    op.create_index(
        op.f("ix_cash_account_transactions_cash_account_id"),
        "cash_account_transactions",
        ["cash_account_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_cash_account_transactions_cash_account_id"),
        table_name="cash_account_transactions",
    )
    op.drop_index("ix_cash_tx_traded_at", table_name="cash_account_transactions")
    op.drop_table("cash_account_transactions")
