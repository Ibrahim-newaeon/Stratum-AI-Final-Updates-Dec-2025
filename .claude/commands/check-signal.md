---
description: Analyze signal health, freshness, and trust-gate impact for a named signal
argument-hint: <signal_name>
allowed-tools: Read, Grep, Glob, Bash(grep:*), Bash(find:*), Bash(rg:*)
---

Analyze signal health for: $ARGUMENTS

## Steps

1. Locate signal definition in `backend/app/analytics/logic/` or `backend/app/services/`
2. Check signal collector implementation (`backend/app/workers/`)
3. Review signal health calculation logic (`backend/app/analytics/logic/signal_health.py`)
4. Identify potential degradation causes
5. Verify trust gate thresholds against `TrustGateConfig`

## Output

- Current health formula and weight contribution
- Data freshness requirements / SLA
- Failure modes (zero events, stale, malformed)
- Recommendations

For deep audits, delegate to the `signal-auditor` subagent.
