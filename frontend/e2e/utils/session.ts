import type { Page } from '@playwright/test'

/**
 * Seed an authenticated session the way the app actually reads it.
 *
 * AuthContext restores a session from `localStorage['stratum_auth']` (a full
 * User object validated for id/email/role) on mount — no backend call. The old
 * E2E suite set `auth_token`/`user`, which the app ignores, so every protected
 * page redirected to /login. Set the correct key here.
 */
export interface E2EUser {
  id: string
  email: string
  name: string
  role: 'superadmin' | 'admin' | 'manager' | 'analyst' | 'viewer'
  organization?: string
  permissions: string[]
  tenant_id?: number | null
  user_type?: 'agency' | 'portal'
}

export const DEFAULT_USER: E2EUser = {
  id: 'e2e-admin-1',
  email: 'e2e@stratum.test',
  name: 'E2E Admin',
  role: 'admin',
  organization: 'E2E Org',
  permissions: ['all'],
  tenant_id: 1,
  user_type: 'agency',
}

/**
 * Install the session before any app code runs (addInitScript runs on every
 * navigation/reload), so AuthContext sees it on first mount.
 */
export async function authenticate(page: Page, user: E2EUser = DEFAULT_USER): Promise<void> {
  await page.addInitScript((u) => {
    localStorage.setItem('stratum_auth', JSON.stringify(u))
    // A non-expired-looking placeholder; the app does not verify it against a
    // backend for session restore, but some code reads it for API headers.
    sessionStorage.setItem('access_token', 'e2e.placeholder.token')
  }, user)
}
