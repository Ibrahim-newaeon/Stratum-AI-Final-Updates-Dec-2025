"""Catch-up migration for model <-> migration schema drift (issue #343).

The embed-widget models (``app/models/embed_widgets.py``) and
``CRMSyncLog`` (``app/models/crm.py``) were added to the codebase without
a corresponding migration, and ``ChangelogEntry.tenant_id`` /
``CMSAuthor.job_title`` / ``CMSAuthor.github_handle`` were added to
existing models the same way. Because ``app/models/__init__.py`` never
imported those modules, ``migrations/env.py``'s metadata was blind to
them and autogenerate could not flag the drift. Production databases
built purely via ``alembic upgrade head`` therefore lack:

Tables
    - embed_widgets
    - embed_tokens
    - embed_domain_whitelist
    - embed_widget_views
    - crm_sync_logs

Columns
    - changelog_entries.tenant_id (nullable, FK -> tenants.id)
    - cms_authors.job_title
    - cms_authors.github_handle

Some environments already have these objects (created manually or via
``Base.metadata.create_all`` in dev), so in online mode every operation
is guarded with inspector-based existence checks / IF EXISTS semantics:
re-running on a database that already has them is a no-op, not an error.

Locking behavior on the pre-existing tables: the FK on
``changelog_entries.tenant_id`` is added ``NOT VALID`` (no full-table
scan under ACCESS EXCLUSIVE) and validated afterwards in an autocommit
block (SHARE UPDATE EXCLUSIVE only), and its index is built with
``CREATE INDEX CONCURRENTLY``. The five new tables are created plainly
(they are empty).

Offline mode (``alembic upgrade head --sql``): inspectors cannot run
against a mock connection, so the full DDL plan is emitted unguarded and
with plain (non-concurrent) FK/index statements — offline output is for
review, not execution.

Migration 034 intended to enable RLS on the embed tables but its guarded
DO-blocks skipped them because the tables never existed at that point in
the chain. This migration re-applies the exact 034 policy pattern to the
five new tenant-scoped tables (idempotent: policies are dropped and
recreated).

The ``crm_provider`` enum type is reused from migration 013 (created
here idempotently for safety, never dropped on downgrade because 013
owns it).

Known residual drift (deliberately NOT touched here): the database has a
legacy ``cms_authors.title`` VARCHAR(100) column that the ``CMSAuthor``
model no longer maps (superseded by ``job_title``). Now that
``app/models/__init__.py`` registers the cms module, a naive
``alembic revision --autogenerate`` will propose dropping it — do not
accept that without confirming nothing still reads the column.
Likewise, ``app/models/audit_services.py`` remains unregistered and its
tables unmigrated until its own catch-up migration lands (issue #512).

Revision ID: 055_catchup_embed_crm_cms_drift
Revises: 054_add_action_confirmation_columns
Create Date: 2026-07-04 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import context, op

# revision identifiers, used by Alembic.
revision = "055_catchup_embed_crm_cms_drift"
down_revision = "054_add_action_confirmation_columns"
branch_labels = None
depends_on = None

# Tenant-scoped tables created by this migration (RLS pattern from 034)
NEW_TENANT_SCOPED_TABLES = [
    "embed_widgets",
    "embed_tokens",
    "embed_domain_whitelist",
    "embed_widget_views",
    "crm_sync_logs",
]

CHANGELOG_FK_NAME = "fk_changelog_entries_tenant_id_tenants"
CHANGELOG_INDEX_NAME = "ix_changelog_entries_tenant_id"


def _apply_rls(table: str) -> None:
    """Apply the tenant-isolation RLS policies (same pattern as 034)."""
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


def _ensure_crm_provider_enum() -> None:
    """Create the crm_provider enum if missing (normally exists from 013).

    Uses a DO-block instead of inspector/checkfirst so it also works in
    offline (--sql) mode, where catalog queries are impossible.
    """
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE crm_provider AS ENUM (
                'hubspot', 'salesforce', 'pipedrive', 'zoho'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """)


def _create_embed_widgets() -> None:
    op.create_table(
        "embed_widgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Widget identification
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # Widget type and configuration
        sa.Column("widget_type", sa.String(length=50), nullable=False),
        sa.Column("widget_size", sa.String(length=50), nullable=False),
        # Custom dimensions (for CUSTOM size)
        sa.Column("custom_width", sa.Integer(), nullable=True),
        sa.Column("custom_height", sa.Integer(), nullable=True),
        # Branding
        sa.Column("branding_level", sa.String(length=50), nullable=False),
        sa.Column("custom_logo_url", sa.String(length=512), nullable=True),
        sa.Column("custom_accent_color", sa.String(length=7), nullable=True),
        sa.Column("custom_background_color", sa.String(length=7), nullable=True),
        sa.Column("custom_text_color", sa.String(length=7), nullable=True),
        # Data source configuration
        sa.Column("data_scope", postgresql.JSONB(), nullable=False),
        sa.Column("refresh_interval_seconds", sa.Integer(), nullable=False),
        # Status
        sa.Column("is_active", sa.Boolean(), nullable=False),
        # Analytics
        sa.Column("total_views", sa.BigInteger(), nullable=False),
        sa.Column("total_unique_domains", sa.Integer(), nullable=False),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_embed_widgets_tenant_id_tenants",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_embed_widgets_tenant_id", "embed_widgets", ["tenant_id"])
    op.create_index("ix_embed_widgets_tenant", "embed_widgets", ["tenant_id"])
    op.create_index(
        "ix_embed_widgets_type", "embed_widgets", ["tenant_id", "widget_type"]
    )
    op.create_index(
        "ix_embed_widgets_active", "embed_widgets", ["tenant_id", "is_active"]
    )


def _create_embed_tokens() -> None:
    op.create_table(
        "embed_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("widget_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Token identification
        sa.Column("token_prefix", sa.String(length=8), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        # Domain binding
        sa.Column(
            "allowed_domains",
            postgresql.ARRAY(sa.String(length=255)),
            nullable=False,
        ),
        # Token lifecycle
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        # Refresh token (for rotation)
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=True),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=True),
        # Rate limiting
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False),
        sa.Column("current_minute_requests", sa.Integer(), nullable=False),
        sa.Column("current_minute_start", sa.DateTime(timezone=True), nullable=True),
        # Usage analytics
        sa.Column("total_requests", sa.BigInteger(), nullable=False),
        sa.Column("total_errors", sa.BigInteger(), nullable=False),
        # Security
        sa.Column("last_origin", sa.String(length=512), nullable=True),
        sa.Column("suspicious_activity", sa.Boolean(), nullable=False),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_embed_tokens_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["widget_id"],
            ["embed_widgets.id"],
            name="fk_embed_tokens_widget_id_embed_widgets",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_embed_tokens_tenant_id", "embed_tokens", ["tenant_id"])
    op.create_index("ix_embed_tokens_widget_id", "embed_tokens", ["widget_id"])
    op.create_index("ix_embed_tokens_tenant", "embed_tokens", ["tenant_id"])
    op.create_index("ix_embed_tokens_widget", "embed_tokens", ["widget_id"])
    op.create_index("ix_embed_tokens_prefix", "embed_tokens", ["token_prefix"])
    op.create_index("ix_embed_tokens_hash", "embed_tokens", ["token_hash"])
    op.create_index("ix_embed_tokens_status", "embed_tokens", ["status"])


def _create_embed_domain_whitelist() -> None:
    op.create_table(
        "embed_domain_whitelist",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        # Domain pattern (supports wildcards)
        sa.Column("domain_pattern", sa.String(length=255), nullable=False),
        # Verification status
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("verification_token", sa.String(length=64), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        # Status
        sa.Column("is_active", sa.Boolean(), nullable=False),
        # Notes
        sa.Column("description", sa.Text(), nullable=True),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_embed_domain_whitelist_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "domain_pattern",
            name="uq_embed_domain_whitelist_tenant_domain",
        ),
    )
    op.create_index(
        "ix_embed_domain_whitelist_tenant_id",
        "embed_domain_whitelist",
        ["tenant_id"],
    )
    op.create_index(
        "ix_embed_domain_whitelist_tenant", "embed_domain_whitelist", ["tenant_id"]
    )


def _create_embed_widget_views() -> None:
    # Anonymized view log: tenant_id / widget_id / token_id are plain
    # columns (no FKs) by design in the model.
    op.create_table(
        "embed_widget_views",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("widget_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_id", postgresql.UUID(as_uuid=True), nullable=False),
        # View details (anonymized)
        sa.Column("view_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origin_domain", sa.String(length=255), nullable=True),
        # Geo (country-level only)
        sa.Column("country_code", sa.String(length=2), nullable=True),
        # Device category
        sa.Column("device_type", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_embed_widget_views_tenant_id", "embed_widget_views", ["tenant_id"]
    )
    op.create_index(
        "ix_embed_widget_views_widget_id", "embed_widget_views", ["widget_id"]
    )
    op.create_index(
        "ix_embed_widget_views_token_id", "embed_widget_views", ["token_id"]
    )
    op.create_index(
        "ix_embed_widget_views_tenant_date",
        "embed_widget_views",
        ["tenant_id", "view_date"],
    )
    op.create_index(
        "ix_embed_widget_views_widget_date",
        "embed_widget_views",
        ["widget_id", "view_date"],
    )


def _create_crm_sync_logs() -> None:
    # Reuse the crm_provider enum created by migration 013.
    crm_provider = postgresql.ENUM(
        "hubspot",
        "salesforce",
        "pipedrive",
        "zoho",
        name="crm_provider",
        create_type=False,
    )
    op.create_table(
        "crm_sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("provider", crm_provider, nullable=False),
        # Sync details
        sa.Column("sync_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        # Record counts
        sa.Column("records_processed", sa.Integer(), nullable=False),
        sa.Column("records_created", sa.Integer(), nullable=False),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("records_failed", sa.Integer(), nullable=False),
        # Error tracking
        sa.Column("error_message", sa.Text(), nullable=True),
        # Flexible metadata for sync results
        sa.Column("sync_metadata", postgresql.JSONB(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_crm_sync_logs_tenant_id_tenants",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_crm_sync_logs_tenant_id", "crm_sync_logs", ["tenant_id"])
    op.create_index(
        "ix_crm_sync_log_tenant_provider", "crm_sync_logs", ["tenant_id", "provider"]
    )
    op.create_index(
        "ix_crm_sync_log_started", "crm_sync_logs", ["tenant_id", "started_at"]
    )


def _add_changelog_tenant_column() -> None:
    op.add_column(
        "changelog_entries",
        sa.Column("tenant_id", sa.Integer(), nullable=True),
    )


def _add_cms_author_columns(add_job_title: bool, add_github_handle: bool) -> None:
    if add_job_title:
        op.add_column(
            "cms_authors",
            sa.Column("job_title", sa.String(length=100), nullable=True),
        )
    if add_github_handle:
        op.add_column(
            "cms_authors",
            sa.Column("github_handle", sa.String(length=50), nullable=True),
        )


def _upgrade_offline() -> None:
    """Emit the full, unguarded DDL plan for --sql review mode.

    Inspector-based existence checks are impossible against a mock
    connection, and CONCURRENTLY / autocommit blocks make no sense in a
    reviewed script, so plain equivalents are emitted.
    """
    _create_embed_widgets()
    _create_embed_tokens()
    _create_embed_domain_whitelist()
    _create_embed_widget_views()
    _create_crm_sync_logs()

    _add_changelog_tenant_column()
    op.create_foreign_key(
        CHANGELOG_FK_NAME,
        "changelog_entries",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(CHANGELOG_INDEX_NAME, "changelog_entries", ["tenant_id"])
    _add_cms_author_columns(add_job_title=True, add_github_handle=True)


def _upgrade_online() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # ==========================================================================
    # Missing tables (skip any that already exist, e.g. via create_all)
    # ==========================================================================
    if "embed_widgets" not in existing_tables:
        _create_embed_widgets()
    if "embed_tokens" not in existing_tables:
        _create_embed_tokens()
    if "embed_domain_whitelist" not in existing_tables:
        _create_embed_domain_whitelist()
    if "embed_widget_views" not in existing_tables:
        _create_embed_widget_views()
    if "crm_sync_logs" not in existing_tables:
        _create_crm_sync_logs()

    # ==========================================================================
    # Missing columns on existing tables
    # ==========================================================================
    changelog_cols = {c["name"] for c in inspector.get_columns("changelog_entries")}
    if "tenant_id" not in changelog_cols:
        _add_changelog_tenant_column()

    # FK guard: match by name OR by constrained column set, so a
    # manually-created FK under a different name is not duplicated.
    has_tenant_fk = any(
        fk["name"] == CHANGELOG_FK_NAME or fk["constrained_columns"] == ["tenant_id"]
        for fk in inspector.get_foreign_keys("changelog_entries")
    )
    if not has_tenant_fk:
        # NOT VALID skips the full-table scan under ACCESS EXCLUSIVE; the
        # explicit VALIDATE below re-checks existing rows under SHARE
        # UPDATE EXCLUSIVE (outside the migration transaction), which
        # does not block reads/writes.
        op.execute(
            f"ALTER TABLE changelog_entries "
            f"ADD CONSTRAINT {CHANGELOG_FK_NAME} "
            f"FOREIGN KEY (tenant_id) REFERENCES tenants (id) "
            f"ON DELETE CASCADE NOT VALID"
        )
        with op.get_context().autocommit_block():
            op.execute(
                f"ALTER TABLE changelog_entries "
                f"VALIDATE CONSTRAINT {CHANGELOG_FK_NAME}"
            )

    # CONCURRENTLY cannot run inside a transaction -> autocommit block.
    # IF NOT EXISTS makes it a no-op when the index (or a manual
    # equivalent under this name) already exists.
    with op.get_context().autocommit_block():
        op.execute(
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {CHANGELOG_INDEX_NAME} "
            f"ON changelog_entries (tenant_id)"
        )

    cms_author_cols = {c["name"] for c in inspector.get_columns("cms_authors")}
    _add_cms_author_columns(
        add_job_title="job_title" not in cms_author_cols,
        add_github_handle="github_handle" not in cms_author_cols,
    )


def upgrade() -> None:
    # Enum types (idempotent; crm_provider normally exists from 013)
    _ensure_crm_provider_enum()

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
    """Refuse to downgrade if the objects being dropped contain data.

    Destructive-refusal contract: downgrade() drops five tables and three
    columns. If ANY of the five tables contains at least one row, or any
    of the three columns contains a non-NULL value, this raises
    RuntimeError naming the offending objects and nothing is dropped.
    Manual intervention (back up / clear the data, then re-run) is
    required — data is never destroyed silently. Empty objects are
    dropped as usual.
    """
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    non_empty: list[str] = []

    for table in NEW_TENANT_SCOPED_TABLES:
        if table in existing_tables:
            has_rows = bind.execute(
                sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")
            ).scalar()
            if has_rows:
                non_empty.append(f"table {table} is non-empty")

    column_checks = [
        ("changelog_entries", "tenant_id"),
        ("cms_authors", "job_title"),
        ("cms_authors", "github_handle"),
    ]
    for table, column in column_checks:
        if table not in existing_tables:
            continue
        cols = {c["name"] for c in inspector.get_columns(table)}
        if column not in cols:
            continue
        has_values = bind.execute(
            sa.text(f"SELECT EXISTS (SELECT 1 FROM {table} WHERE {column} IS NOT NULL)")
        ).scalar()
        if has_values:
            non_empty.append(f"column {table}.{column} has non-null values")

    if non_empty:
        raise RuntimeError(
            "Refusing to downgrade 055_catchup_embed_crm_cms_drift: it would "
            "destroy data. Offending objects: "
            + "; ".join(non_empty)
            + ". Back up / clear these objects manually, then re-run the "
            "downgrade. Nothing has been dropped."
        )


def downgrade() -> None:
    """Drop exactly what upgrade() added — unless that would lose data.

    Destructive-refusal contract (online mode): before dropping anything,
    every target table is checked for rows and every target column for
    non-NULL values. If any contain data, a RuntimeError is raised naming
    them and the downgrade aborts with the schema untouched; the operator
    must back up or clear the data manually first. IF EXISTS semantics
    keep the downgrade clean in environments where upgrade skipped
    creation.

    Offline (--sql) mode cannot query row counts, so the emitted script
    contains the plain drops WITHOUT the data-loss guard — review before
    executing.
    """
    if not context.is_offline_mode():
        _assert_no_data_loss(op.get_bind())

    # Remove RLS policies first (guarded, mirrors 034 downgrade)
    for table in NEW_TENANT_SCOPED_TABLES:
        _remove_rls(table)

    # Drop tables (children before parents; IF EXISTS so environments where
    # upgrade skipped creation still downgrade cleanly)
    op.execute("DROP TABLE IF EXISTS embed_tokens")
    op.execute("DROP TABLE IF EXISTS embed_widget_views")
    op.execute("DROP TABLE IF EXISTS embed_domain_whitelist")
    op.execute("DROP TABLE IF EXISTS embed_widgets")
    op.execute("DROP TABLE IF EXISTS crm_sync_logs")

    # NOTE: the crm_provider enum type is owned by migration 013 and is
    # intentionally NOT dropped here.

    # Remove added columns (index on tenant_id is dropped with the column)
    op.execute(
        f"ALTER TABLE changelog_entries DROP CONSTRAINT IF EXISTS {CHANGELOG_FK_NAME}"
    )
    op.execute(f"DROP INDEX IF EXISTS {CHANGELOG_INDEX_NAME}")
    op.execute("ALTER TABLE changelog_entries DROP COLUMN IF EXISTS tenant_id")
    op.execute("ALTER TABLE cms_authors DROP COLUMN IF EXISTS job_title")
    op.execute("ALTER TABLE cms_authors DROP COLUMN IF EXISTS github_handle")
