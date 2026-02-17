/**
 * KG Revenue Attribution - Knowledge Graph revenue attribution view
 *
 * Shows attributed revenue across channels with model comparison
 * and channel breakdown visualization.
 */

import { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { motion } from 'framer-motion';
import {
  CurrencyDollarIcon,
  MapPinIcon,
  ArrowsRightLeftIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from 'recharts';
import { cn } from '@/lib/utils';
import { useKGRevenueAttribution, useKGChannelBreakdown } from '@/api/knowledgeGraph';

const fadeIn = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.3 },
};

const periods = [
  { value: '7d', label: '7 Days' },
  { value: '30d', label: '30 Days' },
  { value: '90d', label: '90 Days' },
];

export default function KGRevenueAttribution() {
  const [period, setPeriod] = useState('30d');

  const { data: revenueData, isLoading: revenueLoading } = useKGRevenueAttribution(period);
  const { data: channelData, isLoading: channelsLoading } = useKGChannelBreakdown(period);

  const isLoading = revenueLoading || channelsLoading;

  const formatCurrency = (value: number): string =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);

  const formatCompact = (value: number): string => {
    if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
    return value.toString();
  };

  const metricCards = [
    {
      label: 'Attributed Revenue',
      value: formatCurrency(revenueData?.attributedRevenue ?? 0),
      icon: CurrencyDollarIcon,
      color: 'text-green-500',
    },
    {
      label: 'Touchpoints Tracked',
      value: formatCompact(revenueData?.touchpointsTracked ?? 0),
      icon: MapPinIcon,
      color: 'text-blue-500',
    },
    {
      label: 'Avg Path Length',
      value: `${revenueData?.avgPathLength ?? 0} steps`,
      icon: ArrowsRightLeftIcon,
      color: 'text-purple-500',
    },
    {
      label: 'Conversion Window',
      value: revenueData?.conversionWindow ?? '-',
      icon: ClockIcon,
      color: 'text-amber-500',
    },
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <>
      <Helmet>
        <title>Revenue Attribution - Knowledge Graph | Stratum AI</title>
      </Helmet>

      <div className="space-y-6 max-w-7xl mx-auto">
        {/* Header + Period Filter */}
        <motion.div className="flex items-center justify-between" {...fadeIn}>
          <div>
            <h1 className="text-2xl font-bold">Revenue Attribution</h1>
            <p className="text-muted-foreground">
              Multi-touch attribution across all channels
            </p>
          </div>
          <div className="flex items-center gap-1 p-1 rounded-lg bg-white/5 border border-white/10">
            {periods.map((p) => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={cn(
                  'px-3 py-1.5 text-sm rounded-md transition-colors',
                  period === p.value
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {p.label}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Metric Cards */}
        <motion.div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
          {...fadeIn}
          transition={{ delay: 0.1 }}
        >
          {metricCards.map((card) => (
            <div
              key={card.label}
              className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-4"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-white/5">
                  <card.icon className={cn('h-5 w-5', card.color)} />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{card.label}</p>
                  <p className="text-lg font-bold">{card.value}</p>
                </div>
              </div>
            </div>
          ))}
        </motion.div>

        {/* Channel Breakdown + Model Comparison */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Channel Breakdown Chart */}
          <motion.div
            className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-6"
            {...fadeIn}
            transition={{ delay: 0.15 }}
          >
            <h3 className="font-semibold mb-4">Channel Breakdown</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={channelData || []}
                layout="vertical"
                margin={{ top: 0, right: 20, bottom: 0, left: 80 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(255,255,255,0.05)"
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11, fill: 'rgba(245,245,247,0.4)' }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                />
                <YAxis
                  type="category"
                  dataKey="channel"
                  tick={{ fontSize: 12, fill: 'rgba(245,245,247,0.7)' }}
                  axisLine={false}
                  tickLine={false}
                  width={80}
                />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(11, 18, 21, 0.95)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    fontSize: 12,
                    color: 'rgba(245,245,247,0.92)',
                  }}
                  formatter={(value) => [formatCurrency(Number(value)), 'Revenue']}
                />
                <Bar dataKey="revenue" radius={[0, 4, 4, 0]}>
                  {(channelData || []).map((entry, index) => (
                    <Cell key={index} fill={entry.color} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>

          {/* Model Comparison Table */}
          <motion.div
            className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-6"
            {...fadeIn}
            transition={{ delay: 0.2 }}
          >
            <h3 className="font-semibold mb-4">Attribution Model Comparison</h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">
                      Channel
                    </th>
                    <th className="text-right py-2 px-3 text-sm font-medium text-muted-foreground">
                      First Touch
                    </th>
                    <th className="text-right py-2 px-3 text-sm font-medium text-muted-foreground">
                      Last Touch
                    </th>
                    <th className="text-right py-2 px-3 text-sm font-medium text-muted-foreground">
                      Linear
                    </th>
                    <th className="text-right py-2 px-3 text-sm font-medium text-primary">
                      Data-Driven
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {(revenueData?.modelComparison || []).map((row) => (
                    <tr key={row.channel} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-3 px-3 text-sm font-medium">{row.channel}</td>
                      <td className="py-3 px-3 text-sm text-right text-muted-foreground">
                        {row.firstTouch}%
                      </td>
                      <td className="py-3 px-3 text-sm text-right text-muted-foreground">
                        {row.lastTouch}%
                      </td>
                      <td className="py-3 px-3 text-sm text-right text-muted-foreground">
                        {row.linear}%
                      </td>
                      <td className="py-3 px-3 text-sm text-right font-medium text-primary">
                        {row.dataDriven}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        </div>
      </div>
    </>
  );
}
