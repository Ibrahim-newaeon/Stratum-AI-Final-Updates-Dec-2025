#!/usr/bin/env bash
# PostToolUse hook: auto-format files after Edit/Write/MultiEdit.
# Reads the JSON event from stdin, extracts the touched file path, and runs
# the appropriate formatter. Failures are logged but never block the tool result.

set -uo pipefail

# Read the hook event payload from stdin
payload="$(cat)"

# Extract the file path from the tool input. Supports Edit/Write/MultiEdit.
file_path="$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    ti = data.get("tool_input", {}) or {}
    print(ti.get("file_path") or ti.get("path") or "")
except Exception:
    print("")
' 2>/dev/null)"

if [[ -z "${file_path}" || ! -f "${file_path}" ]]; then
  exit 0
fi

case "${file_path}" in
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      ruff format "${file_path}" >/dev/null 2>&1 || true
      ruff check --fix --quiet "${file_path}" >/dev/null 2>&1 || true
    fi
    ;;
  *.ts|*.tsx|*.js|*.jsx|*.json|*.css|*.md)
    if [[ -d "$(dirname "${file_path}")/node_modules" ]] || [[ -f "frontend/package.json" ]]; then
      if command -v npx >/dev/null 2>&1; then
        (cd frontend 2>/dev/null && npx --no-install prettier --write "${file_path}" >/dev/null 2>&1) || true
      fi
    fi
    ;;
esac

exit 0
