#!/bin/sh
set -e

echo "=== Railway Container Starting ==="
echo "PORT=${PORT:-not set}"
echo "PWD=$(pwd)"
echo "Python: $(python --version 2>&1)"

# When a command is passed (docker-compose worker/scheduler/flower services,
# or a Railway service with a custom start command), run it instead of the
# API server. DB wait, migrations, casts, and seeds are the api service's
# job — worker containers must not race it on schema changes.
if [ "$#" -gt 0 ]; then
    echo "Command override: $*"
    exec "$@"
fi

# Derive DATABASE_URL_SYNC from DATABASE_URL if not set (Railway only injects DATABASE_URL)
if [ -z "$DATABASE_URL_SYNC" ] && [ -n "$DATABASE_URL" ]; then
    DATABASE_URL_SYNC=$(echo "$DATABASE_URL" | sed 's/postgresql+asyncpg/postgresql/g')
    export DATABASE_URL_SYNC
    echo "Derived DATABASE_URL_SYNC from DATABASE_URL"
fi

# Wait for the database hostname to resolve. Railway's internal DNS sometimes
# isn't ready in the first 1-2 seconds of container start; without this wait,
# fix_alembic_version.py was hitting "Temporary failure in name resolution"
# and silently skipping the version-column widening step.
if [ -n "$DATABASE_URL_SYNC" ]; then
    DB_HOST=$(python - <<'PY'
import os, urllib.parse
url = os.environ.get("DATABASE_URL_SYNC", "")
try:
    parsed = urllib.parse.urlparse(url)
    print(parsed.hostname or "")
except Exception:
    print("")
PY
)
    if [ -n "$DB_HOST" ]; then
        for i in 1 2 3 4 5 6 7 8 9 10; do
            if getent hosts "$DB_HOST" >/dev/null 2>&1; then
                echo "DB host $DB_HOST resolved (attempt $i)"
                break
            fi
            echo "Waiting for DB host $DB_HOST to resolve (attempt $i/10)..."
            sleep 1
        done
    fi
fi

# Database bootstrap (migrations, enum casts, role backfill, seeds) runs under
# a Postgres advisory lock so that when the API is scaled to multiple replicas
# they serialize instead of racing `alembic upgrade head` on boot [INF-011].
# The lock holder runs release.sh; the others block, then run it as an
# idempotent no-op. See scripts/with_pg_lock.py and release.sh.
if [ -n "$DATABASE_URL_SYNC" ]; then
    echo "Running release-phase DB bootstrap under advisory lock..."
    python scripts/with_pg_lock.py sh release.sh
fi

echo "Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
    --workers "${UVICORN_WORKERS:-1}" --log-level info
