"""create fx_rate_snapshots table

Revision ID: b0a16e793b3b
Revises: a79eb8a519a3
Create Date: 2026-05-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b0a16e793b3b"
down_revision: str | None = "a79eb8a519a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fx_rate_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("base_currency", sa.String(length=10), nullable=False),
        sa.Column("quote_currency", sa.String(length=10), nullable=False),
        sa.Column("rate", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "base_currency",
            "quote_currency",
            "recorded_at",
            name="uq_fx_snap_base_quote_recorded",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "ix_fx_snap_pair_recorded",
        "fx_rate_snapshots",
        ["base_currency", "quote_currency", "recorded_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_fx_snap_pair_recorded", table_name="fx_rate_snapshots")
    op.drop_table("fx_rate_snapshots")
