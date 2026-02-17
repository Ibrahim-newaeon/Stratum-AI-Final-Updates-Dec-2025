/**
 * Tenant Insights Dashboard
 *
 * Aggregated performance view with KPI cards, revenue vs spend chart,
 * platform performance table, and top campaigns table.
 * Wired to real dashboard APIs — no mock data.
 */

import { useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { motion } from 'framer-motion';
import {
  CurrencyDollarIcon,
  BanknotesIcon,
  ArrowTrendingUpIcon,
  ShoppingCartIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import { usePriceMetrics } from '@/hooks/usePriceMetrics';
import {
  useDashboardOverview,
  useDashboardCampaigns,
  type TimePeriod,
  type PlatformSummary,
  type CampaignSummaryItem,
} from '@/api/dashboard';

const fadeIn = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.3 },
};

type DateRange = '7d' | '30d' | '90d';

const dateRangeToTimePeriod: Record<DateRange, TimePeriod> = {
  '7d': '7d',
  '30d': '30d',
  '90d': '90d',
};

export default function TenantInsights() {
  const [dateRange, setDateRange] = useState<DateRange>('30d');
  const { showPriceMetrics } = usePriceMetrics();

  const period = dateRangeToTimePeriod[dateRange];

  // Fetch real API data
  const { data: overview, isLoading: overviewLoading } = useDashboardOverview(period);
  const { data: campaigns, isLoading: campaignsLoading } = useDashboardCampaigns({
    period,
    page_size: 5,
    sort_by: 'spend',
    sort_order: 'desc',
  });

  const isLoading = overviewLoading || campaignsLoading;

  const formatCurrency = (value: number): string =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value);

  // Build KPI cards from real metrics (price metrics filtered by toggle)
  const kpis = useMemo(() => {
    const m = overview?.metrics;
    const priceLabels = ['Revenue', 'Ad Spend', 'ROAS'];
    const all = [
      {
        label: 'Revenue',
        value: m?.revenue?.formatted ?? '$0',
        trend: m?.revenue?.change_percent ?? 0,
        icon: CurrencyDollarIcon,
        color: 'text-green-500',
      },
      {
        label: 'Ad Spend',
        value: m?.spend?.formatted ?? '$0',
        trend: m?.spend?.change_percent ?? 0,
        icon: BanknotesIcon,
        color: 'text-blue-500',
      },
      {
        label: 'ROAS',
        value: m?.roas?.formatted ?? '0x',
        trend: m?.roas?.change_percent ?? 0,
        icon: ArrowTrendingUpIcon,
        color: 'text-purple-500',
      },
      {
        label: 'Conversions',
        value: m?.conversions?.formatted ?? '0',
        trend: m?.conversions?.change_percent ?? 0,
        icon: ShoppingCartIcon,
        color: 'text-amber-500',
      },
    ];
    return showPriceMetrics ? all : all.filter((k) => !priceLabels.includes(k.label));
  }, [overview?.metrics, showPriceMetrics]);

  // Platform performance from real data
  const platformPerformance: PlatformSummary[] = overview?.platforms ?? [];

  // Top campaigns from real data
  const topCampaigns: CampaignSummaryItem[] = campaigns?.campaigns ?? [];

  const platformBadge = (platform: string) => {
    const colors: Record<string, string> = {
      Google: 'bg-blue-500/10 text-blue-400',
      Meta: 'bg-indigo-500/10 text-indigo-400',
      TikTok: 'bg-gray-500/10 text-gray-300',
      Snapchat: 'bg-yellow-500/10 text-yellow-400',
      google: 'bg-blue-500/10 text-blue-400',
      meta: 'bg-indigo-500/10 text-indigo-400',
      tiktok: 'bg-gray-500/10 text-gray-300',
      snapchat: 'bg-yellow-500/10 text-yellow-400',
    };
    return colors[platform] || 'bg-gray-500/10 text-gray-400';
  };

  // Skeleton loader component
  const Skeleton = ({ className = '' }: { className?: string }) => (
    <div className={cn('animate-pulse bg-white/10 rounded', className)} />
  );

  return (
    <>
      <Helmet>
        <title>Insights | Stratum AI</title>
      </Helmet>

      <div className="space-y-6 max-w-7xl mx-auto">
        {/* Header */}
        <motion.div className="flex items-center justify-between" {...fadeIn}>
          <div>
            <h1 className="text-2xl font-bold">Insights</h1>
            <p className="text-muted-foreground">Performance overview across all platforms</p>
          </div>
          <div className="flex items-center gap-1 p-1 rounded-lg bg-white/5 border border-white/10">
            {(['7d', '30d', '90d'] as DateRange[]).map((range) => (
              <button
                key={range}
                onClick={() => setDateRange(range)}
                className={cn(
                  'px-3 py-1.5 text-sm rounded-md transition-colors uppercase',
                  dateRange === range
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {range}
              </button>
            ))}
          </div>
        </motion.div>

        {/* KPI Cards */}
        <motion.div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
          {...fadeIn}
          transition={{ delay: 0.1 }}
        >
          {isLoading
            ? Array.from({ length: 4 }).map((_, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-4"
                >
                  <Skeleton className="h-5 w-5 mb-2" />
                  <Skeleton className="h-8 w-24 mb-1" />
                  <Skeleton className="h-3 w-16" />
                </div>
              ))
            : kpis.map((kpi) => (
                <div
                  key={kpi.label}
                  className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <kpi.icon className={cn('h-5 w-5', kpi.color)} />
                    <span
                      className={cn(
                        'text-xs font-medium px-2 py-0.5 rounded-full',
                        kpi.trend >= 0
                          ? 'bg-green-500/10 text-green-500'
                          : 'bg-red-500/10 text-red-500'
                      )}
                    >
                      {kpi.trend >= 0 ? '+' : ''}
                      {kpi.trend?.toFixed(1) ?? '0'}%
                    </span>
                  </div>
                  <p className="text-2xl font-bold">{kpi.value}</p>
                  <p className="text-xs text-muted-foreground mt-1">{kpi.label}</p>
                </div>
              ))}
        </motion.div>

        {/* Platform Performance Table */}
        <motion.div
          className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-6"
          {...fadeIn}
          transition={{ delay: 0.15 }}
        >
          <h3 className="font-semibold mb-4">Platform Performance</h3>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : platformPerformance.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>No platform data available for this period</p>
              <p className="text-sm mt-1">Connect an ad platform to see performance metrics</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/10">
                    {['Platform', 'Status', ...(showPriceMetrics ? ['Spend', 'Revenue', 'ROAS'] : []), 'Campaigns'].map((h) => (
                      <th
                        key={h}
                        className="text-left py-2 px-3 text-sm font-medium text-muted-foreground"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {platformPerformance.map((row) => (
                    <tr key={row.platform} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-3 px-3">
                        <span
                          className={cn(
                            'px-2 py-0.5 rounded-full text-xs font-medium capitalize',
                            platformBadge(row.platform)
                          )}
                        >
                          {row.platform}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={cn(
                            'px-2 py-0.5 rounded-full text-xs font-medium',
                            row.status === 'connected'
                              ? 'bg-green-500/10 text-green-400'
                              : row.status === 'error'
                                ? 'bg-red-500/10 text-red-400'
                                : 'bg-gray-500/10 text-gray-400'
                          )}
                        >
                          {row.status}
                        </span>
                      </td>
                      {showPriceMetrics && (
                        <td className="py-3 px-3 text-sm">{formatCurrency(row.spend)}</td>
                      )}
                      {showPriceMetrics && (
                        <td className="py-3 px-3 text-sm text-green-400">
                          {formatCurrency(row.revenue)}
                        </td>
                      )}
                      {showPriceMetrics && (
                        <td className="py-3 px-3 text-sm font-medium">
                          {row.roas != null ? `${row.roas.toFixed(2)}x` : '—'}
                        </td>
                      )}
                      <td className="py-3 px-3 text-sm">{row.campaigns_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </motion.div>

        {/* Top Campaigns Table */}
        <motion.div
          className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-6"
          {...fadeIn}
          transition={{ delay: 0.2 }}
        >
          <h3 className="font-semibold mb-4">Top Campaigns</h3>
          {campaignsLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : topCampaigns.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>No campaign data available</p>
              <p className="text-sm mt-1">
                Campaigns will appear here once platforms are connected and synced
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/10">
                    {['Campaign', 'Platform', 'Status', ...(showPriceMetrics ? ['Spend', 'Revenue', 'ROAS'] : [])].map((h) => (
                      <th
                        key={h}
                        className="text-left py-2 px-3 text-sm font-medium text-muted-foreground"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {topCampaigns.map((c) => (
                    <tr key={c.id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-3 px-3 text-sm font-medium">{c.name}</td>
                      <td className="py-3 px-3">
                        <span
                          className={cn(
                            'px-2 py-0.5 rounded-full text-xs font-medium',
                            platformBadge(c.platform)
                          )}
                        >
                          {c.platform}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={cn(
                            'px-2 py-0.5 rounded-full text-xs font-medium capitalize',
                            c.status === 'active'
                              ? 'bg-green-500/10 text-green-400'
                              : c.status === 'paused'
                                ? 'bg-amber-500/10 text-amber-400'
                                : 'bg-gray-500/10 text-gray-400'
                          )}
                        >
                          {c.status}
                        </span>
                      </td>
                      {showPriceMetrics && (
                        <td className="py-3 px-3 text-sm">{formatCurrency(c.spend)}</td>
                      )}
                      {showPriceMetrics && (
                        <td className="py-3 px-3 text-sm text-green-400">
                          {formatCurrency(c.revenue)}
                        </td>
                      )}
                      {showPriceMetrics && (
                        <td className="py-3 px-3 text-sm font-medium">
                          {c.roas != null ? `${c.roas.toFixed(2)}x` : '—'}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </motion.div>
      </div>
    </>
  );
}
