"""add_last_price_to_asset_symbols

Revision ID: c1d4f8e2b3a7
Revises: f3b9e1c72d06
Create Date: 2026-04-24 00:00:00.000000

Adds two nullable columns to asset_symbols:
- last_price (NUMERIC 20,6) — cached price from the price-refresh scheduler.
- last_price_refreshed_at (DATETIME tz-aware) — when the cache was last written.

Values are populated by the scheduler slice (future PR) — this migration only
adds the columns and the supporting index. All existing rows will have NULL.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d4f8e2b3a7"
down_revision: str | None = "f3b9e1c72d06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "asset_symbols",
        sa.Column("last_price", sa.Numeric(precision=20, scale=6), nullable=True),
    )
    op.add_column(
        "asset_symbols",
        sa.Column(
            "last_price_refreshed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_asset_symbols_last_refreshed",
        "asset_symbols",
        ["last_price_refreshed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_asset_symbols_last_refreshed", table_name="asset_symbols")
    op.drop_column("asset_symbols", "last_price_refreshed_at")
    op.drop_column("asset_symbols", "last_price")
