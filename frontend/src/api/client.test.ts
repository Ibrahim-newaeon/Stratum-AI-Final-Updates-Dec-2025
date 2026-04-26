/**
 * Stratum AI - API Client Tests
 *
 * Tests for token management, tenant ID management,
 * request interceptors (auth + tenant headers), and
 * response interceptor (401 handling + token refresh mutex).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import axios from 'axios';

// ---------------------------------------------------------------------------
// Mock sessionStorage (tokens now use sessionStorage to reduce XSS surface)
// ---------------------------------------------------------------------------
const mockSessionStorage = (() => {
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
    _reset: () => {
      store = {};
    },
    _getStore: () => store,
  };
})();

Object.defineProperty(window, 'sessionStorage', { value: mockSessionStorage });

// Mock localStorage for tenant_id (still uses localStorage)
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
    _reset: () => {
      store = {};
    },
    _getStore: () => store,
  };
})();

Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

// ---------------------------------------------------------------------------
// Import AFTER localStorage mock is in place
// ---------------------------------------------------------------------------
import {
  apiClient,
  setAccessToken,
  getAccessToken,
  setTenantId,
  getTenantId,
} from './client';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Reset module-level state by clearing tokens + storage */
function resetClientState() {
  setAccessToken(null);
  setTenantId(null);
  mockSessionStorage._reset();
  mockLocalStorage._reset();
  // Restore the original implementation (mockClear only clears calls, not mockImplementation)
  mockSessionStorage.getItem.mockImplementation((key: string) => mockSessionStorage._getStore()[key] ?? null);
  mockSessionStorage.setItem.mockClear();
  mockSessionStorage.removeItem.mockClear();
  mockLocalStorage.getItem.mockImplementation((key: string) => mockLocalStorage._getStore()[key] ?? null);
  mockLocalStorage.setItem.mockClear();
  mockLocalStorage.removeItem.mockClear();
}

// =============================================================================
// Tests
// =============================================================================

describe('API Client - Token Management', () => {
  beforeEach(resetClientState);

  it('setAccessToken stores the token and persists to sessionStorage', () => {
    setAccessToken('tok_abc');

    expect(getAccessToken()).toBe('tok_abc');
    expect(mockSessionStorage.setItem).toHaveBeenCalledWith('access_token', 'tok_abc');
  });

  it('setAccessToken(null) clears token and removes from sessionStorage', () => {
    setAccessToken('tok_abc');
    mockSessionStorage.removeItem.mockClear();

    setAccessToken(null);

    expect(getAccessToken()).toBeNull();
    expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('access_token');
  });

  it('getAccessToken falls back to sessionStorage when in-memory value is null', () => {
    // Clear in-memory token
    setAccessToken(null);

    // Directly write to the mock store (bypassing setAccessToken)
    mockSessionStorage._getStore()['access_token'] = 'tok_from_storage';

    const token = getAccessToken();
    expect(token).toBe('tok_from_storage');
  });
});

describe('API Client - Tenant ID Management', () => {
  beforeEach(resetClientState);

  it('setTenantId stores the tenant ID and persists to localStorage', () => {
    setTenantId(42);

    expect(getTenantId()).toBe(42);
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('tenant_id', '42');
  });

  it('setTenantId(null) removes from localStorage', () => {
    setTenantId(42);
    mockLocalStorage.removeItem.mockClear();

    setTenantId(null);

    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('tenant_id');
  });

  it('getTenantId returns null when nothing is stored', () => {
    setTenantId(null);
    mockLocalStorage._reset();

    const id = getTenantId();
    expect(id).toBeNull();
  });

  it('getTenantId reads from localStorage when in-memory value is null', () => {
    setTenantId(null);
    mockLocalStorage._reset();
    // Directly write to the mock store
    mockLocalStorage._getStore()['tenant_id'] = '99';

    const id = getTenantId();
    expect(id).toBe(99);
  });
});

describe('API Client - Request Interceptor', () => {
  beforeEach(resetClientState);

  it('adds Authorization header when token is set', async () => {
    setAccessToken('my-token');

    // Use the interceptor by creating a config manually
    const config = await (apiClient.interceptors.request as any).handlers[0].fulfilled({
      headers: {},
    });

    expect(config.headers.Authorization).toBe('Bearer my-token');
  });

  it('adds X-Tenant-ID header', async () => {
    setTenantId(7);

    const config = await (apiClient.interceptors.request as any).handlers[0].fulfilled({
      headers: {},
    });

    expect(config.headers['X-Tenant-ID']).toBe('7');
  });

  it('does NOT add X-Superadmin-Bypass header (removed for security)', async () => {
    const config = await (apiClient.interceptors.request as any).handlers[0].fulfilled({
      headers: {},
    });

    expect(config.headers['X-Superadmin-Bypass']).toBeUndefined();
  });
});

describe('API Client - Response Interceptor (401 Handling)', () => {
  beforeEach(() => {
    resetClientState();
  });

  it('rejects 401 when no refresh token is available (no redirect without refresh attempt)', async () => {
    const errorHandler = (apiClient.interceptors.response as any).handlers[0].rejected;

    const error = {
      response: { status: 401 },
      config: { headers: {} },
    };

    // When no refresh_token in localStorage, it skips refresh and just rejects
    await expect(errorHandler(error)).rejects.toEqual(error);
  });

  it('does not retry 401 when _retry is already set', async () => {
    const errorHandler = (apiClient.interceptors.response as any).handlers[0].rejected;

    const error = {
      response: { status: 401 },
      config: { headers: {}, _retry: true },
    };

    // Already retried — should just reject
    await expect(errorHandler(error)).rejects.toEqual(error);
  });

  it('passes through non-401 errors without modification', async () => {
    const errorHandler = (apiClient.interceptors.response as any).handlers[0].rejected;

    const error = {
      response: { status: 500 },
      config: { headers: {} },
    };

    await expect(errorHandler(error)).rejects.toEqual(error);
  });
});

describe('API Client - Type Exports', () => {
  it('apiClient is an axios instance with baseURL configured', () => {
    expect(apiClient).toBeDefined();
    expect(apiClient.defaults.baseURL).toBeDefined();
    expect(apiClient.defaults.timeout).toBe(30000);
    expect(apiClient.defaults.headers['Content-Type']).toBe('application/json');
  });
});
