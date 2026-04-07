/**
 * Stratum AI - DemoContext Tests
 *
 * Tests for DemoProvider, useDemo hook, demo mode entry/exit,
 * localStorage persistence, URL parameter handling, and demo data.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, renderHook, act } from '@testing-library/react';
import {
  DemoProvider,
  useDemo,
  DEMO_TENANT,
  DEMO_USER,
  DEMO_METRICS,
  DEMO_CAMPAIGNS,
  DEMO_SEGMENTS,
  DEMO_EVENTS,
  DEMO_TRUST_GATE_HISTORY,
} from './DemoContext';
import type { ReactNode } from 'react';

// =============================================================================
// Mock localStorage
// =============================================================================

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

// =============================================================================
// Mock window.location & history
// =============================================================================

const mockReplaceState = vi.fn();

Object.defineProperty(window, 'history', {
  writable: true,
  value: {
    replaceState: mockReplaceState,
    pushState: vi.fn(),
    state: null,
    length: 1,
  },
});

// Helper to set the URL search params
function setSearchParams(params: string) {
  Object.defineProperty(window, 'location', {
    writable: true,
    value: {
      ...window.location,
      search: params,
      href: `http://localhost${params ? '?' + params : ''}`,
      origin: 'http://localhost',
      pathname: '/',
    },
  });
}

// =============================================================================
// Helpers
// =============================================================================

function resetAll() {
  Object.keys(mockStore).forEach((k) => delete mockStore[k]);
  mockLocalStorage.getItem.mockClear();
  mockLocalStorage.setItem.mockClear();
  mockLocalStorage.removeItem.mockClear();
  mockReplaceState.mockClear();
  setSearchParams('');
}

const wrapper = ({ children }: { children: ReactNode }) => (
  <DemoProvider>{children}</DemoProvider>
);

// =============================================================================
// Tests
// =============================================================================

describe('DemoContext', () => {
  beforeEach(resetAll);

  // ---------------------------------------------------------------------------
  // useDemo outside provider
  // ---------------------------------------------------------------------------

  describe('useDemo outside provider', () => {
    it('throws an error when used outside DemoProvider', () => {
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        renderHook(() => useDemo());
      }).toThrow('useDemo must be used within a DemoProvider');

      spy.mockRestore();
    });
  });

  // ---------------------------------------------------------------------------
  // Default values
  // ---------------------------------------------------------------------------

  describe('Default values', () => {
    it('starts with isDemoMode=false', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      expect(result.current.isDemoMode).toBe(false);
    });

    it('provides demo tenant data', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      expect(result.current.demoTenant).toEqual(DEMO_TENANT);
    });

    it('provides demo user data', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      expect(result.current.demoUser).toEqual(DEMO_USER);
    });

    it('provides demo metrics data', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      expect(result.current.demoMetrics).toBeDefined();
      expect(result.current.demoMetrics.signalHealth.overall).toBe(82);
    });

    it('provides demo campaigns', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      expect(result.current.demoCampaigns).toEqual(DEMO_CAMPAIGNS);
      expect(result.current.demoCampaigns).toHaveLength(4);
    });

    it('provides demo segments', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      expect(result.current.demoSegments).toEqual(DEMO_SEGMENTS);
      expect(result.current.demoSegments).toHaveLength(6);
    });

    it('provides demo events', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      expect(result.current.demoEvents).toEqual(DEMO_EVENTS);
      expect(result.current.demoEvents).toHaveLength(5);
    });

    it('provides demo trust gate history', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      expect(result.current.demoTrustGateHistory).toEqual(DEMO_TRUST_GATE_HISTORY);
      expect(result.current.demoTrustGateHistory).toHaveLength(8);
    });

    it('provides enterDemoMode and exitDemoMode functions', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      expect(typeof result.current.enterDemoMode).toBe('function');
      expect(typeof result.current.exitDemoMode).toBe('function');
    });
  });

  // ---------------------------------------------------------------------------
  // Entering demo mode
  // ---------------------------------------------------------------------------

  describe('Entering demo mode', () => {
    it('sets isDemoMode to true when enterDemoMode is called', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      act(() => {
        result.current.enterDemoMode();
      });

      expect(result.current.isDemoMode).toBe(true);
    });

    it('persists demo mode to localStorage', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      act(() => {
        result.current.enterDemoMode();
      });

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('stratum_demo_mode', 'true');
    });

    it('updates URL with demo=true parameter', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      act(() => {
        result.current.enterDemoMode();
      });

      expect(mockReplaceState).toHaveBeenCalled();
      const calledUrl = mockReplaceState.mock.calls[0][2];
      expect(calledUrl).toContain('demo=true');
    });
  });

  // ---------------------------------------------------------------------------
  // Exiting demo mode
  // ---------------------------------------------------------------------------

  describe('Exiting demo mode', () => {
    it('sets isDemoMode to false when exitDemoMode is called', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      // First enter demo mode
      act(() => {
        result.current.enterDemoMode();
      });
      expect(result.current.isDemoMode).toBe(true);

      // Then exit
      act(() => {
        result.current.exitDemoMode();
      });

      expect(result.current.isDemoMode).toBe(false);
    });

    it('removes demo mode from localStorage', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      act(() => {
        result.current.enterDemoMode();
      });
      mockLocalStorage.removeItem.mockClear();

      act(() => {
        result.current.exitDemoMode();
      });

      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('stratum_demo_mode');
    });

    it('removes demo parameter from URL', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      act(() => {
        result.current.enterDemoMode();
      });
      mockReplaceState.mockClear();

      act(() => {
        result.current.exitDemoMode();
      });

      expect(mockReplaceState).toHaveBeenCalled();
      const calledUrl = mockReplaceState.mock.calls[0][2];
      expect(calledUrl).not.toContain('demo=true');
    });
  });

  // ---------------------------------------------------------------------------
  // Initialization from URL
  // ---------------------------------------------------------------------------

  describe('Initialization from URL', () => {
    it('activates demo mode when URL has demo=true', () => {
      setSearchParams('demo=true');

      const { result } = renderHook(() => useDemo(), { wrapper });

      expect(result.current.isDemoMode).toBe(true);
    });

    it('does not activate demo mode when URL has no demo param', () => {
      setSearchParams('');

      const { result } = renderHook(() => useDemo(), { wrapper });

      expect(result.current.isDemoMode).toBe(false);
    });
  });

  // ---------------------------------------------------------------------------
  // Initialization from localStorage
  // ---------------------------------------------------------------------------

  describe('Initialization from localStorage', () => {
    it('activates demo mode when localStorage has stratum_demo_mode=true', () => {
      mockStore['stratum_demo_mode'] = 'true';

      const { result } = renderHook(() => useDemo(), { wrapper });

      expect(result.current.isDemoMode).toBe(true);
    });

    it('does not activate demo mode when localStorage value is "false"', () => {
      mockStore['stratum_demo_mode'] = 'false';

      const { result } = renderHook(() => useDemo(), { wrapper });

      expect(result.current.isDemoMode).toBe(false);
    });

    it('does not activate demo mode when localStorage key is absent', () => {
      const { result } = renderHook(() => useDemo(), { wrapper });

      expect(result.current.isDemoMode).toBe(false);
    });
  });

  // ---------------------------------------------------------------------------
  // Provider rendering
  // ---------------------------------------------------------------------------

  describe('Provider rendering', () => {
    it('renders children correctly', () => {
      render(
        <DemoProvider>
          <div data-testid="child">Demo Child</div>
        </DemoProvider>
      );

      expect(screen.getByTestId('child')).toBeDefined();
      expect(screen.getByText('Demo Child')).toBeDefined();
    });

    it('provides context to nested consumer components', () => {
      function DemoConsumer() {
        const { isDemoMode, demoTenant } = useDemo();
        return (
          <div>
            <span data-testid="demo-mode">{String(isDemoMode)}</span>
            <span data-testid="tenant-name">{demoTenant.name}</span>
          </div>
        );
      }

      render(
        <DemoProvider>
          <DemoConsumer />
        </DemoProvider>
      );

      expect(screen.getByTestId('demo-mode').textContent).toBe('false');
      expect(screen.getByTestId('tenant-name').textContent).toBe('Acme Commerce');
    });
  });

  // ---------------------------------------------------------------------------
  // Demo data constants
  // ---------------------------------------------------------------------------

  describe('Demo data constants', () => {
    it('DEMO_TENANT has expected structure', () => {
      expect(DEMO_TENANT.id).toBe('demo-tenant-001');
      expect(DEMO_TENANT.name).toBe('Acme Commerce');
      expect(DEMO_TENANT.industry).toBe('E-commerce');
      expect(DEMO_TENANT.tier).toBe('growth');
    });

    it('DEMO_USER has expected structure', () => {
      expect(DEMO_USER.id).toBe('demo-user-001');
      expect(DEMO_USER.name).toBe('Demo User');
      expect(DEMO_USER.email).toBe('demo@stratum.ai');
      expect(DEMO_USER.role).toBe('admin');
    });

    it('DEMO_METRICS has signal health data', () => {
      expect(DEMO_METRICS.signalHealth).toBeDefined();
      expect(DEMO_METRICS.signalHealth.overall).toBeGreaterThan(0);
      expect(DEMO_METRICS.signalHealth.components).toBeDefined();
    });

    it('DEMO_METRICS has trust gate stats', () => {
      expect(DEMO_METRICS.trustGate).toBeDefined();
      expect(DEMO_METRICS.trustGate.totalDecisions).toBe(1247);
      expect(DEMO_METRICS.trustGate.passRate).toBe(87.3);
    });

    it('DEMO_METRICS has revenue data', () => {
      expect(DEMO_METRICS.revenue).toBeDefined();
      expect(DEMO_METRICS.revenue.arr).toBe(2450000);
      expect(DEMO_METRICS.revenue.ltvCacRatio).toBe(3.94);
    });

    it('DEMO_CAMPAIGNS contains multiple campaigns', () => {
      expect(DEMO_CAMPAIGNS.length).toBeGreaterThan(0);
      expect(DEMO_CAMPAIGNS[0]).toHaveProperty('id');
      expect(DEMO_CAMPAIGNS[0]).toHaveProperty('name');
      expect(DEMO_CAMPAIGNS[0]).toHaveProperty('platform');
      expect(DEMO_CAMPAIGNS[0]).toHaveProperty('roas');
      expect(DEMO_CAMPAIGNS[0]).toHaveProperty('signalHealth');
    });

    it('DEMO_SEGMENTS has expected segment types', () => {
      const segmentNames = DEMO_SEGMENTS.map((s) => s.name);
      expect(segmentNames).toContain('Champions');
      expect(segmentNames).toContain('At Risk');
      expect(segmentNames).toContain('New Customers');
    });

    it('DEMO_EVENTS has expected event types', () => {
      const eventTypes = DEMO_EVENTS.map((e) => e.type);
      expect(eventTypes).toContain('purchase');
      expect(eventTypes).toContain('add_to_cart');
      expect(eventTypes).toContain('page_view');
    });

    it('DEMO_TRUST_GATE_HISTORY has time-series structure', () => {
      expect(DEMO_TRUST_GATE_HISTORY.length).toBeGreaterThan(0);
      expect(DEMO_TRUST_GATE_HISTORY[0]).toHaveProperty('time');
      expect(DEMO_TRUST_GATE_HISTORY[0]).toHaveProperty('passed');
      expect(DEMO_TRUST_GATE_HISTORY[0]).toHaveProperty('held');
      expect(DEMO_TRUST_GATE_HISTORY[0]).toHaveProperty('blocked');
    });
  });
});
