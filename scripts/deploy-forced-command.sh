#!/usr/bin/env bash
# =============================================================================
# Forced command for the GitHub Actions deploy key
# =============================================================================
# INSTALLED COPY LIVES AT /opt/stratum/deploy-forced-command.sh on the server.
# This file is the reviewable original -- editing it here changes nothing until
# it is copied over, because authorized_keys pins the server path. Kept in the
# repo so the restriction is auditable and can be restored.
#
# Referenced from /root/.ssh/authorized_keys as:
#   command="/opt/stratum/deploy-forced-command.sh",no-agent-forwarding,
#   no-port-forwarding,no-pty,no-user-rc,no-X11-forwarding ssh-ed25519 AAAA...
# Pinned in authorized_keys, so this is the only thing that key can run --
# holding it does not grant a root shell. It accepts three commands, fast-
# forwards the checkout, and hands over to the deploy script from the repo so
# the deploy steps are reviewed alongside the code they ship.
set -euo pipefail

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

case "${SSH_ORIGINAL_COMMAND:-}" in
  'deploy staging') TARGET=staging; DIR=/opt/stratum-staging ;;
  'deploy prod')    TARGET=prod;    DIR=/opt/stratum ;;
  'status')
    for d in /opt/stratum /opt/stratum-staging; do
      [ -d "$d/.git" ] || continue
      git -C "$d" fetch --quiet origin 2>/dev/null || true
      printf '%s HEAD=%s behind=%s\n' "$d"         "$(git -C "$d" rev-parse --short HEAD)"         "$(git -C "$d" rev-list --count HEAD..origin/main 2>/dev/null || echo '?')"
    done
    exit 0 ;;
  *)
    echo "refused: this key runs only 'deploy staging', 'deploy prod' or 'status'" >&2
    exit 1 ;;
esac

log "fast-forwarding $DIR to origin/main"
git -C "$DIR" fetch --quiet origin
git -C "$DIR" reset --hard --quiet origin/main
git -C "$DIR" log --oneline -1

exec bash "$DIR/scripts/deploy-remote.sh" "$TARGET"
