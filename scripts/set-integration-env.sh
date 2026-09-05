#!/usr/bin/env bash
# =============================================================================
# Stratum AI - Set integration credentials in .env, idempotently
# =============================================================================
# Hand-editing .env on a production host is how half-configured integrations
# happen: a stray quote, a space around the '=', a duplicated key three lines
# further down, or one of a required pair pasted and the other forgotten.
# Settings.validate_integration_config raises on the last one in production and
# staging, so a slip takes the API down on the next restart rather than
# degrading quietly.
#
# This script writes the keys for you: it updates a key in place if it is
# already there, appends it if not, and never leaves two lines for one key.
#
# Values are read from a hidden prompt, never from the command line, so a
# secret does not reach your shell history, the process list, or this file.
#
#   ./scripts/set-integration-env.sh PIPEDRIVE_CLIENT_ID PIPEDRIVE_CLIENT_SECRET
#   ./scripts/set-integration-env.sh --check PIPEDRIVE_CLIENT_ID
#   ./scripts/set-integration-env.sh --file /opt/stratum-ai/.env HUBSPOT_CLIENT_ID
#
# Nothing here prints a secret. --check reports <set> or <missing> only.
# =============================================================================

set -euo pipefail

ENV_FILE=".env"
CHECK_ONLY=false
KEYS=()

usage() {
    cat <<'EOF'
Set integration credentials in .env, idempotently.

  set-integration-env.sh [--file PATH] KEY [KEY...]   set keys (hidden prompt)
  set-integration-env.sh --check KEY [KEY...]         report <set>/<empty>/<missing>
  set-integration-env.sh --help

--file defaults to ./.env, so run this from the deploy directory.
Values are never taken from the command line and never printed.
EOF
    exit "${1:-0}"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --check)   CHECK_ONLY=true; shift ;;
        --file)    ENV_FILE="${2:?--file needs a path}"; shift 2 ;;
        -h|--help) usage 0 ;;
        -*)        echo "ERROR: unknown option $1" >&2; usage 1 >&2 ;;
        *)         KEYS+=("$1"); shift ;;
    esac
done

[ "${#KEYS[@]}" -gt 0 ] || { echo "ERROR: name at least one variable" >&2; usage 1 >&2; }

# A typo'd path would otherwise be "fixed" by creating a fresh .env with two
# keys in it, which starts the stack with every other setting missing.
[ -f "$ENV_FILE" ] || {
    echo "ERROR: $ENV_FILE not found." >&2
    echo "       Run from the deploy directory (/opt/stratum-ai) or pass --file." >&2
    exit 1
}

for key in "${KEYS[@]}"; do
    if ! printf '%s' "$key" | grep -qE '^[A-Z][A-Z0-9_]*$'; then
        echo "ERROR: '$key' is not a valid variable name (A-Z, 0-9, _)" >&2
        exit 1
    fi
done

# -----------------------------------------------------------------------------
# --check: report presence, never values
# -----------------------------------------------------------------------------
if [ "$CHECK_ONLY" = true ]; then
    missing=0
    for key in "${KEYS[@]}"; do
        line="$(grep -E "^${key}=" "$ENV_FILE" | tail -n1 || true)"
        value="${line#*=}"
        if [ -z "$line" ]; then
            printf '%-32s %s\n' "$key" "<missing>"
            missing=1
        elif [ -z "$value" ]; then
            printf '%-32s %s\n' "$key" "<empty>"
            missing=1
        else
            printf '%-32s %s\n' "$key" "<set>"
        fi
    done
    [ "$missing" -eq 0 ] || exit 1
    exit 0
fi

# -----------------------------------------------------------------------------
# Collect values from hidden prompts
# -----------------------------------------------------------------------------
VALUES=()
for key in "${KEYS[@]}"; do
    printf 'Value for %s (input hidden): ' "$key" >&2
    value=""
    IFS= read -rs value || true
    printf '\n' >&2

    # An unquoted .env is what Settings and docker compose env_file both expect.
    # These three mistakes all produce a value that loads but is wrong, so they
    # are rejected here rather than discovered at OAuth time.
    case "$value" in
        "")       echo "ERROR: $key is empty. Set both keys of a pair or neither." >&2; exit 1 ;;
        \"*|\'*)  echo "ERROR: $key starts with a quote. .env values are unquoted." >&2; exit 1 ;;
        *[[:space:]]) echo "ERROR: $key has trailing whitespace — re-copy it." >&2; exit 1 ;;
    esac
    case "$value" in
        [[:space:]]*) echo "ERROR: $key has leading whitespace — re-copy it." >&2; exit 1 ;;
    esac

    VALUES+=("$value")
done

# -----------------------------------------------------------------------------
# Back up, then write atomically
# -----------------------------------------------------------------------------
backup="${ENV_FILE}.bak.$(date +%Y%m%d-%H%M%S)"
cp -p "$ENV_FILE" "$backup"
chmod 600 "$backup"

tmp="$(mktemp "${ENV_FILE}.tmp.XXXXXX")"
chmod 600 "$tmp"
trap 'rm -f "$tmp" "$tmp.next"' EXIT
cp "$ENV_FILE" "$tmp"

changed=0
for i in "${!KEYS[@]}"; do
    key="${KEYS[$i]}"
    value="${VALUES[$i]}"

    existing="$(grep -cE "^${key}=" "$tmp" || true)"

    if [ "$existing" -gt 0 ]; then
        # Rewrite every occurrence and keep the first, so a file that already
        # had the key twice comes out with one line rather than two.
        # The value goes through the environment, not -v: awk processes
        # backslash escapes in a -v assignment, so a secret containing \n
        # would be written as a real newline and split across two lines.
        _K="$key" _V="$value" awk '
            BEGIN { k = ENVIRON["_K"]; v = ENVIRON["_V"] }
            index($0, k "=") == 1 {
                if (!seen) { print k "=" v; seen = 1 }
                next
            }
            { print }
        ' "$tmp" > "$tmp.next"
        mv "$tmp.next" "$tmp"
        if [ "$existing" -gt 1 ]; then
            echo "note: collapsed $existing duplicate lines for $key" >&2
        fi
    else
        printf '%s=%s\n' "$key" "$value" >> "$tmp"
    fi
    changed=$((changed + 1))
    echo "set  $key=<set>"
done

chmod --reference="$ENV_FILE" "$tmp" 2>/dev/null || chmod 600 "$tmp"
mv "$tmp" "$ENV_FILE"
trap - EXIT

echo
echo "Wrote $changed key(s) to $ENV_FILE. Backup: $backup"
echo
echo "Verify, then apply:"
echo "  ./scripts/set-integration-env.sh --check ${KEYS[*]}"
echo "  ./scripts/deploy-beta.sh update"
echo
echo "A restart is not enough: env_file changes need the containers recreated."
