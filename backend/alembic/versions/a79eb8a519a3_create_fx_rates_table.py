"""create_fx_rates_table

Revision ID: a79eb8a519a3
Revises: b400f96993ed
Create Date: 2026-04-25 07:18:48.000695

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a79eb8a519a3"
down_revision: str | None = "b400f96993ed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fx_rates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("base_currency", sa.String(length=10), nullable=False),
        sa.Column("quote_currency", sa.String(length=10), nullable=False),
        sa.Column("rate", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("base_currency", "quote_currency", name="uq_fx_base_quote"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_fx_fetched_at", "fx_rates", ["fetched_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_fx_fetched_at", table_name="fx_rates")
    op.drop_table("fx_rates")
