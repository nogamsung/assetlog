"""drop_users_table_and_user_id

Single-owner refactor: removes the placeholder ``users`` table and the
``user_assets.user_id`` column / FK / index. The composite unique constraint
on (user_id, asset_symbol_id) is replaced by a single-column unique on
asset_symbol_id (each holding still occurs at most once per symbol).

Revision ID: c8a4f1e927b3
Revises: bb1257ce7410
Create Date: 2026-04-27 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8a4f1e927b3"
down_revision: str | None = "bb1257ce7410"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The original a2f8c3d91e45 migration created this FK without a name,
    # so the DB-side name is whatever the backend auto-assigned (e.g. MySQL's
    # ``user_assets_ibfk_2``) rather than ``fk_user_assets_user_id``. Look it
    # up at runtime so the migration works regardless of naming.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    user_fk_name: str | None = None
    for fk in insp.get_foreign_keys("user_assets"):
        if (
            fk.get("referred_table") == "users"
            and fk.get("constrained_columns") == ["user_id"]
        ):
            user_fk_name = fk.get("name")
            break
    if user_fk_name is None:
        raise RuntimeError(
            "Expected FK user_assets.user_id -> users.id was not found",
        )

    # --- user_assets: drop FK + composite unique + index, then drop user_id column ---
    with op.batch_alter_table("user_assets") as batch:
        batch.drop_constraint(user_fk_name, type_="foreignkey")
        batch.drop_constraint("uq_user_asset_symbol", type_="unique")
        batch.drop_index("ix_user_assets_user_id")
        batch.drop_column("user_id")
        batch.create_unique_constraint("uq_user_asset_symbol", ["asset_symbol_id"])

    # --- users: drop the table entirely ---
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")


def downgrade() -> None:
    # Re-create users table with the original schema
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
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
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Restore user_assets.user_id column + FK + index + composite unique
    with op.batch_alter_table("user_assets") as batch:
        batch.drop_constraint("uq_user_asset_symbol", type_="unique")
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=False))
        batch.create_index("ix_user_assets_user_id", ["user_id"], unique=False)
        batch.create_foreign_key(
            "fk_user_assets_user_id",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_unique_constraint(
            "uq_user_asset_symbol",
            ["user_id", "asset_symbol_id"],
        )
