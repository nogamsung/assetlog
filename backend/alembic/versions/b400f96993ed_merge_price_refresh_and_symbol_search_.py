"""merge price_refresh and symbol_search heads

Revision ID: b400f96993ed
Revises: d2e5a9f1c8b4, e4a7c2d15f09
Create Date: 2026-04-24 16:35:12.224836

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b400f96993ed'
down_revision: Union[str, Sequence[str], None] = ('d2e5a9f1c8b4', 'e4a7c2d15f09')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
