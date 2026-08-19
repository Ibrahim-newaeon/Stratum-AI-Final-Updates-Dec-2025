# Production readiness audit — 2026-08-18

A read-only audit of the repository at commit `17d40c3a`, split by area.
Sixteen documents plus `findings.json`, which is the machine-readable form
of the same findings.

**These files are a dated snapshot and are kept as one.** They are not
maintained in place, because the value of an audit is what was true on the
day it ran. The delta below is where "what is true now" lives.

## Read this first — what changed since the audit ran

Verified against the working tree on **2026-08-20**, at `15649873`.
Eleven PRs (#700–#715) landed in between.

### Findings

| ID | Audit verdict (08-18) | Status 08-20 | Evidence |
|----|----------------------|--------------|----------|
| F-001 – F-004 | P1, blocking | **Closed** | Re-verified in-tree the same day; see `15-launch-scope-vs-deck.md` §1 |
| F-005 | P2 — Node 26 vs CI 24 | **Closed** | `frontend/Dockerfile` is `node:24-alpine` |
| F-006 | P2 — E2E outside the release gate | **Closed** | `.github/workflows/ci.yml:495` defines the `e2e` job; it is in the gate's `needs:` at line 748 |
| F-013 | P2 — competitor intel fabricates data | **Closed** | #707/#708 stopped `_apply_scan_result` inventing spend/impressions/CTR; it now records only sourced fields and marks `data_source="website_scrape"` |
| F-014 | P2 — campaign publish has no platform call | **Open, deliberate** | `config.py:492` keeps `enable_campaign_publish` off; needs a real publish adapter, not a flag flip |
| F-010 | P2 — conflicting env templates | **Not re-verified.** Five templates still coexist: `.env.example`, `.env.hetzner.template`, `.env.production.example`, `.env.production.template`, `backend/.env.example` |

Findings not listed above were not re-checked on 08-20. Absence from this
table means unverified, not closed.

### Launch flags

`15-launch-scope-vs-deck.md` §2 tabulates seven shelved flags. Three have
since been un-gated, so that table now misstates the position:

| Flag | Audit (08-18) | `config.py` default now | |
|------|---------------|-------------------------|--|
| `feature_automation_rules` | off | **`True`** | #700 — the schema mismatch it was gated for was fixed back in `ff6823ca` |
| `feature_competitor_intel` | off | **`True`** | #707/#708 — fabricated benchmarks removed first |
| `enable_newsletter_beat` | off | **`True`** | #702 — kept as an operator kill switch |
| `feature_knowledge_graph` | off | `False` | Stack complete (#703, #704, #709–#713). Enabled **per environment**, only after `scripts/backfill_knowledge_graph.py` has run there — see `backend/app/workers/celery_app.py:258-262` for why |
| `enable_campaign_builder_beat` | off | `False` | Blocked on live platform credentials |
| `enable_campaign_publish` | off | `False` | Deferred — needs its own spec |
| `feature_drip_campaigns` | off | `False` | Deferred — no execution engine exists |

The audit's headline finding still stands: `features-sales-kit.html` marks
several of the still-off flags **Production**. Four of seven surfaces are
now honest; publish, drip, and the builder beat are not.

## Index

| File | Covers |
|------|--------|
| `00-inventory.md` | Repo inventory and scale |
| `01-architecture.md` | System architecture, module boundaries |
| `02-frontend.md` | React/TypeScript surface |
| `03-backend.md` | FastAPI services and middleware |
| `04-api-contract.md` | Endpoint contract conformance |
| `05-data-layer.md` | Models, migrations, query patterns |
| `06-auth-security.md` | AuthN/AuthZ, MFA, secrets handling |
| `07-business-logic-workflows.md` | Trust gate, autopilot, campaign flows |
| `08-infra-devops.md` | Compose stacks, deploy, backups |
| `09-observability.md` | Metrics, alerts, logging |
| `10-testing-quality.md` | Suite composition and coverage |
| `11-performance-scalability.md` | Hot paths and limits |
| `12-ux-a11y-i18n.md` | Accessibility and localisation |
| `13-analytics-tracking.md` | Instrumentation |
| `14-compliance-legal-cost.md` | GDPR/CCPA posture, cost model |
| `15-launch-scope-vs-deck.md` | Shipped scope vs sales claims |
| `99-production-plan.md` | Phased remediation plan |
| `findings.json` | All findings, machine-readable |
