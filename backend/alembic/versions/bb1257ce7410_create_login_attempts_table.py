"""create_login_attempts_table

Revision ID: bb1257ce7410
Revises: 20a532087071
Create Date: 2026-04-26 11:02:46.571047

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bb1257ce7410"
down_revision: str | None = "20a532087071"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column(
            "attempted_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "ix_login_attempts_ip_attempted",
        "login_attempts",
        ["ip", "attempted_at"],
        unique=False,
    )
    op.create_index(
        "ix_login_attempts_attempted",
        "login_attempts",
        ["attempted_at"],
        unique=False,
    )
    op.create_index(
        "ix_login_attempts_success_attempted",
        "login_attempts",
        ["success", "attempted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_login_attempts_success_attempted", table_name="login_attempts")
    op.drop_index("ix_login_attempts_ip_attempted", table_name="login_attempts")
    op.drop_index("ix_login_attempts_attempted", table_name="login_attempts")
    op.drop_table("login_attempts")
