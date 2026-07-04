"""Catch-up migration for the audit-services model <-> migration drift (issue #512).

Every model in ``app/models/audit_services.py`` (the audit-recommended
services: EMQ measurements, offline conversions, model A/B testing,
conversion latency, creative performance, competitor benchmarks, budget
reallocation, audience insights, LTV predictions, model retraining) was
added to the codebase without a corresponding migration, and the module
was never registered in ``app/models/__init__.py`` — so autogenerate was
blind to it (same failure mode as migration 055 / issue #343).
Production databases built purely via ``alembic upgrade head`` therefore
lack all 18 tables:

    emq_measurements            offline_conversion_batches
    offline_conversions         model_experiments
    experiment_predictions      conversion_latencies
    conversion_latency_stats    creatives
    creative_performance        creative_fatigue_alerts
    competitor_benchmark_audits budget_reallocation_plans
    budget_reallocation_changes audience_records
    audience_overlaps           customer_ltv_predictions
    ltv_cohort_analyses         model_retraining_jobs

Migration 034 intended to enable RLS on 15 of these tables but its
guarded DO-blocks silently skipped them because the tables never existed
at that point in the chain. This migration re-applies the exact 034
policy pattern to every tenant-scoped table (idempotent: policies are
dropped and recreated). Two deviations from 034's list, both documented:

- ``competitor_benchmark_audits`` HAS a ``tenant_id`` column but was
  missing from 034's list entirely — RLS is applied here anyway, per the
  platform rule that every tenant-scoped table gets the policy pair.
- ``model_retraining_jobs.tenant_id`` is nullable (NULL = global model).
  034 listed it, so the policy pair is applied as intended; note that
  under FORCE RLS the NULL-tenant (global) rows are only visible to
  superadmin sessions.

``experiment_predictions`` and ``budget_reallocation_changes`` have no
``tenant_id`` (tenancy flows through their parent FK) and get no RLS,
matching 034's explicit notes.

Enum columns: the five ``StrEnumType`` columns are created as native
PostgreSQL enums (``emq_status``, ``conversion_upload_status``,
``experiment_status``, ``reallocation_status``, ``customer_segment``).
``StrEnumType.bind_expression`` CASTs bind parameters to the PG enum
type, and a VARCHAR column cannot be compared against that cast
(``operator does not exist: character varying = emq_status``) — native
enum columns are required for the ORM to work, same as
``crm_sync_logs.provider`` in migration 055. The types are created
idempotently via DO-blocks (works in offline mode too). They are owned
by this migration and used by no other table, so downgrade drops them
(``DROP TYPE IF EXISTS``) after dropping the tables — unlike 055's
``crm_provider``, which is shared with migration 013 and must survive.

All 18 tables are new (empty), so plain ``op.create_table`` with inline
FKs is lock-safe — no NOT VALID / VALIDATE dance is needed (that is only
required when adding FKs to existing, populated tables, as 055 did for
``changelog_entries``).

Some environments already have some of these objects (created manually
or via ``Base.metadata.create_all`` in dev), so in online mode every
create is guarded with a single inspector snapshot: re-running on a
database that already has them is a no-op, not an error, and RLS is
(re)applied even to tables that pre-existed without policies.

Offline mode (``alembic upgrade head --sql``): inspectors cannot run
against a mock connection, so the full DDL plan is emitted unguarded —
offline output is for review, not execution. Offline downgrade likewise
emits the plain drops WITHOUT the data-loss guard — review before
executing.

Model note (issue #512 step 0): the long-standing "'metadata' column
name conflicts with SQLAlchemy" exclusion comment was stale. The model
maps the attribute ``Creative.creative_metadata`` onto the DB column
``"metadata"`` (``Column("metadata", JSONB)``), which is the supported
pattern — no rename was needed, and this migration creates the column
under its real name ``metadata``.

Revision ID: 056_catchup_audit_services_drift
Revises: 055_catchup_embed_crm_cms_drift
Create Date: 2026-07-04 12:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import context, op

# revision identifiers, used by Alembic.
revision = "056_catchup_audit_services_drift"
down_revision = "055_catchup_embed_crm_cms_drift"
branch_labels = None
depends_on = None

# Tenant-scoped tables created by this migration (RLS pattern from 034).
# 034 listed all of these except competitor_benchmark_audits, which it
# missed despite the table having tenant_id — included here on purpose.
NEW_TENANT_SCOPED_TABLES = [
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
    "competitor_benchmark_audits",  # missing from 034's list; has tenant_id
    "budget_reallocation_plans",
    # Note: budget_reallocation_changes does NOT have tenant_id (uses FK to budget_reallocation_plans)
    "audience_records",
    "audience_overlaps",
    "customer_ltv_predictions",
    "ltv_cohort_analyses",
    "model_retraining_jobs",  # tenant_id nullable (NULL = global model)
]

# Every table this migration creates, in child-before-parent drop order.
ALL_TABLES_DROP_ORDER = [
    "experiment_predictions",  # -> model_experiments
    "offline_conversions",  # -> offline_conversion_batches
    "creative_performance",  # -> creatives
    "creative_fatigue_alerts",  # -> creatives
    "budget_reallocation_changes",  # -> budget_reallocation_plans
    "audience_overlaps",  # -> audience_records
    "emq_measurements",
    "offline_conversion_batches",
    "model_experiments",
    "conversion_latencies",
    "conversion_latency_stats",
    "creatives",
    "competitor_benchmark_audits",
    "budget_reallocation_plans",
    "audience_records",
    "customer_ltv_predictions",
    "ltv_cohort_analyses",
    "model_retraining_jobs",
]

# Enum types owned by this migration (name -> values). Used by no other
# migration's tables, so downgrade may drop them.
OWNED_ENUMS: dict[str, list[str]] = {
    "emq_status": ["pending", "calculated", "failed"],
    "conversion_upload_status": [
        "pending",
        "processing",
        "completed",
        "partial",
        "failed",
    ],
    "experiment_status": ["draft", "running", "paused", "completed", "cancelled"],
    "reallocation_status": [
        "proposed",
        "approved",
        "executing",
        "completed",
        "rolled_back",
        "rejected",
    ],
    "customer_segment": ["vip", "high_value", "medium_value", "low_value", "at_risk"],
}


def _pg_enum(name: str) -> postgresql.ENUM:
    """Reference an enum type created by _ensure_enums (never inline-created)."""
    return postgresql.ENUM(*OWNED_ENUMS[name], name=name, create_type=False)


def _ensure_enums() -> None:
    """Create the five enum types if missing.

    Uses DO-blocks instead of inspector/checkfirst so this also works in
    offline (--sql) mode, where catalog queries are impossible, and is a
    no-op when a type already exists (e.g. created manually in dev).
    """
    for name, values in OWNED_ENUMS.items():
        quoted = ", ".join(f"'{v}'" for v in values)
        op.execute(f"""
            DO $$
            BEGIN
                CREATE TYPE {name} AS ENUM ({quoted});
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """)


def _apply_rls(table: str) -> None:
    """Apply the tenant-isolation RLS policies (same pattern as 034/055)."""
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
                RAISE NOTICE 'Table {table} missing tenant_id, skipping RLS';
            END IF;
        END $$;
        """)


def _remove_rls(table: str) -> None:
    """Remove the RLS policies added by this migration (034 pattern)."""
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


# =============================================================================
# Table creators (faithful to app/models/audit_services.py; all Python-side
# defaults in the models stay Python-side — no server defaults)
# =============================================================================


def _create_emq_measurements() -> None:
    op.create_table(
        "emq_measurements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Measurement details
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("pixel_id", sa.String(length=255), nullable=False),
        sa.Column("measurement_date", sa.Date(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        # EMQ scores (0-10 scale)
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("parameter_quality", sa.Float(), nullable=True),
        sa.Column("deduplication_quality", sa.Float(), nullable=True),
        sa.Column("event_coverage", sa.Float(), nullable=True),
        # Event counts
        sa.Column("events_received", sa.Integer(), nullable=False),
        sa.Column("events_matched", sa.Integer(), nullable=False),
        sa.Column("events_attributed", sa.Integer(), nullable=False),
        # Match rates
        sa.Column("email_match_rate", sa.Float(), nullable=True),
        sa.Column("phone_match_rate", sa.Float(), nullable=True),
        sa.Column("combined_match_rate", sa.Float(), nullable=True),
        # Status
        sa.Column("status", _pg_enum("emq_status"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Raw response / recommendations
        sa.Column("raw_response", postgresql.JSONB(), nullable=True),
        sa.Column("recommendations", postgresql.JSONB(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_emq_measurements_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "platform",
            "pixel_id",
            "measurement_date",
            "event_type",
            name="uq_emq_measurement",
        ),
    )
    op.create_index("ix_emq_measurements_tenant_id", "emq_measurements", ["tenant_id"])
    op.create_index(
        "ix_emq_tenant_date", "emq_measurements", ["tenant_id", "measurement_date"]
    )
    op.create_index(
        "ix_emq_platform", "emq_measurements", ["tenant_id", "platform", "pixel_id"]
    )


def _create_offline_conversion_batches() -> None:
    op.create_table(
        "offline_conversion_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Batch details
        sa.Column("batch_name", sa.String(length=255), nullable=True),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("upload_type", sa.String(length=50), nullable=False),
        # Counts
        sa.Column("total_records", sa.Integer(), nullable=False),
        sa.Column("successful_records", sa.Integer(), nullable=False),
        sa.Column("failed_records", sa.Integer(), nullable=False),
        sa.Column("duplicate_records", sa.Integer(), nullable=False),
        # Status
        sa.Column("status", _pg_enum("conversion_upload_status"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", postgresql.JSONB(), nullable=True),
        # Platform response
        sa.Column("platform_batch_id", sa.String(length=255), nullable=True),
        sa.Column("platform_response", postgresql.JSONB(), nullable=True),
        # File info
        sa.Column("source_file", sa.String(length=500), nullable=True),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        # Timestamps
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        # Created by
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_offline_conversion_batches_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_offline_conversion_batches_created_by_user_id_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_offline_conversion_batches_tenant_id",
        "offline_conversion_batches",
        ["tenant_id"],
    )
    op.create_index(
        "ix_offline_conversion_batches_created_by_user_id",
        "offline_conversion_batches",
        ["created_by_user_id"],
    )
    op.create_index(
        "ix_offline_batch_tenant",
        "offline_conversion_batches",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_offline_batch_status",
        "offline_conversion_batches",
        ["tenant_id", "status"],
    )


def _create_offline_conversions() -> None:
    op.create_table(
        "offline_conversions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Conversion details
        sa.Column("event_name", sa.String(length=100), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value_cents", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        # Identifiers (hashed)
        sa.Column("email_hash", sa.String(length=64), nullable=True),
        sa.Column("phone_hash", sa.String(length=64), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("click_id", sa.String(length=255), nullable=True),
        # Platform info
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("platform_event_id", sa.String(length=255), nullable=True),
        # Upload status
        sa.Column("uploaded", sa.Boolean(), nullable=False),
        sa.Column("upload_attempts", sa.Integer(), nullable=False),
        sa.Column("last_upload_error", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_offline_conversions_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["offline_conversion_batches.id"],
            name="fk_offline_conversions_batch_id_offline_conversion_batches",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_offline_conversions_tenant_id", "offline_conversions", ["tenant_id"]
    )
    op.create_index(
        "ix_offline_conversions_batch_id", "offline_conversions", ["batch_id"]
    )
    op.create_index(
        "ix_offline_conv_tenant", "offline_conversions", ["tenant_id", "event_time"]
    )
    op.create_index("ix_offline_conv_batch", "offline_conversions", ["batch_id"])
    op.create_index(
        "ix_offline_conv_uploaded", "offline_conversions", ["tenant_id", "uploaded"]
    )


def _create_model_experiments() -> None:
    op.create_table(
        "model_experiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Experiment details
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        # Variants
        sa.Column("champion_version", sa.String(length=50), nullable=False),
        sa.Column("challenger_version", sa.String(length=50), nullable=False),
        # Traffic split (0-1, percentage going to challenger)
        sa.Column("traffic_split", sa.Float(), nullable=False),
        # Status
        sa.Column("status", _pg_enum("experiment_status"), nullable=False),
        # Configuration
        sa.Column("min_samples", sa.Integer(), nullable=False),
        sa.Column("significance_threshold", sa.Float(), nullable=False),
        sa.Column("primary_metric", sa.String(length=50), nullable=False),
        # Results
        sa.Column("champion_predictions", sa.Integer(), nullable=False),
        sa.Column("challenger_predictions", sa.Integer(), nullable=False),
        sa.Column("champion_metrics", postgresql.JSONB(), nullable=True),
        sa.Column("challenger_metrics", postgresql.JSONB(), nullable=True),
        sa.Column("winner", sa.String(length=20), nullable=True),
        # Statistical results
        sa.Column("p_value", sa.Float(), nullable=True),
        sa.Column("effect_size", sa.Float(), nullable=True),
        sa.Column("confidence_interval", postgresql.JSONB(), nullable=True),
        # Timestamps
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        # Created by
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_model_experiments_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_model_experiments_created_by_user_id_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_model_experiments_tenant_id", "model_experiments", ["tenant_id"]
    )
    op.create_index(
        "ix_model_experiments_created_by_user_id",
        "model_experiments",
        ["created_by_user_id"],
    )
    op.create_index("ix_model_exp_tenant", "model_experiments", ["tenant_id"])
    op.create_index("ix_model_exp_status", "model_experiments", ["tenant_id", "status"])
    op.create_index(
        "ix_model_exp_model", "model_experiments", ["tenant_id", "model_name"]
    )


def _create_experiment_predictions() -> None:
    # No tenant_id by design: tenancy flows through model_experiments.
    op.create_table(
        "experiment_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Prediction details
        sa.Column("entity_id", sa.String(length=255), nullable=False),
        sa.Column("variant", sa.String(length=20), nullable=False),
        sa.Column("predicted_value", sa.Float(), nullable=False),
        sa.Column("actual_value", sa.Float(), nullable=True),
        # Features used
        sa.Column("features", postgresql.JSONB(), nullable=True),
        # Timestamps
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["model_experiments.id"],
            name="fk_experiment_predictions_experiment_id_model_experiments",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_experiment_predictions_experiment_id",
        "experiment_predictions",
        ["experiment_id"],
    )
    op.create_index(
        "ix_exp_pred_experiment", "experiment_predictions", ["experiment_id"]
    )
    op.create_index(
        "ix_exp_pred_variant", "experiment_predictions", ["experiment_id", "variant"]
    )


def _create_conversion_latencies() -> None:
    op.create_table(
        "conversion_latencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Event details
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=True),
        # Latency measurement (milliseconds)
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        # Context
        sa.Column("campaign_id", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=True),
        # Timestamps
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_conversion_latencies_tenant_id_tenants",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_conversion_latencies_tenant_id", "conversion_latencies", ["tenant_id"]
    )
    op.create_index(
        "ix_conv_latency_tenant", "conversion_latencies", ["tenant_id", "event_time"]
    )
    op.create_index(
        "ix_conv_latency_platform",
        "conversion_latencies",
        ["tenant_id", "platform", "event_type"],
    )


def _create_conversion_latency_stats() -> None:
    op.create_table(
        "conversion_latency_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Aggregation period
        sa.Column("period_date", sa.Date(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        # Statistics (milliseconds)
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("avg_latency_ms", sa.Float(), nullable=True),
        sa.Column("median_latency_ms", sa.Float(), nullable=True),
        sa.Column("p95_latency_ms", sa.Float(), nullable=True),
        sa.Column("p99_latency_ms", sa.Float(), nullable=True),
        sa.Column("min_latency_ms", sa.Integer(), nullable=True),
        sa.Column("max_latency_ms", sa.Integer(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_conversion_latency_stats_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "period_date",
            "platform",
            "event_type",
            name="uq_latency_stats",
        ),
    )
    op.create_index(
        "ix_conversion_latency_stats_tenant_id",
        "conversion_latency_stats",
        ["tenant_id"],
    )
    op.create_index(
        "ix_latency_stats_tenant",
        "conversion_latency_stats",
        ["tenant_id", "period_date"],
    )


def _create_creatives() -> None:
    op.create_table(
        "creatives",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Creative details
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=True),
        sa.Column("creative_type", sa.String(length=50), nullable=True),
        # Asset info
        sa.Column("asset_url", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        # DB column is literally named "metadata"; the model maps it as
        # Creative.creative_metadata (SQLAlchemy reserves the attribute name)
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        # Status
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_creatives_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("tenant_id", "platform", "external_id", name="uq_creative"),
    )
    op.create_index("ix_creatives_tenant_id", "creatives", ["tenant_id"])
    op.create_index("ix_creative_tenant", "creatives", ["tenant_id"])
    op.create_index(
        "ix_creative_external", "creatives", ["tenant_id", "platform", "external_id"]
    )


def _create_creative_performance() -> None:
    op.create_table(
        "creative_performance",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("creative_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Period
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("campaign_id", sa.String(length=255), nullable=True),
        # Metrics
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("conversions", sa.Integer(), nullable=False),
        sa.Column("spend_cents", sa.BigInteger(), nullable=False),
        sa.Column("revenue_cents", sa.BigInteger(), nullable=False),
        # Calculated metrics
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("cvr", sa.Float(), nullable=True),
        sa.Column("cpc_cents", sa.Integer(), nullable=True),
        sa.Column("cpm_cents", sa.Integer(), nullable=True),
        sa.Column("roas", sa.Float(), nullable=True),
        # Engagement metrics
        sa.Column("video_views", sa.Integer(), nullable=False),
        sa.Column("video_completions", sa.Integer(), nullable=False),
        sa.Column("engagements", sa.Integer(), nullable=False),
        sa.Column("shares", sa.Integer(), nullable=False),
        # Fatigue indicators
        sa.Column("frequency", sa.Float(), nullable=True),
        sa.Column("reach", sa.Integer(), nullable=False),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["creative_id"],
            ["creatives.id"],
            name="fk_creative_performance_creative_id_creatives",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_creative_performance_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "creative_id", "date", "campaign_id", name="uq_creative_perf"
        ),
    )
    op.create_index(
        "ix_creative_performance_creative_id", "creative_performance", ["creative_id"]
    )
    op.create_index(
        "ix_creative_performance_tenant_id", "creative_performance", ["tenant_id"]
    )
    op.create_index(
        "ix_creative_perf_tenant", "creative_performance", ["tenant_id", "date"]
    )
    op.create_index(
        "ix_creative_perf_creative", "creative_performance", ["creative_id", "date"]
    )


def _create_creative_fatigue_alerts() -> None:
    op.create_table(
        "creative_fatigue_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("creative_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Alert details
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        # Metrics at alert time
        sa.Column("current_ctr", sa.Float(), nullable=True),
        sa.Column("baseline_ctr", sa.Float(), nullable=True),
        sa.Column("ctr_decline_percent", sa.Float(), nullable=True),
        sa.Column("current_frequency", sa.Float(), nullable=True),
        sa.Column("days_active", sa.Integer(), nullable=True),
        # Recommendations
        sa.Column("recommendation", sa.Text(), nullable=True),
        # Status
        sa.Column("is_acknowledged", sa.Boolean(), nullable=False),
        sa.Column("acknowledged_by_user_id", sa.Integer(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["creative_id"],
            ["creatives.id"],
            name="fk_creative_fatigue_alerts_creative_id_creatives",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_creative_fatigue_alerts_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by_user_id"],
            ["users.id"],
            name="fk_creative_fatigue_alerts_acknowledged_by_user_id_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_creative_fatigue_alerts_creative_id",
        "creative_fatigue_alerts",
        ["creative_id"],
    )
    op.create_index(
        "ix_creative_fatigue_alerts_tenant_id",
        "creative_fatigue_alerts",
        ["tenant_id"],
    )
    op.create_index(
        "ix_creative_fatigue_alerts_acknowledged_by_user_id",
        "creative_fatigue_alerts",
        ["acknowledged_by_user_id"],
    )
    op.create_index(
        "ix_fatigue_alert_tenant",
        "creative_fatigue_alerts",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_fatigue_alert_creative", "creative_fatigue_alerts", ["creative_id"]
    )


def _create_competitor_benchmark_audits() -> None:
    op.create_table(
        "competitor_benchmark_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Benchmark context
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("industry", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=50), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        # Your metrics
        sa.Column("your_metrics", postgresql.JSONB(), nullable=False),
        # Industry benchmarks
        sa.Column("industry_metrics", postgresql.JSONB(), nullable=False),
        # Percentile rankings
        sa.Column("percentile_rankings", postgresql.JSONB(), nullable=False),
        # Performance summary
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("metrics_above_median", sa.Integer(), nullable=False),
        sa.Column("metrics_below_median", sa.Integer(), nullable=False),
        # Recommendations
        sa.Column("recommendations", postgresql.JSONB(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_competitor_benchmark_audits_tenant_id_tenants",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_competitor_benchmark_audits_tenant_id",
        "competitor_benchmark_audits",
        ["tenant_id"],
    )
    op.create_index(
        "ix_benchmark_tenant", "competitor_benchmark_audits", ["tenant_id", "date"]
    )
    op.create_index(
        "ix_benchmark_industry",
        "competitor_benchmark_audits",
        ["tenant_id", "industry", "platform"],
    )


def _create_budget_reallocation_plans() -> None:
    op.create_table(
        "budget_reallocation_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Plan details
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("strategy", sa.String(length=50), nullable=False),
        # Configuration
        sa.Column("config", postgresql.JSONB(), nullable=False),
        # Budget summary
        sa.Column("total_current_budget_cents", sa.BigInteger(), nullable=False),
        sa.Column("total_new_budget_cents", sa.BigInteger(), nullable=False),
        sa.Column("campaigns_affected", sa.Integer(), nullable=False),
        # Expected impact
        sa.Column("projected_roas_change", sa.Float(), nullable=True),
        sa.Column("projected_spend_change", sa.Float(), nullable=True),
        sa.Column("projected_revenue_change", sa.Float(), nullable=True),
        # Status
        sa.Column("status", _pg_enum("reallocation_status"), nullable=False),
        # Approval
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        # Execution
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rollback_reason", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        # Created by
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_budget_reallocation_plans_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_user_id"],
            ["users.id"],
            name="fk_budget_reallocation_plans_approved_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_budget_reallocation_plans_created_by_user_id_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_budget_reallocation_plans_tenant_id",
        "budget_reallocation_plans",
        ["tenant_id"],
    )
    op.create_index(
        "ix_budget_reallocation_plans_approved_by_user_id",
        "budget_reallocation_plans",
        ["approved_by_user_id"],
    )
    op.create_index(
        "ix_budget_reallocation_plans_created_by_user_id",
        "budget_reallocation_plans",
        ["created_by_user_id"],
    )
    op.create_index(
        "ix_realloc_plan_tenant",
        "budget_reallocation_plans",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_realloc_plan_status",
        "budget_reallocation_plans",
        ["tenant_id", "status"],
    )


def _create_budget_reallocation_changes() -> None:
    # No tenant_id by design: tenancy flows through budget_reallocation_plans.
    op.create_table(
        "budget_reallocation_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Campaign details
        sa.Column("campaign_id", sa.String(length=255), nullable=False),
        sa.Column("campaign_name", sa.String(length=500), nullable=True),
        sa.Column("platform", sa.String(length=50), nullable=False),
        # Budget change
        sa.Column("current_budget_cents", sa.BigInteger(), nullable=False),
        sa.Column("new_budget_cents", sa.BigInteger(), nullable=False),
        sa.Column("change_percent", sa.Float(), nullable=False),
        # Rationale
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("performance_metrics", postgresql.JSONB(), nullable=True),
        # Execution status
        sa.Column("executed", sa.Boolean(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        # The convention-generated name exceeds PostgreSQL's 63-char limit;
        # this is the exact deterministic truncation SQLAlchemy emits for
        # it (so create_all-built dev schemas carry the identical name).
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["budget_reallocation_plans.id"],
            name="fk_budget_reallocation_changes_plan_id_budget_reallocat_f6f9",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_budget_reallocation_changes_plan_id",
        "budget_reallocation_changes",
        ["plan_id"],
    )
    op.create_index(
        "ix_realloc_change_plan", "budget_reallocation_changes", ["plan_id"]
    )


def _create_audience_records() -> None:
    op.create_table(
        "audience_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Audience details
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("audience_type", sa.String(length=50), nullable=False),
        sa.Column("size", sa.Integer(), nullable=True),
        # Configuration
        sa.Column("lookalike_percent", sa.Float(), nullable=True),
        sa.Column("source_audience_id", sa.String(length=255), nullable=True),
        # Quality scores
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("expansion_potential", sa.String(length=20), nullable=True),
        # Performance
        sa.Column("current_metrics", postgresql.JSONB(), nullable=True),
        sa.Column("historical_metrics", postgresql.JSONB(), nullable=True),
        # LTV data
        sa.Column("avg_ltv", sa.Float(), nullable=True),
        # Status
        sa.Column("is_active", sa.Boolean(), nullable=False),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_audience_records_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("tenant_id", "platform", "external_id", name="uq_audience"),
    )
    op.create_index("ix_audience_records_tenant_id", "audience_records", ["tenant_id"])
    op.create_index("ix_audience_tenant", "audience_records", ["tenant_id"])
    op.create_index(
        "ix_audience_external",
        "audience_records",
        ["tenant_id", "platform", "external_id"],
    )


def _create_audience_overlaps() -> None:
    op.create_table(
        "audience_overlaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("audience_id_1", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("audience_id_2", postgresql.UUID(as_uuid=True), nullable=False),
        # Overlap metrics
        sa.Column("overlap_percent", sa.Float(), nullable=False),
        sa.Column("overlap_size", sa.Integer(), nullable=True),
        # Analysis date
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_audience_overlaps_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["audience_id_1"],
            ["audience_records.id"],
            name="fk_audience_overlaps_audience_id_1_audience_records",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["audience_id_2"],
            ["audience_records.id"],
            name="fk_audience_overlaps_audience_id_2_audience_records",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_audience_overlaps_tenant_id", "audience_overlaps", ["tenant_id"]
    )
    op.create_index(
        "ix_audience_overlaps_audience_id_1", "audience_overlaps", ["audience_id_1"]
    )
    op.create_index(
        "ix_audience_overlaps_audience_id_2", "audience_overlaps", ["audience_id_2"]
    )
    op.create_index("ix_overlap_tenant", "audience_overlaps", ["tenant_id"])
    op.create_index(
        "ix_overlap_audiences", "audience_overlaps", ["audience_id_1", "audience_id_2"]
    )


def _create_customer_ltv_predictions() -> None:
    op.create_table(
        "customer_ltv_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Customer identifier
        sa.Column("customer_id", sa.String(length=255), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        # Acquisition info
        sa.Column("acquisition_date", sa.Date(), nullable=True),
        sa.Column("acquisition_channel", sa.String(length=100), nullable=True),
        # Behavior metrics (at prediction time)
        sa.Column("total_orders", sa.Integer(), nullable=False),
        sa.Column("total_revenue_cents", sa.BigInteger(), nullable=False),
        sa.Column("avg_order_value_cents", sa.Integer(), nullable=True),
        sa.Column("days_since_last_order", sa.Integer(), nullable=True),
        # Predictions
        sa.Column("predicted_ltv_30d_cents", sa.BigInteger(), nullable=True),
        sa.Column("predicted_ltv_90d_cents", sa.BigInteger(), nullable=True),
        sa.Column("predicted_ltv_365d_cents", sa.BigInteger(), nullable=True),
        sa.Column("predicted_ltv_lifetime_cents", sa.BigInteger(), nullable=True),
        # Segment
        sa.Column("segment", _pg_enum("customer_segment"), nullable=True),
        # Risk
        sa.Column("churn_probability", sa.Float(), nullable=True),
        # Confidence
        sa.Column("confidence", sa.Float(), nullable=True),
        # Recommendation
        sa.Column("max_cac_cents", sa.Integer(), nullable=True),
        # Model info
        sa.Column("model_version", sa.String(length=50), nullable=True),
        # Timestamps
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_customer_ltv_predictions_tenant_id_tenants",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_customer_ltv_predictions_tenant_id",
        "customer_ltv_predictions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_ltv_pred_tenant",
        "customer_ltv_predictions",
        ["tenant_id", "predicted_at"],
    )
    op.create_index(
        "ix_ltv_pred_customer",
        "customer_ltv_predictions",
        ["tenant_id", "customer_id"],
    )
    op.create_index(
        "ix_ltv_pred_segment", "customer_ltv_predictions", ["tenant_id", "segment"]
    )


def _create_ltv_cohort_analyses() -> None:
    op.create_table(
        "ltv_cohort_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Cohort identifier (YYYY-MM)
        sa.Column("cohort_month", sa.String(length=7), nullable=False),
        # Cohort metrics
        sa.Column("customer_count", sa.Integer(), nullable=False),
        sa.Column("total_revenue_cents", sa.BigInteger(), nullable=False),
        sa.Column("avg_ltv_cents", sa.BigInteger(), nullable=True),
        sa.Column("median_ltv_cents", sa.BigInteger(), nullable=True),
        sa.Column("ltv_p90_cents", sa.BigInteger(), nullable=True),
        # Purchase metrics
        sa.Column("avg_orders", sa.Float(), nullable=True),
        sa.Column("avg_retention_days", sa.Float(), nullable=True),
        # Segment distribution
        sa.Column("segment_distribution", postgresql.JSONB(), nullable=True),
        # Analysis date
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_ltv_cohort_analyses_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("tenant_id", "cohort_month", name="uq_ltv_cohort"),
    )
    op.create_index(
        "ix_ltv_cohort_analyses_tenant_id", "ltv_cohort_analyses", ["tenant_id"]
    )
    op.create_index("ix_ltv_cohort_tenant", "ltv_cohort_analyses", ["tenant_id"])


def _create_model_retraining_jobs() -> None:
    op.create_table(
        "model_retraining_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        # Nullable: NULL means a global (non-tenant) model
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        # Job details
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("trigger_reason", sa.Text(), nullable=True),
        # Status (plain string in the model, not an enum)
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Training data
        sa.Column("training_start_date", sa.Date(), nullable=True),
        sa.Column("training_end_date", sa.Date(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=True),
        # Model info
        sa.Column("old_version", sa.String(length=50), nullable=True),
        sa.Column("new_version", sa.String(length=50), nullable=True),
        # Metrics
        sa.Column("old_metrics", postgresql.JSONB(), nullable=True),
        sa.Column("new_metrics", postgresql.JSONB(), nullable=True),
        sa.Column("improvement", postgresql.JSONB(), nullable=True),
        # Timing
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_model_retraining_jobs_tenant_id_tenants",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_retrain_job_tenant", "model_retraining_jobs", ["tenant_id", "created_at"]
    )
    op.create_index(
        "ix_retrain_job_model", "model_retraining_jobs", ["model_name", "created_at"]
    )
    op.create_index("ix_retrain_job_status", "model_retraining_jobs", ["status"])


# Parent-before-child creation order (FKs are inline).
_CREATORS = {
    "emq_measurements": _create_emq_measurements,
    "offline_conversion_batches": _create_offline_conversion_batches,
    "offline_conversions": _create_offline_conversions,
    "model_experiments": _create_model_experiments,
    "experiment_predictions": _create_experiment_predictions,
    "conversion_latencies": _create_conversion_latencies,
    "conversion_latency_stats": _create_conversion_latency_stats,
    "creatives": _create_creatives,
    "creative_performance": _create_creative_performance,
    "creative_fatigue_alerts": _create_creative_fatigue_alerts,
    "competitor_benchmark_audits": _create_competitor_benchmark_audits,
    "budget_reallocation_plans": _create_budget_reallocation_plans,
    "budget_reallocation_changes": _create_budget_reallocation_changes,
    "audience_records": _create_audience_records,
    "audience_overlaps": _create_audience_overlaps,
    "customer_ltv_predictions": _create_customer_ltv_predictions,
    "ltv_cohort_analyses": _create_ltv_cohort_analyses,
    "model_retraining_jobs": _create_model_retraining_jobs,
}


def _upgrade_offline() -> None:
    """Emit the full, unguarded DDL plan for --sql review mode.

    Inspector-based existence checks are impossible against a mock
    connection, so every table is created unconditionally — offline
    output is for review, not execution.
    """
    for creator in _CREATORS.values():
        creator()


def _upgrade_online() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # Skip any table that already exists (e.g. via create_all in dev or a
    # manual catch-up); single inspector snapshot, parent-before-child order.
    for table, creator in _CREATORS.items():
        if table not in existing_tables:
            creator()


def upgrade() -> None:
    # Enum types first (idempotent DO-blocks; offline-safe)
    _ensure_enums()

    if context.is_offline_mode():
        _upgrade_offline()
    else:
        _upgrade_online()

    # ==========================================================================
    # RLS policies (034 pattern; idempotent, applied even if the table
    # pre-existed without policies)
    # ==========================================================================
    for table in NEW_TENANT_SCOPED_TABLES:
        _apply_rls(table)


def _assert_no_data_loss(bind: sa.engine.Connection) -> None:
    """Refuse to downgrade if the tables being dropped contain data.

    Destructive-refusal contract: downgrade() drops all 18 audit-services
    tables. If ANY of them contains at least one row, this raises
    RuntimeError naming the offending tables and nothing is dropped.
    Manual intervention (back up / clear the data, then re-run) is
    required — data is never destroyed silently. Empty tables are dropped
    as usual.
    """
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    non_empty: list[str] = []

    for table in ALL_TABLES_DROP_ORDER:
        if table in existing_tables:
            has_rows = bind.execute(
                sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")
            ).scalar()
            if has_rows:
                non_empty.append(f"table {table} is non-empty")

    if non_empty:
        raise RuntimeError(
            "Refusing to downgrade 056_catchup_audit_services_drift: it would "
            "destroy data. Offending objects: "
            + "; ".join(non_empty)
            + ". Back up / clear these objects manually, then re-run the "
            "downgrade. Nothing has been dropped."
        )


def downgrade() -> None:
    """Drop exactly what upgrade() added — unless that would lose data.

    Destructive-refusal contract (online mode): before dropping anything,
    every target table is checked for rows. If any contain data, a
    RuntimeError is raised naming them and the downgrade aborts with the
    schema untouched; the operator must back up or clear the data
    manually first. IF EXISTS semantics keep the downgrade clean in
    environments where upgrade skipped creation.

    Offline (--sql) mode cannot query row counts, so the emitted script
    contains the plain drops WITHOUT the data-loss guard — review before
    executing.

    The five enum types are owned by this migration and used by no other
    table, so they ARE dropped (unlike shared types such as
    ``crm_provider``, owned by 013). DROP TYPE without CASCADE fails
    safely if some out-of-band object still depends on a type.
    """
    if not context.is_offline_mode():
        _assert_no_data_loss(op.get_bind())

    # Remove RLS policies first (guarded, mirrors 034/055 downgrade)
    for table in NEW_TENANT_SCOPED_TABLES:
        _remove_rls(table)

    # Drop tables (children before parents; IF EXISTS so environments where
    # upgrade skipped creation still downgrade cleanly)
    for table in ALL_TABLES_DROP_ORDER:
        op.execute(f"DROP TABLE IF EXISTS {table}")

    # Drop the enum types owned by this migration (no CASCADE on purpose)
    for enum_name in OWNED_ENUMS:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
