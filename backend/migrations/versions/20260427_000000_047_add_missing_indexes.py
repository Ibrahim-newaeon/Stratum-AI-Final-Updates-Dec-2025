# =============================================================================
# Stratum AI — Migration: Missing Indexes + Performance Fixes
# =============================================================================
"""
Add missing indexes on foreign key columns and frequently queried columns.
This resolves H1 (campaign endpoint timeout) and M2 (unindexed FKs).

Indexes added:
- campaigns: tenant_id + is_deleted, tenant_id + updated_at, tenant_id + name, external_id
- campaign_metrics: campaign_id, date (time-series queries)
- cdp_profiles: tenant_id + email (identity resolution lookups)
- audience_sync: tenant_id + segment_id, platform_audience_id
- trust_gate_evaluations: tenant_id + created_at (recent evaluations)
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = "047_add_missing_indexes"
down_revision = "e21f74be91a2"
branch_labels = None
depends_on = None


def _index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index already exists on the given table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT 1 FROM pg_indexes
            WHERE tablename = :table_name AND indexname = :index_name
            """
        ),
        {"table_name": table_name, "index_name": index_name},
    )
    return result.scalar() is not None


def _create_index_if_not_exists(
    index_name: str, table_name: str, columns: list[str]
) -> None:
    """Create an index only if it doesn't already exist."""
    if _index_exists(table_name, index_name):
        return
    op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Campaigns — list query optimization
    # -------------------------------------------------------------------------
    _create_index_if_not_exists(
        "ix_campaigns_tenant_deleted", "campaigns", ["tenant_id", "is_deleted"]
    )
    _create_index_if_not_exists(
        "ix_campaigns_tenant_updated", "campaigns", ["tenant_id", "updated_at"]
    )
    _create_index_if_not_exists(
        "ix_campaigns_name_search", "campaigns", ["tenant_id", "name"]
    )
    _create_index_if_not_exists(
        "ix_campaigns_external", "campaigns", ["external_id"]
    )

    # -------------------------------------------------------------------------
    # Campaign Metrics — time-series analytics
    # -------------------------------------------------------------------------
    _create_index_if_not_exists(
        "ix_campaign_metrics_campaign_date", "campaign_metrics", ["campaign_id", "date"]
    )
    _create_index_if_not_exists(
        "ix_campaign_metrics_tenant_date", "campaign_metrics", ["tenant_id", "date"]
    )

    # -------------------------------------------------------------------------
    # CDP Profiles — identity resolution lookups
    # -------------------------------------------------------------------------
    _create_index_if_not_exists(
        "ix_cdp_profiles_tenant_email", "cdp_profiles", ["tenant_id", "email"]
    )
    _create_index_if_not_exists(
        "ix_cdp_profiles_tenant_external", "cdp_profiles", ["tenant_id", "external_id"]
    )

    # -------------------------------------------------------------------------
    # Audience Sync — segment → platform lookups
    # -------------------------------------------------------------------------
    _create_index_if_not_exists(
        "ix_audience_sync_jobs_segment", "audience_sync_jobs", ["segment_id"]
    )
    _create_index_if_not_exists(
        "ix_audience_sync_jobs_tenant", "audience_sync_jobs", ["tenant_id"]
    )

    # -------------------------------------------------------------------------
    # Trust Gate Evaluations — recent evaluations dashboard
    # -------------------------------------------------------------------------
    _create_index_if_not_exists(
        "ix_trust_evaluations_tenant_created",
        "trust_gate_evaluations",
        ["tenant_id", "created_at"],
    )

    # -------------------------------------------------------------------------
    # Webhook Logs — delivery status lookups
    # -------------------------------------------------------------------------
    _create_index_if_not_exists(
        "ix_webhook_logs_webhook_status",
        "webhook_delivery_logs",
        ["webhook_id", "status"],
    )

    # -------------------------------------------------------------------------
    # Campaign Builder — draft lookups
    # -------------------------------------------------------------------------
    _create_index_if_not_exists(
        "ix_campaign_drafts_tenant_status", "campaign_drafts", ["tenant_id", "status"]
    )


def downgrade() -> None:
    # Drop all indexes in reverse order
    indexes_to_drop = [
        ("ix_campaign_drafts_tenant_status", "campaign_drafts"),
        ("ix_webhook_logs_webhook_status", "webhook_delivery_logs"),
        ("ix_trust_evaluations_tenant_created", "trust_gate_evaluations"),
        ("ix_audience_sync_jobs_tenant", "audience_sync_jobs"),
        ("ix_audience_sync_jobs_segment", "audience_sync_jobs"),
        ("ix_cdp_profiles_tenant_external", "cdp_profiles"),
        ("ix_cdp_profiles_tenant_email", "cdp_profiles"),
        ("ix_campaign_metrics_tenant_date", "campaign_metrics"),
        ("ix_campaign_metrics_campaign_date", "campaign_metrics"),
        ("ix_campaigns_external", "campaigns"),
        ("ix_campaigns_name_search", "campaigns"),
        ("ix_campaigns_tenant_updated", "campaigns"),
        ("ix_campaigns_tenant_deleted", "campaigns"),
    ]
    for idx_name, table in indexes_to_drop:
        if _index_exists(table, idx_name):
            op.drop_index(idx_name, table_name=table)
