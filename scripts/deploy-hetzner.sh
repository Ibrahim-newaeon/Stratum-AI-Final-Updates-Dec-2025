#!/usr/bin/env bash
# =============================================================================
# Stratum AI - Hetzner deployment (Cloudflare edge)
# =============================================================================
# Commands: setup | deploy | update | status | logs | backup | restore | verify
#           verify-restore | observability
#
# Run on the Hetzner host, from the repository root.
#
#   ./scripts/deploy-hetzner.sh setup     # one-time: firewall, certs, dirs
#   ./scripts/deploy-hetzner.sh deploy    # first bring-up
#   ./scripts/deploy-hetzner.sh update    # pull + migrate + restart
#   ./scripts/deploy-hetzner.sh verify    # post-cutover assertions
#   ./scripts/deploy-hetzner.sh observability  # prometheus/alertmanager/grafana
#
# Modelled on scripts/deploy-beta.sh so the operational vocabulary is the same,
# with two differences that matter: backups live off-host (Cloudflare R2), and
# `restore` is a first-class command. A backup nobody has restored is a guess.
# =============================================================================

set -euo pipefail

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.hetzner.yml"
ENV_FILE=".env"
CERT_DIR="./certs"
CF_ORIGIN_PULL_CA_URL="https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

require_env() {
    [ -f "$ENV_FILE" ] || { log_error "$ENV_FILE not found — copy .env.hetzner.template and fill it in"; exit 1; }
}

dc() { docker compose $COMPOSE_FILES "$@"; }

# -----------------------------------------------------------------------------
# setup
# -----------------------------------------------------------------------------
setup() {
    require_env

    log_info "Configuring firewall"
    # The origin must be unreachable except through Cloudflare. Without this,
    # anyone who learns the host address bypasses the WAF, the edge rate limits,
    # and — critically — can send a forged CF-Connecting-IP header. nginx would
    # ignore that header from a non-Cloudflare peer, but defence in depth is
    # cheaper than relying on one control.
    if command -v ufw >/dev/null 2>&1; then
        ufw --force reset >/dev/null
        ufw default deny incoming
        ufw default allow outgoing
        ufw allow 22/tcp comment 'ssh'
        while read -r cidr; do
            [ -z "$cidr" ] && continue
            ufw allow from "$cidr" to any port 443 proto tcp comment 'cloudflare'
            ufw allow from "$cidr" to any port 80 proto tcp comment 'cloudflare'
        done < <(cf_ip_list)
        ufw --force enable
        log_info "Firewall: 443/80 restricted to Cloudflare ranges, 22 open"
    else
        log_warn "ufw not present — restrict 80/443 to Cloudflare ranges manually"
    fi

    log_info "Preparing certificate directory"
    mkdir -p "$CERT_DIR"
    chmod 700 "$CERT_DIR"

    if [ ! -f "$CERT_DIR/cloudflare-origin-pull-ca.pem" ]; then
        log_info "Fetching Cloudflare origin-pull CA"
        curl -fsSL "$CF_ORIGIN_PULL_CA_URL" -o "$CERT_DIR/cloudflare-origin-pull-ca.pem"
    fi

    if [ ! -f "$CERT_DIR/origin.pem" ] || [ ! -f "$CERT_DIR/origin.key" ]; then
        log_error "Origin certificate missing."
        cat <<'EOS'

  Create one in the Cloudflare dashboard:
    SSL/TLS -> Origin Server -> Create Certificate
    Hostnames: api.stratumai.app
    Validity:  15 years

  Save the certificate to ./certs/origin.pem and the key to ./certs/origin.key,
  then: chmod 600 ./certs/origin.key

  Then set SSL/TLS -> Overview -> Full (strict), and enable
  SSL/TLS -> Origin Server -> Authenticated Origin Pulls.

EOS
        exit 1
    fi

    chmod 600 "$CERT_DIR/origin.key"
    log_info "Setup complete"
}

cf_ip_list() {
    curl -fsSL https://www.cloudflare.com/ips-v4 2>/dev/null || true
    echo
    curl -fsSL https://www.cloudflare.com/ips-v6 2>/dev/null || true
}

# -----------------------------------------------------------------------------
# deploy / update
# -----------------------------------------------------------------------------
deploy() {
    require_env
    log_info "Building images"
    dc build
    log_info "Starting stack"
    dc up -d
    wait_healthy
    log_info "Deployed"
}

update() {
    require_env
    log_info "Backing up before update"
    backup || { log_error "Backup failed — aborting update"; exit 1; }

    log_info "Pulling changes"
    git pull --ff-only

    log_info "Rebuilding"
    dc build

    # The api service runs `alembic upgrade head` in its command, so recreating
    # it applies migrations. Restart the API first and workers after, so a
    # worker never runs against a schema the API has not migrated yet.
    log_info "Restarting API (applies migrations)"
    dc up -d --no-deps api
    wait_healthy

    log_info "Restarting workers"
    dc up -d --no-deps worker scheduler

    # Recreate, do not reload. A single-file bind mount pins the host file's
    # INODE, and `git pull` writes a new one — so the container keeps serving
    # the config it started with and `nginx -s reload` re-reads that same stale
    # file, reporting success. Config changes appeared to deploy and did not.
    log_info "Recreating edge (picks up config changes)"
    dc up -d --force-recreate --no-deps edge
    dc exec -T edge nginx -t

    log_info "Update complete"
}

wait_healthy() {
    log_info "Waiting for API health"
    for _ in $(seq 1 30); do
        if dc exec -T api curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
            log_info "API healthy"
            return 0
        fi
        sleep 5
    done
    log_error "API did not become healthy"
    dc logs --tail 80 api
    return 1
}

# -----------------------------------------------------------------------------
# backup / restore
# -----------------------------------------------------------------------------
backup() {
    require_env
    log_info "Triggering an immediate off-host backup"
    # `once` runs a single cycle and exits with the dump's status, so a failure
    # here can abort an update rather than being logged and ignored.
    dc exec -T backup /bin/sh /opt/backup/run.sh once
}

restore() {
    require_env
    local key="${1:-}"
    if [ -z "$key" ]; then
        log_error "Usage: $0 restore <s3-key>"
        log_info "Available backups:"
        dc exec -T backup aws s3 ls "s3://${R2_BUCKET:-stratum-backups}/postgres/" \
            --endpoint-url "$R2_ENDPOINT"
        exit 1
    fi

    # Restoring over a live database is how a bad afternoon becomes a bad
    # quarter. Require explicit confirmation and stop the writers first.
    log_warn "This will overwrite the CURRENT database with ${key}."
    read -r -p "Type RESTORE to continue: " confirm
    [ "$confirm" = "RESTORE" ] || { log_info "Aborted"; exit 1; }

    log_info "Stopping writers"
    dc stop api worker scheduler

    log_info "Restoring ${key}"
    dc exec -T backup /bin/sh -c \
        "aws s3 cp 's3://${R2_BUCKET:-stratum-backups}/postgres/${key}' - \
         --endpoint-url \"\$R2_ENDPOINT\" | gunzip | psql"

    log_info "Restarting stack"
    dc up -d
    wait_healthy
    log_info "Restore complete — verify before announcing recovery"
}

# -----------------------------------------------------------------------------
# verify-restore — prove a backup actually restores
# -----------------------------------------------------------------------------
# `restore` above overwrites the live database, so it is not something anyone
# runs to check that backups work. This restores the newest object (or a named
# one) into a throwaway database, asserts against it, and drops it. Nothing the
# application uses is touched.
verify_restore() {
    require_env
    log_info "Restoring the newest backup into a scratch database"
    log_warn "This briefly holds a second copy of the data on the db volume."
    dc exec -T backup-verify /bin/sh /opt/backup/verify-restore.sh once "${1:-}"
}

# -----------------------------------------------------------------------------
# verify — post-cutover assertions
# -----------------------------------------------------------------------------
verify() {
    require_env
    local fail=0

    log_info "1/4 API reachable through Cloudflare"
    if curl -fsS https://api.stratumai.app/health >/dev/null; then
        log_info "    ok"
    else
        log_error "    unreachable"; fail=1
    fi

    log_info "2/4 Direct-to-origin refused"
    local origin_ip
    origin_ip="$(curl -fsS https://ifconfig.me 2>/dev/null || echo '')"
    if [ -n "$origin_ip" ] && curl -fsS --max-time 5 "https://${origin_ip}/health" \
        --resolve "api.stratumai.app:443:${origin_ip}" >/dev/null 2>&1; then
        log_error "    origin answered a non-Cloudflare client"; fail=1
    else
        log_info "    ok (refused or unreachable)"
    fi

    log_info "3/4 Real client IP reaching the application"
    # The audit trail is the consumer that matters. A Cloudflare address here
    # means the real_ip block is not doing its job — see issue #652.
    local logged
    # Read the container's stream, not the file. access.log is a symlink to
    # /dev/stdout, so `tail` on it never returns — that hang is what stopped
    # this check running at all the first time it was needed.
    logged="$(dc logs --tail 40 edge 2>/dev/null | grep -E 'GET|POST' | tail -n 1 | awk '{print $1}')"
    case "$logged" in
        172.6[4-9].*|104.1[6-9].*|162.15[89].*|103.2*|141.101.*|108.162.*)
            log_error "    edge logged a Cloudflare address ($logged)"; fail=1 ;;
        "") log_warn "    no access-log entry yet" ;;
        *)  log_info "    ok ($logged)" ;;
    esac

    log_info "4/5 A backup exists in R2"
    if dc exec -T backup aws s3 ls "s3://${R2_BUCKET:-stratum-backups}/postgres/" \
        --endpoint-url "$R2_ENDPOINT" 2>/dev/null | tail -1 | grep -q .; then
        log_info "    ok"
    else
        log_error "    no backup objects found"; fail=1
    fi

    # An object existing is not the same claim as that object restoring, and
    # the difference only ever shows up during a recovery. verify-restore.sh
    # writes this marker after a dump has actually been restored and asserted
    # against, so its age is the age of the last real proof.
    log_info "5/5 A backup has been proven restorable recently"
    local marker marker_date marker_epoch age_days
    marker="$(dc exec -T backup aws s3 cp \
        "s3://${R2_BUCKET:-stratum-backups}/postgres/.last-verified" - \
        --endpoint-url "$R2_ENDPOINT" 2>/dev/null || true)"
    marker_date="$(echo "$marker" | sed -n 's/^verified_at=\([0-9-]*\)T.*/\1/p')"
    if [ -z "$marker_date" ]; then
        log_error "    no verification marker — backups have never been restore-tested"
        log_info  "    run: $0 verify-restore"
        fail=1
    else
        marker_epoch="$(date -u -d "$marker_date" +%s 2>/dev/null || echo 0)"
        age_days=$(( ( $(date -u +%s) - marker_epoch ) / 86400 ))
        # The backup-verify service runs weekly; twice that is a clear signal
        # it has stopped rather than merely not fired yet.
        if [ "$marker_epoch" -eq 0 ]; then
            log_warn "    marker present but unparseable ($marker_date)"
        elif [ "$age_days" -gt 14 ]; then
            log_error "    last verified $age_days days ago — backup-verify is not running"; fail=1
        else
            log_info "    ok (last verified $age_days day(s) ago)"
        fi
    fi

    [ "$fail" -eq 0 ] && log_info "All checks passed" || log_error "Checks failed"
    return "$fail"
}

status() { require_env; dc ps; }
logs()   { require_env; dc logs --tail "${2:-100}" -f "${1:-}"; }

# -----------------------------------------------------------------------------
# observability
# -----------------------------------------------------------------------------
# Brings up Prometheus, Alertmanager and Grafana on loopback only. Kept as a
# separate command rather than folded into `deploy` so that a monitoring
# problem can never take the API down with it.
observability() {
    require_env

    local key_file="infrastructure/prometheus/metrics_api_key"

    # /metrics is tenant-exempt and served on the same port as the public API.
    # The edge denies it, but the scrape reaches api:8000 directly, so the key
    # is what separates Prometheus from anything else on the compose network.
    if ! grep -q '^METRICS_API_KEY=.\+' "$ENV_FILE"; then
        log_error "METRICS_API_KEY is not set in $ENV_FILE"
        log_error "Generate one with: openssl rand -hex 32"
        exit 1
    fi
    for var in GRAFANA_ADMIN_USER GRAFANA_ADMIN_PASSWORD; do
        grep -q "^${var}=.\+" "$ENV_FILE" || {
            log_error "$var is not set in $ENV_FILE"; exit 1; }
    done

    # Prometheus reads the bearer token from a file, so mirror the variable out
    # of .env. Written with a trailing-newline-free printf: Prometheus sends the
    # file's bytes verbatim, and a stray \n produces a 403 that looks like a
    # wrong key.
    log_info "Writing scrape credentials to $key_file"
    printf '%s' "$(grep -m1 '^METRICS_API_KEY=' "$ENV_FILE" | cut -d= -f2-)" > "$key_file"
    # Owned by nobody(65534) — the uid prom/prometheus runs as. Left root-owned
    # at 0600 the container cannot read it and the target fails with
    # "unable to read authorization credentials: permission denied", which
    # reads like a bad key rather than a bad mode. 0400 after the chown, so it
    # stays unreadable to every other account on the host.
    chown 65534:65534 "$key_file"
    chmod 400 "$key_file"

    # Alertmanager config is rendered, not mounted directly, because the Slack
    # webhook is a credential and belongs in .env rather than in git.
    # Alertmanager does no environment substitution of its own, and a config
    # naming a receiver with an empty api_url fails to load — so the choice
    # between "notify Slack" and "UI only" is made here, at render time.
    local am_src am_out slack_url slack_url_critical
    am_out="infrastructure/prometheus/alertmanager.generated.yml"
    slack_url="$(grep -m1 '^SLACK_WEBHOOK_URL=' "$ENV_FILE" | cut -d= -f2-)"
    slack_url_critical="$(grep -m1 '^SLACK_WEBHOOK_URL_CRITICAL=' "$ENV_FILE" | cut -d= -f2-)"

    # A Slack webhook is bound to one channel, so two channels means two
    # webhooks. With only one configured, both severities share it rather than
    # the critical receiver silently losing its destination.
    if [ -z "$slack_url_critical" ] && [ -n "$slack_url" ]; then
        log_warn "SLACK_WEBHOOK_URL_CRITICAL unset — critical alerts share the default channel"
        slack_url_critical="$slack_url"
    fi

    if [ -n "$slack_url" ]; then
        am_src="infrastructure/prometheus/alertmanager.slack.yml"
        log_info "Rendering Alertmanager config with Slack notifications"
        # Explicit variable list: the template also contains Go templating
        # ({{ .Status }}), which must reach Alertmanager untouched.
        SLACK_WEBHOOK_URL="$slack_url" \
        SLACK_WEBHOOK_URL_CRITICAL="$slack_url_critical" \
            envsubst '${SLACK_WEBHOOK_URL} ${SLACK_WEBHOOK_URL_CRITICAL}' \
            < "$am_src" > "$am_out"
    else
        am_src="infrastructure/prometheus/alertmanager.yml"
        log_warn "SLACK_WEBHOOK_URL is not set — alerts will be visible in the"
        log_warn "Alertmanager UI over the tunnel, and will page nobody."
        cp "$am_src" "$am_out"
    fi
    # Same ownership dance as the scrape key above, and for the same reason:
    # prom/alertmanager runs as nobody(65534), so a root-owned 0600 file is
    # unreadable to it. Left that way, amtool reports
    # "FAILED: open /am.yml: permission denied" — which reads like a broken
    # config rather than a broken mode.
    chown 65534:65534 "$am_out"
    chmod 400 "$am_out"

    # Fail before starting rather than after: amtool reports the line, a
    # crash-looping container reports only that it restarted.
    if command -v docker >/dev/null 2>&1; then
        docker run --rm -v "$PWD/$am_out:/am.yml:ro" \
            --entrypoint amtool prom/alertmanager:v0.27.0 \
            check-config /am.yml >/dev/null 2>&1 || {
                log_error "Rendered Alertmanager config is invalid: $am_out"
                exit 1; }
    fi

    log_info "Starting observability stack (loopback only)"
    docker compose $COMPOSE_FILES -f docker-compose.observability.yml \
        up -d prometheus alertmanager grafana

    log_info "Waiting for Prometheus to load its rules"
    local ok=0
    for _ in $(seq 1 30); do
        if curl -sf http://127.0.0.1:9090/-/ready >/dev/null 2>&1; then ok=1; break; fi
        sleep 2
    done
    [ "$ok" = 1 ] || { log_error "Prometheus did not become ready"; exit 1; }

    # A target that is down and a rule that failed to load both report success
    # at the container level, so assert on the API rather than on `docker ps`.
    local up_count
    up_count=$(curl -sf 'http://127.0.0.1:9090/api/v1/query?query=up{job="stratum-api"}' \
        | grep -o '"value":\[[^]]*,"1"\]' | wc -l)
    if [ "$up_count" -lt 1 ]; then
        log_warn "Prometheus is running but the stratum-api target is not up yet"
        log_warn "Check http://127.0.0.1:9090/targets — a 403 there means the key is wrong"
    else
        log_info "stratum-api target is up"
    fi

    echo
    log_info "Nothing is published beyond loopback. Tunnel in from your workstation:"
    echo "    ssh -L 9090:127.0.0.1:9090 -L 9093:127.0.0.1:9093 -L 3001:127.0.0.1:3001 root@<host>"
    echo "    Grafana       http://localhost:3001"
    echo "    Prometheus    http://localhost:9090"
    echo "    Alertmanager  http://localhost:9093"
}

case "${1:-}" in
    setup)   setup ;;
    deploy)  deploy ;;
    update)  update ;;
    status)  status ;;
    logs)    shift; logs "$@" ;;
    backup)  backup ;;
    restore) shift; restore "$@" ;;
    verify)  verify ;;
    verify-restore) shift; verify_restore "$@" ;;
    observability) observability ;;
    *)
        echo "Usage: $0 {setup|deploy|update|status|logs|backup|restore <key>|verify|verify-restore [key]|observability}"
        exit 1
        ;;
esac
