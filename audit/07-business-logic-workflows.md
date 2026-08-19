# Phase 7 — Business Logic & Workflows

## 1. Trust-Gated Autopilot

Core loop documented `CLAUDE.md:10-16`:

```
Signal Health → Trust Gate → EXECUTE | HOLD | BLOCK
```

Implementation:
- `analytics/logic/signal_health.py` — weighted components (EMQ 35%, API 25%, etc. per CLAUDE.md)
- `stratum/core/trust_gate.py` — PASS/HOLD/BLOCK with action-specific thresholds
- `autopilot/enforcer.py` — enforcement modes (Advisory / Soft-Block / Hard-Block)
- `autopilot/service.py` — queue, execute, audit

Tests: `test_autopilot_enforcer.py`, `test_autopilot_service.py`, `test_stratum_trust_gate.py`, `test_autopilot_execution_gate.py`, integration load test `tests/load/autopilot-enforcement-load-test.js`.

## 2. EMQ & QA Fixes

`qa_fixes.py` — one-click EMQ remediation:
- Lists issues, playbook, apply fix, history
- Tenant guard: `request.state.tenant_id != tenant_id` → 403 (`qa_fixes.py:76-77`)
- **No explicit permission** (e.g. CAMPAIGN_APPROVE) on apply endpoint

## 3. CDP Workflows

Profiles, segments, identity graph, audience sync, webhooks, GDPR export/erase endpoints under `cdp.py`, `gdpr.py`.

Webhook HMAC: secret generated at create (`cdp.py:2417-2425`), rotation endpoint (`cdp.py:2692-2731`).

## 4. Payments / Subscription

- Stripe checkout + webhooks (`payments.py`, `stripe_webhook.py`)
- Tier limits → HTTP 402 (`client.ts:168-177`)
- Idempotency via Redis SET NX (`stripe_webhook.py:51-77`) — fails open on Redis error

## 5. Campaign Builder

Publish gated off:

```453:457:backend/app/core/config.py
    # Campaign publish marks a draft PUBLISHED with no platform call ...
    enable_campaign_publish: bool = Field(default=False)
```

Draft CRUD available; publish returns 503 when disabled.

## 6. Shelved / Incomplete Features

| Feature | Status | Evidence |
|---------|--------|----------|
| Competitor intel | OFF — random data if enabled | `config.py:427-428` |
| Automation rules | OFF — schema mismatch | `config.py:428-429` |
| Drip campaigns | OFF — no execution engine | `config.py:449-452` |
| Knowledge graph | OFF — needs Apache AGE | `config.py:436-440` |

## 7. Business Logic Findings

| ID | Sev | Title |
|----|-----|-------|
| F-009 | P2 | Stripe webhook duplicate processing if Redis down |
| F-014 | P2 | Campaign publish disabled — incomplete go-live path |
| F-013 | P2 | Competitor intel fabricates data when flag enabled |

## 8. Workflow Validation Checklist

- [ ] Autopilot never executes when signal_health < 70 (trust gate tests)
- [ ] EMQ apply fix audited in history endpoint
- [ ] Stripe subscription state matches tenant tier after webhook
- [ ] GDPR erase removes PII and revokes tokens
- [ ] Audience sync respects platform OAuth token refresh

## 9. Positive Controls

- Explicit feature flags for immature automation (`config.py:426-457`)
- Trust gate high-risk actions require 80+ health (`trust_gate.py:49-59`)
- Emergency stop always allowed (`trust_gate.py:72-77`)
- Load test on main for autopilot enforcement (`ci.yml:849-854`)

## 10. Searches Run

```
read config.py feature_* flags lines 426-457
read trust_gate.py thresholds 44-77
grep "enable_campaign_publish" backend/  → config + endpoints
glob backend/tests/**/test_autopilot*.py  → 6+ files
glob backend/tests/**/test_gdpr*.py       → test_gdpr_api.py
```
