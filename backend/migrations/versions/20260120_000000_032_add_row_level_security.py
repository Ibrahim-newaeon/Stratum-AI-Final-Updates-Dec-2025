# =============================================================================
# Stratum AI - PostgreSQL Row-Level Security Migration
# =============================================================================
"""
Add Row-Level Security (RLS) policies to all tenant-scoped tables.
This provides database-level enforcement of multi-tenancy, preventing
data leaks even if application-level filtering is bypassed.

Revision ID: 032_add_row_level_security
Revises: 031_cdp_audience_sync
Create Date: 2026-01-20
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = "032_add_row_level_security"
down_revision = "031_cdp_audience_sync"
branch_labels = None
depends_on = None

# Tables that have tenant_id and need RLS
TENANT_SCOPED_TABLES = [
    # Core models
    "users",
    "campaigns",
    "creative_assets",
    "rules",
    "competitor_benchmarks",
    "audit_logs",
    # Trust layer
    "fact_signal_health_daily",
    "fact_attribution_variance_daily",
    "fact_actions_queue",
    # Campaign builder
    "tenant_platform_connections",
    "tenant_ad_accounts",
    "campaign_drafts",
    "campaign_publish_logs",
    # CRM
    "crm_connections",
    "crm_contacts",
    "crm_deals",
    "crm_sync_logs",
    # Pacing & Forecasting
    "targets",
    "daily_kpis",
    "pacing_alerts",
    "forecasts",
    # Profit
    "product_catalogs",
    "product_margins",
    "daily_profit_metrics",
    # Attribution
    "daily_attributed_revenue",
    "conversion_paths",
    # Reporting
    "report_templates",
    "scheduled_reports",
    "report_executions",
    # Autopilot
    "tenant_enforcement_settings",
    "enforcement_audit_logs",
    # CDP
    "cdp_sources",
    "cdp_profiles",
    "cdp_profile_identifiers",
    "cdp_events",
    "cdp_consents",
    "cdp_webhooks",
    "cdp_identity_links",
    "cdp_profile_merges",
    "cdp_canonical_identities",
    "cdp_segments",
    "cdp_segment_memberships",
    "cdp_computed_traits",
    "cdp_funnels",
    "cdp_funnel_entries",
    # Audience Sync
    "platform_audiences",
    "audience_sync_jobs",
]


def upgrade() -> None:
    """
    Enable Row-Level Security on all tenant-scoped tables.

    RLS ensures that even with direct database access, users can only
    see data belonging to their tenant_id (set via session variable).
    """

    # Create a function to get the current tenant_id from session
    op.execute("""
        CREATE OR REPLACE FUNCTION current_tenant_id()
        RETURNS INTEGER AS $$
        BEGIN
            -- Get tenant_id from session variable, default to 0 (no access)
            RETURN COALESCE(
                NULLIF(current_setting('app.tenant_id', true), '')::INTEGER,
                0
            );
        EXCEPTION WHEN OTHERS THEN
            RETURN 0;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    # Create a function to check if user is superadmin (bypasses RLS)
    op.execute("""
        CREATE OR REPLACE FUNCTION is_superadmin()
        RETURNS BOOLEAN AS $$
        BEGIN
            RETURN COALESCE(
                current_setting('app.is_superadmin', true)::BOOLEAN,
                false
            );
        EXCEPTION WHEN OTHERS THEN
            RETURN false;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    # Enable RLS and create policies for each tenant-scoped table
    for table in TENANT_SCOPED_TABLES:
        # Check if table exists before applying RLS
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = '{table}'
                ) THEN
                    -- Enable RLS
                    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

                    -- Force RLS even for table owner (important for security)
                    ALTER TABLE {table} FORCE ROW LEVEL SECURITY;

                    -- Drop existing policies if any
                    DROP POLICY IF EXISTS tenant_isolation_policy ON {table};
                    DROP POLICY IF EXISTS superadmin_bypass_policy ON {table};

                    -- Policy: Users can only access their tenant's data
                    CREATE POLICY tenant_isolation_policy ON {table}
                        FOR ALL
                        USING (tenant_id = current_tenant_id() OR is_superadmin());

                    -- Policy for INSERT: Auto-set tenant_id
                    DROP POLICY IF EXISTS tenant_insert_policy ON {table};
                    CREATE POLICY tenant_insert_policy ON {table}
                        FOR INSERT
                        WITH CHECK (tenant_id = current_tenant_id() OR is_superadmin());

                    RAISE NOTICE 'RLS enabled for table: {table}';
                ELSE
                    RAISE NOTICE 'Table {table} does not exist, skipping RLS';
                END IF;
            END $$;
        """)

    # Create helper function to set tenant context (called by middleware)
    op.execute("""
        CREATE OR REPLACE FUNCTION set_tenant_context(
            p_tenant_id INTEGER,
            p_is_superadmin BOOLEAN DEFAULT false
        ) RETURNS VOID AS $$
        BEGIN
            PERFORM set_config('app.tenant_id', p_tenant_id::TEXT, false);
            PERFORM set_config('app.is_superadmin', p_is_superadmin::TEXT, false);
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create a trigger function to auto-set tenant_id on insert
    op.execute("""
        CREATE OR REPLACE FUNCTION set_tenant_id_on_insert()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Only set if not already set and we have a tenant context
            IF NEW.tenant_id IS NULL AND current_tenant_id() > 0 THEN
                NEW.tenant_id := current_tenant_id();
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Add audit logging for RLS bypass attempts
    op.execute("""
        CREATE TABLE IF NOT EXISTS rls_audit_log (
            id SERIAL PRIMARY KEY,
            event_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            table_name TEXT NOT NULL,
            operation TEXT NOT NULL,
            tenant_id INTEGER,
            user_id INTEGER,
            was_superadmin BOOLEAN DEFAULT false,
            details JSONB DEFAULT '{}'::JSONB
        );

        CREATE INDEX IF NOT EXISTS ix_rls_audit_log_time
            ON rls_audit_log(event_time);
        CREATE INDEX IF NOT EXISTS ix_rls_audit_log_tenant
            ON rls_audit_log(tenant_id);
    """)


def downgrade() -> None:
    """Remove RLS policies and functions."""

    # Disable RLS on all tables
    for table in TENANT_SCOPED_TABLES:
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = '{table}'
                ) THEN
                    DROP POLICY IF EXISTS tenant_isolation_policy ON {table};
                    DROP POLICY IF EXISTS superadmin_bypass_policy ON {table};
                    DROP POLICY IF EXISTS tenant_insert_policy ON {table};
                    ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
                    ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
                END IF;
            END $$;
        """)

    # Drop helper functions
    op.execute("DROP FUNCTION IF EXISTS set_tenant_context(INTEGER, BOOLEAN);")
    op.execute("DROP FUNCTION IF EXISTS set_tenant_id_on_insert();")
    op.execute("DROP FUNCTION IF EXISTS is_superadmin();")
    op.execute("DROP FUNCTION IF EXISTS current_tenant_id();")

    # Drop audit table
    op.execute("DROP TABLE IF EXISTS rls_audit_log;")
