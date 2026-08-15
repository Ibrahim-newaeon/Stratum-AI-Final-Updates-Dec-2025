#!/bin/sh
# =============================================================================
# Stratum AI - Off-host Postgres backup to Cloudflare R2
# =============================================================================
# Runs as a long-lived container. Each cycle streams a compressed logical dump
# directly to R2 and prunes objects past the retention window.
#
# Design notes:
#   * The dump is piped, never written to local disk. A plaintext copy of a
#     multi-tenant database sitting on the application host is exactly what the
#     off-host requirement exists to avoid.
#   * `set -e` is deliberately NOT used for the whole script: a failed cycle
#     must log loudly and retry on the next interval rather than kill the
#     container into a restart loop that hides the cause.
#   * The exit status checked is pg_dump's, not gzip's or the pipeline's last
#     command — `set -o pipefail` is not in POSIX sh, so the status is captured
#     explicitly via a marker file.
# =============================================================================

: "${R2_ENDPOINT:?R2_ENDPOINT is required}"
: "${R2_BUCKET:=stratum-backups}"
: "${BACKUP_INTERVAL_SECONDS:=21600}"
: "${BACKUP_RETENTION_DAYS:=30}"
: "${PGDATABASE:=stratum_ai}"

log() {
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [backup] $*"
}

# The image supplies pg_dump and gzip; only the AWS CLI has to be added.
# Failing here must be loud and fatal — an earlier version logged a warning and
# carried on, which produced a "backup" whose every tool was missing:
#     pg_dump: command not found
#     gzip: command not found
# and an upload of nothing at all.
if ! command -v aws >/dev/null 2>&1; then
    log "installing aws-cli"
    apk add --no-cache aws-cli >/dev/null 2>&1 || {
        log "FATAL: could not install aws-cli"
        exit 1
    }
fi

for tool in pg_dump gzip aws; do
    command -v "$tool" >/dev/null 2>&1 || {
        log "FATAL: $tool is missing; refusing to pretend to back up"
        exit 1
    }
done
log "tools present: $(pg_dump --version | head -1)"

run_backup() {
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    key="s3://${R2_BUCKET}/postgres/${PGDATABASE}-${stamp}.sql.gz"
    status_file="/tmp/dump_status"

    log "starting dump -> ${key}"

    # `{ pg_dump; echo $? >status; } | gzip | aws s3 cp -` lets us see whether
    # pg_dump itself succeeded. Without it a dump that dies halfway still
    # produces a valid gzip stream and a successful upload — a backup that
    # looks fine and restores to a truncated database.
    {
        pg_dump --no-owner --no-acl --format=plain
        echo $? > "$status_file"
    } | gzip -9 | aws s3 cp - "$key" \
        --endpoint-url "$R2_ENDPOINT" \
        --content-type application/gzip \
        --only-show-errors

    upload_rc=$?
    dump_rc="$(cat "$status_file" 2>/dev/null || echo 1)"

    if [ "$dump_rc" != "0" ]; then
        log "ERROR: pg_dump exited ${dump_rc}; the uploaded object is incomplete"
        aws s3 rm "$key" --endpoint-url "$R2_ENDPOINT" --only-show-errors 2>/dev/null
        log "removed truncated object ${key}"
        return 1
    fi

    if [ "$upload_rc" != "0" ]; then
        log "ERROR: upload to R2 failed (rc=${upload_rc})"
        return 1
    fi

    size="$(aws s3 ls "$key" --endpoint-url "$R2_ENDPOINT" 2>/dev/null | awk '{print $3}')"
    log "completed ${key} (${size:-unknown} bytes)"
    return 0
}

prune_old() {
    # `date -d "N days ago"` is GNU syntax; this runs on Alpine, where busybox
    # date rejects it and the whole prune was skipping with a warning every
    # cycle — retention silently unenforced while backups accumulated.
    # Epoch arithmetic works on both: busybox takes -D %s, GNU takes @epoch.
    cutoff_epoch=$(( $(date -u +%s) - BACKUP_RETENTION_DAYS * 86400 ))
    cutoff="$(date -u -D %s -d "$cutoff_epoch" +%Y-%m-%d 2>/dev/null \
              || date -u -d "@$cutoff_epoch" +%Y-%m-%d 2>/dev/null)"
    [ -z "$cutoff" ] && { log "WARNING: cannot compute cutoff; skipping prune"; return 0; }
    log "pruning objects older than $cutoff"

    aws s3 ls "s3://${R2_BUCKET}/postgres/" --endpoint-url "$R2_ENDPOINT" 2>/dev/null \
    | while read -r d _t _s name; do
        [ -z "$name" ] && continue
        # String compare on ISO dates is a correct chronological compare.
        if [ "$d" \< "$cutoff" ]; then
            aws s3 rm "s3://${R2_BUCKET}/postgres/${name}" \
                --endpoint-url "$R2_ENDPOINT" --only-show-errors
            log "pruned ${name}"
        fi
    done
}

# `run.sh once` performs a single backup and exits, which is what
# deploy-hetzner.sh calls before an update and what an operator runs by hand.
# Sourcing this file to reach run_backup would enter the loop below instead.
if [ "${1:-}" = "once" ]; then
    log "one-shot backup requested"
    if run_backup; then
        prune_old
        exit 0
    fi
    exit 1
fi

log "starting; interval=${BACKUP_INTERVAL_SECONDS}s retention=${BACKUP_RETENTION_DAYS}d bucket=${R2_BUCKET}"

while true; do
    if run_backup; then
        prune_old
    else
        log "cycle failed; retrying at next interval"
    fi
    sleep "$BACKUP_INTERVAL_SECONDS"
done
