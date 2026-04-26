"""Merge launch_readiness and drop_orphaned_autopilot heads

Revision ID: e21f74be91a2
Revises: 046_add_launch_readiness, 046_drop_orphaned_autopilot_020_tables
Create Date: 2026-04-26 13:37:18.893056+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e21f74be91a2'
down_revision: Union[str, None] = ('046_add_launch_readiness', '046_drop_orphaned_autopilot_020_tables')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
