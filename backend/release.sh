#!/bin/sh
# Release-phase database bootstrap [INF-011]: migrations, varchar→enum casts,
# superadmin role backfill, and optional seeds. Extracted from start.sh so the
# whole block runs under a single Postgres advisory lock
# (scripts/with_pg_lock.py). That serializes concurrent API replicas — before
# this, every replica ran `alembic upgrade head` at once on boot, racing the
# alembic_version row and the DDL/UPDATE statements below.
#
# Safe to run repeatedly and concurrently: alembic upgrade is a no-op at head,
# the cast/role steps check for existence first, and the seeds are idempotent.
# Assumes DATABASE_URL_SYNC is exported by the caller (start.sh).
set -e

# Run migrations
echo "Running alembic version fix..."
python fix_alembic_version.py || echo "Alembic fix skipped"
echo "Running migrations..."
timeout 120 python -m alembic upgrade head

# Seed superadmin if SEED_SUPERADMIN=true
if [ "$SEED_SUPERADMIN" = "true" ]; then
    echo "Seeding superadmin user..."
    if [ -z "$SUPERADMIN_PASSWORD" ]; then
        echo "ERROR: SUPERADMIN_PASSWORD is required when SEED_SUPERADMIN=true"
        exit 1
    fi
    python scripts/seed_superadmin.py
fi

# Create implicit casts from varchar to PostgreSQL ENUM types
# (asyncpg + SQLAlchemy StrEnumType sends varchar values to PG ENUM columns)
echo "Creating varchar-to-enum implicit casts..."
python -c "
import sqlalchemy, os
engine = sqlalchemy.create_engine(os.environ['DATABASE_URL_SYNC'])
with engine.connect() as conn:
    # Discover all enum types in public schema
    result = conn.execute(sqlalchemy.text('''
        SELECT t.typname
        FROM pg_type t
        JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typtype = 'e' AND n.nspname = 'public'
    '''))
    enum_types = [row[0] for row in result]
    created = 0
    for enum_name in enum_types:
        # Check if cast already exists
        exists = conn.execute(sqlalchemy.text('''
            SELECT 1 FROM pg_cast c
            JOIN pg_type src ON c.castsource = src.oid
            JOIN pg_type tgt ON c.casttarget = tgt.oid
            WHERE src.typname = 'varchar' AND tgt.typname = :ename
        '''), {'ename': enum_name}).fetchone()
        if not exists:
            conn.execute(sqlalchemy.text(
                f'CREATE CAST (varchar AS \"{enum_name}\") WITH INOUT AS IMPLICIT'
            ))
            created += 1
    conn.commit()
    print(f'Found {len(enum_types)} enum types, created {created} new casts')
" || { echo "Enum cast creation failed"; exit 1; }

# Ensure all superadmin users have cms_role set
echo "Ensuring superadmin CMS roles..."
python -c "
import sqlalchemy, os
engine = sqlalchemy.create_engine(os.environ['DATABASE_URL_SYNC'])
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text(
        \"UPDATE users SET cms_role = 'super_admin' WHERE role = 'superadmin' AND (cms_role IS NULL OR cms_role = '') AND is_deleted = false\"
    ))
    conn.commit()
    print(f'Updated {result.rowcount} superadmin(s) with cms_role')
" || { echo "CMS role fix failed"; exit 1; }

# Seed CMS content pages (docs articles + marketing pages) when SEED_CMS_PAGES=true.
# Runs after migrations so cms_pages exists. Idempotent — existing pages are
# skipped — so it is safe to leave enabled. Non-fatal: a seed hiccup must never
# block the app from starting.
if [ "$SEED_CMS_PAGES" = "true" ]; then
    echo "Seeding CMS docs pages..."
    python scripts/seed_docs_pages.py || echo "Docs pages seed skipped/failed (non-fatal)"
    echo "Seeding CMS marketing pages..."
    python scripts/seed_marketing_pages.py || echo "Marketing pages seed skipped/failed (non-fatal)"
fi

echo "Release-phase DB bootstrap complete."
