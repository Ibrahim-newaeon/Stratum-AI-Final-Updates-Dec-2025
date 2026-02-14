/**
 * Stratum AI - Unified Dashboard
 *
 * Main dashboard component that integrates all backend APIs:
 * - Overview metrics with real data
 * - Signal health & trust gate status
 * - AI recommendations with approve/reject
 * - Activity feed
 * - Platform performance
 * - Quick actions
 */

import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  ArrowRight,
  BarChart3,
  ChevronDown,
  DollarSign,
  Loader2,
  MousePointerClick,
  RefreshCw,
  Settings,
  Target,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { usePriceMetrics } from '@/hooks/usePriceMetrics';
import {
  TimePeriod,
  useApproveRecommendation,
  useDashboardActivity,
  useDashboardCampaigns,
  useDashboardOverview,
  useDashboardQuickActions,
  useDashboardRecommendations,
  useDashboardSignalHealth,
  useRejectRecommendation,
} from '@/api/dashboard';

// Components
import { SignalHealthCard } from './widgets/SignalHealthCard';
import { TrustGateStatus } from './widgets/TrustGateStatus';
import { RecommendationsCard } from './widgets/RecommendationsCard';
import { ActivityFeed } from './widgets/ActivityFeed';
import { MetricCard } from './widgets/MetricCard';
import { PlatformBreakdown } from './widgets/PlatformBreakdown';
import { CampaignPerformanceTable } from './widgets/CampaignPerformanceTable';
import { QuickActionsBar } from './widgets/QuickActionsBar';

// Period options
const periodOptions: { value: TimePeriod; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'yesterday', label: 'Yesterday' },
  { value: '7d', label: 'Last 7 Days' },
  { value: '30d', label: 'Last 30 Days' },
  { value: '90d', label: 'Last 90 Days' },
  { value: 'this_month', label: 'This Month' },
  { value: 'last_month', label: 'Last Month' },
];

export default function UnifiedDashboard() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [period, setPeriod] = useState<TimePeriod>('7d');
  const [showPeriodDropdown, setShowPeriodDropdown] = useState(false);
  const { showPriceMetrics } = usePriceMetrics();

  // Fetch all dashboard data
  const {
    data: overview,
    isLoading: overviewLoading,
  } = useDashboardOverview(period);

  const { data: campaigns, isLoading: campaignsLoading } = useDashboardCampaigns({
    period,
    page_size: 5,
    sort_by: 'spend',
    sort_order: 'desc',
  });

  const { data: recommendations, isLoading: recommendationsLoading } = useDashboardRecommendations({
    limit: 5,
  });

  const { data: activity, isLoading: activityLoading } = useDashboardActivity({
    limit: 10,
  });

  const { data: signalHealth, isLoading: signalHealthLoading } = useDashboardSignalHealth();

  const { data: quickActions } = useDashboardQuickActions();

  // Mutations
  const approveRecommendation = useApproveRecommendation();
  const rejectRecommendation = useRejectRecommendation();

  // Handlers
  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  }, [queryClient]);

  const handlePeriodChange = useCallback((newPeriod: TimePeriod) => {
    setPeriod(newPeriod);
    setShowPeriodDropdown(false);
  }, []);

  const handleApproveRecommendation = useCallback(
    async (id: string) => {
      await approveRecommendation.mutateAsync(id);
    },
    [approveRecommendation]
  );

  const handleRejectRecommendation = useCallback(
    async (id: string) => {
      await rejectRecommendation.mutateAsync(id);
    },
    [rejectRecommendation]
  );

  const isLoading = overviewLoading || signalHealthLoading;

  // Check if user needs to complete onboarding
  if (overview && !overview.onboarding_complete) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-8">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-6">
            <Settings className="w-8 h-8 text-primary" />
          </div>
          <h2 className="text-2xl font-bold mb-3">Complete Your Setup</h2>
          <p className="text-muted-foreground mb-6">
            Let's get your account set up so you can start optimizing your campaigns with Stratum
            AI.
          </p>
          <button
            onClick={() => navigate('/onboarding')}
            className="inline-flex items-center px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            Start Setup
            <ArrowRight className="w-4 h-4 ml-2" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            {overview?.period_label || 'Last 7 Days'} Overview
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Period Selector */}
          <div className="relative">
            <button
              onClick={() => setShowPeriodDropdown(!showPeriodDropdown)}
              className="inline-flex items-center px-4 py-2 border rounded-lg text-sm font-medium bg-background hover:bg-muted transition-colors"
            >
              {periodOptions.find((p) => p.value === period)?.label || 'Last 7 Days'}
              <ChevronDown className="w-4 h-4 ml-2" />
            </button>

            {showPeriodDropdown && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowPeriodDropdown(false)} />
                <div className="absolute right-0 mt-2 w-48 bg-card border rounded-lg shadow-lg z-20 py-1">
                  {periodOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => handlePeriodChange(option.value)}
                      className={cn(
                        'w-full px-4 py-2 text-left text-sm hover:bg-muted transition-colors',
                        period === option.value && 'bg-muted font-medium'
                      )}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="inline-flex items-center px-4 py-2 border rounded-lg text-sm font-medium bg-background hover:bg-muted transition-colors disabled:opacity-50"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Refresh
          </button>
        </div>
      </div>

      {/* Quick Actions Bar */}
      {quickActions && <QuickActionsBar actions={quickActions.actions} />}

      {/* Trust Gate & Signal Health Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <TrustGateStatus signalHealth={signalHealth} loading={signalHealthLoading} />
        </div>
        <div>
          <SignalHealthCard signalHealth={signalHealth} loading={signalHealthLoading} />
        </div>
      </div>

      {/* Key Metrics */}
      {(() => {
        const hidden = overview?.hidden_metrics || [];
        const priceHidden = !showPriceMetrics ? ['spend', 'revenue', 'roas', 'cpa'] : [];
        const allHidden = [...hidden, ...priceHidden];
        const primaryCards = [
          !allHidden.includes('spend') && (
            <MetricCard
              key="spend"
              title="Total Spend"
              value={overview?.metrics.spend.formatted || '$0'}
              change={overview?.metrics.spend.change_percent}
              trend={overview?.metrics.spend.trend}
              icon={<DollarSign className="w-5 h-5" />}
              loading={overviewLoading}
            />
          ),
          !allHidden.includes('revenue') && (
            <MetricCard
              key="revenue"
              title="Revenue"
              value={overview?.metrics.revenue.formatted || '$0'}
              change={overview?.metrics.revenue.change_percent}
              trend={overview?.metrics.revenue.trend}
              icon={<TrendingUp className="w-5 h-5" />}
              loading={overviewLoading}
              positive
            />
          ),
          !allHidden.includes('roas') && (
            <MetricCard
              key="roas"
              title="ROAS"
              value={overview?.metrics.roas.formatted || '0x'}
              change={overview?.metrics.roas.change_percent}
              trend={overview?.metrics.roas.trend}
              icon={<Target className="w-5 h-5" />}
              loading={overviewLoading}
              highlight={(overview?.metrics.roas.value ?? 0) >= 3}
              positive
            />
          ),
          !allHidden.includes('conversions') && (
            <MetricCard
              key="conversions"
              title="Conversions"
              value={overview?.metrics.conversions.formatted || '0'}
              change={overview?.metrics.conversions.change_percent}
              trend={overview?.metrics.conversions.trend}
              icon={<MousePointerClick className="w-5 h-5" />}
              loading={overviewLoading}
              positive
            />
          ),
        ].filter(Boolean);

        return primaryCards.length > 0 ? (
          <div className={cn(
            'grid gap-4',
            primaryCards.length === 4 ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4' :
            primaryCards.length === 3 ? 'grid-cols-1 sm:grid-cols-3' :
            primaryCards.length === 2 ? 'grid-cols-1 sm:grid-cols-2' :
            'grid-cols-1'
          )}>
            {primaryCards}
          </div>
        ) : null;
      })()}

      {/* Secondary Metrics Row */}
      {(() => {
        const hidden = overview?.hidden_metrics || [];
        const priceHidden2 = !showPriceMetrics ? ['spend', 'revenue', 'roas', 'cpa'] : [];
        const allHidden2 = [...hidden, ...priceHidden2];
        const secondaryCards = [
          !allHidden2.includes('cpa') && (
            <MetricCard
              key="cpa"
              title="CPA"
              value={overview?.metrics.cpa.formatted || '$0'}
              change={overview?.metrics.cpa.change_percent}
              trend={overview?.metrics.cpa.trend}
              icon={<DollarSign className="w-4 h-4" />}
              size="small"
              loading={overviewLoading}
            />
          ),
          !allHidden2.includes('ctr') && (
            <MetricCard
              key="ctr"
              title="CTR"
              value={overview?.metrics.ctr.formatted || '0%'}
              change={overview?.metrics.ctr.change_percent}
              trend={overview?.metrics.ctr.trend}
              icon={<MousePointerClick className="w-4 h-4" />}
              size="small"
              loading={overviewLoading}
            />
          ),
          !allHidden2.includes('impressions') && (
            <MetricCard
              key="impressions"
              title="Impressions"
              value={overview?.metrics.impressions.formatted || '0'}
              icon={<BarChart3 className="w-4 h-4" />}
              size="small"
              loading={overviewLoading}
            />
          ),
          !allHidden2.includes('clicks') && (
            <MetricCard
              key="clicks"
              title="Clicks"
              value={overview?.metrics.clicks.formatted || '0'}
              icon={<MousePointerClick className="w-4 h-4" />}
              size="small"
              loading={overviewLoading}
            />
          ),
        ].filter(Boolean);

        return secondaryCards.length > 0 ? (
          <div className={cn(
            'grid gap-4',
            secondaryCards.length === 4 ? 'grid-cols-2 sm:grid-cols-4' :
            secondaryCards.length === 3 ? 'grid-cols-3' :
            secondaryCards.length === 2 ? 'grid-cols-2' :
            'grid-cols-1'
          )}>
            {secondaryCards}
          </div>
        ) : null;
      })()}

      {/* Platform Breakdown */}
      <PlatformBreakdown platforms={overview?.platforms || []} loading={overviewLoading} />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Campaigns Table - Takes 2 columns */}
        <div className="lg:col-span-2">
          <CampaignPerformanceTable
            campaigns={campaigns?.campaigns || []}
            loading={campaignsLoading}
            onViewAll={() => navigate('/dashboard/campaigns')}
          />
        </div>

        {/* Right Column - Recommendations & Activity */}
        <div className="space-y-6">
          <RecommendationsCard
            recommendations={recommendations?.recommendations || []}
            loading={recommendationsLoading}
            onApprove={handleApproveRecommendation}
            onReject={handleRejectRecommendation}
            onViewAll={() => navigate('/dashboard/recommendations')}
          />

          <ActivityFeed
            activities={activity?.activities || []}
            loading={activityLoading}
            onViewAll={() => navigate('/dashboard/activity')}
          />
        </div>
      </div>
    </div>
  );
}
