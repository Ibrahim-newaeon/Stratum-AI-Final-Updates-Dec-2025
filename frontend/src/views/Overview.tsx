/**
 * Dashboard Overview Page
 * Stratum AI Marketing Intelligence Platform
 *
 * Features:
 * - Real-time KPI cards with animations
 * - Interactive charts with error boundaries
 * - Campaign performance table
 * - Advanced filtering with empty states
 * - Keyboard shortcuts
 * - Responsive design
 * - Full accessibility support
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { listItem, staggerContainer } from '@/lib/animations';
import {
  AlertTriangle,
  BarChart3,
  Bell,
  CheckCircle,
  DollarSign,
  Download,
  Eye,
  Info,
  Keyboard,
  MousePointerClick,
  RefreshCw,
  ShoppingCart,
  Target,
  TrendingUp,
} from 'lucide-react';
import { cn, formatCompactNumber, formatCurrency } from '@/lib/utils';
import { KPICard } from '@/components/dashboard/KPICard';
import { CampaignTable } from '@/components/dashboard/CampaignTable';
import { FilterBar } from '@/components/dashboard/FilterBar';
import { SimulateSlider } from '@/components/widgets/SimulateSlider';
import { LivePredictionsWidget } from '@/components/widgets/LivePredictionsWidget';
import { ROASAlertsWidget } from '@/components/widgets/ROASAlertsWidget';
import { BudgetOptimizerWidget } from '@/components/widgets/BudgetOptimizerWidget';
import {
  DailyTrendChart,
  PlatformPerformanceChart,
  RegionalBreakdownChart,
  ROASByPlatformChart,
} from '@/components/charts';
import { AlertSkeleton, TableSkeleton } from '@/components/ui/Skeleton';
import { NoFilterResultsState } from '@/components/ui/EmptyState';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import {
  Campaign,
  DailyPerformance,
  DashboardFilters,
  KPIMetrics,
  PlatformSummary,
} from '@/types/dashboard';
import { useAnomalies, useCampaigns, useTenantOverview } from '@/api/hooks';
import { ExportFormat, useExportDashboard } from '@/api/dashboard';
import { useTenantStore } from '@/stores/tenantStore';

// Mock data for demonstration
const mockCampaigns: Campaign[] = [
  {
    campaign_id: '1',
    campaign_name: 'Summer Sale 2024',
    platform: 'Meta Ads',
    region: 'Saudi Arabia',
    campaign_type: 'Conversion',
    spend: 12500,
    revenue: 45000,
    conversions: 450,
    impressions: 1250000,
    clicks: 25000,
    ctr: 2.0,
    cpm: 10.0,
    cpa: 27.78,
    roas: 3.6,
    status: 'Active',
    start_date: '2024-06-01',
  },
  {
    campaign_id: '2',
    campaign_name: 'Brand Awareness Q4',
    platform: 'Google Ads',
    region: 'UAE',
    campaign_type: 'Brand Awareness',
    spend: 8200,
    revenue: 28700,
    conversions: 287,
    impressions: 980000,
    clicks: 19600,
    ctr: 2.0,
    cpm: 8.37,
    cpa: 28.57,
    roas: 3.5,
    status: 'Active',
    start_date: '2024-09-15',
  },
  {
    campaign_id: '3',
    campaign_name: 'Retargeting - Cart Abandoners',
    platform: 'Meta Ads',
    region: 'Saudi Arabia',
    campaign_type: 'Retargeting',
    spend: 5600,
    revenue: 22400,
    conversions: 320,
    impressions: 560000,
    clicks: 11200,
    ctr: 2.0,
    cpm: 10.0,
    cpa: 17.5,
    roas: 4.0,
    status: 'Active',
    start_date: '2024-10-01',
  },
  {
    campaign_id: '4',
    campaign_name: 'TikTok Influencer Campaign',
    platform: 'TikTok Ads',
    region: 'UAE',
    campaign_type: 'Prospecting',
    spend: 15000,
    revenue: 37500,
    conversions: 500,
    impressions: 2500000,
    clicks: 50000,
    ctr: 2.0,
    cpm: 6.0,
    cpa: 30.0,
    roas: 2.5,
    status: 'Active',
    start_date: '2024-11-01',
  },
  {
    campaign_id: '5',
    campaign_name: 'Snapchat Gen-Z Reach',
    platform: 'Snapchat Ads',
    region: 'Qatar',
    campaign_type: 'Prospecting',
    spend: 4500,
    revenue: 11250,
    conversions: 150,
    impressions: 750000,
    clicks: 15000,
    ctr: 2.0,
    cpm: 6.0,
    cpa: 30.0,
    roas: 2.5,
    status: 'Active',
    start_date: '2024-11-15',
  },
];

const mockPlatformSummary: PlatformSummary[] = [
  {
    platform: 'Meta Ads',
    spend: 18100,
    revenue: 67400,
    conversions: 770,
    roas: 3.72,
    cpa: 23.51,
    impressions: 1810000,
    clicks: 36200,
  },
  {
    platform: 'Google Ads',
    spend: 8200,
    revenue: 28700,
    conversions: 287,
    roas: 3.5,
    cpa: 28.57,
    impressions: 980000,
    clicks: 19600,
  },
  {
    platform: 'TikTok Ads',
    spend: 15000,
    revenue: 37500,
    conversions: 500,
    roas: 2.5,
    cpa: 30.0,
    impressions: 2500000,
    clicks: 50000,
  },
  {
    platform: 'Snapchat Ads',
    spend: 4500,
    revenue: 11250,
    conversions: 150,
    roas: 2.5,
    cpa: 30.0,
    impressions: 750000,
    clicks: 15000,
  },
];

const mockDailyPerformance: DailyPerformance[] = Array.from({ length: 30 }, (_, i) => {
  const date = new Date();
  date.setDate(date.getDate() - (29 - i));
  return {
    date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    spend: 1200 + Math.random() * 800 + i * 20,
    revenue: 4000 + Math.random() * 2000 + i * 60,
    conversions: 40 + Math.floor(Math.random() * 20) + Math.floor(i * 0.5),
    roas: 2.5 + Math.random() * 1.5 + i * 0.03,
    ctr: 1.5 + Math.random() * 1.5,
    cpa: 25 + Math.random() * 15,
    impressions: 120000 + Math.random() * 50000 + i * 2000,
    clicks: 2400 + Math.floor(Math.random() * 1000) + i * 40,
  };
});

const mockAlerts = [
  {
    id: '1',
    severity: 'warning' as const,
    title: 'Campaign budget depleted',
    message: '"Summer Sale 2024" has reached 95% of daily budget',
    time: '10 minutes ago',
  },
  {
    id: '2',
    severity: 'good' as const,
    title: 'ROAS target achieved',
    message: '"Brand Awareness Q4" exceeded 4.0x ROAS target',
    time: '1 hour ago',
  },
  {
    id: '3',
    severity: 'critical' as const,
    title: 'New optimization suggestion',
    message: 'AI detected underperforming keywords in 3 campaigns',
    time: '3 hours ago',
  },
];

// Regional data for pie chart
const regionalData = [
  { name: 'Saudi Arabia', value: 45 },
  { name: 'UAE', value: 30 },
  { name: 'Qatar', value: 10 },
  { name: 'Kuwait', value: 8 },
  { name: 'Other', value: 7 },
];

export function Overview() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [showKeyboardHints, setShowKeyboardHints] = useState(false);

  // Get tenant ID from tenant store
  const tenantId = useTenantStore((state) => state.tenantId) ?? 1;

  // Fetch data from API with fallback to mock data
  const {
    data: campaignsData,
    isLoading: campaignsLoading,
    refetch: refetchCampaigns,
  } = useCampaigns();
  const { data: overviewData } = useTenantOverview(tenantId);
  const { data: _anomaliesData } = useAnomalies(tenantId);

  // Export mutation
  const exportMutation = useExportDashboard();

  // Filter state
  const [filters, setFilters] = useState<DashboardFilters>({
    dateRange: {
      start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
      end: new Date(),
    },
    platforms: ['Meta Ads', 'Google Ads', 'TikTok Ads', 'Snapchat Ads'],
    regions: ['Saudi Arabia', 'UAE', 'Qatar', 'Kuwait', 'Jordan', 'Iraq'],
    campaignTypes: ['Prospecting', 'Retargeting', 'Brand Awareness', 'Conversion'],
  });

  // Use API campaigns or fall back to mock data
  const campaigns = useMemo(() => {
    if (campaignsData?.items && campaignsData.items.length > 0) {
      return campaignsData.items.map((c: any) => ({
        campaign_id: c.id?.toString() || c.campaign_id,
        campaign_name: c.name || c.campaign_name,
        platform: c.platform || 'Unknown',
        region: c.region || 'Unknown',
        campaign_type: c.campaign_type || 'Conversion',
        spend: c.spend || 0,
        revenue: c.revenue || 0,
        conversions: c.conversions || 0,
        impressions: c.impressions || 0,
        clicks: c.clicks || 0,
        ctr: c.ctr || 0,
        cpm: c.cpm || 0,
        cpa: c.cpa || 0,
        roas: c.roas || 0,
        status: c.status || 'Active',
        start_date: c.start_date || c.startDate || new Date().toISOString(),
      })) as Campaign[];
    }
    return mockCampaigns;
  }, [campaignsData]);

  // Memoized: Calculate KPI metrics from campaigns (API or mock)
  const kpis = useMemo((): KPIMetrics => {
    // Use API overview data if available
    if (overviewData?.kpis) {
      // Cast to allow access to both snake_case and camelCase properties
      const apiKpis = overviewData.kpis as Record<string, number | undefined>;
      return {
        totalSpend: apiKpis.total_spend ?? apiKpis.totalSpend ?? 0,
        totalRevenue: apiKpis.total_revenue ?? apiKpis.totalRevenue ?? 0,
        overallROAS: apiKpis.roas ?? 0,
        totalConversions: apiKpis.conversions ?? 0,
        overallCPA: apiKpis.cpa ?? 0,
        avgCTR: apiKpis.ctr ?? 2.0,
        avgCPM: apiKpis.cpm ?? 10.0,
        totalImpressions: apiKpis.impressions ?? 0,
        totalClicks: apiKpis.clicks ?? 0,
        spendDelta: apiKpis.spendDelta ?? 12.5,
        revenueDelta: apiKpis.revenueDelta ?? 23.4,
        roasDelta: apiKpis.roasDelta ?? 9.7,
        conversionsDelta: apiKpis.conversionsDelta ?? 21.5,
      };
    }

    // Fall back to calculating from campaigns
    const totalSpend = campaigns.reduce((sum, c) => sum + c.spend, 0);
    const totalRevenue = campaigns.reduce((sum, c) => sum + c.revenue, 0);
    const totalConversions = campaigns.reduce((sum, c) => sum + c.conversions, 0);
    const overallROAS = totalSpend > 0 ? totalRevenue / totalSpend : 0;
    const overallCPA = totalConversions > 0 ? totalSpend / totalConversions : 0;
    const avgCTR =
      campaigns.length > 0 ? campaigns.reduce((sum, c) => sum + c.ctr, 0) / campaigns.length : 0;
    const avgCPM =
      campaigns.length > 0 ? campaigns.reduce((sum, c) => sum + c.cpm, 0) / campaigns.length : 0;
    const totalImpressions = campaigns.reduce((sum, c) => sum + c.impressions, 0);
    const totalClicks = campaigns.reduce((sum, c) => sum + c.clicks, 0);

    return {
      totalSpend,
      totalRevenue,
      overallROAS,
      totalConversions,
      overallCPA,
      avgCTR,
      avgCPM,
      totalImpressions,
      totalClicks,
      spendDelta: 12.5,
      revenueDelta: 23.4,
      roasDelta: 9.7,
      conversionsDelta: 21.5,
    };
  }, [campaigns, overviewData]);

  // Memoized: Filter campaigns based on current filters
  const filteredCampaigns = useMemo(() => {
    return campaigns.filter((campaign) => {
      if (filters.platforms.length > 0 && !filters.platforms.includes(campaign.platform)) {
        return false;
      }
      if (filters.regions.length > 0 && !filters.regions.includes(campaign.region)) {
        return false;
      }
      if (
        filters.campaignTypes.length > 0 &&
        !filters.campaignTypes.includes(campaign.campaign_type)
      ) {
        return false;
      }
      return true;
    });
  }, [filters, campaigns]);

  // Check if filters resulted in empty data
  const hasNoFilterResults = filteredCampaigns.length === 0 && campaigns.length > 0;

  // Refresh data
  const handleRefresh = useCallback(async () => {
    setLoading(true);
    // Refetch API data
    await refetchCampaigns();
    setLastUpdated(new Date());
    setLoading(false);
  }, [refetchCampaigns]);

  // Handle filter changes
  const handleFilterChange = useCallback((newFilters: Partial<DashboardFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  }, []);

  // Clear all filters
  const handleClearFilters = useCallback(() => {
    setFilters({
      dateRange: {
        start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
        end: new Date(),
      },
      platforms: ['Meta Ads', 'Google Ads', 'TikTok Ads', 'Snapchat Ads'],
      regions: ['Saudi Arabia', 'UAE', 'Qatar', 'Kuwait', 'Jordan', 'Iraq'],
      campaignTypes: ['Prospecting', 'Retargeting', 'Brand Awareness', 'Conversion'],
    });
  }, []);

  // Export handler
  const handleExport = useCallback(
    (format: ExportFormat = 'csv') => {
      exportMutation.mutate({
        format,
        period: '30d',
        include_campaigns: true,
        include_metrics: true,
        include_recommendations: true,
      });
    },
    [exportMutation]
  );

  // KPI action handlers
  const handleViewDetails = useCallback((metric: string) => {
    console.log('View details for:', metric);
  }, []);

  const handleSetAlert = useCallback((metric: string) => {
    console.log('Set alert for:', metric);
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (e.key.toLowerCase()) {
        case 'r':
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            handleRefresh();
          }
          break;
        case 'e':
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            handleExport('csv');
          }
          break;
        case '?':
          e.preventDefault();
          setShowKeyboardHints((prev) => !prev);
          break;
        case 'escape':
          setShowKeyboardHints(false);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleRefresh, handleExport]);

  // Set initial loading based on API loading state
  useEffect(() => {
    if (!campaignsLoading) {
      setInitialLoading(false);
    }
  }, [campaignsLoading]);

  // Auto-refresh every 5 minutes
  useEffect(() => {
    const interval = setInterval(handleRefresh, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [handleRefresh]);

  // Calculate active filter count
  const activeFilterCount =
    (filters.platforms.length < 4 ? 4 - filters.platforms.length : 0) +
    (filters.regions.length < 6 ? 6 - filters.regions.length : 0);

  return (
    <div className="space-y-6">
      {/* Keyboard Shortcuts Modal */}
      {showKeyboardHints && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={() => setShowKeyboardHints(false)}
        >
          <div
            className="bg-card border rounded-xl p-6 shadow-xl max-w-sm w-full mx-4 animate-in fade-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-4">
              <Keyboard className="w-5 h-5 text-primary" />
              <h3 className="text-lg font-semibold">Keyboard Shortcuts</h3>
            </div>
            <div className="space-y-3">
              {[
                { key: 'R', action: 'Refresh data' },
                { key: 'E', action: 'Export dashboard' },
                { key: '?', action: 'Toggle shortcuts' },
                { key: 'Esc', action: 'Close modal' },
              ].map((shortcut) => (
                <div key={shortcut.key} className="flex items-center justify-between">
                  <span className="text-muted-foreground">{shortcut.action}</span>
                  <kbd className="px-2 py-1 text-xs font-mono bg-muted rounded border">
                    {shortcut.key}
                  </kbd>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-foreground">{t('overview.title')}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Last updated: {lastUpdated.toLocaleString()} | Stratum AI
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Keyboard shortcut hint */}
          <button
            onClick={() => setShowKeyboardHints(true)}
            className="hidden lg:flex items-center px-3 py-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
            title="Keyboard shortcuts (?)"
          >
            <Keyboard className="w-4 h-4 mr-1" />
            <kbd className="px-1.5 py-0.5 text-xs bg-muted rounded">?</kbd>
          </button>

          <button
            onClick={handleRefresh}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 border rounded-lg text-sm font-medium bg-background hover:bg-muted transition-colors disabled:opacity-50"
            aria-label="Refresh data (R)"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                Refreshing...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh
              </>
            )}
          </button>

          <button
            onClick={() => handleExport('csv')}
            disabled={exportMutation.isPending}
            className="inline-flex items-center px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            aria-label="Export dashboard (E)"
          >
            {exportMutation.isPending ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="w-4 h-4 mr-2" />
                {t('common.export')}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar
        filters={filters}
        onChange={handleFilterChange}
        platforms={['Meta Ads', 'Google Ads', 'TikTok Ads', 'Snapchat Ads']}
        regions={['Saudi Arabia', 'UAE', 'Qatar', 'Kuwait', 'Jordan', 'Iraq']}
      />

      {/* Primary KPI Cards */}
      <motion.div
        className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        <motion.div
          variants={listItem}
          className="rounded-xl backdrop-blur-xl transition-all hover:scale-[1.02]"
          style={{
            background: 'rgba(168, 85, 247, 0.1)',
            border: '1px solid rgba(168, 85, 247, 0.2)',
            boxShadow: '0 8px 32px rgba(168, 85, 247, 0.1)',
          }}
        >
          <KPICard
            title="Total Spend"
            value={formatCurrency(kpis.totalSpend)}
            numericValue={kpis.totalSpend}
            prefix="$"
            delta={kpis.spendDelta}
            deltaText="vs last period"
            trend={kpis.spendDelta && kpis.spendDelta > 0 ? 'up' : 'down'}
            icon={<DollarSign className="w-5 h-5" />}
            loading={initialLoading}
            onViewDetails={() => handleViewDetails('spend')}
            onSetAlert={() => handleSetAlert('spend')}
          />
        </motion.div>

        <motion.div
          variants={listItem}
          className="rounded-xl backdrop-blur-xl transition-all hover:scale-[1.02]"
          style={{
            background: 'rgba(34, 197, 94, 0.1)',
            border: '1px solid rgba(34, 197, 94, 0.2)',
            boxShadow: '0 8px 32px rgba(34, 197, 94, 0.1)',
          }}
        >
          <KPICard
            title="Total Revenue"
            value={formatCurrency(kpis.totalRevenue)}
            numericValue={kpis.totalRevenue}
            prefix="$"
            delta={kpis.revenueDelta}
            deltaText="vs last period"
            trend={kpis.revenueDelta && kpis.revenueDelta > 0 ? 'up' : 'down'}
            trendIsGood={true}
            icon={<TrendingUp className="w-5 h-5" />}
            loading={initialLoading}
            onViewDetails={() => handleViewDetails('revenue')}
            onSetAlert={() => handleSetAlert('revenue')}
          />
        </motion.div>

        <motion.div
          variants={listItem}
          className="rounded-xl backdrop-blur-xl transition-all hover:scale-[1.02]"
          style={{
            background: 'rgba(217, 38, 101, 0.1)',
            border: '1px solid rgba(217, 38, 101, 0.2)',
            boxShadow: '0 8px 32px rgba(217, 38, 101, 0.1)',
          }}
        >
          <KPICard
            title="ROAS"
            value={`${kpis.overallROAS.toFixed(2)}x`}
            numericValue={kpis.overallROAS}
            suffix="x"
            decimals={2}
            delta={kpis.roasDelta}
            deltaText="vs target"
            trend={kpis.roasDelta && kpis.roasDelta > 0 ? 'up' : 'down'}
            trendIsGood={true}
            highlight={kpis.overallROAS >= 3.0}
            icon={<Target className="w-5 h-5" />}
            loading={initialLoading}
            onViewDetails={() => handleViewDetails('roas')}
            onSetAlert={() => handleSetAlert('roas')}
          />
        </motion.div>

        <motion.div
          variants={listItem}
          className="rounded-xl backdrop-blur-xl transition-all hover:scale-[1.02]"
          style={{
            background: 'rgba(249, 115, 22, 0.1)',
            border: '1px solid rgba(249, 115, 22, 0.2)',
            boxShadow: '0 8px 32px rgba(249, 115, 22, 0.1)',
          }}
        >
          <KPICard
            title="Total Conversions"
            value={kpis.totalConversions.toLocaleString('en-US')}
            numericValue={kpis.totalConversions}
            delta={kpis.conversionsDelta}
            deltaText="vs last period"
            trend={kpis.conversionsDelta && kpis.conversionsDelta > 0 ? 'up' : 'down'}
            trendIsGood={true}
            icon={<ShoppingCart className="w-5 h-5" />}
            loading={initialLoading}
            onViewDetails={() => handleViewDetails('conversions')}
            onSetAlert={() => handleSetAlert('conversions')}
          />
        </motion.div>
      </motion.div>

      {/* Secondary KPI Cards */}
      <motion.div
        className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        <motion.div
          variants={listItem}
          className="rounded-xl backdrop-blur-xl transition-all hover:scale-[1.02]"
          style={{
            background: 'rgba(236, 72, 153, 0.1)',
            border: '1px solid rgba(236, 72, 153, 0.2)',
            boxShadow: '0 8px 32px rgba(236, 72, 153, 0.1)',
          }}
        >
          <KPICard
            title="CPA"
            value={formatCurrency(kpis.overallCPA)}
            numericValue={kpis.overallCPA}
            prefix="$"
            decimals={2}
            size="small"
            icon={<DollarSign className="w-4 h-4" />}
            loading={initialLoading}
          />
        </motion.div>

        <motion.div
          variants={listItem}
          className="rounded-xl backdrop-blur-xl transition-all hover:scale-[1.02]"
          style={{
            background: 'rgba(34, 197, 94, 0.1)',
            border: '1px solid rgba(34, 197, 94, 0.2)',
            boxShadow: '0 8px 32px rgba(34, 197, 94, 0.1)',
          }}
        >
          <KPICard
            title="CTR"
            value={`${kpis.avgCTR.toFixed(2)}%`}
            numericValue={kpis.avgCTR}
            suffix="%"
            decimals={2}
            size="small"
            icon={<MousePointerClick className="w-4 h-4" />}
            loading={initialLoading}
          />
        </motion.div>

        <motion.div
          variants={listItem}
          className="rounded-xl backdrop-blur-xl transition-all hover:scale-[1.02]"
          style={{
            background: 'rgba(168, 85, 247, 0.1)',
            border: '1px solid rgba(168, 85, 247, 0.2)',
            boxShadow: '0 8px 32px rgba(168, 85, 247, 0.1)',
          }}
        >
          <KPICard
            title="CPM"
            value={formatCurrency(kpis.avgCPM)}
            numericValue={kpis.avgCPM}
            prefix="$"
            decimals={2}
            size="small"
            icon={<BarChart3 className="w-4 h-4" />}
            loading={initialLoading}
          />
        </motion.div>

        <motion.div
          variants={listItem}
          className="rounded-xl backdrop-blur-xl transition-all hover:scale-[1.02]"
          style={{
            background: 'rgba(249, 115, 22, 0.1)',
            border: '1px solid rgba(249, 115, 22, 0.2)',
            boxShadow: '0 8px 32px rgba(249, 115, 22, 0.1)',
          }}
        >
          <KPICard
            title="Impressions"
            value={formatCompactNumber(kpis.totalImpressions)}
            numericValue={kpis.totalImpressions}
            size="small"
            icon={<Eye className="w-4 h-4" />}
            loading={initialLoading}
          />
        </motion.div>

        <motion.div
          variants={listItem}
          className="rounded-xl backdrop-blur-xl transition-all hover:scale-[1.02]"
          style={{
            background: 'rgba(217, 38, 101, 0.1)',
            border: '1px solid rgba(217, 38, 101, 0.2)',
            boxShadow: '0 8px 32px rgba(217, 38, 101, 0.1)',
          }}
        >
          <KPICard
            title="Clicks"
            value={formatCompactNumber(kpis.totalClicks)}
            numericValue={kpis.totalClicks}
            size="small"
            icon={<MousePointerClick className="w-4 h-4" />}
            loading={initialLoading}
          />
        </motion.div>
      </motion.div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PlatformPerformanceChart
          data={mockPlatformSummary}
          loading={initialLoading}
          onRefresh={handleRefresh}
        />

        <ROASByPlatformChart
          data={mockPlatformSummary}
          loading={initialLoading}
          targetROAS={3.0}
          onRefresh={handleRefresh}
        />
      </div>

      {/* Second Row of Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <DailyTrendChart
            data={mockDailyPerformance}
            loading={initialLoading}
            onRefresh={handleRefresh}
          />
        </div>

        <RegionalBreakdownChart
          data={regionalData}
          loading={initialLoading}
          onRefresh={handleRefresh}
        />
      </div>

      {/* Third Row - Table and Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Campaign Performance Table */}
        <div className="lg:col-span-2">
          {initialLoading ? (
            <TableSkeleton rows={5} columns={7} />
          ) : hasNoFilterResults ? (
            <div
              className="rounded-xl overflow-hidden backdrop-blur-xl"
              style={{
                background: 'rgba(168, 85, 247, 0.08)',
                border: '1px solid rgba(168, 85, 247, 0.2)',
                boxShadow: '0 8px 32px rgba(168, 85, 247, 0.1)',
              }}
            >
              <div className="px-6 py-4 border-b border-purple-500/20">
                <h3 className="text-lg font-semibold text-foreground">Top Performing Campaigns</h3>
              </div>
              <NoFilterResultsState
                onClearFilters={handleClearFilters}
                filterCount={activeFilterCount}
              />
            </div>
          ) : (
            <div
              className="rounded-xl overflow-hidden backdrop-blur-xl"
              style={{
                background: 'rgba(168, 85, 247, 0.08)',
                border: '1px solid rgba(168, 85, 247, 0.2)',
                boxShadow: '0 8px 32px rgba(168, 85, 247, 0.1)',
              }}
            >
              <div className="px-6 py-4 border-b border-purple-500/20">
                <h3 className="text-lg font-semibold text-foreground">Top Performing Campaigns</h3>
              </div>
              <ErrorBoundary>
                <CampaignTable
                  campaigns={filteredCampaigns}
                  onCampaignClick={(campaignId) => {
                    console.log('Navigate to campaign:', campaignId);
                  }}
                />
              </ErrorBoundary>
            </div>
          )}
        </div>

        {/* Simulator Widget */}
        <ErrorBoundary>
          <SimulateSlider />
        </ErrorBoundary>
      </div>

      {/* AI Predictions Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <ErrorBoundary>
          <LivePredictionsWidget />
        </ErrorBoundary>

        <ErrorBoundary>
          <ROASAlertsWidget />
        </ErrorBoundary>

        <ErrorBoundary>
          <BudgetOptimizerWidget />
        </ErrorBoundary>
      </div>

      {/* Alerts Section */}
      <div
        className="rounded-xl p-6 backdrop-blur-xl"
        style={{
          background: 'rgba(34, 197, 94, 0.08)',
          border: '1px solid rgba(34, 197, 94, 0.2)',
          boxShadow: '0 8px 32px rgba(34, 197, 94, 0.1)',
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <Bell className="w-5 h-5" />
            {t('overview.recentAlerts')}
          </h3>
          <button className="text-sm text-primary hover:underline">{t('common.viewAll')}</button>
        </div>

        {initialLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <AlertSkeleton key={i} />
            ))}
          </div>
        ) : (
          <motion.div
            className="grid grid-cols-1 md:grid-cols-3 gap-4"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            {mockAlerts.map((alert) => (
              <motion.div
                key={alert.id}
                variants={listItem}
                whileHover={{ scale: 1.02, y: -2 }}
                whileTap={{ scale: 0.98 }}
                className={cn(
                  'p-4 rounded-lg border-l-4 transition-colors cursor-pointer',
                  alert.severity === 'warning' &&
                    'bg-amber-500/10 border-amber-500 hover:bg-amber-500/15',
                  alert.severity === 'good' &&
                    'bg-green-500/10 border-green-500 hover:bg-green-500/15',
                  alert.severity === 'critical' &&
                    'bg-red-500/10 border-red-500 hover:bg-red-500/15'
                )}
                role="button"
                tabIndex={0}
                aria-label={`${alert.severity} alert: ${alert.title}`}
              >
                <div className="flex items-start gap-3">
                  {alert.severity === 'warning' && (
                    <AlertTriangle
                      className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0"
                      aria-hidden="true"
                    />
                  )}
                  {alert.severity === 'good' && (
                    <CheckCircle
                      className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0"
                      aria-hidden="true"
                    />
                  )}
                  {alert.severity === 'critical' && (
                    <Info
                      className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0"
                      aria-hidden="true"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm text-foreground">{alert.title}</p>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                      {alert.message}
                    </p>
                    <p className="text-xs text-muted-foreground mt-2">{alert.time}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </div>
  );
}

export default Overview;
