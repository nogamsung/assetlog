"""price_points: collapse to one row per (asset_symbol_id, calendar day)

Revision ID: a1c8b3e64d92
Revises: f9d2a6e147bc
Create Date: 2026-05-15 14:00:00.000000

Adds a STORED generated DATE column derived from ``fetched_at`` and a
UNIQUE index on ``(asset_symbol_id, fetched_date)`` so the 10-min refresh
job can upsert into a single per-symbol-per-day row instead of appending
endlessly.

dev environments routinely TRUNCATE this table, so the upgrade does the
same — picking a deterministic "winner" per (symbol, day) from the old
append-only rows would otherwise be racy and ambiguous.

"""

from collections.abc import Sequence

from alembic import op

revision: str = "a1c8b3e64d92"
down_revision: str | tuple[str, ...] | None = "f9d2a6e147bc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Dev data is throwaway — the scheduler will repopulate within 10 min.
    op.execute("TRUNCATE TABLE price_points")
    op.execute(
        "ALTER TABLE price_points "
        "ADD COLUMN fetched_date DATE "
        "GENERATED ALWAYS AS (DATE(fetched_at)) STORED NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_price_point_symbol_date "
        "ON price_points (asset_symbol_id, fetched_date)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_price_point_symbol_date ON price_points")
    op.execute("ALTER TABLE price_points DROP COLUMN fetched_date")
