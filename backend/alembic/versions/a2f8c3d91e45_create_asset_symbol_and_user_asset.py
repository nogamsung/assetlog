"""create_asset_symbol_and_user_asset

Revision ID: a2f8c3d91e45
Revises: 36d1bb1747be
Create Date: 2026-04-23 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2f8c3d91e45"
down_revision: str | None = "36d1bb1747be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- asset_symbols ---
    op.create_table(
        "asset_symbols",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "asset_type",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("exchange", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "asset_type",
            "symbol",
            "exchange",
            name="uq_asset_type_symbol_exchange",
        ),
    )
    op.create_index("ix_asset_symbols_symbol", "asset_symbols", ["symbol"], unique=False)
    op.create_index(
        "ix_asset_symbols_type_exchange",
        "asset_symbols",
        ["asset_type", "exchange"],
        unique=False,
    )

    # --- user_assets ---
    op.create_table(
        "user_assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("asset_symbol_id", sa.Integer(), nullable=False),
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
            ["asset_symbol_id"],
            ["asset_symbols.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "asset_symbol_id", name="uq_user_asset_symbol"),
    )
    op.create_index("ix_user_assets_user_id", "user_assets", ["user_id"], unique=False)
    op.create_index(
        "ix_user_assets_asset_symbol_id",
        "user_assets",
        ["asset_symbol_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_assets_asset_symbol_id", table_name="user_assets")
    op.drop_index("ix_user_assets_user_id", table_name="user_assets")
    op.drop_table("user_assets")
    op.drop_index("ix_asset_symbols_type_exchange", table_name="asset_symbols")
    op.drop_index("ix_asset_symbols_symbol", table_name="asset_symbols")
    op.drop_table("asset_symbols")
