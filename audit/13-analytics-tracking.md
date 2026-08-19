# Phase 13 — Analytics & Tracking

## 1. Product Analytics (Client)

**Search:** `grep -r "gtag\|mixpanel\|posthog\|plausible\|segment\.track\|analytics\.track" frontend/src`

**Result:** 0 third-party product analytics SDK integrations.

Matches for "google-analytics" refer to **integration setup UI** (connecting customer GA accounts), not Stratum's own telemetry:

```1311:1311:frontend/src/views/Settings.tsx
      id: 'google-analytics',
```

GTM placeholder in platform setup modal (`PlatformSetupModal.tsx:830-831`).

## 2. Error & Performance Monitoring

| Tool | Where |
|------|-------|
| Sentry (frontend) | `main.tsx:5`, `lib/sentry.ts`, `ErrorBoundary.tsx` |
| Sentry (backend) | `main.py:117-163` when `SENTRY_DSN` set |

No evidence of browser RUM beyond Sentry tracing integration (`main.tsx` imports `browserTracingIntegration`).

## 3. Server-Side / Marketing Analytics

**UNKNOWN — not present in available evidence:**
- Server-side GA4 / Meta Pixel on marketing site
- Cookie consent banner implementation for EU traffic
- Event taxonomy document for product funnel

Landing pages exist (`Landing.tsx`, `LandingAr.tsx`) — tracking scripts not verified in this audit pass.

## 4. CDP / EMQ (Product Domain, Not Web Analytics)

Platform's core "analytics" is **advertising signal quality** (EMQ, signal health, attribution) — server-side in `backend/app/analytics/logic/`, not browser tracking.

## 5. Audit Logging (Compliance Analytics)

`AuditMiddleware` logs state-changing API actions (`main.py:414-415`).

Tenant audit log UI: `frontend/src/views/tenant/AuditLog.tsx`.

## 6. Findings

| ID | Sev | Title |
|----|-----|-------|
| — | P2 | No documented first-party web analytics / consent strategy in repo |
| — | P3 | Cannot verify marketing conversion tracking without deployed HTML review |

0 P0/P1 findings — absence of third-party trackers reduces GDPR cookie scope but also limits funnel visibility.

## 7. Positive Controls

- No silent third-party tracker SDKs in frontend bundle (grep verified)
- Sentry configured with `send_default_pii=False` on backend
- Customer GA/GTM handled as **integration** (tenant-scoped credentials), not embedded in Stratum SPA by default

## 8. Searches Run

```
grep "gtag|mixpanel|posthog|plausible" frontend/src     → 0 product analytics
grep "@sentry" frontend/src                             → main.tsx, sentry.ts, ErrorBoundary
grep "google-analytics" frontend/src                    → Settings integration UI only
grep "cookie|consent|gdpr" frontend/src/views/pages/legal  → Privacy.tsx, DPA.tsx exist
```

## 9. Recommendations (if product analytics desired)

1. Document decision: no first-party analytics vs add Plausible/PostHog with consent banner
2. If added, wire through `feature_flags` and tenant privacy settings
3. Keep advertising EMQ metrics separate from web product analytics taxonomy

## 10. Missing Data

- Production landing page rendered HTML: **UNKNOWN**
- Actual Sentry DSN configured in prod: **UNKNOWN**
