"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    # Production safety — release.sh runs `alembic upgrade head` on boot
    # against the live database, so locking behaviour here is a production
    # concern. Full notes: backend/docs/02-backend/database-schema.md
    # ("Production safety").
    #
    #   * Indexing a table that already has rows? postgresql_concurrently=True
    #     plus op.get_bind().execution_options(isolation_level="AUTOCOMMIT").
    #     Not needed for an index created with its table in this migration.
    #   * Adding NOT NULL? Give it a server_default, or add nullable, backfill,
    #     then tighten.
    #   * Prefer IF NOT EXISTS / IF EXISTS — replicas can run this concurrently.
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    # Write a real downgrade. Leave `pass` only when the upgrade genuinely
    # cannot be reversed, and say so in a comment when that is the case.
    ${downgrades if downgrades else "pass"}
