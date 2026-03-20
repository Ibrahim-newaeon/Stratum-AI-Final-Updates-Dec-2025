/**
 * Stratum AI - DashboardSimulationContext Tests
 *
 * Tests for DashboardSimulationProvider, useDashboardSimulation hook,
 * provider rendering, and simulation data propagation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, renderHook } from '@testing-library/react';
import { DashboardSimulationProvider, useDashboardSimulation } from './DashboardSimulationContext';
import type { ReactNode } from 'react';

// =============================================================================
// Mock useLiveSimulation
// =============================================================================

const mockSimulationData = {
  campaigns: [
    {
      campaign_id: 'test-1',
      campaign_name: 'Test Campaign',
      platform: 'Meta Ads',
      region: 'Saudi Arabia',
      campaign_type: 'Prospecting',
      spend: 1000,
      revenue: 4000,
      conversions: 50,
      impressions: 100000,
      clicks: 2000,
      ctr: 2.0,
      cpm: 10.0,
      cpa: 20.0,
      roas: 4.0,
      status: 'Active' as const,
      start_date: '2025-01-01T00:00:00Z',
    },
  ],
  platformSummary: [
    {
      platform: 'Meta Ads',
      spend: 1000,
      revenue: 4000,
      conversions: 50,
      roas: 4.0,
      cpa: 20.0,
      impressions: 100000,
      clicks: 2000,
    },
  ],
  dailyTrend: [
    {
      date: 'Jan 1',
      spend: 500,
      revenue: 2000,
      conversions: 25,
      roas: 4.0,
      ctr: 2.0,
      cpa: 20.0,
      impressions: 50000,
      clicks: 1000,
    },
  ],
  regionalBreakdown: [
    { name: 'Saudi Arabia', value: 40 },
    { name: 'UAE', value: 30 },
  ],
  kpis: {
    totalSpend: 1000,
    totalRevenue: 4000,
    overallROAS: 4.0,
    totalConversions: 50,
    overallCPA: 20.0,
    avgCTR: 2.0,
    avgCPM: 10.0,
    totalImpressions: 100000,
    totalClicks: 2000,
    spendDelta: 8.5,
    revenueDelta: 15.2,
    roasDelta: 6.8,
    conversionsDelta: 12.1,
  },
  alerts: [
    {
      id: 'a1',
      severity: 'good' as const,
      title: 'Test Alert',
      message: 'All systems operational',
      time: '2 min ago',
    },
  ],
  connections: [
    {
      platform: 'Meta Ads',
      status: 'connected' as const,
      lastSync: '1m ago',
      campaigns: 7,
      health: 91,
      icon: 'meta',
    },
  ],
  signalHealth: {
    overall: 85,
    emq: 82,
    apiHealth: 90,
    eventLoss: 85,
    platformStability: 88,
    dataQuality: 87,
    status: 'PASS' as const,
  },
  lastUpdated: new Date('2025-12-01T00:00:00Z'),
  isLive: true,
  setIsLive: vi.fn(),
  refresh: vi.fn(),
};

vi.mock('@/lib/liveSimulation', () => ({
  useLiveSimulation: vi.fn(() => mockSimulationData),
}));

// =============================================================================
// Helpers
// =============================================================================

const wrapper = ({ children }: { children: ReactNode }) => (
  <DashboardSimulationProvider>{children}</DashboardSimulationProvider>
);

const wrapperWithInterval = (interval: number) => {
  return ({ children }: { children: ReactNode }) => (
    <DashboardSimulationProvider refreshInterval={interval}>
      {children}
    </DashboardSimulationProvider>
  );
};

// =============================================================================
// Tests
// =============================================================================

describe('DashboardSimulationContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ---------------------------------------------------------------------------
  // useDashboardSimulation outside provider
  // ---------------------------------------------------------------------------

  describe('useDashboardSimulation outside provider', () => {
    it('throws an error when used outside DashboardSimulationProvider', () => {
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        renderHook(() => useDashboardSimulation());
      }).toThrow('useDashboardSimulation must be used inside <DashboardSimulationProvider>');

      spy.mockRestore();
    });
  });

  // ---------------------------------------------------------------------------
  // Provider rendering
  // ---------------------------------------------------------------------------

  describe('Provider rendering', () => {
    it('renders children correctly', () => {
      render(
        <DashboardSimulationProvider>
          <div data-testid="child">Dashboard</div>
        </DashboardSimulationProvider>
      );

      expect(screen.getByTestId('child')).toBeDefined();
      expect(screen.getByText('Dashboard')).toBeDefined();
    });

    it('accepts a custom refreshInterval prop', async () => {
      const { useLiveSimulation } = await import('@/lib/liveSimulation');

      renderHook(() => useDashboardSimulation(), {
        wrapper: wrapperWithInterval(5000),
      });

      expect(useLiveSimulation).toHaveBeenCalledWith(5000);
    });

    it('uses default refreshInterval of 10000 when not specified', async () => {
      const { useLiveSimulation } = await import('@/lib/liveSimulation');

      renderHook(() => useDashboardSimulation(), { wrapper });

      expect(useLiveSimulation).toHaveBeenCalledWith(10000);
    });
  });

  // ---------------------------------------------------------------------------
  // Simulation data access
  // ---------------------------------------------------------------------------

  describe('Simulation data access', () => {
    it('provides campaigns data', () => {
      const { result } = renderHook(() => useDashboardSimulation(), { wrapper });

      expect(result.current.campaigns).toEqual(mockSimulationData.campaigns);
      expect(result.current.campaigns).toHaveLength(1);
      expect(result.current.campaigns[0].campaign_name).toBe('Test Campaign');
    });

    it('provides platform summary data', () => {
      const { result } = renderHook(() => useDashboardSimulation(), { wrapper });

      expect(result.current.platformSummary).toEqual(mockSimulationData.platformSummary);
      expect(result.current.platformSummary[0].platform).toBe('Meta Ads');
    });

    it('provides daily trend data', () => {
      const { result } = renderHook(() => useDashboardSimulation(), { wrapper });

      expect(result.current.dailyTrend).toEqual(mockSimulationData.dailyTrend);
    });

    it('provides regional breakdown data', () => {
      const { result } = renderHook(() => useDashboardSimulation(), { wrapper });

      expect(result.current.regionalBreakdown).toEqual(mockSimulationData.regionalBreakdown);
      expect(result.current.regionalBreakdown).toHaveLength(2);
    });

    it('provides KPI metrics', () => {
      const { result } = renderHook(() => useDashboardSimulation(), { wrapper });

      expect(result.current.kpis).toEqual(mockSimulationData.kpis);
      expect(result.current.kpis?.totalSpend).toBe(1000);
      expect(result.current.kpis?.overallROAS).toBe(4.0);
    });

    it('provides alerts', () => {
      const { result } = renderHook(() => useDashboardSimulation(), { wrapper });

      expect(result.current.alerts).toEqual(mockSimulationData.alerts);
      expect(result.current.alerts[0].severity).toBe('good');
    });

    it('provides platform connections', () => {
      const { result } = renderHook(() => useDashboardSimulation(), { wrapper });

      expect(result.current.connections).toEqual(mockSimulationData.connections);
      expect(result.current.connections[0].status).toBe('connected');
    });

    it('provides signal health data', () => {
      const { result } = renderHook(() => useDashboardSimulation(), { wrapper });

      expect(result.current.signalHealth).toEqual(mockSimulationData.signalHealth);
      expect(result.current.signalHealth?.overall).toBe(85);
      expect(result.current.signalHealth?.status).toBe('PASS');
    });

    it('provides lastUpdated timestamp', () => {
      const { result } = renderHook(() => useDashboardSimulation(), { wrapper });

      expect(result.current.lastUpdated).toEqual(mockSimulationData.lastUpdated);
    });

    it('provides isLive state', () => {
      const { result } = renderHook(() => useDashboardSimulation(), { wrapper });

      expect(result.current.isLive).toBe(true);
    });

    it('provides setIsLive function', () => {
      const { result } = renderHook(() => useDashboardSimulation(), { wrapper });

      expect(typeof result.current.setIsLive).toBe('function');
    });

    it('provides refresh function', () => {
      const { result } = renderHook(() => useDashboardSimulation(), { wrapper });

      expect(typeof result.current.refresh).toBe('function');
    });
  });

  // ---------------------------------------------------------------------------
  // Context consumed by nested components
  // ---------------------------------------------------------------------------

  describe('Context consumed by nested components', () => {
    it('provides simulation data to deeply nested consumer', () => {
      function DashboardConsumer() {
        const sim = useDashboardSimulation();
        return (
          <div>
            <span data-testid="total-spend">{sim.kpis?.totalSpend}</span>
            <span data-testid="roas">{sim.kpis?.overallROAS}</span>
            <span data-testid="is-live">{String(sim.isLive)}</span>
            <span data-testid="signal-status">{sim.signalHealth?.status}</span>
          </div>
        );
      }

      render(
        <DashboardSimulationProvider>
          <div>
            <div>
              <DashboardConsumer />
            </div>
          </div>
        </DashboardSimulationProvider>
      );

      expect(screen.getByTestId('total-spend').textContent).toBe('1000');
      expect(screen.getByTestId('roas').textContent).toBe('4');
      expect(screen.getByTestId('is-live').textContent).toBe('true');
      expect(screen.getByTestId('signal-status').textContent).toBe('PASS');
    });
  });
});
