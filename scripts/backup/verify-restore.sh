#!/bin/sh
# =============================================================================
# Stratum AI - Restore verification for the R2 Postgres backups
# =============================================================================
# Proves a backup object actually restores. run.sh already checks that pg_dump
# exited 0 and that the upload completed, but neither says the bytes in R2
# reconstruct a working schema: a dump can be complete, uploaded, correctly
# sized, and still fail to restore — a missing extension on the target, an
# object the role cannot create, a truncation gzip happily compressed.
#
# deploy-hetzner.sh already has `restore`, but it overwrites the live database
# and asks the operator to type RESTORE first. That is the right shape for a
# recovery and the wrong shape for a routine check, so nothing was exercising
# the backups. This restores into a throwaway database instead, asserts against
# it, and drops it.
#
# Design notes:
#   * The scratch database lives on the same server as production, because the
#     dump needs pgvector and Apache AGE and this is the only host that has
#     them (see backend/Dockerfile.postgres). It is created and dropped inside
#     one run and is never written to by the application.
#   * ON_ERROR_STOP=1 is the whole point. Without it psql reports errors and
#     keeps going, exits 0, and a broken dump passes.
#   * The assertions run against the RESTORED database only. Comparing row
#     counts to production would be flaky by construction — the dump is a
#     point in time and production moves on — so the one cross-check is
#     alembic_version, which changes only on migration.
#   * A successful run writes a marker object to R2. That is what makes
#     "backups are verified" checkable later instead of assumed; `verify` in
#     deploy-hetzner.sh reads its age.
# =============================================================================

: "${R2_ENDPOINT:?R2_ENDPOINT is required}"
: "${R2_BUCKET:=stratum-backups}"
: "${PGDATABASE:=stratum_ai}"
: "${VERIFY_INTERVAL_SECONDS:=604800}"
: "${VERIFY_MIN_TENANTS:=0}"

PREFIX="s3://${R2_BUCKET}/postgres"
MARKER_KEY="${PREFIX}/.last-verified"

log() {
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [verify-restore] $*"
}

if ! command -v aws >/dev/null 2>&1; then
    log "installing aws-cli"
    apk add --no-cache aws-cli >/dev/null 2>&1 || {
        log "FATAL: could not install aws-cli"
        exit 1
    }
fi

for tool in psql gunzip aws createdb dropdb; do
    command -v "$tool" >/dev/null 2>&1 || {
        log "FATAL: $tool is missing; refusing to report an unverified backup as verified"
        exit 1
    }
done

# Every psql call targets a database explicitly. PGDATABASE is exported for the
# backup container as a whole, and inheriting it here is how a verification run
# would end up asserting against production and passing without restoring
# anything.
q() {
    db="$1"
    shift
    psql --dbname "$db" --no-psqlrc --tuples-only --no-align --quiet -c "$*"
}

latest_key() {
    # Object names are ${db}-YYYYMMDDTHHMMSSZ.sql.gz, so a lexicographic sort is
    # a chronological sort. The marker object is excluded: it is not a dump, and
    # picking it up would "verify" a text file.
    aws s3 ls "${PREFIX}/" --endpoint-url "$R2_ENDPOINT" 2>/dev/null \
        | awk '{print $4}' \
        | grep '\.sql\.gz$' \
        | sort \
        | tail -1
}

SCRATCH=""

cleanup() {
    [ -z "$SCRATCH" ] && return 0
    # Always attempt the drop, including on an interrupt. A scratch database
    # left behind holds a full copy of production on the production volume.
    if dropdb --if-exists --force "$SCRATCH" 2>/dev/null; then
        log "dropped scratch database ${SCRATCH}"
    else
        log "WARNING: could not drop ${SCRATCH}; it is holding a full copy of the data and must be removed by hand"
    fi
    SCRATCH=""
}
trap cleanup EXIT INT TERM

verify_once() {
    key_name="${1:-}"
    [ -z "$key_name" ] && key_name="$(latest_key)"

    if [ -z "$key_name" ]; then
        log "ERROR: no backup objects found under ${PREFIX}/"
        return 1
    fi

    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    SCRATCH="restore_check_${stamp}"

    # Refuse to go anywhere near the real database, whatever produced the name.
    if [ "$SCRATCH" = "$PGDATABASE" ]; then
        log "FATAL: scratch name collides with ${PGDATABASE}"
        return 1
    fi

    log "verifying ${key_name} -> ${SCRATCH}"

    if ! createdb "$SCRATCH"; then
        log "ERROR: could not create scratch database ${SCRATCH}"
        return 1
    fi

    # The restore's own exit status, not the pipeline's. Same reasoning as
    # run.sh: gunzip succeeding says nothing about whether psql applied the SQL.
    status_file="/tmp/restore_status"
    rm -f "$status_file"

    aws s3 cp "${PREFIX}/${key_name}" - --endpoint-url "$R2_ENDPOINT" --only-show-errors \
        | gunzip \
        | { psql --dbname "$SCRATCH" --no-psqlrc --quiet \
                 --set ON_ERROR_STOP=1 --output /dev/null 2>/tmp/restore_stderr
            echo $? > "$status_file"; }

    restore_rc="$(cat "$status_file" 2>/dev/null || echo 1)"
    if [ "$restore_rc" != "0" ]; then
        log "ERROR: restore failed (psql rc=${restore_rc})"
        log "first errors:"
        head -20 /tmp/restore_stderr 2>/dev/null | while read -r line; do log "    $line"; done
        return 1
    fi

    log "restore applied cleanly; asserting"

    fail=0

    # 1. Extensions. Their absence is the failure mode most likely to appear
    #    only at recovery time, on a host rebuilt without the custom image.
    for ext in vector age; do
        found="$(q "$SCRATCH" "SELECT 1 FROM pg_extension WHERE extname = '${ext}'")"
        if [ "$found" = "1" ]; then
            log "    ok: extension ${ext}"
        else
            log "    FAIL: extension ${ext} missing from the restored database"
            fail=1
        fi
    done

    # 2. Schema version, cross-checked against production. A dump that restores
    #    at an older revision than the running application is a dump that will
    #    not accept the application's writes.
    restored_rev="$(q "$SCRATCH" "SELECT version_num FROM alembic_version")"
    live_rev="$(q "$PGDATABASE" "SELECT version_num FROM alembic_version")"
    if [ -z "$restored_rev" ]; then
        log "    FAIL: alembic_version is empty in the restored database"
        fail=1
    elif [ "$restored_rev" != "$live_rev" ]; then
        # Worth failing on rather than warning: it means the dump predates a
        # migration, so recovering from it would need that migration re-run.
        log "    FAIL: schema revision ${restored_rev} != live ${live_rev}"
        fail=1
    else
        log "    ok: alembic_version ${restored_rev}"
    fi

    # 3. Core tables present and readable. SELECT count(*) rather than a
    #    catalogue lookup: a table can exist in the catalogue and still be
    #    unreadable if its data did not come across.
    for tbl in tenants users; do
        n="$(q "$SCRATCH" "SELECT count(*) FROM ${tbl}" 2>/dev/null)"
        if [ -z "$n" ]; then
            log "    FAIL: cannot read ${tbl} in the restored database"
            fail=1
        else
            log "    ok: ${tbl} has ${n} rows"
            if [ "$tbl" = "tenants" ] && [ "$n" -lt "$VERIFY_MIN_TENANTS" ]; then
                log "    FAIL: tenants=${n} is below VERIFY_MIN_TENANTS=${VERIFY_MIN_TENANTS}"
                fail=1
            fi
        fi
    done

    if [ "$fail" -ne 0 ]; then
        log "ERROR: ${key_name} restored but failed assertions"
        return 1
    fi

    # Marker last, and only on a clean pass — its presence is the claim that a
    # backup was proven restorable, so it must never outrun the proof.
    printf 'verified_at=%s\nkey=%s\nrevision=%s\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$key_name" "$restored_rev" \
        | aws s3 cp - "$MARKER_KEY" --endpoint-url "$R2_ENDPOINT" \
            --content-type text/plain --only-show-errors \
        || log "WARNING: verification passed but the marker could not be written"

    log "PASS: ${key_name} is restorable"
    return 0
}

case "${1:-}" in
    once)
        verify_once "${2:-}"
        rc=$?
        cleanup
        exit "$rc"
        ;;
esac

log "starting; interval=${VERIFY_INTERVAL_SECONDS}s bucket=${R2_BUCKET}"
while true; do
    # Same posture as run.sh: a failed cycle logs loudly and waits, rather than
    # exiting into a restart loop that buries the reason.
    verify_once || log "cycle failed; retrying at next interval"
    cleanup
    sleep "$VERIFY_INTERVAL_SECONDS"
done
