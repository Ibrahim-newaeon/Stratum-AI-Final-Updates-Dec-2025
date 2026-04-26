"""Drop orphaned autopilot tables from migration 020

Revision ID: 046_drop_orphaned_autopilot_020_tables
Revises: 25b2d4ee6525
Create Date: 2026-04-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '046_drop_orphaned_autopilot_020_tables'
down_revision: Union[str, None] = '25b2d4ee6525'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop orphaned tables created by migration 020 that have no corresponding
    # SQLAlchemy models or application code references.
    op.drop_table('autopilot_pending_confirmations')
    op.drop_table('autopilot_intervention_log')
    op.drop_table('autopilot_enforcement_settings')


def downgrade() -> None:
    # Tables are orphaned and have no model definitions. Re-creating them
    # would require copying the full original migration 020. If downgrade is
    # needed, restore from a database backup taken before this migration.
    raise NotImplementedError(
        "Downgrade not supported for dropping orphaned autopilot tables. "
        "Restore from backup if needed."
    )
