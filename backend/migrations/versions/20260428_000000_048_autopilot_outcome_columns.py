# =============================================================================
# Stratum AI — Migration: autopilot outcome columns (Phase A)
# =============================================================================
"""
Adds outcome tracking columns to the enforcement_audit_logs table so the
outcome-triggered upgrade nudges can roll up "value delivered" over a
period without scanning JSON details.

Phase A ships the schema + a stub estimator that always returns 0/None.
Phase B will swap in a real counterfactual estimator (linear extrapolation
of pre-pause burn rate × hours-saved, with conservative_factor=0.5 to
avoid over-claiming).

Columns added:
  value_delivered_cents  INTEGER NULL
    Estimated dollar value the autopilot decision delivered (saved or
    earned). Stored in cents to avoid float arithmetic.
  outcome_type           VARCHAR(32) NULL
    Categorical outcome: 'saved' (avoided overspend), 'earned' (gained
    revenue), 'prevented' (blocked a violation), 'neutral' (no $ value).
  outcome_confidence     VARCHAR(16) NULL
    'low' | 'medium' | 'high' — used by the frontend nudge to qualify
    the claim ("Stratum's saved you AT LEAST $1,420 this week").

All three are NULL-able so backfill / rollout is non-breaking.
"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers
revision = "048_autopilot_outcome_columns"
down_revision = "047_add_missing_indexes"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """Defensive check — skip if the column already exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = :table AND column_name = :column
            """
        ),
        {"table": table, "column": column},
    )
    return result.first() is not None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT 1
              FROM information_schema.tables
             WHERE table_name = :table
            """
        ),
        {"table": table},
    )
    return result.first() is not None


def upgrade() -> None:
    if not _table_exists("enforcement_audit_logs"):
        return

    if not _column_exists("enforcement_audit_logs", "value_delivered_cents"):
        op.add_column(
            "enforcement_audit_logs",
            sa.Column("value_delivered_cents", sa.Integer(), nullable=True),
        )

    if not _column_exists("enforcement_audit_logs", "outcome_type"):
        op.add_column(
            "enforcement_audit_logs",
            sa.Column("outcome_type", sa.String(length=32), nullable=True),
        )

    if not _column_exists("enforcement_audit_logs", "outcome_confidence"):
        op.add_column(
            "enforcement_audit_logs",
            sa.Column("outcome_confidence", sa.String(length=16), nullable=True),
        )

    # Index on tenant_id + value_delivered_cents helps the rollup endpoint
    # answer "how much value delivered to tenant X over period P" without
    # a full scan.
    op.create_index(
        "ix_enforcement_audit_logs_tenant_outcome",
        "enforcement_audit_logs",
        ["tenant_id", "timestamp", "value_delivered_cents"],
        if_not_exists=True,
    )


def downgrade() -> None:
    if not _table_exists("enforcement_audit_logs"):
        return

    op.drop_index(
        "ix_enforcement_audit_logs_tenant_outcome",
        table_name="enforcement_audit_logs",
        if_exists=True,
    )

    for column in ("outcome_confidence", "outcome_type", "value_delivered_cents"):
        if _column_exists("enforcement_audit_logs", column):
            op.drop_column("enforcement_audit_logs", column)
