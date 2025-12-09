"""Add LinkedIn platform and WhatsApp models

Revision ID: 002
Revises: 001
Create Date: 2024-12-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Add LinkedIn to AdPlatform enum
    # =========================================================================
    op.execute("ALTER TYPE adplatform ADD VALUE 'linkedin'")

    # =========================================================================
    # Add NOTIFY_WHATSAPP to RuleAction enum (if not exists)
    # =========================================================================
    op.execute("ALTER TYPE ruleaction ADD VALUE 'notify_whatsapp'")

    # =========================================================================
    # Create WhatsApp-related enum types
    # =========================================================================
    op.execute("CREATE TYPE whatsappoptinstatus AS ENUM ('pending', 'opted_in', 'opted_out')")
    op.execute("CREATE TYPE whatsappmessagedirection AS ENUM ('outbound', 'inbound')")
    op.execute("CREATE TYPE whatsappmessagestatus AS ENUM ('pending', 'sent', 'delivered', 'read', 'failed')")
    op.execute("CREATE TYPE whatsapptemplatestatus AS ENUM ('pending', 'approved', 'rejected', 'paused')")
    op.execute("CREATE TYPE whatsapptemplatecategory AS ENUM ('MARKETING', 'UTILITY', 'AUTHENTICATION')")

    # =========================================================================
    # WhatsApp Contacts table
    # =========================================================================
    op.create_table(
        'whatsapp_contacts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        # Contact Info (E.164 format)
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('country_code', sa.String(length=5), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),

        # Verification
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verification_code', sa.String(length=6), nullable=True),
        sa.Column('verification_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),

        # Opt-in Status
        sa.Column('opt_in_status', postgresql.ENUM('pending', 'opted_in', 'opted_out', name='whatsappoptinstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('opt_in_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('opt_out_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('opt_in_method', sa.String(length=50), nullable=True),

        # WhatsApp Profile
        sa.Column('wa_id', sa.String(length=50), nullable=True),
        sa.Column('profile_name', sa.String(length=255), nullable=True),
        sa.Column('profile_picture_url', sa.String(length=500), nullable=True),

        # Preferences
        sa.Column('notification_types', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='["alerts", "reports", "digests"]'),
        sa.Column('quiet_hours', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{"enabled": false, "start": "22:00", "end": "08:00"}'),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'),
        sa.Column('language', sa.String(length=10), nullable=False, server_default='en'),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),

        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_whatsapp_contacts_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_whatsapp_contacts')
    )
    op.create_index('ix_wa_contacts_tenant_phone', 'whatsapp_contacts', ['tenant_id', 'phone_number'])
    op.create_index('ix_wa_contacts_user', 'whatsapp_contacts', ['user_id'])
    op.create_index('ix_wa_contacts_opt_in', 'whatsapp_contacts', ['tenant_id', 'opt_in_status'])

    # =========================================================================
    # WhatsApp Templates table
    # =========================================================================
    op.create_table(
        'whatsapp_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Template Info
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False, server_default='en'),
        sa.Column('category', postgresql.ENUM('MARKETING', 'UTILITY', 'AUTHENTICATION', name='whatsapptemplatecategory', create_type=False), nullable=False),

        # Template Content
        sa.Column('header_type', sa.String(length=20), nullable=True),
        sa.Column('header_content', sa.Text(), nullable=True),
        sa.Column('body_text', sa.Text(), nullable=False),
        sa.Column('footer_text', sa.String(length=60), nullable=True),

        # Variables/Parameters
        sa.Column('header_variables', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('body_variables', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),

        # Buttons
        sa.Column('buttons', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),

        # Meta Approval
        sa.Column('meta_template_id', sa.String(length=100), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'approved', 'rejected', 'paused', name='whatsapptemplatestatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),

        # Usage Tracking
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),

        sa.PrimaryKeyConstraint('id', name='pk_whatsapp_templates')
    )
    op.create_index('ix_wa_templates_tenant_status', 'whatsapp_templates', ['tenant_id', 'status'])
    op.create_index('ix_wa_templates_name', 'whatsapp_templates', ['tenant_id', 'name'])

    # =========================================================================
    # WhatsApp Messages table
    # =========================================================================
    op.create_table(
        'whatsapp_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=True),

        # Message Details
        sa.Column('direction', postgresql.ENUM('outbound', 'inbound', name='whatsappmessagedirection', create_type=False), nullable=False, server_default='outbound'),
        sa.Column('message_type', sa.String(length=20), nullable=False),

        # Content
        sa.Column('template_name', sa.String(length=100), nullable=True),
        sa.Column('template_variables', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('media_url', sa.String(length=500), nullable=True),
        sa.Column('media_type', sa.String(length=50), nullable=True),

        # WhatsApp API Response
        sa.Column('wamid', sa.String(length=100), nullable=True),
        sa.Column('recipient_wa_id', sa.String(length=50), nullable=True),

        # Status Tracking
        sa.Column('status', postgresql.ENUM('pending', 'sent', 'delivered', 'read', 'failed', name='whatsappmessagestatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('status_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),

        # Error Handling
        sa.Column('error_code', sa.String(length=20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),

        # Timing
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),

        sa.ForeignKeyConstraint(['contact_id'], ['whatsapp_contacts.id'], name='fk_whatsapp_messages_contact_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['whatsapp_templates.id'], name='fk_whatsapp_messages_template_id', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_whatsapp_messages')
    )
    op.create_index('ix_wa_messages_contact', 'whatsapp_messages', ['contact_id', 'created_at'])
    op.create_index('ix_wa_messages_status', 'whatsapp_messages', ['tenant_id', 'status'])
    op.create_index('ix_wa_messages_wamid', 'whatsapp_messages', ['wamid'])

    # =========================================================================
    # WhatsApp Conversations table
    # =========================================================================
    op.create_table(
        'whatsapp_conversations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('contact_id', sa.Integer(), nullable=False),

        # Conversation Window
        sa.Column('conversation_id', sa.String(length=100), nullable=True),
        sa.Column('origin_type', sa.String(length=20), nullable=False),

        # Pricing Category
        sa.Column('pricing_category', sa.String(length=30), nullable=True),

        # Window Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),

        # Stats
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),

        sa.ForeignKeyConstraint(['contact_id'], ['whatsapp_contacts.id'], name='fk_whatsapp_conversations_contact_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_whatsapp_conversations')
    )
    op.create_index('ix_wa_conversations_contact', 'whatsapp_conversations', ['contact_id'])
    op.create_index('ix_wa_conversations_active', 'whatsapp_conversations', ['tenant_id', 'is_active', 'expires_at'])


def downgrade() -> None:
    # Drop WhatsApp tables in reverse order
    op.drop_table('whatsapp_conversations')
    op.drop_table('whatsapp_messages')
    op.drop_table('whatsapp_templates')
    op.drop_table('whatsapp_contacts')

    # Drop WhatsApp enum types
    op.execute("DROP TYPE whatsapptemplatecategory")
    op.execute("DROP TYPE whatsapptemplatestatus")
    op.execute("DROP TYPE whatsappmessagestatus")
    op.execute("DROP TYPE whatsappmessagedirection")
    op.execute("DROP TYPE whatsappoptinstatus")

    # Note: Cannot easily remove enum values in PostgreSQL
    # The linkedin and notify_whatsapp enum values will remain
