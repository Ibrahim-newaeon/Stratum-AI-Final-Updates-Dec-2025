"""Add audience_sync_jobs.profiles_suppressed (GDPR-01).

Audience sync now withholds segment members that hold no advertising consent.
Without a counter the suppression is invisible: a tenant sees a small audience
and has no way to tell consent from a broken segment. This column records how
many members were lawfully withheld on each run.

Production safety: ADD COLUMN with a constant DEFAULT is metadata-only on
PostgreSQL 11+ (no table rewrite, brief ACCESS EXCLUSIVE lock only). Safe to
run online on a large audience_sync_jobs table.

Revision ID: 062_add_sync_job_profiles_suppressed
Revises: 061_add_tenant_encryption_keys
"""

import sqlalchemy as sa

from alembic import op

revision = "062_add_sync_job_profiles_suppressed"
down_revision = "061_add_tenant_encryption_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audience_sync_jobs",
        sa.Column(
            "profiles_suppressed",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("audience_sync_jobs", "profiles_suppressed")
