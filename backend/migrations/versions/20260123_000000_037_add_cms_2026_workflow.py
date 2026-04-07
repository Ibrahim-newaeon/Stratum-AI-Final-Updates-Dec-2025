"""Add CMS 2026 workflow tables and columns

Revision ID: 037_add_cms_2026_workflow
Revises: 036_add_cms_tables
Create Date: 2026-01-23

Adds:
- cms_post_versions: Content versioning for audit trail and rollback
- cms_workflow_logs: Workflow audit trail for all status changes
- New columns on cms_posts for workflow tracking
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '037_add_cms_2026_workflow'
down_revision: Union[str, None] = '036_add_cms_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # Add 2026 workflow columns to cms_posts table
    # ==========================================================================

    # Workflow tracking
    op.add_column('cms_posts', sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('cms_posts', sa.Column('submitted_by_id', sa.Integer(), nullable=True))

    # Review tracking
    op.add_column('cms_posts', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('cms_posts', sa.Column('reviewed_by_id', sa.Integer(), nullable=True))
    op.add_column('cms_posts', sa.Column('review_notes', sa.Text(), nullable=True))

    # Approval tracking
    op.add_column('cms_posts', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('cms_posts', sa.Column('approved_by_id', sa.Integer(), nullable=True))

    # Rejection tracking
    op.add_column('cms_posts', sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('cms_posts', sa.Column('rejected_by_id', sa.Integer(), nullable=True))
    op.add_column('cms_posts', sa.Column('rejection_reason', sa.Text(), nullable=True))

    # Versioning
    op.add_column('cms_posts', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('cms_posts', sa.Column('current_version_id', sa.UUID(), nullable=True))

    # Assigned reviewer
    op.add_column('cms_posts', sa.Column('assigned_reviewer_id', sa.Integer(), nullable=True))
    op.add_column('cms_posts', sa.Column('review_due_date', sa.DateTime(timezone=True), nullable=True))

    # Content locking
    op.add_column('cms_posts', sa.Column('locked_by_id', sa.Integer(), nullable=True))
    op.add_column('cms_posts', sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True))

    # Add foreign key constraints for user references
    op.create_foreign_key(
        'fk_cms_posts_submitted_by',
        'cms_posts', 'users',
        ['submitted_by_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_cms_posts_reviewed_by',
        'cms_posts', 'users',
        ['reviewed_by_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_cms_posts_approved_by',
        'cms_posts', 'users',
        ['approved_by_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_cms_posts_rejected_by',
        'cms_posts', 'users',
        ['rejected_by_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_cms_posts_assigned_reviewer',
        'cms_posts', 'users',
        ['assigned_reviewer_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_cms_posts_locked_by',
        'cms_posts', 'users',
        ['locked_by_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add indexes for workflow queries
    op.create_index('ix_cms_posts_scheduled', 'cms_posts', ['scheduled_at'])
    op.create_index('ix_cms_posts_reviewer', 'cms_posts', ['assigned_reviewer_id'])

    # ==========================================================================
    # Create cms_post_versions table (Content Versioning)
    # ==========================================================================
    op.create_table('cms_post_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('post_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),

        # Content snapshot
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('content_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Metadata snapshot
        sa.Column('meta_title', sa.String(length=70), nullable=True),
        sa.Column('meta_description', sa.String(length=160), nullable=True),
        sa.Column('featured_image_url', sa.String(length=500), nullable=True),

        # Who created this version
        sa.Column('created_by_id', sa.Integer(), nullable=True),

        # Change tracking
        sa.Column('change_summary', sa.String(length=500), nullable=True),
        sa.Column('change_type', sa.String(length=50), nullable=True),

        # Metrics at this version
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('reading_time_minutes', sa.Integer(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['post_id'], ['cms_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Indexes for version queries
    op.create_index('ix_cms_post_versions_post', 'cms_post_versions', ['post_id'])
    op.create_index('ix_cms_post_versions_version', 'cms_post_versions', ['post_id', 'version'])
    op.create_index('ix_cms_post_versions_created', 'cms_post_versions', ['created_at'])

    # ==========================================================================
    # Create cms_workflow_logs table (Audit Trail)
    # ==========================================================================
    op.create_table('cms_workflow_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('post_id', sa.UUID(), nullable=False),

        # Action details
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('from_status', sa.String(length=20), nullable=True),
        sa.Column('to_status', sa.String(length=20), nullable=True),

        # Actor
        sa.Column('performed_by_id', sa.Integer(), nullable=True),
        sa.Column('performed_by_role', sa.String(length=50), nullable=True),

        # Context
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Version reference
        sa.Column('version_number', sa.Integer(), nullable=True),

        # Security audit
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['post_id'], ['cms_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['performed_by_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Indexes for audit queries
    op.create_index('ix_cms_workflow_logs_post', 'cms_workflow_logs', ['post_id'])
    op.create_index('ix_cms_workflow_logs_action', 'cms_workflow_logs', ['action'])
    op.create_index('ix_cms_workflow_logs_user', 'cms_workflow_logs', ['performed_by_id'])
    op.create_index('ix_cms_workflow_logs_created', 'cms_workflow_logs', ['created_at'])
    op.create_index('ix_cms_workflow_logs_status', 'cms_workflow_logs', ['to_status'])


def downgrade() -> None:
    # Drop cms_workflow_logs table
    op.drop_index('ix_cms_workflow_logs_status', table_name='cms_workflow_logs')
    op.drop_index('ix_cms_workflow_logs_created', table_name='cms_workflow_logs')
    op.drop_index('ix_cms_workflow_logs_user', table_name='cms_workflow_logs')
    op.drop_index('ix_cms_workflow_logs_action', table_name='cms_workflow_logs')
    op.drop_index('ix_cms_workflow_logs_post', table_name='cms_workflow_logs')
    op.drop_table('cms_workflow_logs')

    # Drop cms_post_versions table
    op.drop_index('ix_cms_post_versions_created', table_name='cms_post_versions')
    op.drop_index('ix_cms_post_versions_version', table_name='cms_post_versions')
    op.drop_index('ix_cms_post_versions_post', table_name='cms_post_versions')
    op.drop_table('cms_post_versions')

    # Drop indexes from cms_posts
    op.drop_index('ix_cms_posts_reviewer', table_name='cms_posts')
    op.drop_index('ix_cms_posts_scheduled', table_name='cms_posts')

    # Drop foreign key constraints
    op.drop_constraint('fk_cms_posts_locked_by', 'cms_posts', type_='foreignkey')
    op.drop_constraint('fk_cms_posts_assigned_reviewer', 'cms_posts', type_='foreignkey')
    op.drop_constraint('fk_cms_posts_rejected_by', 'cms_posts', type_='foreignkey')
    op.drop_constraint('fk_cms_posts_approved_by', 'cms_posts', type_='foreignkey')
    op.drop_constraint('fk_cms_posts_reviewed_by', 'cms_posts', type_='foreignkey')
    op.drop_constraint('fk_cms_posts_submitted_by', 'cms_posts', type_='foreignkey')

    # Drop columns from cms_posts
    op.drop_column('cms_posts', 'locked_at')
    op.drop_column('cms_posts', 'locked_by_id')
    op.drop_column('cms_posts', 'review_due_date')
    op.drop_column('cms_posts', 'assigned_reviewer_id')
    op.drop_column('cms_posts', 'current_version_id')
    op.drop_column('cms_posts', 'version')
    op.drop_column('cms_posts', 'rejection_reason')
    op.drop_column('cms_posts', 'rejected_by_id')
    op.drop_column('cms_posts', 'rejected_at')
    op.drop_column('cms_posts', 'approved_by_id')
    op.drop_column('cms_posts', 'approved_at')
    op.drop_column('cms_posts', 'review_notes')
    op.drop_column('cms_posts', 'reviewed_by_id')
    op.drop_column('cms_posts', 'reviewed_at')
    op.drop_column('cms_posts', 'submitted_by_id')
    op.drop_column('cms_posts', 'submitted_at')
