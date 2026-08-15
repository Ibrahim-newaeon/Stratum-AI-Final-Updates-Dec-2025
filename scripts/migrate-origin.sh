#!/usr/bin/env bash
# =============================================================================
# Stratum AI - Move a deployment between origins
# =============================================================================
#   ./scripts/migrate-origin.sh preflight        # safe to run any time
#   ./scripts/migrate-origin.sh import <dump.gz> # load a dump into this origin
#   ./scripts/migrate-origin.sh export <out.gz>  # take a dump from this origin
#
# Run on the TARGET host, from the repository root.
#
# The copying is the easy part. What this script is really for is the
# precondition: PII_ENCRYPTION_KEY derives the Fernet keys for every encrypted
# column — user email, name, phone, and since #650 every ad-platform and CRM
# credential. Restore a dump under a different key and nothing errors. The
# ciphertext is still there, decrypt_pii raises InvalidToken, and
# app/auth/deps.py catches it: names come back None, emails fall back to the
# JWT claim, credentials fail to decrypt when a sync next runs. You get a
# running system full of unreadable data and no failed deploy to point at.
#
# So `import` refuses to load a dump whose encrypted rows do not decrypt under
# the key in this environment. It is cheaper to stop here than to discover it
# three days later with new writes layered on top.
# =============================================================================

set -euo pipefail

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.hetzner.yml"
ENV_FILE=".env"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

dc() { docker compose $COMPOSE_FILES "$@"; }

require_env() {
    [ -f "$ENV_FILE" ] || { log_error "$ENV_FILE not found"; exit 1; }
    # shellcheck disable=SC1090
    set -a; . "./$ENV_FILE"; set +a
    : "${PII_ENCRYPTION_KEY:?PII_ENCRYPTION_KEY must be set}"
}

# -----------------------------------------------------------------------------
# preflight
# -----------------------------------------------------------------------------
preflight() {
    require_env
    local fail=0

    log_info "1/5 Required secrets present and not placeholders"
    for var in SECRET_KEY JWT_SECRET_KEY PII_ENCRYPTION_KEY POSTGRES_PASSWORD; do
        local val="${!var:-}"
        if [ -z "$val" ]; then
            log_error "    $var is empty"; fail=1
        elif [ ${#val} -lt 24 ]; then
            log_error "    $var looks too short (${#val} chars) — generate with: openssl rand -base64 48"; fail=1
        else
            log_info "    $var ok (${#val} chars)"
        fi
    done

    log_info "2/5 Secrets are distinct"
    # Reusing one value across SECRET_KEY/JWT_SECRET_KEY/PII_ENCRYPTION_KEY means
    # one leak compromises sessions and stored PII together.
    if [ "$(printf '%s\n%s\n%s\n' "$SECRET_KEY" "$JWT_SECRET_KEY" "$PII_ENCRYPTION_KEY" | sort -u | wc -l)" -ne 3 ]; then
        log_error "    SECRET_KEY / JWT_SECRET_KEY / PII_ENCRYPTION_KEY are not all distinct"; fail=1
    else
        log_info "    ok"
    fi

    log_info "3/5 Database reachable"
    if dc exec -T db pg_isready -q 2>/dev/null; then
        log_info "    ok"
    else
        log_error "    database not reachable — is the stack up?"; fail=1
    fi

    log_info "4/5 R2 backup destination writable"
    if dc exec -T backup aws s3 ls "s3://${R2_BUCKET:-stratum-backups}/" \
        --endpoint-url "${R2_ENDPOINT:-}" >/dev/null 2>&1; then
        log_info "    ok"
    else
        log_error "    cannot list ${R2_BUCKET:-stratum-backups} — check R2 credentials/endpoint"; fail=1
    fi

    log_info "5/5 PII key matches existing data"
    check_key_matches && log_info "    ok" || fail=1

    [ "$fail" -eq 0 ] && log_info "Preflight passed" || log_error "Preflight failed"
    return "$fail"
}

# -----------------------------------------------------------------------------
# check_key_matches
# -----------------------------------------------------------------------------
# Decrypts a sample of real ciphertext with the configured key. An empty
# database passes trivially — there is nothing to be inconsistent with, which
# is exactly the clean-start case.
check_key_matches() {
    dc exec -T api python - <<'PY'
import sys

from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.security import decrypt_pii, looks_like_pii_ciphertext

engine = create_engine(settings.database_url_sync)
with engine.connect() as conn:
    rows = conn.execute(
        text("SELECT id, tenant_id, email FROM users WHERE email IS NOT NULL LIMIT 25")
    ).fetchall()

if not rows:
    print("    no user rows yet — nothing to verify (clean start)")
    sys.exit(0)

encrypted = [r for r in rows if looks_like_pii_ciphertext(r.email)]
if not encrypted:
    print("    rows exist but none are encrypted — pre-encryption data, nothing to verify")
    sys.exit(0)

failures = 0
for row in encrypted:
    try:
        # Passing tenant_id matters: keys are per-tenant (AUTH-05), and
        # decrypt_pii dual-reads tenant DEK -> tenant-salted -> true-global,
        # so this also accepts rows written before that change.
        decrypt_pii(row.email, row.tenant_id)
    except Exception as exc:
        failures += 1
        print(f"    user {row.id} (tenant {row.tenant_id}): {type(exc).__name__}")

if failures:
    print(f"    {failures}/{len(encrypted)} sampled rows FAILED to decrypt")
    print("    PII_ENCRYPTION_KEY does not match the data in this database.")
    sys.exit(1)

print(f"    {len(encrypted)} sampled rows decrypt correctly")
PY
}

# -----------------------------------------------------------------------------
# export / import
# -----------------------------------------------------------------------------
export_dump() {
    require_env
    local out="${1:-stratum-$(date -u +%Y%m%dT%H%M%SZ).sql.gz}"
    log_info "Exporting to ${out}"
    # Capture pg_dump's status, not the pipeline's: a dump that dies halfway
    # still produces valid gzip, which would look like a good export.
    local status_file
    status_file="$(mktemp)"
    { dc exec -T db pg_dump -U "$POSTGRES_USER" --no-owner --no-acl "$POSTGRES_DB"; echo $? > "$status_file"; } \
        | gzip -9 > "$out"
    local rc; rc="$(cat "$status_file")"; rm -f "$status_file"
    if [ "$rc" != "0" ]; then
        log_error "pg_dump exited $rc — ${out} is incomplete"
        rm -f "$out"
        exit 1
    fi
    log_info "Exported $(du -h "$out" | cut -f1) to ${out}"
}

import_dump() {
    require_env
    local dump="${1:-}"
    [ -n "$dump" ] && [ -f "$dump" ] || { log_error "Usage: $0 import <dump.sql.gz>"; exit 1; }

    log_warn "This loads ${dump} into the CURRENT database."
    read -r -p "Type IMPORT to continue: " confirm
    [ "$confirm" = "IMPORT" ] || { log_info "Aborted"; exit 1; }

    log_info "Stopping writers"
    dc stop api worker scheduler >/dev/null 2>&1 || true
    # The API must be up to run the key check, but must not be serving. Start
    # it without its dependents once the data is in.

    log_info "Loading dump"
    gunzip -c "$dump" | dc exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q

    log_info "Starting API to verify encryption key"
    dc up -d --no-deps api >/dev/null
    sleep 8

    if ! check_key_matches; then
        log_error ""
        log_error "The imported data does not decrypt under this PII_ENCRYPTION_KEY."
        log_error "Nothing is broken *yet* — the ciphertext is intact and the correct"
        log_error "key will still read it. Do NOT start the workers and do NOT let"
        log_error "users write: new rows would be encrypted under the new key and the"
        log_error "table would end up holding two incompatible generations."
        log_error ""
        log_error "Set PII_ENCRYPTION_KEY to the value from the source origin and"
        log_error "re-run: $0 preflight"
        dc stop api >/dev/null 2>&1 || true
        exit 1
    fi

    log_info "Key verified — starting the rest of the stack"
    dc up -d
    log_info "Import complete. Run ./scripts/deploy-hetzner.sh verify next."
}

case "${1:-}" in
    preflight) preflight ;;
    export)    shift; export_dump "$@" ;;
    import)    shift; import_dump "$@" ;;
    *)
        echo "Usage: $0 {preflight|export [out.sql.gz]|import <dump.sql.gz>}"
        exit 1
        ;;
esac
