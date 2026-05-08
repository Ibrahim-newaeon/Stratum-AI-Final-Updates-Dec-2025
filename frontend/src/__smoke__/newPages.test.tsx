/**
 * Module-load smoke tests for the pages added in this branch's session.
 *
 * Catches the "wide" failure modes — syntax errors, missing imports,
 * broken type-only imports, missing default export — without paying
 * the cost of full render mocks per page. Each entry verifies:
 *
 *   1. The module imports cleanly (Vite resolves all `import` paths)
 *   2. It exposes a default-exported function (the React component)
 *
 * Render-time bugs are caught by the per-feature tests where they
 * exist, or by `tsc` for type-level issues. This keeps the suite
 * fast and gives us a safety net for pages that are otherwise
 * uncovered.
 */

import { describe, it, expect } from 'vitest';

const NEW_PAGES: { name: string; loader: () => Promise<{ default: unknown }> }[] = [
  // Phase C — platform-owner console pages
  {
    name: 'console/FeatureFlags',
    loader: () => import('@/views/console/FeatureFlags'),
  },
  {
    name: 'console/PlatformAnalytics',
    loader: () => import('@/views/console/PlatformAnalytics'),
  },
  {
    name: 'console/CrossTenantAnomalies',
    loader: () => import('@/views/console/CrossTenantAnomalies'),
  },
  // Phase 6 (post-merge audit) — console credentials health
  {
    name: 'console/Credentials',
    loader: () => import('@/views/console/Credentials'),
  },
  // audit_services first slice — read-only operator status pane
  {
    name: 'console/AuditServices',
    loader: () => import('@/views/console/AuditServices'),
  },
  // Phase H — GDPR data-rights page
  {
    name: 'GDPR',
    loader: () => import('@/views/GDPR'),
  },
  // Phase I — workspace API key management
  {
    name: 'APIKeys',
    loader: () => import('@/views/APIKeys'),
  },
  // Phase J — unified Integrations hub (rendered inside Settings)
  {
    name: 'tenant/IntegrationsHub',
    loader: () => import('@/views/tenant/IntegrationsHub'),
  },
  // Backend-feature surface — EMQ v2 diagnostics
  {
    name: 'EMQDiagnostics',
    loader: () => import('@/views/EMQDiagnostics'),
  },
  // Backend-feature surface — analytics_ai recommendations + KPIs
  {
    name: 'AIRecommendations',
    loader: () => import('@/views/AIRecommendations'),
  },
];

describe('module-load smoke — pages added in this branch', () => {
  it.each(NEW_PAGES)('$name resolves and exposes a default export', async ({ loader }) => {
    const mod = await loader();
    expect(mod).toBeTruthy();
    expect(typeof mod.default).toBe('function');
  });
});
