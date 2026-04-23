"""create_transactions_table

Revision ID: f3b9e1c72d06
Revises: a2f8c3d91e45
Create Date: 2026-04-23 23:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3b9e1c72d06"
down_revision: str | None = "a2f8c3d91e45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_asset_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=28, scale=10), nullable=False),
        sa.Column("price", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("traded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("memo", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_asset_id"],
            ["user_assets.id"],
            ondelete="CASCADE",
            name="fk_transactions_user_asset_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Single-column index for user_asset_id lookups
    op.create_index(
        "ix_transactions_user_asset_id",
        "transactions",
        ["user_asset_id"],
        unique=False,
    )
    # Composite index for summary aggregation and list queries
    op.create_index(
        "ix_transactions_user_asset_traded_at",
        "transactions",
        ["user_asset_id", "traded_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_user_asset_traded_at", table_name="transactions")
    op.drop_index("ix_transactions_user_asset_id", table_name="transactions")
    op.drop_constraint(
        "fk_transactions_user_asset_id",
        "transactions",
        type_="foreignkey",
    )
    op.drop_table("transactions")
