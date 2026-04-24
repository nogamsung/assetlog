"""add_last_synced_at_to_asset_symbols

Revision ID: e4a7c2d15f09
Revises: c1d4f8e2b3a7
Create Date: 2026-04-24 00:00:00.000000

Adds last_synced_at (DATETIME tz-aware) to asset_symbols.
Populated by the symbol-search adapter fallback upsert pipeline —
records when the symbol was last refreshed from an external source.
All existing rows will have NULL.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4a7c2d15f09"
down_revision: str | None = "c1d4f8e2b3a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "asset_symbols",
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("asset_symbols", "last_synced_at")
