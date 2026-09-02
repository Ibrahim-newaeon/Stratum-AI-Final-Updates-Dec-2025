"""Add paddle_customer_id and paddle_subscription_id to tenants.

Stratum is gaining Paddle as a second payment gateway, selected at runtime by
``settings.payment_gateway``. The Paddle identifiers are added *alongside*
``stripe_customer_id`` rather than replacing it: the gateway is switchable, and
any tenant that ever billed through Stripe still needs its customer ID to
resolve historical invoices.

Production safety:

* Both columns are nullable adds with no default, which is metadata-only on
  PostgreSQL 11+ — no table rewrite and no long lock on existing traffic.
* The index on ``paddle_customer_id`` is created non-concurrently. That is a
  deliberate choice, not an oversight: ``tenants`` holds one row per customer
  workspace, so the ACCESS EXCLUSIVE lock is measured in milliseconds. Building
  it CONCURRENTLY would require running outside a transaction and give up this
  migration's atomicity for no practical gain at this table's size. If
  ``tenants`` ever grows to the point where this matters, switch to
  CONCURRENTLY and move it to its own migration.
* ``paddle_customer_id`` is indexed because the webhook handler falls back to
  looking a tenant up by it (see ``paddle_webhook._resolve_tenant``), which is
  on the hot path for every subscription event.
* ``paddle_subscription_id`` is not indexed — nothing queries by it; it is
  stored for support and reconciliation.

Revision ID: 067_add_paddle_billing_ids
Revises: 066_add_drip_enrollment
Create Date: 2026-09-02 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "067_add_paddle_billing_ids"
down_revision = "066_add_drip_enrollment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("paddle_customer_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("paddle_subscription_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_tenants_paddle_customer_id",
        "tenants",
        ["paddle_customer_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tenants_paddle_customer_id", table_name="tenants")
    op.drop_column("tenants", "paddle_subscription_id")
    op.drop_column("tenants", "paddle_customer_id")
