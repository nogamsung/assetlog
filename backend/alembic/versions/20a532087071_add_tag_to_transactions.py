"""add_tag_to_transactions

Revision ID: 20a532087071
Revises: a79eb8a519a3
Create Date: 2026-04-25 07:35:32.912132

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20a532087071"
down_revision: str | None = "a79eb8a519a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("tag", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_transactions_tag"), "transactions", ["tag"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_tag"), table_name="transactions")
    op.drop_column("transactions", "tag")
