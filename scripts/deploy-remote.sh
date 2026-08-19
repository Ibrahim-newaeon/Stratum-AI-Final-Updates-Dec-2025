#!/usr/bin/env bash
# =============================================================================
# Stratum AI - remote deploy, run on the server by the GitHub Actions key
# =============================================================================
# Invoked by /opt/stratum/deploy-forced-command.sh, which has already fast-
# forwarded the checkout to origin/main. This script is therefore the version
# that was just deployed, which is deliberate: the deploy steps are reviewed in
# the same PR as the code they ship.
#
# Usage: deploy-remote.sh <staging|prod>
#
# The database container is built rather than pulled (Apache AGE and pgvector
# in one image), so a change to backend/Dockerfile.postgres recreates it. That
# is downtime, not a rolling update, which is why prod takes a dump first.
set -euo pipefail

TARGET="${1:-}"

case "$TARGET" in
  staging)
    DIR=/opt/stratum-staging
    COMPOSE_FILES="-f docker-compose.staging.yml -f docker-compose.staging.local.yml"
    API_CONTAINER=stratum_staging_api
    HEALTH_URL="http://127.0.0.1:8000/health"
    ;;
  prod)
    DIR=/opt/stratum
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.hetzner.yml -f docker-compose.observability.yml"
    API_CONTAINER=stratum_api
    HEALTH_URL="http://127.0.0.1:8000/health"
    ;;
  *)
    echo "usage: $0 <staging|prod>" >&2
    exit 2
    ;;
esac

cd "$DIR"
echo "==> deploying $TARGET from $(git rev-parse --short HEAD) ($DIR)"

# ---------------------------------------------------------------------------
# Back up before anything can migrate. Restoring is a manual decision, but not
# having the option is not.
# ---------------------------------------------------------------------------
if [ "$TARGET" = "prod" ]; then
  mkdir -p /opt/stratum-dumps
  DUMP="/opt/stratum-dumps/prod-$(date -u +%Y%m%d-%H%M%S).sql.gz"
  echo "==> dumping database to $DUMP"
  docker exec stratum_db sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' | gzip >"$DUMP"
  gzip -t "$DUMP"
  echo "==> dump ok ($(du -h "$DUMP" | cut -f1))"
  # Keep the last 20; a 26MB database compresses to well under a megabyte, but
  # unbounded growth on a 150GB disk is still someone's future incident.
  # shellcheck disable=SC2012  # names are generated above, always prod-<ts>.sql.gz
  ls -1t /opt/stratum-dumps/prod-*.sql.gz | tail -n +21 | xargs -r rm --
fi

# ---------------------------------------------------------------------------
# Build, then start. Migrations run from the api container's own command, so
# `up -d` is what applies them.
# ---------------------------------------------------------------------------
echo "==> building"
# shellcheck disable=SC2086
docker compose $COMPOSE_FILES build

echo "==> starting"
# shellcheck disable=SC2086
docker compose $COMPOSE_FILES up -d

# ---------------------------------------------------------------------------
# Verify. A deploy that returns 0 without checking is a deploy that reports
# success while the api crash-loops on a bad migration.
# ---------------------------------------------------------------------------
echo "==> waiting for $API_CONTAINER to answer $HEALTH_URL"
for attempt in $(seq 1 40); do
  if docker exec "$API_CONTAINER" sh -lc "curl -fsS $HEALTH_URL" >/dev/null 2>&1; then
    echo "==> healthy after ${attempt} attempt(s)"
    echo "==> alembic: $(docker exec "$API_CONTAINER" sh -lc 'cd /app && alembic current 2>/dev/null | tail -1')"
    echo "==> deployed $TARGET at $(git rev-parse --short HEAD)"
    exit 0
  fi
  sleep 5
done

echo "!! $API_CONTAINER did not become healthy" >&2
# shellcheck disable=SC2086
docker compose $COMPOSE_FILES logs --tail 60 api >&2 || true
exit 1
