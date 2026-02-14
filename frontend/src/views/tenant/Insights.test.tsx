/**
 * Stratum AI - Insights View Component Tests
 *
 * Tests cover:
 * - KPI cards rendering with real API data
 * - Price metrics toggle (show/hide revenue, spend, ROAS)
 * - Loading skeleton display
 * - Empty state handling
 * - Date range selector
 * - Platform performance table
 * - Top campaigns table
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { HelmetProvider } from 'react-helmet-async';
import TenantInsights from './Insights';

// =============================================================================
// Mock API hooks
// =============================================================================

const mockOverviewData = {
  metrics: {
    revenue: { value: 125000, formatted: '$125,000', change_percent: 12.5, trend: 'up' as const },
    spend: { value: 45000, formatted: '$45,000', change_percent: -3.2, trend: 'down' as const },
    roas: { value: 2.78, formatted: '2.78x', change_percent: 8.1, trend: 'up' as const },
    conversions: { value: 1250, formatted: '1,250', change_percent: 15.3, trend: 'up' as const },
    cpa: { value: 36, formatted: '$36.00', change_percent: -5.0, trend: 'down' as const },
    impressions: { value: 500000, formatted: '500K', change_percent: 10.0, trend: 'up' as const },
    clicks: { value: 25000, formatted: '25K', change_percent: 7.5, trend: 'up' as const },
    ctr: { value: 5.0, formatted: '5.0%', change_percent: 2.0, trend: 'up' as const },
  },
  platforms: [
    { platform: 'Meta', status: 'connected' as const, spend: 25000, revenue: 75000, roas: 3.0, campaigns_count: 12, last_synced_at: '2025-12-01T00:00:00Z' },
    { platform: 'Google', status: 'connected' as const, spend: 20000, revenue: 50000, roas: 2.5, campaigns_count: 8, last_synced_at: '2025-12-01T00:00:00Z' },
  ],
};

const mockCampaignsData = {
  campaigns: [
    { id: 1, name: 'Summer Sale', platform: 'Meta', status: 'active', spend: 5000, revenue: 15000, roas: 3.0, conversions: 150, trend: 'up' as const, scaling_score: 85, recommendation: null },
    { id: 2, name: 'Brand Awareness', platform: 'Google', status: 'paused', spend: 3000, revenue: 6000, roas: 2.0, conversions: 80, trend: 'down' as const, scaling_score: null, recommendation: 'Review targeting' },
  ],
};

let mockOverviewReturn: { data: typeof mockOverviewData | undefined; isLoading: boolean };
let mockCampaignsReturn: { data: typeof mockCampaignsData | undefined; isLoading: boolean };
let mockShowPriceMetrics = true;

vi.mock('@/api/dashboard', () => ({
  useDashboardOverview: () => mockOverviewReturn,
  useDashboardCampaigns: () => mockCampaignsReturn,
}));

vi.mock('@/hooks/usePriceMetrics', () => ({
  usePriceMetrics: () => ({ showPriceMetrics: mockShowPriceMetrics }),
}));

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => {
      const { initial, animate, transition, whileHover, whileTap, ...validProps } = props;
      return <div {...validProps}>{children}</div>;
    },
  },
  AnimatePresence: ({ children }: React.PropsWithChildren) => <>{children}</>,
}));

// =============================================================================
// Helper
// =============================================================================

const renderInsights = () =>
  render(
    <HelmetProvider>
      <TenantInsights />
    </HelmetProvider>
  );

// =============================================================================
// Tests
// =============================================================================

describe('TenantInsights', () => {
  beforeEach(() => {
    mockOverviewReturn = { data: mockOverviewData, isLoading: false };
    mockCampaignsReturn = { data: mockCampaignsData, isLoading: false };
    mockShowPriceMetrics = true;
  });

  // ---------------------------------------------------------------------------
  // 1. Basic Rendering
  // ---------------------------------------------------------------------------

  describe('Basic Rendering', () => {
    it('should render the Insights heading', () => {
      renderInsights();
      expect(screen.getByText('Insights')).toBeInTheDocument();
    });

    it('should render the subheading', () => {
      renderInsights();
      expect(screen.getByText('Performance overview across all platforms')).toBeInTheDocument();
    });

    it('should render date range selector buttons', () => {
      renderInsights();
      expect(screen.getByText('7d')).toBeInTheDocument();
      expect(screen.getByText('30d')).toBeInTheDocument();
      expect(screen.getByText('90d')).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // 2. KPI Cards with Price Metrics ON
  // ---------------------------------------------------------------------------

  describe('KPI Cards (price metrics enabled)', () => {
    beforeEach(() => {
      mockShowPriceMetrics = true;
    });

    it('should display Revenue KPI card', () => {
      renderInsights();
      expect(screen.getByText('Revenue')).toBeInTheDocument();
      expect(screen.getByText('$125,000')).toBeInTheDocument();
    });

    it('should display Ad Spend KPI card', () => {
      renderInsights();
      expect(screen.getByText('Ad Spend')).toBeInTheDocument();
      expect(screen.getByText('$45,000')).toBeInTheDocument();
    });

    it('should display ROAS KPI card', () => {
      renderInsights();
      expect(screen.getByText('ROAS')).toBeInTheDocument();
      expect(screen.getByText('2.78x')).toBeInTheDocument();
    });

    it('should display Conversions KPI card', () => {
      renderInsights();
      expect(screen.getByText('Conversions')).toBeInTheDocument();
      expect(screen.getByText('1,250')).toBeInTheDocument();
    });

    it('should show positive trend indicators', () => {
      renderInsights();
      expect(screen.getByText('+12.5%')).toBeInTheDocument();
    });

    it('should show negative trend indicators', () => {
      renderInsights();
      expect(screen.getByText('-3.2%')).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // 3. KPI Cards with Price Metrics OFF
  // ---------------------------------------------------------------------------

  describe('KPI Cards (price metrics disabled)', () => {
    beforeEach(() => {
      mockShowPriceMetrics = false;
    });

    it('should NOT display Revenue KPI card', () => {
      renderInsights();
      expect(screen.queryByText('Revenue')).not.toBeInTheDocument();
    });

    it('should NOT display Ad Spend KPI card', () => {
      renderInsights();
      expect(screen.queryByText('Ad Spend')).not.toBeInTheDocument();
    });

    it('should NOT display ROAS KPI card', () => {
      renderInsights();
      expect(screen.queryByText('ROAS')).not.toBeInTheDocument();
    });

    it('should still display Conversions KPI card', () => {
      renderInsights();
      expect(screen.getByText('Conversions')).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // 4. Loading States
  // ---------------------------------------------------------------------------

  describe('Loading States', () => {
    it('should show skeletons when overview is loading', () => {
      mockOverviewReturn = { data: undefined, isLoading: true };
      const { container } = renderInsights();
      const skeletons = container.querySelectorAll('.animate-pulse');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('should show skeletons when campaigns are loading', () => {
      mockCampaignsReturn = { data: undefined, isLoading: true };
      const { container } = renderInsights();
      const skeletons = container.querySelectorAll('.animate-pulse');
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  // ---------------------------------------------------------------------------
  // 5. Empty States
  // ---------------------------------------------------------------------------

  describe('Empty States', () => {
    it('should show empty state for platform performance', () => {
      mockOverviewReturn = {
        data: { ...mockOverviewData, platforms: [] },
        isLoading: false,
      };
      renderInsights();
      expect(screen.getByText('No platform data available for this period')).toBeInTheDocument();
    });

    it('should show empty state for campaigns', () => {
      mockCampaignsReturn = {
        data: { campaigns: [] },
        isLoading: false,
      };
      renderInsights();
      expect(screen.getByText('No campaign data available')).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // 6. Platform Performance Table
  // ---------------------------------------------------------------------------

  describe('Platform Performance Table', () => {
    it('should render platform names', () => {
      renderInsights();
      expect(screen.getByText('Platform Performance')).toBeInTheDocument();
      // Platform names in badges
      expect(screen.getAllByText('Meta').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Google').length).toBeGreaterThanOrEqual(1);
    });

    it('should render platform status badges', () => {
      renderInsights();
      const connectedBadges = screen.getAllByText('connected');
      expect(connectedBadges.length).toBe(2);
    });

    it('should hide spend/revenue/ROAS columns when price metrics disabled', () => {
      mockShowPriceMetrics = false;
      renderInsights();
      // The table headers should not include Spend, Revenue, ROAS
      const headerCells = screen.getAllByRole('columnheader');
      const headerTexts = headerCells.map((th) => th.textContent);
      expect(headerTexts).not.toContain('Spend');
      expect(headerTexts).not.toContain('Revenue');
    });
  });

  // ---------------------------------------------------------------------------
  // 7. Top Campaigns Table
  // ---------------------------------------------------------------------------

  describe('Top Campaigns Table', () => {
    it('should render campaign names', () => {
      renderInsights();
      expect(screen.getByText('Top Campaigns')).toBeInTheDocument();
      expect(screen.getByText('Summer Sale')).toBeInTheDocument();
      expect(screen.getByText('Brand Awareness')).toBeInTheDocument();
    });

    it('should render campaign status badges', () => {
      renderInsights();
      expect(screen.getByText('active')).toBeInTheDocument();
      expect(screen.getByText('paused')).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // 8. Date Range Interaction
  // ---------------------------------------------------------------------------

  describe('Date Range Selector', () => {
    it('should have 30d selected by default', () => {
      renderInsights();
      const button30d = screen.getByText('30d');
      // The active button should have primary styling
      expect(button30d.className).toContain('bg-primary');
    });

    it('should allow clicking different date ranges', () => {
      renderInsights();
      const button7d = screen.getByText('7d');
      fireEvent.click(button7d);
      // After clicking, 7d should now be active
      expect(button7d.className).toContain('bg-primary');
    });
  });
});
