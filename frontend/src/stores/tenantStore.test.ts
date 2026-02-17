/**
 * Stratum AI - Tenant Store Tests
 *
 * Comprehensive Vitest test suite for the Zustand tenant store
 * covering state management, role checks, superadmin controls,
 * persistence, and logout behavior.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useTenantStore } from './tenantStore';
import type { User, Tenant, UserRole } from './tenantStore';

// =============================================================================
// Mock localStorage
// =============================================================================

const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
    _getStore: () => store,
  };
})();

Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

// =============================================================================
// Test Fixtures
// =============================================================================

const createMockUser = (overrides: Partial<User> = {}): User => ({
  id: 1,
  email: 'user@stratum.ai',
  full_name: 'Test User',
  role: 'user',
  avatar_url: null,
  locale: 'en',
  timezone: 'UTC',
  is_active: true,
  is_verified: true,
  last_login_at: '2025-12-01T00:00:00Z',
  created_at: '2025-01-01T00:00:00Z',
  ...overrides,
});

const createSuperAdminUser = (overrides: Partial<User> = {}): User =>
  createMockUser({ id: 99, email: 'admin@stratum.ai', full_name: 'Super Admin', role: 'superadmin', ...overrides });

const createAdminUser = (overrides: Partial<User> = {}): User =>
  createMockUser({ id: 2, email: 'admin@stratum.ai', full_name: 'Admin User', role: 'admin', ...overrides });

const createMockTenant = (overrides: Partial<Tenant> = {}): Tenant => ({
  id: 10,
  name: 'Acme Corp',
  slug: 'acme-corp',
  domain: 'acme.stratum.ai',
  plan: 'enterprise',
  plan_expires_at: '2026-12-31T00:00:00Z',
  max_users: 50,
  max_campaigns: 100,
  settings: { theme: 'dark' },
  feature_flags: {
    cdp_enabled: true,
    autopilot: true,
    whatsapp: false,
  },
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-12-01T00:00:00Z',
  ...overrides,
});

// =============================================================================
// Reset helper
// =============================================================================

const resetStore = () => {
  const state = useTenantStore.getState();
  // Call logout to clear state and localStorage
  state.logout();
  // Also reset dateRange to a known value since logout does not reset it
  useTenantStore.setState({
    dateRange: { start: '2025-11-01', end: '2025-12-01' },
  });
  // Clear all mock calls
  mockLocalStorage.getItem.mockClear();
  mockLocalStorage.setItem.mockClear();
  mockLocalStorage.removeItem.mockClear();
  mockLocalStorage.clear.mockClear();
};

// =============================================================================
// Tests
// =============================================================================

describe('tenantStore', () => {
  beforeEach(() => {
    resetStore();
  });

  // ===========================================================================
  // 1. Initial State
  // ===========================================================================

  describe('Initial State', () => {
    it('should have correct default state values', () => {
      const state = useTenantStore.getState();

      expect(state.tenantId).toBeNull();
      expect(state.tenant).toBeNull();
      expect(state.user).toBeNull();
      expect(state.isSuperAdminMode).toBe(false);
      expect(state.superAdminBypass).toBe(false);
      expect(state.selectedPlatforms).toEqual([]);
      expect(state.dateRange).toHaveProperty('start');
      expect(state.dateRange).toHaveProperty('end');
    });

    it('should have tenantId starting as null', () => {
      const state = useTenantStore.getState();
      expect(state.tenantId).toBeNull();
    });

    it('should have user starting as null', () => {
      const state = useTenantStore.getState();
      expect(state.user).toBeNull();
    });
  });

  // ===========================================================================
  // 2. Tenant Operations
  // ===========================================================================

  describe('Tenant Operations', () => {
    it('should set tenantId via setTenantId', () => {
      useTenantStore.getState().setTenantId(42);

      const state = useTenantStore.getState();
      expect(state.tenantId).toBe(42);
    });

    it('should sync tenantId to localStorage when setting a non-null id', () => {
      useTenantStore.getState().setTenantId(42);

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('tenant_id', '42');
    });

    it('should remove tenant_id from localStorage when setting null', () => {
      useTenantStore.getState().setTenantId(42);
      mockLocalStorage.removeItem.mockClear();

      useTenantStore.getState().setTenantId(null);

      expect(useTenantStore.getState().tenantId).toBeNull();
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('tenant_id');
    });

    it('should store a full tenant object via setTenant', () => {
      const tenant = createMockTenant();
      useTenantStore.getState().setTenant(tenant);

      const state = useTenantStore.getState();
      expect(state.tenant).toEqual(tenant);
      expect(state.tenantId).toBe(tenant.id);
    });

    it('should also set tenantId when setting tenant', () => {
      const tenant = createMockTenant({ id: 77 });
      useTenantStore.getState().setTenant(tenant);

      expect(useTenantStore.getState().tenantId).toBe(77);
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('tenant_id', '77');
    });

    it('should clear tenant and tenantId when setting tenant to null', () => {
      // First set a tenant
      useTenantStore.getState().setTenant(createMockTenant());
      expect(useTenantStore.getState().tenant).not.toBeNull();

      // Then clear it
      useTenantStore.getState().setTenant(null);

      const state = useTenantStore.getState();
      expect(state.tenant).toBeNull();
      expect(state.tenantId).toBeNull();
    });
  });

  // ===========================================================================
  // 3. User Operations
  // ===========================================================================

  describe('User Operations', () => {
    it('should store user object via setUser', () => {
      const user = createMockUser();
      useTenantStore.getState().setUser(user);

      const state = useTenantStore.getState();
      expect(state.user).toEqual(user);
    });

    it('should auto-enable superadmin mode when user role is superadmin', () => {
      const superadmin = createSuperAdminUser();
      useTenantStore.getState().setUser(superadmin);

      const state = useTenantStore.getState();
      expect(state.user?.role).toBe('superadmin');
      expect(state.isSuperAdminMode).toBe(true);
    });

    it('should not enable superadmin mode when user role is admin', () => {
      const admin = createAdminUser();
      useTenantStore.getState().setUser(admin);

      const state = useTenantStore.getState();
      expect(state.user?.role).toBe('admin');
      expect(state.isSuperAdminMode).toBe(false);
    });

    it('should not enable superadmin mode when user role is user', () => {
      const user = createMockUser({ role: 'user' });
      useTenantStore.getState().setUser(user);

      expect(useTenantStore.getState().isSuperAdminMode).toBe(false);
    });

    it('should clear user when setUser is called with null', () => {
      useTenantStore.getState().setUser(createMockUser());
      expect(useTenantStore.getState().user).not.toBeNull();

      useTenantStore.getState().setUser(null);
      expect(useTenantStore.getState().user).toBeNull();
    });
  });

  // ===========================================================================
  // 4. Role Checks
  // ===========================================================================

  describe('Role Checks', () => {
    it('isSuperAdmin should return true for superadmin role', () => {
      useTenantStore.getState().setUser(createSuperAdminUser());

      expect(useTenantStore.getState().isSuperAdmin()).toBe(true);
    });

    it('isSuperAdmin should return false for admin role', () => {
      useTenantStore.getState().setUser(createAdminUser());

      expect(useTenantStore.getState().isSuperAdmin()).toBe(false);
    });

    it('isSuperAdmin should return false when user is null', () => {
      expect(useTenantStore.getState().isSuperAdmin()).toBe(false);
    });

    it('isAdmin should return true for admin role', () => {
      useTenantStore.getState().setUser(createAdminUser());

      expect(useTenantStore.getState().isAdmin()).toBe(true);
    });

    it('isAdmin should return true for superadmin role', () => {
      useTenantStore.getState().setUser(createSuperAdminUser());

      expect(useTenantStore.getState().isAdmin()).toBe(true);
    });

    it('isAdmin should return false for regular user role', () => {
      useTenantStore.getState().setUser(createMockUser({ role: 'user' }));

      expect(useTenantStore.getState().isAdmin()).toBe(false);
    });

    it('hasRole should return true when user role is in the given array', () => {
      useTenantStore.getState().setUser(createMockUser({ role: 'media_buyer' }));

      expect(useTenantStore.getState().hasRole(['media_buyer', 'analyst'])).toBe(true);
    });

    it('hasRole should return false when user role is not in the given array', () => {
      useTenantStore.getState().setUser(createMockUser({ role: 'viewer' }));

      expect(useTenantStore.getState().hasRole(['admin', 'superadmin'])).toBe(false);
    });

    it('hasRole should return false when user is null', () => {
      expect(useTenantStore.getState().hasRole(['admin', 'superadmin'])).toBe(false);
    });

    it('hasRole should work for each UserRole type', () => {
      const roles: UserRole[] = ['superadmin', 'admin', 'user', 'manager', 'media_buyer', 'analyst', 'account_manager', 'viewer'];

      for (const role of roles) {
        useTenantStore.getState().setUser(createMockUser({ role }));
        expect(useTenantStore.getState().hasRole([role])).toBe(true);
        expect(useTenantStore.getState().hasRole(roles.filter((r) => r !== role))).toBe(false);

        // Reset superAdminMode for next iteration
        useTenantStore.setState({ isSuperAdminMode: false });
      }
    });
  });

  // ===========================================================================
  // 5. Feature Flags
  // ===========================================================================

  describe('Feature Flags', () => {
    it('hasFeature should return true for enabled feature flags', () => {
      useTenantStore.getState().setTenant(
        createMockTenant({
          feature_flags: { cdp_enabled: true, whatsapp: false },
        })
      );

      expect(useTenantStore.getState().hasFeature('cdp_enabled')).toBe(true);
    });

    it('hasFeature should return false for disabled feature flags', () => {
      useTenantStore.getState().setTenant(
        createMockTenant({
          feature_flags: { cdp_enabled: true, whatsapp: false },
        })
      );

      expect(useTenantStore.getState().hasFeature('whatsapp')).toBe(false);
    });

    it('hasFeature should return false for non-existent feature flags', () => {
      useTenantStore.getState().setTenant(createMockTenant());

      expect(useTenantStore.getState().hasFeature('nonexistent_feature')).toBe(false);
    });

    it('hasFeature should return false when tenant is null', () => {
      expect(useTenantStore.getState().hasFeature('cdp_enabled')).toBe(false);
    });
  });

  // ===========================================================================
  // 6. SuperAdmin Controls
  // ===========================================================================

  describe('SuperAdmin Controls', () => {
    it('setSuperAdminMode should enable mode for superadmin users', () => {
      useTenantStore.getState().setUser(createSuperAdminUser());
      // setUser auto-enables it, so disable first to test setSuperAdminMode
      useTenantStore.getState().setSuperAdminMode(false);
      expect(useTenantStore.getState().isSuperAdminMode).toBe(false);

      useTenantStore.getState().setSuperAdminMode(true);
      expect(useTenantStore.getState().isSuperAdminMode).toBe(true);
    });

    it('setSuperAdminMode should not enable mode for non-superadmin users', () => {
      useTenantStore.getState().setUser(createAdminUser());
      expect(useTenantStore.getState().isSuperAdminMode).toBe(false);

      useTenantStore.getState().setSuperAdminMode(true);
      expect(useTenantStore.getState().isSuperAdminMode).toBe(false);
    });

    it('setSuperAdminMode should not work when user is null', () => {
      useTenantStore.getState().setSuperAdminMode(true);
      expect(useTenantStore.getState().isSuperAdminMode).toBe(false);
    });

    it('setSuperAdminBypass should enable bypass for superadmin users', () => {
      useTenantStore.getState().setUser(createSuperAdminUser());

      useTenantStore.getState().setSuperAdminBypass(true);
      expect(useTenantStore.getState().superAdminBypass).toBe(true);

      useTenantStore.getState().setSuperAdminBypass(false);
      expect(useTenantStore.getState().superAdminBypass).toBe(false);
    });

    it('setSuperAdminBypass should not enable bypass for non-superadmin users', () => {
      useTenantStore.getState().setUser(createMockUser({ role: 'manager' }));

      useTenantStore.getState().setSuperAdminBypass(true);
      expect(useTenantStore.getState().superAdminBypass).toBe(false);
    });

    it('setSuperAdminBypass should not work when user is null', () => {
      useTenantStore.getState().setSuperAdminBypass(true);
      expect(useTenantStore.getState().superAdminBypass).toBe(false);
    });
  });

  // ===========================================================================
  // 7. Logout
  // ===========================================================================

  describe('Logout', () => {
    it('should clear all state on logout', () => {
      // Set up a fully populated store
      useTenantStore.getState().setTenant(createMockTenant());
      useTenantStore.getState().setUser(createSuperAdminUser());
      useTenantStore.getState().setSelectedPlatforms(['meta', 'google']);

      // Verify state is populated before logout
      expect(useTenantStore.getState().tenant).not.toBeNull();
      expect(useTenantStore.getState().user).not.toBeNull();
      expect(useTenantStore.getState().tenantId).not.toBeNull();
      expect(useTenantStore.getState().isSuperAdminMode).toBe(true);
      expect(useTenantStore.getState().selectedPlatforms.length).toBeGreaterThan(0);

      // Logout
      useTenantStore.getState().logout();

      const state = useTenantStore.getState();
      expect(state.tenantId).toBeNull();
      expect(state.tenant).toBeNull();
      expect(state.user).toBeNull();
      expect(state.isSuperAdminMode).toBe(false);
      expect(state.superAdminBypass).toBe(false);
      expect(state.selectedPlatforms).toEqual([]);
    });

    it('should clear localStorage keys on logout', () => {
      useTenantStore.getState().setTenantId(10);
      mockLocalStorage.removeItem.mockClear();

      useTenantStore.getState().logout();

      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('tenant_id');
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('refresh_token');
    });
  });

  // ===========================================================================
  // 8. Date Range & Platforms
  // ===========================================================================

  describe('Date Range & Platforms', () => {
    it('should update date range via setDateRange', () => {
      useTenantStore.getState().setDateRange('2025-01-01', '2025-06-30');

      const state = useTenantStore.getState();
      expect(state.dateRange.start).toBe('2025-01-01');
      expect(state.dateRange.end).toBe('2025-06-30');
    });

    it('should update selected platforms via setSelectedPlatforms', () => {
      useTenantStore.getState().setSelectedPlatforms(['meta', 'google', 'tiktok']);

      const state = useTenantStore.getState();
      expect(state.selectedPlatforms).toEqual(['meta', 'google', 'tiktok']);
    });

    it('should allow clearing platforms by setting an empty array', () => {
      useTenantStore.getState().setSelectedPlatforms(['meta']);
      expect(useTenantStore.getState().selectedPlatforms).toEqual(['meta']);

      useTenantStore.getState().setSelectedPlatforms([]);
      expect(useTenantStore.getState().selectedPlatforms).toEqual([]);
    });

    it('should allow overwriting date range multiple times', () => {
      useTenantStore.getState().setDateRange('2025-01-01', '2025-03-31');
      expect(useTenantStore.getState().dateRange).toEqual({ start: '2025-01-01', end: '2025-03-31' });

      useTenantStore.getState().setDateRange('2025-07-01', '2025-12-31');
      expect(useTenantStore.getState().dateRange).toEqual({ start: '2025-07-01', end: '2025-12-31' });
    });
  });

  // ===========================================================================
  // 9. Persistence Configuration
  // ===========================================================================

  describe('Persistence', () => {
    it('should use the correct localStorage key for persistence', () => {
      // Trigger a state change that is persisted
      useTenantStore.getState().setTenantId(5);

      // The persist middleware should use 'stratum-tenant-store' key
      const calls = mockLocalStorage.setItem.mock.calls;
      const persistCall = calls.find(
        (call: [string, string]) => call[0] === 'stratum-tenant-store'
      );
      // The Zustand persist middleware writes to this key
      expect(persistCall).toBeDefined();
    });
  });

  // ===========================================================================
  // 10. Edge Cases
  // ===========================================================================

  describe('Edge Cases', () => {
    it('should handle setting the same tenantId twice without errors', () => {
      useTenantStore.getState().setTenantId(1);
      useTenantStore.getState().setTenantId(1);

      expect(useTenantStore.getState().tenantId).toBe(1);
    });

    it('should handle switching users from superadmin to regular user', () => {
      // Login as superadmin
      useTenantStore.getState().setUser(createSuperAdminUser());
      expect(useTenantStore.getState().isSuperAdminMode).toBe(true);

      // Switch to regular user - note: setUser does not auto-disable superAdminMode
      // It only auto-enables for superadmin. The mode stays until explicitly changed or logout.
      useTenantStore.getState().setUser(createMockUser({ role: 'user' }));
      expect(useTenantStore.getState().user?.role).toBe('user');
    });

    it('should handle tenant with empty feature_flags', () => {
      useTenantStore.getState().setTenant(createMockTenant({ feature_flags: {} }));

      expect(useTenantStore.getState().hasFeature('anything')).toBe(false);
    });

    it('should handle setting tenant which also updates tenantId', () => {
      const tenant = createMockTenant({ id: 55 });
      useTenantStore.getState().setTenant(tenant);

      expect(useTenantStore.getState().tenantId).toBe(55);
      expect(useTenantStore.getState().tenant?.id).toBe(55);
    });
  });
});
