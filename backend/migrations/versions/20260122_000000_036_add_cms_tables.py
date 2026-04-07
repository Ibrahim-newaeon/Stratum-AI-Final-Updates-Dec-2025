"""Add CMS tables

Revision ID: 036_add_cms_tables
Revises: 035_add_settings_tables
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '036_add_cms_tables'
down_revision: Union[str, None] = '035_add_settings_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create cms_categories table
    op.create_table('cms_categories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_cms_categories_active', 'cms_categories', ['is_active'])
    op.create_index('ix_cms_categories_slug', 'cms_categories', ['slug'])

    # Create cms_tags table
    op.create_table('cms_tags',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_cms_tags_slug', 'cms_tags', ['slug'])

    # Create cms_authors table
    op.create_table('cms_authors',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('avatar_url', sa.String(length=512), nullable=True),
        sa.Column('title', sa.String(length=100), nullable=True),
        sa.Column('company', sa.String(length=100), nullable=True),
        sa.Column('website_url', sa.String(length=512), nullable=True),
        sa.Column('twitter_handle', sa.String(length=50), nullable=True),
        sa.Column('linkedin_url', sa.String(length=512), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_cms_authors_active', 'cms_authors', ['is_active'])
    op.create_index('ix_cms_authors_slug', 'cms_authors', ['slug'])
    op.create_index('ix_cms_authors_user', 'cms_authors', ['user_id'])

    # Create cms_posts table
    op.create_table('cms_posts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('category_id', sa.UUID(), nullable=True),
        sa.Column('author_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('content_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('content_type', sa.String(length=20), nullable=False, server_default='blog_post'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('meta_title', sa.String(length=70), nullable=True),
        sa.Column('meta_description', sa.String(length=160), nullable=True),
        sa.Column('canonical_url', sa.String(length=512), nullable=True),
        sa.Column('og_image_url', sa.String(length=512), nullable=True),
        sa.Column('featured_image_url', sa.String(length=512), nullable=True),
        sa.Column('featured_image_alt', sa.String(length=255), nullable=True),
        sa.Column('reading_time_minutes', sa.Integer(), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('allow_comments', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['author_id'], ['cms_authors.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['category_id'], ['cms_categories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_cms_posts_author', 'cms_posts', ['author_id'])
    op.create_index('ix_cms_posts_category', 'cms_posts', ['category_id'])
    op.create_index('ix_cms_posts_content_type', 'cms_posts', ['content_type'])
    op.create_index('ix_cms_posts_featured', 'cms_posts', ['is_featured'])
    op.create_index('ix_cms_posts_not_deleted', 'cms_posts', ['is_deleted'])
    op.create_index('ix_cms_posts_published', 'cms_posts', ['published_at'])
    op.create_index('ix_cms_posts_slug', 'cms_posts', ['slug'])
    op.create_index('ix_cms_posts_status', 'cms_posts', ['status'])

    # Create cms_post_tags association table
    op.create_table('cms_post_tags',
        sa.Column('post_id', sa.UUID(), nullable=False),
        sa.Column('tag_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['cms_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['cms_tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('post_id', 'tag_id')
    )

    # Create cms_pages table
    op.create_table('cms_pages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('content_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('meta_title', sa.String(length=70), nullable=True),
        sa.Column('meta_description', sa.String(length=160), nullable=True),
        sa.Column('show_in_navigation', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('navigation_label', sa.String(length=50), nullable=True),
        sa.Column('navigation_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('template', sa.String(length=50), nullable=False, server_default='default'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_cms_pages_nav', 'cms_pages', ['show_in_navigation'])
    op.create_index('ix_cms_pages_not_deleted', 'cms_pages', ['is_deleted'])
    op.create_index('ix_cms_pages_slug', 'cms_pages', ['slug'])
    op.create_index('ix_cms_pages_status', 'cms_pages', ['status'])

    # Create cms_contact_submissions table
    op.create_table('cms_contact_submissions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('subject', sa.String(length=255), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('source_page', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_by_user_id', sa.Integer(), nullable=True),
        sa.Column('is_responded', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_notes', sa.Text(), nullable=True),
        sa.Column('is_spam', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('spam_score', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cms_contacts_created', 'cms_contact_submissions', ['created_at'])
    op.create_index('ix_cms_contacts_email', 'cms_contact_submissions', ['email'])
    op.create_index('ix_cms_contacts_read', 'cms_contact_submissions', ['is_read'])
    op.create_index('ix_cms_contacts_spam', 'cms_contact_submissions', ['is_spam'])


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index('ix_cms_contacts_spam', table_name='cms_contact_submissions')
    op.drop_index('ix_cms_contacts_read', table_name='cms_contact_submissions')
    op.drop_index('ix_cms_contacts_email', table_name='cms_contact_submissions')
    op.drop_index('ix_cms_contacts_created', table_name='cms_contact_submissions')
    op.drop_table('cms_contact_submissions')

    op.drop_index('ix_cms_pages_status', table_name='cms_pages')
    op.drop_index('ix_cms_pages_slug', table_name='cms_pages')
    op.drop_index('ix_cms_pages_not_deleted', table_name='cms_pages')
    op.drop_index('ix_cms_pages_nav', table_name='cms_pages')
    op.drop_table('cms_pages')

    op.drop_table('cms_post_tags')

    op.drop_index('ix_cms_posts_status', table_name='cms_posts')
    op.drop_index('ix_cms_posts_slug', table_name='cms_posts')
    op.drop_index('ix_cms_posts_published', table_name='cms_posts')
    op.drop_index('ix_cms_posts_not_deleted', table_name='cms_posts')
    op.drop_index('ix_cms_posts_featured', table_name='cms_posts')
    op.drop_index('ix_cms_posts_content_type', table_name='cms_posts')
    op.drop_index('ix_cms_posts_category', table_name='cms_posts')
    op.drop_index('ix_cms_posts_author', table_name='cms_posts')
    op.drop_table('cms_posts')

    op.drop_index('ix_cms_authors_user', table_name='cms_authors')
    op.drop_index('ix_cms_authors_slug', table_name='cms_authors')
    op.drop_index('ix_cms_authors_active', table_name='cms_authors')
    op.drop_table('cms_authors')

    op.drop_index('ix_cms_tags_slug', table_name='cms_tags')
    op.drop_table('cms_tags')

    op.drop_index('ix_cms_categories_slug', table_name='cms_categories')
    op.drop_index('ix_cms_categories_active', table_name='cms_categories')
    op.drop_table('cms_categories')
