"""normalize external_source: toss_securities → toss_investment, shinhan → shinhan_investment

Revision ID: f9d2a6e147bc
Revises: e8a4c1f72b5d
Create Date: 2026-05-15 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "f9d2a6e147bc"
down_revision: str | tuple[str, ...] | None = "e8a4c1f72b5d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLES = ("transactions", "cash_account_transactions", "dividends")
_RENAMES = {
    "toss_securities": "toss_investment",
    "shinhan": "shinhan_investment",
}


def upgrade() -> None:
    for table in _TABLES:
        for old, new in _RENAMES.items():
            op.execute(
                f"UPDATE {table} SET external_source = '{new}' "
                f"WHERE external_source = '{old}'"
            )


def downgrade() -> None:
    for table in _TABLES:
        for old, new in _RENAMES.items():
            op.execute(
                f"UPDATE {table} SET external_source = '{old}' "
                f"WHERE external_source = '{new}'"
            )
