# =============================================================================
# Stratum AI - RLS Coverage Gaps Migration
# =============================================================================
"""
Add Row-Level Security (RLS) policies to tables that were missed in the
initial RLS migration (032). Also fixes table name mismatches.

Revision ID: 034_add_rls_coverage_gaps
Revises: 033_add_mfa_fields
Create Date: 2026-01-20
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = "034_add_rls_coverage_gaps"
down_revision = "033_add_mfa_fields"
branch_labels = None
depends_on = None

# Tables that were MISSED in migration 032 (only those with tenant_id column)
MISSING_TENANT_SCOPED_TABLES = [
    # Attribution - data-driven attribution tables
    "attribution_snapshots",
    "channel_interactions",
    "trained_attribution_models",
    "model_training_runs",
    # Autopilot - additional tables
    "tenant_enforcement_rules",
    "pending_confirmation_tokens",
    # Trust Layer - additional tables
    "signal_health_history",
    "trust_gate_audit_log",
    # CAPI Delivery - all tables
    "capi_delivery_logs",
    "capi_dead_letter_queue",
    "capi_event_dedupe",
    "capi_delivery_daily_stats",
    # Audit Services - tables WITH tenant_id
    "emq_measurements",
    "offline_conversion_batches",
    "offline_conversions",
    "model_experiments",
    # Note: experiment_predictions does NOT have tenant_id (uses FK to model_experiments)
    "conversion_latencies",
    "conversion_latency_stats",
    "creatives",
    "creative_performance",
    "creative_fatigue_alerts",
    "budget_reallocation_plans",
    # Note: budget_reallocation_changes does NOT have tenant_id (uses FK to budget_reallocation_plans)
    "audience_records",
    "audience_overlaps",
    "customer_ltv_predictions",
    "ltv_cohort_analyses",
    "model_retraining_jobs",
    # Reporting - additional tables
    "report_deliveries",
    "delivery_channel_configs",
    # CRM - additional tables
    "touchpoints",
    "daily_pipeline_metrics",
    "crm_writeback_configs",
    "crm_writeback_syncs",
    # Onboarding
    "tenant_onboarding",
    # Embed Widgets
    "embed_widgets",
    "embed_tokens",
    "embed_domain_whitelist",
    "embed_widget_views",
    # Pacing - additional tables
    "pacing_summaries",
    # Profit - additional tables
    "margin_rules",
    "profit_roas_reports",
    "cogs_uploads",
    # Audience Sync - additional tables
    "audience_sync_credentials",
]

# Tables with wrong names in migration 032 (need to fix singular vs plural)
TABLE_NAME_FIXES = [
    # RLS was applied to wrong name (plural) - apply to correct name (singular)
    ("tenant_platform_connections", "tenant_platform_connection"),
    ("tenant_ad_accounts", "tenant_ad_account"),
    ("campaign_drafts", "campaign_draft"),
    ("campaign_publish_logs", "campaign_publish_log"),
    ("product_catalogs", "product_catalog"),
]


def upgrade() -> None:
    """
    Enable Row-Level Security on all missed tenant-scoped tables
    and fix table name mismatches.
    """

    # First, apply RLS to all missing tables
    for table in MISSING_TENANT_SCOPED_TABLES:
        op.execute(f"""
            DO $$
            BEGIN
                -- Check if table exists AND has tenant_id column
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = '{table}' AND column_name = 'tenant_id'
                ) THEN
                    -- Enable RLS
                    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

                    -- Force RLS even for table owner (important for security)
                    ALTER TABLE {table} FORCE ROW LEVEL SECURITY;

                    -- Drop existing policies if any
                    DROP POLICY IF EXISTS tenant_isolation_policy ON {table};
                    DROP POLICY IF EXISTS tenant_insert_policy ON {table};

                    -- Policy: Users can only access their tenant's data
                    CREATE POLICY tenant_isolation_policy ON {table}
                        FOR ALL
                        USING (tenant_id = current_tenant_id() OR is_superadmin());

                    -- Policy for INSERT: Auto-set tenant_id
                    CREATE POLICY tenant_insert_policy ON {table}
                        FOR INSERT
                        WITH CHECK (tenant_id = current_tenant_id() OR is_superadmin());

                    RAISE NOTICE 'RLS enabled for table: {table}';
                ELSE
                    RAISE NOTICE 'Table {table} does not exist or has no tenant_id, skipping RLS';
                END IF;
            END $$;
        """)

    # Fix table name mismatches - apply RLS to correct (singular) names
    for wrong_name, correct_name in TABLE_NAME_FIXES:
        op.execute(f"""
            DO $$
            BEGIN
                -- Check if the correct table exists AND has tenant_id column
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = '{correct_name}' AND column_name = 'tenant_id'
                ) THEN
                    -- Enable RLS on correct table
                    ALTER TABLE {correct_name} ENABLE ROW LEVEL SECURITY;
                    ALTER TABLE {correct_name} FORCE ROW LEVEL SECURITY;

                    -- Drop existing policies if any
                    DROP POLICY IF EXISTS tenant_isolation_policy ON {correct_name};
                    DROP POLICY IF EXISTS tenant_insert_policy ON {correct_name};

                    -- Create policies
                    CREATE POLICY tenant_isolation_policy ON {correct_name}
                        FOR ALL
                        USING (tenant_id = current_tenant_id() OR is_superadmin());

                    CREATE POLICY tenant_insert_policy ON {correct_name}
                        FOR INSERT
                        WITH CHECK (tenant_id = current_tenant_id() OR is_superadmin());

                    RAISE NOTICE 'RLS enabled for correct table: {correct_name} (was {wrong_name})';
                ELSE
                    RAISE NOTICE 'Table {correct_name} does not exist or has no tenant_id, skipping RLS';
                END IF;
            END $$;
        """)


def downgrade() -> None:
    """Remove RLS policies from the tables added in this migration."""

    # Disable RLS on all missing tables
    for table in MISSING_TENANT_SCOPED_TABLES:
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = '{table}'
                ) THEN
                    DROP POLICY IF EXISTS tenant_isolation_policy ON {table};
                    DROP POLICY IF EXISTS tenant_insert_policy ON {table};
                    ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
                    ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
                END IF;
            END $$;
        """)

    # Disable RLS on fixed table names
    for wrong_name, correct_name in TABLE_NAME_FIXES:
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = '{correct_name}'
                ) THEN
                    DROP POLICY IF EXISTS tenant_isolation_policy ON {correct_name};
                    DROP POLICY IF EXISTS tenant_insert_policy ON {correct_name};
                    ALTER TABLE {correct_name} DISABLE ROW LEVEL SECURITY;
                    ALTER TABLE {correct_name} NO FORCE ROW LEVEL SECURITY;
                END IF;
            END $$;
        """)
