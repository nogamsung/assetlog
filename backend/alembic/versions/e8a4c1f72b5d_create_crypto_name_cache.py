"""create crypto_name_cache table

Revision ID: e8a4c1f72b5d
Revises: d7f1c9a3e8b4
Create Date: 2026-05-14 03:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e8a4c1f72b5d"
down_revision: str | tuple[str, ...] | None = "d7f1c9a3e8b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crypto_name_cache",
        sa.Column("base", sa.String(16), nullable=False),
        sa.Column("name", sa.String(64), nullable=True),
        sa.Column("source", sa.String(16), nullable=False, server_default=sa.text("'upbit'")),
        sa.Column(
            "looked_up_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("base"),
    )


def downgrade() -> None:
    op.drop_table("crypto_name_cache")
