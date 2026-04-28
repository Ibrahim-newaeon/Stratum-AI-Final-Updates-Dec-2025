#!/usr/bin/env bash
# PreToolUse hook for Bash: block destructive commands by default.
# Exit 0 = allow. Exit 2 = block (stderr is shown to Claude).
# This is a safety net, not a substitute for review.

set -uo pipefail

payload="$(cat)"

# Extract the bash command being run
command_str="$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    print((data.get("tool_input", {}) or {}).get("command", ""))
except Exception:
    print("")
' 2>/dev/null)"

if [[ -z "${command_str}" ]]; then
  exit 0
fi

deny() {
  echo "BLOCKED by .claude/hooks/block-dangerous-bash.sh: $1" >&2
  echo "Command: ${command_str}" >&2
  echo "If this is intentional, ask the user to run it manually or update the hook." >&2
  exit 2
}

# Force-push to protected branches
if echo "${command_str}" | grep -Eq 'git[[:space:]]+push.*--force.*\b(main|master|production)\b'; then
  deny "force-push to protected branch"
fi
if echo "${command_str}" | grep -Eq 'git[[:space:]]+push.*-f[[:space:]].*\b(main|master|production)\b'; then
  deny "force-push to protected branch"
fi

# Hard reset on shared branches
if echo "${command_str}" | grep -Eq 'git[[:space:]]+reset[[:space:]]+--hard[[:space:]]+(origin/)?(main|master|production)'; then
  deny "hard reset of a shared branch"
fi

# Branch deletion of protected branches
if echo "${command_str}" | grep -Eq 'git[[:space:]]+branch[[:space:]]+-D[[:space:]]+(main|master|production)'; then
  deny "force-delete of a protected branch"
fi

# rm -rf danger zones
if echo "${command_str}" | grep -Eq 'rm[[:space:]]+(-[a-zA-Z]*r[a-zA-Z]*f|-rf|-fr)[[:space:]]+(/|~|\$HOME|/\*|/[a-z])'; then
  deny "rm -rf targeting filesystem root or home"
fi

# Skipping commit hooks without explicit user request
if echo "${command_str}" | grep -Eq 'git[[:space:]]+commit.*--no-verify'; then
  deny "git commit --no-verify (hooks exist for a reason)"
fi

# Production database operations
if echo "${command_str}" | grep -Eq '(DROP|TRUNCATE)[[:space:]]+(TABLE|DATABASE|SCHEMA)' ; then
  deny "DROP/TRUNCATE statement detected"
fi

# Pushing .env files
if echo "${command_str}" | grep -Eq 'git[[:space:]]+(add|commit).*\.env([[:space:]]|$)' && \
   ! echo "${command_str}" | grep -q '\.env\.example'; then
  deny "attempt to commit a .env file"
fi

exit 0
