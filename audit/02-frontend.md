# Phase 2 — Frontend

## 1. Stack

| Layer | Choice | Evidence |
|-------|--------|----------|
| Framework | React 19.2.8 | `frontend/package.json:58-59` |
| Build | Vite 8.2.1 | `frontend/package.json:101` |
| Routing | react-router-dom 7.18 | `frontend/package.json:66` |
| State | Zustand + React Query | `package.json:38,71` |
| Styling | Tailwind 3 + Radix | `package.json:32-34,98` |
| Tests | Vitest 4 + Playwright | `package.json:91,79` |
| Error monitoring | Sentry React | `frontend/src/main.tsx:5`, `lib/sentry.ts:8` |

## 2. API Client & Auth Storage

Access tokens stored in **sessionStorage** (tab-scoped); refresh token same.

```23:40:frontend/src/api/client.ts
// Token management — use in-memory + sessionStorage to reduce XSS persistence
// (sessionStorage is cleared when the tab closes, unlike localStorage)
let accessToken: string | null = null;

export const setAccessToken = (token: string | null) => {
  accessToken = token;
  if (token) {
    sessionStorage.setItem('access_token', token);
  } else {
    sessionStorage.removeItem('access_token');
  }
};
```

Tenant ID persisted in **localStorage** (`client.ts:46-60`). User profile/demo flags also in localStorage (`AuthContext.tsx` grep hits).

401 handling: mutexed refresh → redirect `/login?reason=session_expired` (`client.ts:88-165`).

Runtime API URL: `window.__RUNTIME_CONFIG__?.VITE_API_URL` overrides build-time (`client.ts:10-12`).

## 3. XSS Controls

Central sanitizer for CMS/HTML content:

```5:10:frontend/src/lib/sanitize.ts
 * with dangerouslySetInnerHTML to prevent stored XSS attacks.
...
 * Sanitize HTML content for safe rendering via dangerouslySetInnerHTML.
```

Usages with `sanitizeHtml()` confirmed: `BlogPost.tsx:163`, `DocArticlePage.tsx:221`, legal pages, newsletter templates.

**Search:** `grep dangerouslySetInnerHTML frontend/src` → all reviewed hits pair with `sanitizeHtml` except `chart.tsx:91` (inline style injection for theming — review scope: chart CSS variables only).

## 4. Routing & Views

181 view TSX files under `frontend/src/views/`. Major areas: tenant dashboard, CDP, CMS, superadmin, console, WhatsApp, newsletter, portal, landing/marketing.

Build requires `VITE_API_URL` in production (`ci.yml:462-467` references `vite.config.ts` guard).

## 5. Design System

Primitive components per `CLAUDE.md:186-196`: Card, KPI, StatusPill, Chart, DataTable, ConfirmDrawer, Sidebar, Topbar, ThemeProvider — each with vitest.

Theme: dark/light via `ThemeProvider` + localStorage persistence (`ThemeProvider.tsx`).

## 6. Demo Mode

Demo context writes `stratum_demo_mode` to localStorage (`DemoContext.tsx`, `useDemoMode.ts`). Onboarding can skip via localStorage key (`OnboardingGuard.tsx:40`).

**Risk:** Demo path must not reach production billing/autopilot against live ad accounts — server-side `USE_MOCK_AD_DATA` is separate gate.

## 7. Frontend Findings

| ID | Sev | Title |
|----|-----|-------|
| F-005 | P2 | CI Node 24 vs Dockerfile Node 26 mismatch |
| F-007 | P2 | Ukrainian locale file exists but not registered in i18n |
| F-011 | P2 | tenant_id in localStorage increases XSS blast radius |
| F-006 | P2 | E2E tests not in release gate |

## 8. Positive Controls

- sessionStorage for bearer tokens (`client.ts:23-24`)
- Explicit removal of client-side superadmin bypass header (`client.ts:64`)
- DOMPurify wrapper for CMS HTML (`sanitize.ts`)
- Sentry + ErrorBoundary (`ErrorBoundary.tsx:9`)
- ESLint `--max-warnings 0` in CI (`package.json:9`, `ci.yml:436`)

## 9. Searches Run

```
grep "dangerouslySetInnerHTML" frontend/src/**/*.{tsx,ts}  → 6 files, 5 use sanitizeHtml
grep "localStorage" frontend/src/**/*.{tsx,ts}             → 20+ files
grep "gtag|mixpanel|posthog" frontend/src                  → 0 product analytics SDKs (Sentry only)
glob frontend/src/views/**/*.tsx                           → 181 files
glob frontend/e2e/*.ts                                     → 10 files
```

## 10. Open Questions

- **Production CDN / cache headers for static assets:** UNKNOWN — Vercel config exists (`vercel.json`) but deploy target not verified in evidence.
