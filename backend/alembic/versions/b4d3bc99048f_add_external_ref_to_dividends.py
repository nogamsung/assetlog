"""add external_source and external_id to dividends table

Revision ID: b4d3bc99048f
Revises: f2c93d1a7e64
Create Date: 2026-05-12 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b4d3bc99048f"
down_revision: str | tuple[str, ...] | None = "f2c93d1a7e64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("dividends", sa.Column("external_source", sa.String(32), nullable=True))
    op.add_column("dividends", sa.Column("external_id", sa.String(64), nullable=True))
    op.create_index(
        "uq_dividend_external",
        "dividends",
        ["external_source", "external_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_dividend_external", table_name="dividends")
    op.drop_column("dividends", "external_id")
    op.drop_column("dividends", "external_source")
