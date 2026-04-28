#!/usr/bin/env bash
# PostToolUse rule-check hook — fast pattern scan after every Edit/Write/MultiEdit.
#
# Goal: surface likely violations of the rules encoded in .claude/agents/*.md
# the moment they're introduced, so Claude (or the user) can react before
# the file is committed.
#
# Design choices:
#   - Pure grep / shell — no LLM calls, no network, no DB. Fast (<50ms).
#   - WARN by default (exit 0 with stderr) — false positives are common in
#     pattern matching, so we never block routine edits.
#   - BLOCK (exit 2) only on patterns that almost never false-positive:
#     known vendor token formats, client_secret in frontend code.
#   - Each warning names the matching agent to invoke for a deep review.

set -uo pipefail

payload="$(cat)"

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

WARNINGS=()
BLOCKING=()

add_warn()  { WARNINGS+=("$1"); }
add_block() { BLOCKING+=("$1"); }

# Helper: grep for a pattern in the file and act if found
match_in_file() {
  grep -qE "$1" "${file_path}" 2>/dev/null
}

# ---------------------------------------------------------------------------
# Universal Python checks (apply to any backend/*.py)
# ---------------------------------------------------------------------------
case "${file_path}" in
  *backend/app/*.py | *backend/tests/*.py | *backend/scripts/*.py)
    # 1. Vendor token literals — BLOCKING, almost never false-positive
    if match_in_file '(sk|pk)_(test|live)_[a-zA-Z0-9]{16,}|AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|xox[baprs]-[a-zA-Z0-9-]+|EAA[a-zA-Z0-9]{20,}'; then
      add_block "vendor API token literal detected in ${file_path}"
    fi

    # 2. Generic hardcoded credential heuristic — WARN
    if match_in_file '(api_key|apikey|secret|password|passwd|access_token|refresh_token)[[:space:]]*=[[:space:]]*"[a-zA-Z0-9_\-]{16,}"'; then
      add_warn "possible hardcoded credential in ${file_path} — invoke secret-leak-reviewer"
    fi

    # 3. Secret being logged — WARN
    if match_in_file 'logger\.(info|debug|warning|error|exception)[[:space:]]*\([^)]*\b(token|secret|password|access_token|refresh_token|api_key)\b'; then
      add_warn "credential likely being logged in ${file_path} — invoke secret-leak-reviewer"
    fi

    # 4. random module used for security purposes — WARN
    if match_in_file '^import random|^from random import' && \
       match_in_file 'random\.(choice|randint|random|sample|getrandbits)' && \
       match_in_file '(token|secret|password|key|otp|nonce|session)'; then
      add_warn "random used near security-sensitive code in ${file_path} — use 'secrets' module per CLAUDE.md"
    fi

    # 5. datetime.utcnow() — WARN (CLAUDE.md rule)
    if match_in_file 'datetime\.utcnow\(\)'; then
      add_warn "datetime.utcnow() in ${file_path} — use datetime.now(timezone.utc) per CLAUDE.md"
    fi

    # 6. Bare except / except BaseException — WARN
    if match_in_file '^[[:space:]]*except[[:space:]]*:|except[[:space:]]+BaseException'; then
      add_warn "bare 'except:' or 'except BaseException' in ${file_path} — handle specific exceptions"
    fi
    ;;
esac

# ---------------------------------------------------------------------------
# API endpoint checks
# ---------------------------------------------------------------------------
case "${file_path}" in
  *backend/app/api/v1/endpoints/*.py | *backend/app/api/*.py)
    # tenant_id in Pydantic request body — almost certainly wrong
    if match_in_file 'class[[:space:]]+\w+(Create|Update|Patch|Request)[[:space:]]*\([^)]*BaseModel'; then
      if match_in_file 'tenant_id[[:space:]]*:[[:space:]]*(int|str|UUID|uuid\.UUID)'; then
        add_warn "tenant_id field in Pydantic request schema in ${file_path} — must come from auth, not body. Invoke api-endpoint-reviewer + tenancy-auditor"
      fi
    fi

    # Mutating route without an auth dependency — WARN
    if match_in_file '@(router|app)\.(post|put|patch|delete)' && \
       ! match_in_file 'Depends\([[:space:]]*(get_current_user|get_current_tenant|require_auth|require_admin)' && \
       ! match_in_file '#[[:space:]]*PUBLIC:'; then
      add_warn "mutating route in ${file_path} without auth Depends and no '# PUBLIC:' marker — invoke api-endpoint-reviewer"
    fi

    # Route returning a dict (no response_model) — WARN
    if match_in_file '@(router|app)\.(get|post|put|patch|delete)' && \
       ! match_in_file 'response_model[[:space:]]*='; then
      add_warn "route in ${file_path} missing response_model — invoke api-endpoint-reviewer"
    fi
    ;;
esac

# ---------------------------------------------------------------------------
# Celery task checks
# ---------------------------------------------------------------------------
case "${file_path}" in
  *backend/app/workers/*.py | *backend/app/services/**/tasks*.py)
    if match_in_file '@(app|shared_task|celery_app)\.task'; then
      # bind=True missing
      if ! match_in_file 'bind=True'; then
        add_warn "Celery task in ${file_path} missing bind=True — invoke celery-task-reviewer"
      fi
      # max_retries missing
      if ! match_in_file 'max_retries[[:space:]]*='; then
        add_warn "Celery task in ${file_path} missing max_retries — invoke celery-task-reviewer"
      fi
    fi

    # async session held across an external call — heuristic
    # Look for `await ...client...|httpx|requests` inside `async with .* session`
    if match_in_file 'async with[[:space:]]+[^)]*session' && \
       match_in_file 'await[[:space:]]+(httpx|requests|self\.client|.*_client\.)'; then
      add_warn "async DB session may be held across external call in ${file_path} — invoke celery-task-reviewer"
    fi
    ;;
esac

# ---------------------------------------------------------------------------
# Migration checks
# ---------------------------------------------------------------------------
case "${file_path}" in
  *backend/migrations/versions/*.py | *backend/alembic/versions/*.py)
    if match_in_file 'op\.add_column\([^)]*nullable=False' && \
       ! match_in_file 'server_default'; then
      add_warn "migration adds NOT NULL column without server_default in ${file_path} — invoke migration-auditor"
    fi
    if match_in_file 'op\.create_index\(' && \
       ! match_in_file 'postgresql_concurrently=True'; then
      add_warn "migration creates index without CONCURRENTLY in ${file_path} — invoke migration-auditor"
    fi
    if match_in_file 'op\.drop_(column|table|constraint)\('; then
      add_warn "migration drops a column/table/constraint in ${file_path} — confirm expand/contract with migration-auditor"
    fi
    if match_in_file 'def downgrade\(\):[[:space:]]*$' || \
       match_in_file 'def downgrade\(\)[[:space:]]*->[^:]*:[[:space:]]*pass'; then
      add_warn "empty downgrade() in migration ${file_path} — invoke migration-auditor"
    fi
    ;;
esac

# ---------------------------------------------------------------------------
# Trust engine checks
# ---------------------------------------------------------------------------
case "${file_path}" in
  *backend/app/autopilot/*.py | *backend/app/analytics/logic/signal_health.py | *backend/app/stratum/core/trust_gate.py)
    # Hardcoded threshold near words health/score/emq — WARN
    if match_in_file '\b(score|health|emq|trust)\b[^=]*[<>]=?[[:space:]]*(70|40)\b'; then
      add_warn "possible hardcoded trust threshold (70/40) in ${file_path} — read from TrustGateConfig. Invoke trust-gate-reviewer"
    fi
    # skip_gate / force / override flags — WARN
    if match_in_file '(skip_gate|force_execute|override_gate)[[:space:]]*=[[:space:]]*True'; then
      add_warn "trust-gate override flag set in ${file_path} — verify admin permission and audit log. Invoke trust-gate-reviewer"
    fi
    ;;
esac

# ---------------------------------------------------------------------------
# Frontend checks
# ---------------------------------------------------------------------------
case "${file_path}" in
  *frontend/src/*.ts | *frontend/src/*.tsx | *frontend/src/**/*.ts | *frontend/src/**/*.tsx)
    # client_secret in frontend — BLOCKING
    if match_in_file '(client_secret|service_account|private_key)[[:space:]]*[:=]'; then
      add_block "client_secret/service_account/private_key referenced in frontend ${file_path}"
    fi

    # Vendor tokens — BLOCKING
    if match_in_file '(sk|pk)_(test|live)_[a-zA-Z0-9]{16,}|AKIA[0-9A-Z]{16}'; then
      add_block "vendor API token literal in frontend ${file_path}"
    fi

    # console.log of user/response/token — WARN
    if match_in_file 'console\.(log|debug|info)[[:space:]]*\([^)]*(user|email|response|token|access_token)'; then
      add_warn "console.log of user/response/token in ${file_path} — invoke frontend-reviewer"
    fi

    # useQuery without queryKey
    if match_in_file 'useQuery[[:space:]]*\(' && \
       ! match_in_file 'queryKey[[:space:]]*:'; then
      add_warn "useQuery in ${file_path} appears to lack queryKey — invoke frontend-reviewer"
    fi

    # useMutation without onSuccess invalidation hint
    if match_in_file 'useMutation[[:space:]]*\(' && \
       ! match_in_file 'invalidateQueries|setQueryData|onSuccess'; then
      add_warn "useMutation in ${file_path} without invalidateQueries/onSuccess — UI may show stale data. Invoke frontend-reviewer"
    fi
    ;;
esac

# ---------------------------------------------------------------------------
# Emit results
# ---------------------------------------------------------------------------
emit() {
  local prefix="$1" ; shift
  for msg in "$@"; do
    printf '%s %s\n' "${prefix}" "${msg}" >&2
  done
}

if (( ${#BLOCKING[@]} > 0 )); then
  echo "" >&2
  echo "BLOCKED by .claude/hooks/rule-check.sh — catastrophic pattern detected:" >&2
  emit "  ✗" "${BLOCKING[@]}"
  if (( ${#WARNINGS[@]} > 0 )); then
    echo "" >&2
    echo "Additional warnings on the same file:" >&2
    emit "  ⚠" "${WARNINGS[@]}"
  fi
  echo "" >&2
  echo "Fix the blocking issue and try again. If this is a false positive, edit .claude/hooks/rule-check.sh." >&2
  exit 2
fi

if (( ${#WARNINGS[@]} > 0 )); then
  echo "" >&2
  echo "🚨 .claude/hooks/rule-check.sh — possible rule violations on ${file_path}:" >&2
  emit "  ⚠" "${WARNINGS[@]}"
  echo "" >&2
  echo "These are pattern-based hints, not verdicts. Invoke the named agent to confirm." >&2
fi

exit 0
