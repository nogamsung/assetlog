"""create dividends table

Revision ID: d8e1a5f2b730
Revises: 6c7b2345d068
Create Date: 2026-05-07 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8e1a5f2b730"
down_revision: str | None = "6c7b2345d068"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dividends",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_symbol_id", sa.Integer(), nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["asset_symbol_id"],
            ["asset_symbols.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "asset_symbol_id",
            "ex_date",
            name="uq_dividend_symbol_ex_date",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "ix_dividend_ex_date",
        "dividends",
        ["ex_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_dividend_ex_date", table_name="dividends")
    op.drop_table("dividends")
