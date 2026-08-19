# Phase 4 — API Contract

## 1. Router Structure

Central aggregator: `backend/app/api/v1/__init__.py` — **67** `include_router` calls.

Prefix: `/api/v1` (`config.py:49`, mounted in `main.py`).

Superadmin routes wrapped with `require_super_admin` dependency at inclusion time (`__init__.py:79`).

Feature-gated routers use `FeatureGate` dependency (import `__init__.py:80`).

## 2. Endpoint Modules (68 files)

Full list from glob `backend/app/api/v1/endpoints/*.py`:

auth, mfa, users, tenants, tenant_dashboard, dashboard, cdp, emq_v2, capi, meta_capi, autopilot, autopilot_enforcement, trust_layer, campaigns, campaign_builder, audience_sync, analytics, advanced_analytics, analytics_ai, attribution, data_driven_attribution, pacing, profit, reporting, payments, stripe_webhook, subscription, tier, oauth, integrations, webhooks, whatsapp, cms, landing_cms, newsletter, gdpr, compliance, superadmin, superadmin_analytics, copilot, onboarding, onboarding_agent, feature_flags, launch_readiness, assets, api_keys, developer, qa_fixes, rules, competitors, simulator, knowledge_graph, ml_training, predictions, intelligence, programmatic, embed_widgets, clients, audit_services, changelog, notifications, push_notifications, drip_campaigns, sendgrid_webhook, slack, insights, outbound_integrations, tier, meta_capi, ...

## 3. OpenAPI / Docs

- Swagger UI: `/docs`, ReDoc: `/redoc`, schema: `/openapi.json`
- Production: custom routes replace defaults when `settings.is_production` (`main.py:324-378`)
- Protection: optional `DOCS_API_KEY` query param — **open if unset** (`main.py:343-345`)

## 4. Public / Unauthenticated Surface

From `middleware/tenant.py:25-51`:

| Path | Purpose |
|------|---------|
| `/health`, `/health/ready`, `/health/live` | Probes |
| `/metrics` | Prometheus (separate API key gate in handler) |
| `/docs`, `/redoc`, `/openapi.json` | API docs |
| `/api/v1/auth/*` | Login, register, refresh, password reset, OTP |
| `/public/events/stream` | Landing demo SSE (`main.py:756`) |

Webhooks (Stripe, SendGrid, Meta, WhatsApp) bypass tenant middleware via public path matching — verify each handler performs its own signature check.

## 5. Response Envelope

Standard wrapper: `APIResponse[T]` in `schemas/response.py` (used across endpoints e.g. `qa_fixes.py:26`).

Frontend expects `{ success, data }` on refresh (`client.ts:134-136`).

## 6. Auth Dependency Pattern

Most mutating routes rely on **TenantMiddleware** populating `request.state` rather than explicit `Depends(get_current_user)`.

**Search:** `grep Depends(get_current_user) backend/app/api/**/*.py` → sparse hits (audit_services, cdp, mfa, pacing, etc.) — **not universal**.

Implication: new endpoints must ensure middleware runs and check `request.state.tenant_id` / permissions consistently.

## 7. API Contract Findings

| ID | Sev | Title |
|----|-----|-------|
| F-001 | P1 | OpenAPI exposed without DOCS_API_KEY |
| F-002 | P1 | /metrics tenant-exempt + optional auth |
| F-003 | P1 | WS ?token= query parameter |

## 8. Contract Validation Checklist

- [ ] Generate OpenAPI from running prod build and diff against `backend/docs/**/api-contracts.md`
- [ ] Verify every webhook route has signature verification (Stripe: yes — `stripe_webhook.py:159-161`)
- [ ] Confirm 503 for feature-gated routers when flags false
- [ ] Run integration suite: 706+ tests, floor 600 (`ci.yml:227`)

## 9. Searches Run

```
glob backend/app/api/v1/endpoints/*.py     → 68 files
grep include_router api/v1/__init__.py     → 67
grep "Depends(get_current_user)" backend/app/api  → partial coverage pattern
grep PUBLIC_ENDPOINTS tenant.py            → 25-51
```

## 10. Conflicts

| Source A | Source B | Issue |
|----------|----------|-------|
| `CLAUDE.md` "50+ endpoints" | 68 endpoint modules | Doc undercount — cosmetic |
| Tenant middleware auth | Per-route Depends | Dual pattern — needs discipline |

`needs_human_review: true` for auth dependency convention.
