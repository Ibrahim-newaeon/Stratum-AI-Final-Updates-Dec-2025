"""Add Landing CMS tables

Revision ID: 021
Revises: 020
Create Date: 2026-01-10 00:00:00.000000

New tables:
- landing_page_templates: Base templates for landing pages
- landing_pages: Individual pages created from templates
- landing_page_sections: Sections within pages (toggleable)
- landing_page_section_contents: Translated content for sections
- landing_page_translations: Page-level SEO translations
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '021'
down_revision = '020'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Landing Page Templates
    # ==========================================================================
    op.create_table(
        'landing_page_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        # Template identification
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        # Template content
        sa.Column('html_content', sa.Text(), nullable=False),
        sa.Column('css_content', sa.Text(), nullable=True),
        sa.Column('js_content', sa.Text(), nullable=True),
        # Default configuration
        sa.Column('default_theme', sa.String(20), nullable=False, server_default='dark'),
        sa.Column('supported_languages', sa.String(100), nullable=False, server_default='en,ar'),
        # Section definitions (JSON)
        sa.Column('section_schema', sa.Text(), nullable=True),
        # Metadata
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )

    # ==========================================================================
    # Landing Pages
    # ==========================================================================
    op.create_table(
        'landing_pages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        # Page identification
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        # Template reference
        sa.Column('template_id', sa.Integer(), nullable=False),
        # Page settings
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('default_language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('theme', sa.String(20), nullable=False, server_default='dark'),
        # SEO (default/fallback)
        sa.Column('meta_title', sa.String(200), nullable=True),
        sa.Column('meta_description', sa.String(500), nullable=True),
        sa.Column('meta_keywords', sa.String(500), nullable=True),
        sa.Column('og_image_url', sa.String(500), nullable=True),
        # Custom CSS/JS overrides
        sa.Column('custom_css', sa.Text(), nullable=True),
        sa.Column('custom_js', sa.Text(), nullable=True),
        # Analytics
        sa.Column('ga_tracking_id', sa.String(50), nullable=True),
        sa.Column('fb_pixel_id', sa.String(50), nullable=True),
        # Publishing
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_by_user_id', sa.Integer(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.ForeignKeyConstraint(['template_id'], ['landing_page_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['published_by_user_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('ix_landing_page_slug', 'landing_pages', ['slug'])
    op.create_index('ix_landing_page_status', 'landing_pages', ['status'])

    # ==========================================================================
    # Landing Page Sections
    # ==========================================================================
    op.create_table(
        'landing_page_sections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        # Section identification
        sa.Column('page_id', sa.Integer(), nullable=False),
        sa.Column('section_type', sa.String(50), nullable=False),
        sa.Column('section_key', sa.String(100), nullable=False),
        # Display settings
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        # Content (JSON format)
        sa.Column('content_json', sa.Text(), nullable=True),
        # Styling overrides
        sa.Column('custom_css_class', sa.String(200), nullable=True),
        sa.Column('background_color', sa.String(50), nullable=True),
        sa.Column('background_image_url', sa.String(500), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['page_id'], ['landing_pages.id'], ondelete='CASCADE')
    )
    op.create_index('ix_section_page', 'landing_page_sections', ['page_id', 'section_key'])
    op.create_index('ix_section_order', 'landing_page_sections', ['page_id', 'display_order'])

    # ==========================================================================
    # Landing Page Section Contents (Translations)
    # ==========================================================================
    op.create_table(
        'landing_page_section_contents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        # Section reference
        sa.Column('section_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(10), nullable=False),
        # Content fields (JSON)
        sa.Column('content_data', sa.Text(), nullable=False),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['section_id'], ['landing_page_sections.id'], ondelete='CASCADE')
    )
    op.create_index(
        'ix_section_content_lang',
        'landing_page_section_contents',
        ['section_id', 'language'],
        unique=True
    )

    # ==========================================================================
    # Landing Page Translations (Page-level SEO)
    # ==========================================================================
    op.create_table(
        'landing_page_translations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        # Page reference
        sa.Column('page_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(10), nullable=False),
        # SEO translations
        sa.Column('meta_title', sa.String(200), nullable=True),
        sa.Column('meta_description', sa.String(500), nullable=True),
        sa.Column('meta_keywords', sa.String(500), nullable=True),
        sa.Column('og_image_url', sa.String(500), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['page_id'], ['landing_pages.id'], ondelete='CASCADE')
    )
    op.create_index(
        'ix_page_translation_lang',
        'landing_page_translations',
        ['page_id', 'language'],
        unique=True
    )


def downgrade() -> None:
    # Drop tables in reverse order (respect foreign keys)
    op.drop_index('ix_page_translation_lang', table_name='landing_page_translations')
    op.drop_table('landing_page_translations')

    op.drop_index('ix_section_content_lang', table_name='landing_page_section_contents')
    op.drop_table('landing_page_section_contents')

    op.drop_index('ix_section_order', table_name='landing_page_sections')
    op.drop_index('ix_section_page', table_name='landing_page_sections')
    op.drop_table('landing_page_sections')

    op.drop_index('ix_landing_page_status', table_name='landing_pages')
    op.drop_index('ix_landing_page_slug', table_name='landing_pages')
    op.drop_table('landing_pages')

    op.drop_table('landing_page_templates')
