"""create kr_name_cache table

Revision ID: d7f1c9a3e8b4
Revises: c2f4a8e91d5b
Create Date: 2026-05-13 07:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7f1c9a3e8b4"
down_revision: str | tuple[str, ...] | None = "c2f4a8e91d5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kr_name_cache",
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("code", sa.String(6), nullable=True),
        sa.Column(
            "source",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'naver'"),
        ),
        sa.Column(
            "looked_up_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table("kr_name_cache")
