/**
 * Stratum AI - AuthContext Tests
 *
 * Tests for login flow, logout cleanup, session restore,
 * demo login fallback, and the useAuth hook.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';

// ---------------------------------------------------------------------------
// Mock localStorage
// ---------------------------------------------------------------------------
const mockStore: Record<string, string> = {};
const mockLocalStorage = {
  getItem: vi.fn((key: string) => mockStore[key] ?? null),
  setItem: vi.fn((key: string, value: string) => {
    mockStore[key] = value;
  }),
  removeItem: vi.fn((key: string) => {
    delete mockStore[key];
  }),
  clear: vi.fn(() => {
    Object.keys(mockStore).forEach((k) => delete mockStore[k]);
  }),
  get length() {
    return Object.keys(mockStore).length;
  },
  key: vi.fn((index: number) => Object.keys(mockStore)[index] ?? null),
};

Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

// ---------------------------------------------------------------------------
// Enable demo mode for tests (must be set before AuthContext import)
// ---------------------------------------------------------------------------
(window as any).__RUNTIME_CONFIG__ = { VITE_ENABLE_DEMO_MODE: 'true' };

// ---------------------------------------------------------------------------
// Mock dependencies
// ---------------------------------------------------------------------------

vi.mock('@/stores/tenantStore', () => ({
  useTenantStore: {
    getState: () => ({
      tenantId: null,
      setTenantId: vi.fn(),
      setUser: vi.fn(),
      logout: vi.fn(),
    }),
  },
}));

vi.mock('@/hooks/useIdleTimeout', () => ({
  useIdleTimeout: () => ({
    isWarning: false,
    secondsLeft: 60,
    resetTimer: vi.fn(),
  }),
}));

vi.mock('@/components/auth/IdleTimeoutWarning', () => ({
  default: () => null,
}));

// ---------------------------------------------------------------------------
// Mock fetch
// ---------------------------------------------------------------------------
const mockFetch = vi.fn();
global.fetch = mockFetch;

// ---------------------------------------------------------------------------
// Helper to consume the auth context in tests
// ---------------------------------------------------------------------------
function AuthConsumer({ onRender }: { onRender: (auth: ReturnType<typeof useAuth>) => void }) {
  const auth = useAuth();
  onRender(auth);
  return (
    <div>
      <span data-testid="is-authenticated">{String(auth.isAuthenticated)}</span>
      <span data-testid="user-role">{auth.user?.role ?? 'none'}</span>
      <span data-testid="is-demo">{String(auth.isDemoSession)}</span>
    </div>
  );
}

function renderAuthConsumer(onRender = vi.fn()) {
  return {
    ...render(
      <AuthProvider>
        <AuthConsumer onRender={onRender} />
      </AuthProvider>
    ),
    onRender,
  };
}

// ---------------------------------------------------------------------------
// Reset
// ---------------------------------------------------------------------------
function resetAll() {
  Object.keys(mockStore).forEach((k) => delete mockStore[k]);
  mockLocalStorage.getItem.mockClear();
  mockLocalStorage.setItem.mockClear();
  mockLocalStorage.removeItem.mockClear();
  mockFetch.mockReset();
}

// =============================================================================
// Tests
// =============================================================================

describe('AuthContext', () => {
  beforeEach(resetAll);

  // -------------------------------------------------------------------------
  // useAuth outside provider
  // -------------------------------------------------------------------------

  it('useAuth throws when used outside AuthProvider', () => {
    // Suppress the React error boundary console output
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    function BadConsumer() {
      useAuth();
      return null;
    }

    expect(() => render(<BadConsumer />)).toThrow('useAuth must be used within an AuthProvider');
    spy.mockRestore();
  });

  // -------------------------------------------------------------------------
  // Initial state
  // -------------------------------------------------------------------------

  it('starts with isAuthenticated=false and user=null', async () => {
    const onRender = vi.fn();
    renderAuthConsumer(onRender);

    await waitFor(() => {
      const lastCall = onRender.mock.calls[onRender.mock.calls.length - 1][0];
      expect(lastCall.isLoading).toBe(false);
    });

    const lastAuth = onRender.mock.calls[onRender.mock.calls.length - 1][0];
    expect(lastAuth.isAuthenticated).toBe(false);
    expect(lastAuth.user).toBeNull();
  });

  // -------------------------------------------------------------------------
  // Session restore from localStorage
  // -------------------------------------------------------------------------

  it('restores session from localStorage on mount', async () => {
    const storedUser = {
      id: '1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'admin',
      permissions: ['all'],
      tenant_id: 1,
      user_type: 'agency',
    };
    mockStore['stratum_auth'] = JSON.stringify(storedUser);

    const onRender = vi.fn();
    renderAuthConsumer(onRender);

    await waitFor(() => {
      const lastCall = onRender.mock.calls[onRender.mock.calls.length - 1][0];
      expect(lastCall.isLoading).toBe(false);
    });

    const lastAuth = onRender.mock.calls[onRender.mock.calls.length - 1][0];
    expect(lastAuth.isAuthenticated).toBe(true);
    expect(lastAuth.user?.email).toBe('test@example.com');
    expect(lastAuth.user?.role).toBe('admin');
  });

  it('handles corrupted localStorage gracefully', async () => {
    mockStore['stratum_auth'] = 'not-valid-json{{{';

    const onRender = vi.fn();
    renderAuthConsumer(onRender);

    await waitFor(() => {
      const lastCall = onRender.mock.calls[onRender.mock.calls.length - 1][0];
      expect(lastCall.isLoading).toBe(false);
    });

    const lastAuth = onRender.mock.calls[onRender.mock.calls.length - 1][0];
    expect(lastAuth.isAuthenticated).toBe(false);
    expect(lastAuth.user).toBeNull();
    // Should have cleaned up the corrupted entry
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('stratum_auth');
  });

  // -------------------------------------------------------------------------
  // Login
  // -------------------------------------------------------------------------

  it('login succeeds and sets user state', async () => {
    // Mock login response
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: {
            access_token: 'tok_abc',
            refresh_token: 'ref_xyz',
          },
        }),
        status: 200,
        headers: new Headers(),
      })
      // Mock /users/me response
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: {
            id: 42,
            email: 'user@example.com',
            full_name: 'Test User',
            role: 'admin',
            tenant_id: 1,
            user_type: 'agency',
          },
        }),
      });

    const onRender = vi.fn();
    renderAuthConsumer(onRender);

    await waitFor(() => {
      const lastCall = onRender.mock.calls[onRender.mock.calls.length - 1][0];
      expect(lastCall.isLoading).toBe(false);
    });

    const lastAuth = onRender.mock.calls[onRender.mock.calls.length - 1][0];

    let result: any;
    await act(async () => {
      result = await lastAuth.login('user@example.com', 'password123');
    });

    expect(result.success).toBe(true);
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('access_token', 'tok_abc');
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('refresh_token', 'ref_xyz');
  });

  it('login returns error on 401', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Invalid credentials' }),
      headers: new Headers(),
    });

    const onRender = vi.fn();
    renderAuthConsumer(onRender);

    await waitFor(() => {
      const lastCall = onRender.mock.calls[onRender.mock.calls.length - 1][0];
      expect(lastCall.isLoading).toBe(false);
    });

    const lastAuth = onRender.mock.calls[onRender.mock.calls.length - 1][0];

    let result: any;
    await act(async () => {
      result = await lastAuth.login('bad@example.com', 'wrong');
    });

    expect(result.success).toBe(false);
    expect(result.error).toBe('Invalid credentials');
  });

  it('login returns lockout info on 429', async () => {
    const headers = new Headers();
    headers.set('Retry-After', '300');

    mockFetch.mockResolvedValue({
      ok: false,
      status: 429,
      json: async () => ({ detail: 'Too many attempts' }),
      headers,
    });

    const onRender = vi.fn();
    renderAuthConsumer(onRender);

    await waitFor(() => {
      const lastCall = onRender.mock.calls[onRender.mock.calls.length - 1][0];
      expect(lastCall.isLoading).toBe(false);
    });

    const lastAuth = onRender.mock.calls[onRender.mock.calls.length - 1][0];

    let result: any;
    await act(async () => {
      result = await lastAuth.login('locked@example.com', 'pass');
    });

    expect(result.success).toBe(false);
    expect(result.lockoutSeconds).toBe(300);
  });

  // -------------------------------------------------------------------------
  // Logout
  // -------------------------------------------------------------------------

  it('logout clears user state and all localStorage keys', async () => {
    // Set up an active session
    const storedUser = {
      id: '1',
      email: 'test@example.com',
      name: 'Test',
      role: 'admin',
      permissions: ['all'],
      tenant_id: 1,
    };
    mockStore['stratum_auth'] = JSON.stringify(storedUser);
    mockStore['access_token'] = 'tok';
    mockStore['refresh_token'] = 'ref';
    mockStore['stratum_demo_mode'] = 'false';

    const onRender = vi.fn();
    renderAuthConsumer(onRender);

    await waitFor(() => {
      const lastCall = onRender.mock.calls[onRender.mock.calls.length - 1][0];
      expect(lastCall.isAuthenticated).toBe(true);
    });

    const authBeforeLogout = onRender.mock.calls[onRender.mock.calls.length - 1][0];
    expect(authBeforeLogout.isAuthenticated).toBe(true);

    mockLocalStorage.removeItem.mockClear();

    await act(async () => {
      authBeforeLogout.logout();
    });

    // Verify all keys are cleaned up
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('stratum_auth');
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('access_token');
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('refresh_token');
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('stratum_demo_mode');
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('stratum_onboarding_progress');
    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('stratum_available_tenants');
  });

  // -------------------------------------------------------------------------
  // Demo login
  // -------------------------------------------------------------------------

  it('demoLogin falls back to client-side session when backend fails', async () => {
    // Backend rejects the demo credentials
    mockFetch.mockRejectedValue(new TypeError('fetch failed'));

    const onRender = vi.fn();
    renderAuthConsumer(onRender);

    await waitFor(() => {
      const lastCall = onRender.mock.calls[onRender.mock.calls.length - 1][0];
      expect(lastCall.isLoading).toBe(false);
    });

    const lastAuth = onRender.mock.calls[onRender.mock.calls.length - 1][0];

    let result: any;
    await act(async () => {
      result = await lastAuth.demoLogin('admin');
    });

    expect(result.success).toBe(true);
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('stratum_demo_mode', 'true');
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('access_token', 'demo-token');
  });

  it('demoLogin returns error for unknown role', async () => {
    const onRender = vi.fn();
    renderAuthConsumer(onRender);

    await waitFor(() => {
      const lastCall = onRender.mock.calls[onRender.mock.calls.length - 1][0];
      expect(lastCall.isLoading).toBe(false);
    });

    const lastAuth = onRender.mock.calls[onRender.mock.calls.length - 1][0];

    let result: any;
    await act(async () => {
      result = await lastAuth.demoLogin('nonexistent' as any);
    });

    expect(result.success).toBe(false);
    expect(result.error).toBe('Unknown demo role');
  });

  // -------------------------------------------------------------------------
  // updateUser
  // -------------------------------------------------------------------------

  it('updateUser merges partial data into current user', async () => {
    const storedUser = {
      id: '1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'admin',
      permissions: ['all'],
      tenant_id: 1,
      user_type: 'agency',
    };
    mockStore['stratum_auth'] = JSON.stringify(storedUser);

    const onRender = vi.fn();
    renderAuthConsumer(onRender);

    await waitFor(() => {
      const lastCall = onRender.mock.calls[onRender.mock.calls.length - 1][0];
      expect(lastCall.isAuthenticated).toBe(true);
    });

    const lastAuth = onRender.mock.calls[onRender.mock.calls.length - 1][0];

    await act(async () => {
      lastAuth.updateUser({ name: 'Updated Name', avatar: 'https://example.com/avatar.png' });
    });

    const updated = onRender.mock.calls[onRender.mock.calls.length - 1][0];
    expect(updated.user?.name).toBe('Updated Name');
    expect(updated.user?.avatar).toBe('https://example.com/avatar.png');
    // Other fields should be preserved
    expect(updated.user?.email).toBe('test@example.com');
  });
});
