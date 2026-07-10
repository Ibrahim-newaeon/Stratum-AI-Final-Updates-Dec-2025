"""Add tenant_enforcement_settings.autopilot_frozen (emergency stop).

The true autopilot kill switch. When set, the apply-actions worker skips
approved actions and the approve/confirm endpoints refuse, so no automation
reaches a platform regardless of enforcement mode or signal health. This is
distinct from ``enforcement_enabled`` (a guardrails toggle whose OFF state
loosens control) and from the health-derived "frozen" trust-gate mode.

NOT NULL with a ``false`` server default: on PostgreSQL 11+ a constant
default is a metadata-only change (no table rewrite), and existing tenants
correctly default to not-frozen.

Revision ID: 059_add_autopilot_frozen
Revises: 058_add_whatsapp_to_delivery_channel_enum
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "059_add_autopilot_frozen"
down_revision = "058_add_whatsapp_to_delivery_channel_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_enforcement_settings",
        sa.Column(
            "autopilot_frozen",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("tenant_enforcement_settings", "autopilot_frozen")
