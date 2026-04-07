/**
 * Stratum AI - ProtectedRoute Tests
 *
 * Tests for authentication gating, role hierarchy checks,
 * portal/agency user type filtering, and permission checks.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProtectedRoute, { meetsRoleRequirement } from './ProtectedRoute';

// ---------------------------------------------------------------------------
// Mock useAuth
// ---------------------------------------------------------------------------
const mockUseAuth = vi.fn();

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock LoadingSpinner
vi.mock('@/components/common/LoadingSpinner', () => ({
  default: () => <div data-testid="loading-spinner">Loading...</div>,
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderProtectedRoute(
  props: Partial<React.ComponentProps<typeof ProtectedRoute>> = {},
  initialEntry = '/'
) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <ProtectedRoute {...props}>
        <div data-testid="protected-content">Secret Content</div>
      </ProtectedRoute>
    </MemoryRouter>
  );
}

function mockAuth(overrides: Partial<{
  user: any;
  isAuthenticated: boolean;
  isLoading: boolean;
}> = {}) {
  mockUseAuth.mockReturnValue({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    ...overrides,
  });
}

// =============================================================================
// meetsRoleRequirement (pure function)
// =============================================================================

describe('meetsRoleRequirement', () => {
  it('superadmin meets all role requirements', () => {
    expect(meetsRoleRequirement('superadmin', 'superadmin')).toBe(true);
    expect(meetsRoleRequirement('superadmin', 'admin')).toBe(true);
    expect(meetsRoleRequirement('superadmin', 'manager')).toBe(true);
    expect(meetsRoleRequirement('superadmin', 'analyst')).toBe(true);
    expect(meetsRoleRequirement('superadmin', 'viewer')).toBe(true);
  });

  it('admin meets admin and below but not superadmin', () => {
    expect(meetsRoleRequirement('admin', 'superadmin')).toBe(false);
    expect(meetsRoleRequirement('admin', 'admin')).toBe(true);
    expect(meetsRoleRequirement('admin', 'manager')).toBe(true);
    expect(meetsRoleRequirement('admin', 'analyst')).toBe(true);
    expect(meetsRoleRequirement('admin', 'viewer')).toBe(true);
  });

  it('manager meets manager and below', () => {
    expect(meetsRoleRequirement('manager', 'superadmin')).toBe(false);
    expect(meetsRoleRequirement('manager', 'admin')).toBe(false);
    expect(meetsRoleRequirement('manager', 'manager')).toBe(true);
    expect(meetsRoleRequirement('manager', 'analyst')).toBe(true);
    expect(meetsRoleRequirement('manager', 'viewer')).toBe(true);
  });

  it('analyst meets analyst and viewer only', () => {
    expect(meetsRoleRequirement('analyst', 'manager')).toBe(false);
    expect(meetsRoleRequirement('analyst', 'analyst')).toBe(true);
    expect(meetsRoleRequirement('analyst', 'viewer')).toBe(true);
  });

  it('viewer meets only viewer', () => {
    expect(meetsRoleRequirement('viewer', 'analyst')).toBe(false);
    expect(meetsRoleRequirement('viewer', 'viewer')).toBe(true);
  });

  it('unknown role returns false for any requirement', () => {
    expect(meetsRoleRequirement('unknown_role', 'viewer')).toBe(false);
  });
});

// =============================================================================
// ProtectedRoute Component
// =============================================================================

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  it('shows loading spinner when auth is loading', () => {
    mockAuth({ isLoading: true });
    renderProtectedRoute();

    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Unauthenticated
  // -------------------------------------------------------------------------

  it('redirects to /login when not authenticated', () => {
    mockAuth({ isAuthenticated: false });
    renderProtectedRoute();

    // Content should not be rendered
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Authenticated — no role requirement
  // -------------------------------------------------------------------------

  it('renders children when authenticated with no role requirement', () => {
    mockAuth({
      isAuthenticated: true,
      user: { role: 'viewer', permissions: [], user_type: 'agency' },
    });
    renderProtectedRoute();

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Role hierarchy checks
  // -------------------------------------------------------------------------

  it('renders children when user role meets required role', () => {
    mockAuth({
      isAuthenticated: true,
      user: { role: 'admin', permissions: [], user_type: 'agency' },
    });
    renderProtectedRoute({ requiredRole: 'manager' });

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('blocks access when user role is below required role', () => {
    mockAuth({
      isAuthenticated: true,
      user: { role: 'analyst', permissions: [], user_type: 'agency' },
    });
    renderProtectedRoute({ requiredRole: 'admin' });

    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  it('allows superadmin to access any required role', () => {
    mockAuth({
      isAuthenticated: true,
      user: { role: 'superadmin', permissions: ['all'], user_type: 'agency' },
    });
    renderProtectedRoute({ requiredRole: 'superadmin' });

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Portal / Agency user type gating
  // -------------------------------------------------------------------------

  it('blocks non-portal users from portalOnly routes', () => {
    mockAuth({
      isAuthenticated: true,
      user: { role: 'admin', permissions: ['all'], user_type: 'agency' },
    });
    renderProtectedRoute({ portalOnly: true });

    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  it('allows portal users on portalOnly routes', () => {
    mockAuth({
      isAuthenticated: true,
      user: { role: 'viewer', permissions: ['read'], user_type: 'portal' },
    });
    renderProtectedRoute({ portalOnly: true });

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('blocks portal users from agencyOnly routes', () => {
    mockAuth({
      isAuthenticated: true,
      user: { role: 'viewer', permissions: ['read'], user_type: 'portal' },
    });
    renderProtectedRoute({ agencyOnly: true });

    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  it('allows agency users on agencyOnly routes', () => {
    mockAuth({
      isAuthenticated: true,
      user: { role: 'admin', permissions: ['all'], user_type: 'agency' },
    });
    renderProtectedRoute({ agencyOnly: true });

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Permission checks
  // -------------------------------------------------------------------------

  it('allows access when user has "all" permission', () => {
    mockAuth({
      isAuthenticated: true,
      user: { role: 'admin', permissions: ['all'], user_type: 'agency' },
    });
    renderProtectedRoute({ requiredPermission: 'manage_campaigns' });

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('allows access when user has the specific required permission', () => {
    mockAuth({
      isAuthenticated: true,
      user: { role: 'analyst', permissions: ['read', 'manage_campaigns'], user_type: 'agency' },
    });
    renderProtectedRoute({ requiredPermission: 'manage_campaigns' });

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('blocks access when user lacks the required permission', () => {
    mockAuth({
      isAuthenticated: true,
      user: { role: 'analyst', permissions: ['read'], user_type: 'agency' },
    });
    renderProtectedRoute({ requiredPermission: 'manage_campaigns' });

    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Combined checks
  // -------------------------------------------------------------------------

  it('enforces both role and permission when both are specified', () => {
    // Has permission but not role
    mockAuth({
      isAuthenticated: true,
      user: { role: 'viewer', permissions: ['manage_campaigns'], user_type: 'agency' },
    });
    renderProtectedRoute({ requiredRole: 'admin', requiredPermission: 'manage_campaigns' });

    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });
});
