/**
 * Dashboard view smoke tests.
 *
 * One assertion per view: it imports cleanly and the lazy-loaded
 * component is a function (not undefined / not throwing on module
 * evaluation). This is the lightest possible coverage — far below a
 * proper integration test — but it catches the most common
 * regressions:
 *
 *   • Broken default export after a refactor
 *   • Top-level side-effect crash (e.g., the AuthContext module-load
 *     issue P9 fixed)
 *   • Bad import path / typo
 *   • TypeScript compiles but runtime ESM resolution fails
 *
 * Real per-view rendering tests would need to mock the entire React
 * Query / Router / Auth / i18n chain per view. Those land separately
 * (one file per view) and only after the live-data adapter
 * stabilizes.
 */

import { describe, it, expect } from 'vitest';

const viewModules: Record<string, () => Promise<{ default: unknown }>> = {
  Overview: () => import('../dashboard/Overview'),
  Campaigns: () => import('../Campaigns'),
  Settings: () => import('../Settings'),
  IntegrationHub: () => import('../IntegrationHub'),
  AIInsights: () => import('../AIInsights'),
  ComplianceDashboard: () => import('../ComplianceDashboard'),
  CohortAnalysis: () => import('../CohortAnalysis'),
  FunnelAnalysis: () => import('../FunnelAnalysis'),
  CustomDashboard: () => import('../CustomDashboard'),
  CustomReportBuilder: () => import('../CustomReportBuilder'),
  DeveloperPortal: () => import('../DeveloperPortal'),
  SQLEditor: () => import('../SQLEditor'),
  Stratum: () => import('../Stratum'),
  Predictions: () => import('../Predictions'),
  Rules: () => import('../Rules'),
  CDPDashboard: () => import('../cdp/CDPDashboard'),
  CDPProfiles: () => import('../cdp/CDPProfiles'),
  CDPSegments: () => import('../cdp/CDPSegments'),
};

describe('dashboard view smoke', () => {
  it.each(Object.entries(viewModules))(
    '%s imports without error and exports a default component',
    async (_name, loader) => {
      const mod = await loader();
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    }
  );
});
