# =============================================================================
# Stratum AI - Add whatsapp to delivery_channel enum
# =============================================================================
"""
Add 'whatsapp' value to the PostgreSQL delivery_channel enum type.

The Python ``DeliveryChannel`` enum includes ``WHATSAPP`` and
``DeliveryService.CHANNEL_HANDLERS`` registers ``WhatsAppDelivery``, but the
database enum created in migration 019 only listed email/slack/teams/webhook/s3.
As a result, persisting a ``report_deliveries`` row for the whatsapp channel
raised ``invalid input value for enum delivery_channel: "whatsapp"`` — so
whatsapp report delivery could never succeed. This closes that gap.

Revision ID: 058_add_whatsapp_to_delivery_channel_enum
Revises: 057_add_user_department
Create Date: 2026-07-09 00:00:00.000000
"""

from sqlalchemy import text

from alembic import op

# revision identifiers
revision = "058_add_whatsapp_to_delivery_channel_enum"
down_revision = "057_add_user_department"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Only add if it isn't already present.
    conn = op.get_bind()
    result = conn.execute(
        text(
            "SELECT 1 FROM pg_enum "
            "WHERE enumtypid = 'delivery_channel'::regtype "
            "AND enumlabel = 'whatsapp'"
        )
    )
    if not result.fetchone():
        # ALTER TYPE ... ADD VALUE cannot run inside a transaction in PG < 12.
        # In PG 12+ it can run inside a transaction with IF NOT EXISTS as long
        # as the new value isn't used in the same transaction. PG 16 in use.
        op.execute(
            "ALTER TYPE delivery_channel "
            "ADD VALUE IF NOT EXISTS 'whatsapp' AFTER 'teams'"
        )


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values.
    # The 'whatsapp' value will remain in the enum type.
    pass
