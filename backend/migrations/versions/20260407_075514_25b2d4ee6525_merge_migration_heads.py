"""merge_migration_heads

Revision ID: 25b2d4ee6525
Revises: 025_campaign_builder, 045_add_account_level_analytics
Create Date: 2026-04-07 07:55:14.208678+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '25b2d4ee6525'
down_revision: Union[str, None] = ('025_campaign_builder', '045_add_account_level_analytics')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
