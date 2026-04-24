"""create_price_points_table

Revision ID: d2e5a9f1c8b4
Revises: c1d4f8e2b3a7
Create Date: 2026-04-24 00:00:00.000000

Creates the price_points table for storing historical price ticks written
by the price-refresh scheduler.

Schema:
  - id             BigInteger PK autoincrement
  - asset_symbol_id Integer NOT NULL FK → asset_symbols.id ON DELETE CASCADE
  - price          Numeric(20,6) NOT NULL
  - currency       String(10) NOT NULL
  - fetched_at     DateTime(tz=True) NOT NULL
  - composite index (asset_symbol_id, fetched_at) for efficient latest-price queries
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2e5a9f1c8b4"
down_revision: str | None = "c1d4f8e2b3a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "price_points",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("asset_symbol_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_symbol_id"],
            ["asset_symbols.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_price_points_symbol_fetched",
        "price_points",
        ["asset_symbol_id", sa.text("fetched_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_price_points_symbol_fetched", table_name="price_points")
    op.drop_table("price_points")
