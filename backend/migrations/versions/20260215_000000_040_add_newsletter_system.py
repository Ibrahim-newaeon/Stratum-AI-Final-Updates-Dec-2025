"""Add newsletter email campaign system.

Creates tables for newsletter templates, campaigns, and tracking events.
Adds newsletter subscription fields to landing_page_subscribers.

Revision ID: 040_add_newsletter_system
Revises: 039_add_client_entity_and_portal
Create Date: 2026-02-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "040_add_newsletter_system"
down_revision = "039_add_client_entity_and_portal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create newsletter tables and add subscriber fields."""

    # -----------------------------------------------------------------------
    # Newsletter Templates
    # -----------------------------------------------------------------------
    op.create_table(
        "newsletter_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False, server_default=""),
        sa.Column("preheader_text", sa.String(500), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("thumbnail_url", sa.String(1000), nullable=True),
        sa.Column("category", sa.String(20), nullable=False, server_default="promotional"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_nl_template_tenant", "newsletter_templates", ["tenant_id"])
    op.create_index("ix_nl_template_category", "newsletter_templates", ["category"])

    # -----------------------------------------------------------------------
    # Newsletter Campaigns
    # -----------------------------------------------------------------------
    op.create_table(
        "newsletter_campaigns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("preheader_text", sa.String(500), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("from_name", sa.String(255), nullable=True),
        sa.Column("from_email", sa.String(255), nullable=True),
        sa.Column("reply_to_email", sa.String(255), nullable=True),
        sa.Column(
            "audience_filters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("total_recipients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_delivered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_opened", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_clicked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_bounced", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_unsubscribed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["template_id"], ["newsletter_templates.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_nl_campaign_tenant", "newsletter_campaigns", ["tenant_id"])
    op.create_index("ix_nl_campaign_status", "newsletter_campaigns", ["status"])
    op.create_index(
        "ix_nl_campaign_scheduled", "newsletter_campaigns", ["status", "scheduled_at"]
    )

    # -----------------------------------------------------------------------
    # Newsletter Events (tracking)
    # -----------------------------------------------------------------------
    op.create_table(
        "newsletter_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("subscriber_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["newsletter_campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["subscriber_id"], ["landing_page_subscribers.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_nl_event_campaign", "newsletter_events", ["campaign_id", "event_type"]
    )
    op.create_index(
        "ix_nl_event_subscriber", "newsletter_events", ["subscriber_id", "event_type"]
    )
    op.create_index("ix_nl_event_created", "newsletter_events", ["created_at"])

    # -----------------------------------------------------------------------
    # Add newsletter fields to landing_page_subscribers
    # -----------------------------------------------------------------------
    op.add_column(
        "landing_page_subscribers",
        sa.Column(
            "subscribed_to_newsletter",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "landing_page_subscribers",
        sa.Column("unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "landing_page_subscribers",
        sa.Column(
            "newsletter_preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "landing_page_subscribers",
        sa.Column("last_email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "landing_page_subscribers",
        sa.Column("last_email_opened_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "landing_page_subscribers",
        sa.Column("email_send_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "landing_page_subscribers",
        sa.Column("email_open_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_subscriber_newsletter",
        "landing_page_subscribers",
        ["subscribed_to_newsletter"],
    )


def downgrade() -> None:
    """Reverse newsletter system migration."""

    # Remove subscriber fields
    op.drop_index("ix_subscriber_newsletter", table_name="landing_page_subscribers")
    op.drop_column("landing_page_subscribers", "email_open_count")
    op.drop_column("landing_page_subscribers", "email_send_count")
    op.drop_column("landing_page_subscribers", "last_email_opened_at")
    op.drop_column("landing_page_subscribers", "last_email_sent_at")
    op.drop_column("landing_page_subscribers", "newsletter_preferences")
    op.drop_column("landing_page_subscribers", "unsubscribed_at")
    op.drop_column("landing_page_subscribers", "subscribed_to_newsletter")

    # Drop tables (reverse order)
    op.drop_index("ix_nl_event_created", table_name="newsletter_events")
    op.drop_index("ix_nl_event_subscriber", table_name="newsletter_events")
    op.drop_index("ix_nl_event_campaign", table_name="newsletter_events")
    op.drop_table("newsletter_events")

    op.drop_index("ix_nl_campaign_scheduled", table_name="newsletter_campaigns")
    op.drop_index("ix_nl_campaign_status", table_name="newsletter_campaigns")
    op.drop_index("ix_nl_campaign_tenant", table_name="newsletter_campaigns")
    op.drop_table("newsletter_campaigns")

    op.drop_index("ix_nl_template_category", table_name="newsletter_templates")
    op.drop_index("ix_nl_template_tenant", table_name="newsletter_templates")
    op.drop_table("newsletter_templates")
