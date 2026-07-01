"""add soft-block confirmation columns to fact_actions_queue

When the execution-path enforcement gate soft-blocks an approved action,
the confirmation token it mints was only visible in the ignored Celery
task result — the operator had no way to retrieve it, and re-approving
just re-blocked. Store the token on the action row so the API can expose
it, and record the operator's one-time override (who/when) so the gate
can let the confirmed action through on the next execution attempt.

The column adds are metadata-only. The FK is created NOT VALID (no scan
under ACCESS EXCLUSIVE) and validated in a separate statement, which
only needs SHARE UPDATE EXCLUSIVE and does not block concurrent traffic.

Revision ID: 054_add_action_confirmation_columns
Revises: 053_widen_api_key_prefix
Create Date: 2026-07-02 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "054_add_action_confirmation_columns"
down_revision = "053_widen_api_key_prefix"
branch_labels = None
depends_on = None

FK_NAME = "fk_fact_actions_queue_enforcement_confirmed_by_user_id_users"


def upgrade() -> None:
    op.add_column(
        "fact_actions_queue",
        sa.Column("confirmation_token", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "fact_actions_queue",
        sa.Column(
            "enforcement_confirmed_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "fact_actions_queue",
        sa.Column("enforcement_confirmed_by_user_id", sa.Integer(), nullable=True),
    )
    # NOT VALID skips the full-table scan under ACCESS EXCLUSIVE; the
    # explicit VALIDATE below re-checks existing rows (all NULL here)
    # under SHARE UPDATE EXCLUSIVE, which does not block reads/writes.
    op.create_foreign_key(
        FK_NAME,
        "fact_actions_queue",
        "users",
        ["enforcement_confirmed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
        postgresql_not_valid=True,
    )
    op.execute(f"ALTER TABLE fact_actions_queue VALIDATE CONSTRAINT {FK_NAME}")


def downgrade() -> None:
    op.drop_constraint(FK_NAME, "fact_actions_queue", type_="foreignkey")
    op.drop_column("fact_actions_queue", "enforcement_confirmed_by_user_id")
    op.drop_column("fact_actions_queue", "enforcement_confirmed_at")
    op.drop_column("fact_actions_queue", "confirmation_token")
