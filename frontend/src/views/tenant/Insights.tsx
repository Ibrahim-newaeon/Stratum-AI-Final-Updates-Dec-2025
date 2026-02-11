/**
 * Tenant Insights Dashboard
 *
 * Aggregated performance view with KPI cards, revenue vs spend chart,
 * platform performance table, and top campaigns table.
 */

import { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { motion } from 'framer-motion';
import {
  CurrencyDollarIcon,
  BanknotesIcon,
  ArrowTrendingUpIcon,
  ShoppingCartIcon,
} from '@heroicons/react/24/outline';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { cn } from '@/lib/utils';

const fadeIn = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.3 },
};

type DateRange = '7d' | '30d' | '90d';
type ChartTab = 'revenue' | 'spend' | 'roas';

// Mock data matching superads insights.html
const kpiData = {
  revenue: { value: 124500, trend: 12.4 },
  adSpend: { value: 34200, trend: -3.2 },
  roas: { value: 3.64, trend: 8.1 },
  conversions: { value: 1847, trend: 15.6 },
};

const chartData = Array.from({ length: 30 }, (_, i) => {
  const date = new Date(Date.now() - (29 - i) * 86400000);
  return {
    date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    revenue: 3000 + Math.random() * 3000 + i * 50,
    spend: 800 + Math.random() * 600 + i * 15,
    roas: 2.5 + Math.random() * 2,
  };
});

const platformPerformance = [
  { platform: 'Google Ads', spend: 14200, revenue: 52000, roas: 3.66, conversions: 780, cpa: 18.21, ctr: 3.2 },
  { platform: 'Meta Ads', spend: 12500, revenue: 45000, roas: 3.6, conversions: 620, cpa: 20.16, ctr: 1.8 },
  { platform: 'TikTok Ads', spend: 5200, revenue: 18500, roas: 3.56, conversions: 312, cpa: 16.67, ctr: 2.4 },
  { platform: 'Snapchat Ads', spend: 2300, revenue: 9000, roas: 3.91, conversions: 135, cpa: 17.04, ctr: 1.5 },
];

const topCampaigns = [
  { name: 'Holiday Sale 2024', platform: 'Meta', status: 'active', spend: 8500, revenue: 32000, roas: 3.76 },
  { name: 'Brand Search', platform: 'Google', status: 'active', spend: 6200, revenue: 28000, roas: 4.52 },
  { name: 'Summer Retargeting', platform: 'Meta', status: 'active', spend: 4800, revenue: 15500, roas: 3.23 },
  { name: 'TikTok Awareness', platform: 'TikTok', status: 'paused', spend: 3200, revenue: 11000, roas: 3.44 },
  { name: 'Snap Promo Q4', platform: 'Snapchat', status: 'active', spend: 2100, revenue: 8200, roas: 3.9 },
];

export default function TenantInsights() {
  const [dateRange, setDateRange] = useState<DateRange>('30d');
  const [chartTab, setChartTab] = useState<ChartTab>('revenue');

  const formatCurrency = (value: number): string =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value);

  const kpis = [
    { label: 'Revenue', value: formatCurrency(kpiData.revenue.value), trend: kpiData.revenue.trend, icon: CurrencyDollarIcon, color: 'text-green-500' },
    { label: 'Ad Spend', value: formatCurrency(kpiData.adSpend.value), trend: kpiData.adSpend.trend, icon: BanknotesIcon, color: 'text-blue-500' },
    { label: 'ROAS', value: `${kpiData.roas.value}x`, trend: kpiData.roas.trend, icon: ArrowTrendingUpIcon, color: 'text-purple-500' },
    { label: 'Conversions', value: kpiData.conversions.value.toLocaleString(), trend: kpiData.conversions.trend, icon: ShoppingCartIcon, color: 'text-amber-500' },
  ];

  const platformBadge = (platform: string) => {
    const colors: Record<string, string> = {
      Google: 'bg-blue-500/10 text-blue-400',
      Meta: 'bg-indigo-500/10 text-indigo-400',
      TikTok: 'bg-gray-500/10 text-gray-300',
      Snapchat: 'bg-yellow-500/10 text-yellow-400',
    };
    return colors[platform] || 'bg-gray-500/10 text-gray-400';
  };

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
          {kpis.map((kpi) => (
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
                  {kpi.trend >= 0 ? '+' : ''}{kpi.trend}%
                </span>
              </div>
              <p className="text-2xl font-bold">{kpi.value}</p>
              <p className="text-xs text-muted-foreground mt-1">{kpi.label}</p>
            </div>
          ))}
        </motion.div>

        {/* Revenue vs Spend Chart */}
        <motion.div
          className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-6"
          {...fadeIn}
          transition={{ delay: 0.15 }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Performance Trend</h3>
            <div className="flex items-center gap-1 p-1 rounded-lg bg-white/5">
              {(['revenue', 'spend', 'roas'] as ChartTab[]).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setChartTab(tab)}
                  className={cn(
                    'px-3 py-1 text-xs rounded-md transition-colors capitalize',
                    chartTab === tab
                      ? 'bg-primary/20 text-primary'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: 'rgba(245,245,247,0.4)' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: 'rgba(245,245,247,0.4)' }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => chartTab === 'roas' ? `${v.toFixed(1)}x` : `$${(v/1000).toFixed(0)}k`}
              />
              <Tooltip
                contentStyle={{
                  background: 'rgba(11, 18, 21, 0.95)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '8px',
                  fontSize: 12,
                  color: 'rgba(245,245,247,0.92)',
                }}
              />
              {chartTab === 'revenue' && (
                <Line type="monotone" dataKey="revenue" stroke="#34c759" strokeWidth={2} dot={false} />
              )}
              {chartTab === 'spend' && (
                <Line type="monotone" dataKey="spend" stroke="#3b82f6" strokeWidth={2} dot={false} />
              )}
              {chartTab === 'roas' && (
                <Line type="monotone" dataKey="roas" stroke="#a78bfa" strokeWidth={2} dot={false} />
              )}
            </LineChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Platform Performance Table */}
        <motion.div
          className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-6"
          {...fadeIn}
          transition={{ delay: 0.2 }}
        >
          <h3 className="font-semibold mb-4">Platform Performance</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  {['Platform', 'Spend', 'Revenue', 'ROAS', 'Conversions', 'CPA', 'CTR'].map((h) => (
                    <th key={h} className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {platformPerformance.map((row) => (
                  <tr key={row.platform} className="border-b border-white/5 hover:bg-white/5">
                    <td className="py-3 px-3 text-sm font-medium">{row.platform}</td>
                    <td className="py-3 px-3 text-sm">{formatCurrency(row.spend)}</td>
                    <td className="py-3 px-3 text-sm text-green-400">{formatCurrency(row.revenue)}</td>
                    <td className="py-3 px-3 text-sm font-medium">{row.roas}x</td>
                    <td className="py-3 px-3 text-sm">{row.conversions.toLocaleString()}</td>
                    <td className="py-3 px-3 text-sm">${row.cpa.toFixed(2)}</td>
                    <td className="py-3 px-3 text-sm">{row.ctr}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* Top Campaigns Table */}
        <motion.div
          className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-6"
          {...fadeIn}
          transition={{ delay: 0.25 }}
        >
          <h3 className="font-semibold mb-4">Top Campaigns</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  {['Campaign', 'Platform', 'Status', 'Spend', 'Revenue', 'ROAS'].map((h) => (
                    <th key={h} className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {topCampaigns.map((c) => (
                  <tr key={c.name} className="border-b border-white/5 hover:bg-white/5">
                    <td className="py-3 px-3 text-sm font-medium">{c.name}</td>
                    <td className="py-3 px-3">
                      <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', platformBadge(c.platform))}>
                        {c.platform}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span className={cn(
                        'px-2 py-0.5 rounded-full text-xs font-medium capitalize',
                        c.status === 'active' ? 'bg-green-500/10 text-green-400' : 'bg-gray-500/10 text-gray-400'
                      )}>
                        {c.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-sm">{formatCurrency(c.spend)}</td>
                    <td className="py-3 px-3 text-sm text-green-400">{formatCurrency(c.revenue)}</td>
                    <td className="py-3 px-3 text-sm font-medium">{c.roas}x</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </>
  );
}
