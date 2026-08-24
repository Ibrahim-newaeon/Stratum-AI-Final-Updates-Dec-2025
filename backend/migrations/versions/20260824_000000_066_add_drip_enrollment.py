"""Add drip_sequence_versions and drip_enrollments.

Gives drip campaigns the two things the execution engine cannot be written
without: a frozen copy of the graph a recipient entered on, and a row saying
where that recipient currently stands.

``drip_execution_logs`` already records what happened. Nothing recorded what
happens next, so a sequence could not be resumed after a restart, paused
mid-flight, or checked for whether a recipient was already walking it.

Both tables are new and empty, so this is additive only — no locking concern
on existing traffic. ``drip_sequences.active_version_id`` is a nullable column
add, which is metadata-only on PostgreSQL 11+.

Revision ID: 066_add_drip_enrollment
Revises: 065_add_age_knowledge_graph
Create Date: 2026-08-24 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers
revision = "066_add_drip_enrollment"
down_revision = "065_add_age_knowledge_graph"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Frozen graph snapshots
    # -----------------------------------------------------------------------
    op.create_table(
        "drip_sequence_versions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("sequence_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "nodes", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "edges", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("trigger_type", sa.String(length=50), nullable=False),
        sa.Column(
            "trigger_config",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("entry_node_id", sa.String(length=64), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("published_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["sequence_id"], ["drip_sequences.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["published_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sequence_id", "version", name="uq_drip_version_sequence"),
    )
    op.create_index(
        "ix_drip_sequence_versions_tenant_id", "drip_sequence_versions", ["tenant_id"]
    )
    op.create_index(
        "ix_drip_sequence_versions_sequence_id",
        "drip_sequence_versions",
        ["sequence_id"],
    )
    op.create_index(
        "ix_drip_version_tenant", "drip_sequence_versions", ["tenant_id", "sequence_id"]
    )

    # The sequence points at whichever version new recipients enter on.
    op.add_column(
        "drip_sequences",
        sa.Column("active_version_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_drip_sequences_active_version_id", "drip_sequences", ["active_version_id"]
    )
    op.create_foreign_key(
        "fk_drip_sequences_active_version",
        "drip_sequences",
        "drip_sequence_versions",
        ["active_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -----------------------------------------------------------------------
    # Per-recipient position
    # -----------------------------------------------------------------------
    op.create_table(
        "drip_enrollments",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("sequence_id", sa.String(length=64), nullable=False),
        sa.Column("version_id", sa.String(length=64), nullable=False),
        sa.Column("profile_id", UUID(as_uuid=True), nullable=True),
        sa.Column("recipient_hash", sa.String(length=64), nullable=False),
        # Sized for ciphertext: encrypt_pii is ~2.2x and RFC 5321 caps an
        # address at 320, so 320 would reject the longest legitimate address.
        sa.Column("recipient_email", sa.String(length=1024), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("current_node_id", sa.String(length=64), nullable=True),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("steps_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by", sa.String(length=64), nullable=True),
        sa.Column("entry_trigger", sa.String(length=50), nullable=False),
        sa.Column(
            "entry_context",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("cancel_reason", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["sequence_id"], ["drip_sequences.id"], ondelete="CASCADE"
        ),
        # RESTRICT, not CASCADE: a version with live enrollments on it must not
        # be deletable, or the interpreter loses the graph mid-run.
        sa.ForeignKeyConstraint(
            ["version_id"], ["drip_sequence_versions.id"], ondelete="RESTRICT"
        ),
        # SET NULL, not CASCADE: erasing a CDP profile must not erase the record
        # that we sent that person mail.
        sa.ForeignKeyConstraint(
            ["profile_id"], ["cdp_profiles.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drip_enrollments_tenant_id", "drip_enrollments", ["tenant_id"])
    op.create_index(
        "ix_drip_enrollments_sequence_id", "drip_enrollments", ["sequence_id"]
    )
    op.create_index(
        "ix_drip_enrollments_version_id", "drip_enrollments", ["version_id"]
    )
    op.create_index(
        "ix_drip_enrollments_profile_id", "drip_enrollments", ["profile_id"]
    )
    op.create_index(
        "ix_drip_enrollments_recipient_hash", "drip_enrollments", ["recipient_hash"]
    )

    # One live enrollment per recipient per sequence. Partial, so completing a
    # sequence frees the recipient to enter it again later.
    op.create_index(
        "uq_drip_enrollment_live",
        "drip_enrollments",
        ["sequence_id", "recipient_hash"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'active', 'waiting')"),
    )
    # The sweep's only query.
    op.create_index(
        "ix_drip_enrollment_due",
        "drip_enrollments",
        ["status", "next_due_at"],
        postgresql_where=sa.text("status IN ('pending', 'waiting')"),
    )
    op.create_index(
        "ix_drip_enrollment_tenant_status", "drip_enrollments", ["tenant_id", "status"]
    )
    op.create_index(
        "ix_drip_enrollment_sequence_status",
        "drip_enrollments",
        ["sequence_id", "status"],
    )

    # -----------------------------------------------------------------------
    # Execution log: attach events to an enrollment, and stop storing the
    # recipient address in the clear
    # -----------------------------------------------------------------------
    # The column has always been plaintext, which was survivable while the
    # whole router was 503'd and nothing wrote to it. The execution engine
    # writes real recipients, so it is widened for ciphertext (encrypt_pii is
    # ~2.2x; 320 would reject the longest legitimate address on insert) and
    # written through the same tenant-key accessor as drip_enrollments.
    op.alter_column(
        "drip_execution_logs",
        "recipient_email",
        existing_type=sa.String(length=320),
        type_=sa.String(length=1024),
        existing_nullable=False,
    )
    op.add_column(
        "drip_execution_logs",
        sa.Column("enrollment_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "drip_execution_logs",
        sa.Column("recipient_hash", sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        "fk_drip_execution_logs_enrollment",
        "drip_execution_logs",
        "drip_enrollments",
        ["enrollment_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_drip_execution_logs_enrollment_id",
        "drip_execution_logs",
        ["enrollment_id"],
    )
    op.create_index(
        "ix_drip_execution_logs_recipient_hash",
        "drip_execution_logs",
        ["recipient_hash"],
    )
    op.create_index(
        "ix_drip_exec_enrollment", "drip_execution_logs", ["enrollment_id", "sent_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_drip_exec_enrollment", table_name="drip_execution_logs")
    op.drop_index(
        "ix_drip_execution_logs_recipient_hash", table_name="drip_execution_logs"
    )
    op.drop_index(
        "ix_drip_execution_logs_enrollment_id", table_name="drip_execution_logs"
    )
    op.drop_constraint(
        "fk_drip_execution_logs_enrollment", "drip_execution_logs", type_="foreignkey"
    )
    op.drop_column("drip_execution_logs", "recipient_hash")
    op.drop_column("drip_execution_logs", "enrollment_id")
    # Narrowing back to 320 fails once real ciphertext exists — deliberate, and
    # the same trade-off migrations 063 and 064 made. A downgrade that silently
    # truncated encrypted addresses would be worse than one that refuses.
    op.alter_column(
        "drip_execution_logs",
        "recipient_email",
        existing_type=sa.String(length=1024),
        type_=sa.String(length=320),
        existing_nullable=False,
    )

    op.drop_index("ix_drip_enrollment_sequence_status", table_name="drip_enrollments")
    op.drop_index("ix_drip_enrollment_tenant_status", table_name="drip_enrollments")
    op.drop_index("ix_drip_enrollment_due", table_name="drip_enrollments")
    op.drop_index("uq_drip_enrollment_live", table_name="drip_enrollments")
    op.drop_index("ix_drip_enrollments_recipient_hash", table_name="drip_enrollments")
    op.drop_index("ix_drip_enrollments_profile_id", table_name="drip_enrollments")
    op.drop_index("ix_drip_enrollments_version_id", table_name="drip_enrollments")
    op.drop_index("ix_drip_enrollments_sequence_id", table_name="drip_enrollments")
    op.drop_index("ix_drip_enrollments_tenant_id", table_name="drip_enrollments")
    op.drop_table("drip_enrollments")

    op.drop_constraint(
        "fk_drip_sequences_active_version", "drip_sequences", type_="foreignkey"
    )
    op.drop_index("ix_drip_sequences_active_version_id", table_name="drip_sequences")
    op.drop_column("drip_sequences", "active_version_id")

    op.drop_index("ix_drip_version_tenant", table_name="drip_sequence_versions")
    op.drop_index(
        "ix_drip_sequence_versions_sequence_id", table_name="drip_sequence_versions"
    )
    op.drop_index(
        "ix_drip_sequence_versions_tenant_id", table_name="drip_sequence_versions"
    )
    op.drop_table("drip_sequence_versions")
