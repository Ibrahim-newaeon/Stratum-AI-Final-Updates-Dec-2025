#!/bin/sh
set -e

echo "=== Railway Container Starting ==="
echo "PORT=${PORT:-not set}"
echo "PWD=$(pwd)"
echo "Python: $(python --version 2>&1)"

# Derive DATABASE_URL_SYNC from DATABASE_URL if not set (Railway only injects DATABASE_URL)
if [ -z "$DATABASE_URL_SYNC" ] && [ -n "$DATABASE_URL" ]; then
    DATABASE_URL_SYNC=$(echo "$DATABASE_URL" | sed 's/postgresql+asyncpg/postgresql/g')
    export DATABASE_URL_SYNC
    echo "Derived DATABASE_URL_SYNC from DATABASE_URL"
fi

# Run migrations if DATABASE_URL_SYNC is available
if [ -n "$DATABASE_URL_SYNC" ]; then
    echo "Running alembic version fix..."
    python fix_alembic_version.py || echo "Alembic fix skipped"
    echo "Running migrations..."
    timeout 120 python -m alembic upgrade head
fi

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
if [ -n "$DATABASE_URL_SYNC" ]; then
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
fi

# Ensure all superadmin users have cms_role set
if [ -n "$DATABASE_URL_SYNC" ]; then
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
fi

echo "Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --log-level info
