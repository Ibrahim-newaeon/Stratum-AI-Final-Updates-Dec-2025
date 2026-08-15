#!/usr/bin/env bash
# =============================================================================
# Stratum AI - Refresh the Cloudflare IP ranges in nginx/stratumai.conf
# =============================================================================
# Cloudflare's published ranges change. A stale list is not a loud failure: the
# origin quietly stops trusting CF-Connecting-IP from the new ranges and starts
# recording Cloudflare addresses again — the exact behaviour issue #652 exists
# to prevent, with no error to notice.
#
# Run monthly (cron/systemd timer), or after Cloudflare announces a change.
#
#   ./scripts/refresh-cf-ips.sh          # rewrite the block if it changed
#   ./scripts/refresh-cf-ips.sh --check  # exit 1 if stale, change nothing
# =============================================================================

set -euo pipefail

CONF="nginx/stratumai.conf"
BEGIN="# BEGIN CLOUDFLARE IPS"
END="# END CLOUDFLARE IPS"
CHECK_ONLY=false
[ "${1:-}" = "--check" ] && CHECK_ONLY=true

[ -f "$CONF" ] || { echo "ERROR: $CONF not found (run from the repo root)" >&2; exit 1; }

tmp="$(mktemp)"
trap 'rm -f "$tmp" "$tmp.new"' EXIT

{
    curl -fsSL https://www.cloudflare.com/ips-v4
    echo
    curl -fsSL https://www.cloudflare.com/ips-v6
} | grep -E '^[0-9a-fA-F.:]+/[0-9]+$' | sed 's/^/set_real_ip_from /; s/$/;/' > "$tmp"

# A truncated or empty download must never be written: replacing the block with
# nothing would make nginx trust no proxy at all, silently reverting to logging
# Cloudflare addresses.
count="$(wc -l < "$tmp")"
if [ "$count" -lt 10 ]; then
    echo "ERROR: only $count ranges fetched — refusing to write a suspect list" >&2
    exit 1
fi

current="$(sed -n "/$BEGIN/,/$END/p" "$CONF" | grep '^set_real_ip_from' || true)"
if [ "$current" = "$(cat "$tmp")" ]; then
    echo "Cloudflare ranges are current ($count entries)."
    exit 0
fi

if [ "$CHECK_ONLY" = true ]; then
    echo "STALE: nginx/stratumai.conf does not match Cloudflare's published ranges." >&2
    diff <(echo "$current") "$tmp" || true
    exit 1
fi

awk -v begin="$BEGIN" -v end="$END" -v listfile="$tmp" '
    $0 ~ begin { print; while ((getline line < listfile) > 0) print line; skip = 1; next }
    $0 ~ end   { print; skip = 0; next }
    !skip      { print }
' "$CONF" > "$tmp.new"

mv "$tmp.new" "$CONF"
echo "Updated $CONF with $count Cloudflare ranges."
echo "Reload the edge:  docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.hetzner.yml exec edge nginx -s reload"
