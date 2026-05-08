"""add external_source and external_id to transactions

Revision ID: e5f3c91b2a47
Revises: 6c7b2345d068
Create Date: 2026-05-07 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f3c91b2a47"
down_revision: str | None = "6c7b2345d068"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("external_source", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("external_id", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_tx_external_source_id",
        "transactions",
        ["external_source", "external_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_tx_external_source_id", "transactions", type_="unique")
    op.drop_column("transactions", "external_id")
    op.drop_column("transactions", "external_source")
