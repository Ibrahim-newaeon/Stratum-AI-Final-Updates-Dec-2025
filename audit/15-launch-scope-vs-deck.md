# Launch scope vs investor / sales claims

> **Snapshot of 2026-08-18.** Flag states and several findings have changed since;
> see [`README.md`](README.md) for the verified delta as of 2026-08-20.


**Date:** 2026-08-18 (re-verified against working tree after P1 patches)  
**Verdict change:** Phase A P1s (F-001–F-004) and F-005 are **closed in this tree**. Do not spend 2–4 days on them.  
**What still hits the deck:** seven capability areas are shelved off by default while sales materials mark them **Production**.

## 1. Closed findings (current tree)

| ID | Audit excerpt (stale) | Current code |
|----|----------------------|--------------|
| F-001 | `if not DOCS_API_KEY: return` | `docs_access_allowed` + 503 when key empty (`main.py:72-80`, `392-396`) |
| F-002 | `if not api_key: return True` | `return not require_key`; prod/staging pass `require_key=True` (`main.py:68`, metrics handler) |
| F-003 | `token: Optional[str] = Query` | Parameter removed; `extract_ws_access_token` / `bearer.<jwt>` (`main.py:86-101`, `923-948`) |
| F-004 | `USE_MOCK_AD_DATA:-true` | `:-false` (`docker-compose.yml:104`) |
| F-005 | Node 26 Dockerfile vs CI 24 | `frontend/Dockerfile` is `node:24-alpine` |

`needs_human_review: false` on the above — re-read, not inferred.

## 2. The real gap

`config.py:443-474` shelves seven surfaces. The sales kit (`features-sales-kit.html`) tags several of those same products **Production**.

| Flag | Default | Runtime if left off | Sales kit claim | Deck risk |
|------|---------|---------------------|-----------------|-----------|
| `enable_campaign_publish` | False | Publish endpoint 503; drafts stay (`campaign_builder.py:53-57`) | “Build once, publish to four platforms” + chip **Production** (`features-sales-kit.html:960-969`) | **High** — core product promise |
| `feature_automation_rules` | False | Entire `/rules` router 503 (`rules.py:41-45`) | “Customer-authored automation” + **Production** (`features-sales-kit.html:1057-1067`) | **High** — switching-cost story |
| `feature_competitor_intel` | False | Entire `/competitors` router 503 (`competitors.py:41-45`) | “Competitor intelligence / benchmarking” + **Production** (`features-sales-kit.html:1146-1175`) | **High** — fabricated if flag flipped |
| `feature_drip_campaigns` | False | Entire `/drip-campaigns` router 503 (`drip_campaigns.py:40-44`) | “Drip campaigns — lifecycle email sequences” (`features-sales-kit.html:1275`) | **High** — cited `endpoints/drip_campaigns.py` as evidence |
| `feature_knowledge_graph` | False | Entire KG router 503 (`knowledge_graph.py:33-40`) | Nav ships KG items (`dashboardNav.ts:328-346`) | **Medium** — UI present, API dead |
| `enable_campaign_builder_beat` | False | No live ad-account sync / token refresh beat | Implied by “pushed through the same adapter registry” (`features-sales-kit.html:969`) | **Medium** — drafts without live sync |
| `enable_newsletter_beat` | False | Scheduled send off; **manual send still works** | “Newsletter — subscriber management” (`features-sales-kit.html:1276`) | **Low** — product exists; schedule is opt-in |

Why the flags are off (code’s own comments, `config.py:443-474`):

- Publish: hardcoded SUCCESS, no platform call, no `platform_campaign_id`
- Rules: beat crashes on `rule.conditions` schema mismatch
- Competitors: `random.randint` benchmarks
- Drip: no execution engine; activate + `manual_trigger` are simulated
- Knowledge graph: Apache AGE not in the default image; routes 500 without it
- Campaign-builder beat / newsletter beat: live side effects, opt-in by design

## 3. UI still advertises the dead surfaces

Nav includes Rules, Newsletter, Drip, Knowledge Graph (`frontend/src/components/primitives/nav/dashboardNav.ts:232-491`).  
A demo or investor walkthrough that clicks those items gets **503**, not a “coming soon” empty state.

## 4. What is actually on for launch (defaults)

These flags default **on** and are the honest v1 story:

- Trust engine / autopilot enforcement
- What-if simulator (`feature_what_if_simulator=True`)
- GDPR (`feature_gdpr_compliance=True`)
- Campaign **draft** CRUD (publish only is gated)
- Newsletter **manual** send (beat off)
- CDP, EMQ, CAPI, attribution, pacing, reporting, Stripe

## 5. Decision for the deck (pick one)

**A — Strip the kit (days, not weeks)**  
Change `features-sales-kit.html` chips from Production → Shelved / Roadmap for entries 08 (publish), 10 (rules), 12 (competitor intel), 14 (drip). Hide or badge nav items when the flag is false.

**B — Build to the kit (weeks–months)**  
Do not flip flags. Each needs the missing engine first:

1. Real campaign publish adapter (not SUCCESS stub)
2. Reconcile rules schema + beat
3. Wire competitor worker to a real source (not `random.randint`)
4. Drip step-execution Celery task
5. Provision Apache AGE **or** keep KG off and remove nav

**C — Soft-launch narrative (recommended for fundraising this week)**  
Lead with Trust Gate + Autopilot + CDP/EMQ. Call Builder “drafts + approval, publish next.” Call Rules / Competitors / Drip / KG “built, gated, not in v1.” Do not say Production.

Flipping any of A’s four flags to `True` without the engine is worse than leaving them off: investors can click through to fake publish or random competitor numbers.

## 6. Checklist before the next deck send

- [ ] Sales kit chips match `config.py` defaults
- [ ] Battle card / landing does not claim live cross-platform publish
- [ ] Demo script never opens Rules, Competitors, Drip, or KG
- [ ] Newsletter demo uses **manual send**, not schedule
- [ ] No one sets `FEATURE_COMPETITOR_INTEL=true` or `ENABLE_CAMPAIGN_PUBLISH=true` on a hosted demo
