#!/bin/sh
set -e

echo "=== Railway Container Starting ==="
echo "PORT=${PORT:-not set}"
echo "PWD=$(pwd)"
echo "Python: $(python --version 2>&1)"

# Run migrations if DATABASE_URL_SYNC is available
if [ -n "$DATABASE_URL_SYNC" ]; then
    echo "Running alembic version fix..."
    python fix_alembic_version.py || echo "Alembic fix skipped"
    echo "Running migrations..."
    timeout 120 python -m alembic upgrade head 2>&1 || echo "Migration warning (non-fatal)"
fi

# Seed superadmin if SEED_SUPERADMIN=true
if [ "$SEED_SUPERADMIN" = "true" ]; then
    echo "Seeding superadmin user..."
    SUPERADMIN_PASSWORD="${SUPERADMIN_PASSWORD:-StratumAdmin2026!}" python scripts/seed_superadmin.py 2>&1 || echo "Seed warning (non-fatal)"
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
" 2>&1 || echo "CMS role fix skipped"
fi

echo "Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --log-level info
