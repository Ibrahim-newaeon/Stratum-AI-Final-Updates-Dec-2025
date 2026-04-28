---
description: Debug a trust-gate HOLD or BLOCK — find the root cause and propose a fix
argument-hint: <gate_id|tenant_id|incident>
allowed-tools: Read, Grep, Glob, Bash(grep:*), Bash(rg:*), Bash(git log:*), Bash(git diff:*)
---

Debug trust gate failure for: $ARGUMENTS

## Investigation

1. Check recent signal health scores for the affected tenant
2. Review gate evaluation logs (`backend/app/autopilot/`, structured logs)
3. Check for anomaly flags in `backend/app/analytics/logic/anomalies.py`
4. Verify data freshness — when did each component signal last update?
5. Look for config drift: diff `TrustGateConfig` vs. defaults
6. Check enforcement mode (Advisory / Soft-Block / Hard-Block)

## Output

- Root cause analysis with `file:line` citations
- Which signal component (EMQ / API Health / Event Loss / Platform Stability / Data Quality) drove the score down
- Recommended fix (config, code, or data)
- Prevention measures (test, alert, monitoring)
