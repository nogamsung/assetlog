"""create isin_ticker_cache table

Revision ID: c2f4a8e91d5b
Revises: a4b7e293c8d1, d5e8d86ff010
Create Date: 2026-05-13 06:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c2f4a8e91d5b"
down_revision: str | tuple[str, ...] | None = ("a4b7e293c8d1", "d5e8d86ff010")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "isin_ticker_cache",
        sa.Column("isin", sa.String(12), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=True),
        sa.Column(
            "source",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'openfigi'"),
        ),
        sa.Column(
            "looked_up_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("isin"),
    )


def downgrade() -> None:
    op.drop_table("isin_ticker_cache")
