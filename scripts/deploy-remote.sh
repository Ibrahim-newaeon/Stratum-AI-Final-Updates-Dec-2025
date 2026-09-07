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
    # Staging has no Cloudflare-fronted edge to check through.
    EDGE_HEALTH_HOST=""
    ;;
  prod)
    DIR=/opt/stratum
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.hetzner.yml -f docker-compose.observability.yml"
    API_CONTAINER=stratum_api
    HEALTH_URL="http://127.0.0.1:8000/health"
    EDGE_HEALTH_HOST="api.stratumai.app"
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
# A non-zero exit here is not decided yet. Services that wait on
# `service_healthy` make compose give up while the API is still starting
# normally -- which is how the first production deploy reported failure and
# left worker and scheduler in Created. The health loop below is the
# authority; anything still down is started again after it passes.
# shellcheck disable=SC2086
docker compose $COMPOSE_FILES up -d || echo "==> up -d returned non-zero; deferring to the health check"

# ---------------------------------------------------------------------------
# Verify. A deploy that returns 0 without checking is a deploy that reports
# success while the api crash-loops on a bad migration.
# ---------------------------------------------------------------------------
echo "==> waiting for $API_CONTAINER to answer $HEALTH_URL"
for attempt in $(seq 1 40); do
  if docker exec "$API_CONTAINER" sh -lc "curl -fsS $HEALTH_URL" >/dev/null 2>&1; then
    echo "==> healthy after ${attempt} attempt(s)"

    # Anything that gave up waiting on the API is started now that it is up.
    # Idempotent: services already running are left alone.
    echo "==> starting anything that was still waiting"
    # shellcheck disable=SC2086
    docker compose $COMPOSE_FILES up -d

    # shellcheck disable=SC2086
    not_running=$(docker compose $COMPOSE_FILES ps --status=created --status=exited --quiet | wc -l)
    if [ "$not_running" -ne 0 ]; then
      echo "!! $not_running service(s) are still not running" >&2
      # shellcheck disable=SC2086
      docker compose $COMPOSE_FILES ps >&2
      exit 1
    fi

    # -----------------------------------------------------------------------
    # Recreate the edge, then check through it.
    #
    # nginx/stratumai.conf declares `upstream api_upstream { server api:8000; }`
    # with no resolver, so nginx resolves that name ONCE at startup and caches
    # the address for the life of the process. `up -d` above recreates the api
    # container whenever its image changed, which moves it to a new address on
    # the compose network -- and the edge goes on proxying to the old one.
    #
    # The health loop above cannot see this: it runs curl INSIDE the api
    # container, so it proves the API is up, not that the site is. On
    # 2026-09-07 that combination reported a successful prod deploy while
    # api.stratumai.app returned 502 for 25 minutes.
    #
    # Recreate rather than reload. A single-file bind mount pins the host
    # file's inode and the fast-forward writes a new one, so `nginx -s reload`
    # re-reads the file the container started with and reports success.
    if docker compose $COMPOSE_FILES config --services | grep -qx edge; then
      echo "==> recreating edge (api address and config may both have changed)"
      # shellcheck disable=SC2086
      docker compose $COMPOSE_FILES up -d --force-recreate --no-deps edge
      # shellcheck disable=SC2086
      docker compose $COMPOSE_FILES exec -T edge nginx -t

      if [ -n "$EDGE_HEALTH_HOST" ]; then
        # End-to-end through nginx, which is the path a real request takes.
        # --resolve pins the hostname to the loopback so this never leaves the
        # box, and -k skips verification because the origin certificate is a
        # Cloudflare Origin Certificate, trusted only by Cloudflare. Encryption
        # is not what is being tested here; reachability is.
        echo "==> verifying $EDGE_HEALTH_HOST/health through the edge"
        edge_ok=""
        for edge_attempt in $(seq 1 12); do
          if curl -fsS -k --max-time 10 \
               --resolve "$EDGE_HEALTH_HOST:443:127.0.0.1" \
               "https://$EDGE_HEALTH_HOST/health" >/dev/null 2>&1; then
            echo "==> edge healthy after ${edge_attempt} attempt(s)"
            edge_ok=1
            break
          fi
          sleep 5
        done
        if [ -z "$edge_ok" ]; then
          echo "!! the api container is healthy but the edge does not serve it" >&2
          # shellcheck disable=SC2086
          docker compose $COMPOSE_FILES logs --tail 40 edge >&2 || true
          exit 1
        fi
      fi
    fi

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
