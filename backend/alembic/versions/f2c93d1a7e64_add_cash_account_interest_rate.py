"""merge heads + add cash_account interest_rate_annual

Revision ID: f2c93d1a7e64
Revises: ('d8e1a5f2b730', 'e5f3c91b2a47')
Create Date: 2026-05-11 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f2c93d1a7e64"
down_revision: str | tuple[str, ...] | None = (
    "b0a16e793b3b",
    "d8e1a5f2b730",
    "e5f3c91b2a47",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cash_accounts",
        sa.Column(
            "interest_rate_annual",
            sa.Numeric(precision=6, scale=4),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("cash_accounts", "interest_rate_annual")
