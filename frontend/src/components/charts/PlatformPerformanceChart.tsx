/**
 * Platform Performance Comparison Chart
 * Bar chart comparing spend and revenue across platforms
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { chartTheme, chartFormatters } from '@/lib/chartTheme'
import { PlatformSummary } from '@/types/dashboard'
import { ChartSkeleton } from '@/components/ui/Skeleton'
import { NoChartDataState } from '@/components/ui/EmptyState'
import { ErrorBoundary, ChartErrorFallback } from '@/components/ui/ErrorBoundary'
import { SmartTooltip } from '@/components/guide/SmartTooltip'
import { InfoIcon } from '@/components/ui/InfoIcon'

interface PlatformPerformanceChartProps {
  data: PlatformSummary[]
  loading?: boolean
  height?: number
  title?: string
  onRefresh?: () => void
}

function PlatformPerformanceChartInner({
  data,
  height = 300,
  title = 'Platform Performance Comparison',
}: Omit<PlatformPerformanceChartProps, 'loading' | 'onRefresh'>) {
  if (!data || data.length === 0) {
    return <NoChartDataState />
  }

  return (
    <div className="rounded-xl border bg-card p-6">
      <div className="flex items-center gap-2 mb-4">
        <h3 className="text-lg font-semibold text-foreground">{title}</h3>
        <SmartTooltip
          content="Compare spend vs revenue across advertising platforms. Helps identify which platforms deliver the best value."
          position="right"
          trigger="click"
        >
          <InfoIcon size={14} aria-label="Platform performance information" />
        </SmartTooltip>
      </div>
      <div style={{ height }} role="img" aria-label={`${title} showing spend and revenue comparison`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={chartTheme.colors.spend} stopOpacity={1} />
                <stop offset="100%" stopColor={chartTheme.colors.spend} stopOpacity={0.8} />
              </linearGradient>
              <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={chartTheme.colors.revenue} stopOpacity={1} />
                <stop offset="100%" stopColor={chartTheme.colors.revenue} stopOpacity={0.8} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray={chartTheme.grid.strokeDasharray}
              className="stroke-muted"
              opacity={chartTheme.grid.opacity}
            />
            <XAxis
              dataKey="platform"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              className="text-muted-foreground"
            />
            <YAxis
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={chartFormatters.compact}
              className="text-muted-foreground"
            />
            <Tooltip
              contentStyle={chartTheme.tooltip.contentStyle}
              formatter={(value: number, name: string) => [
                name === 'spend' || name === 'revenue'
                  ? chartFormatters.currency(value)
                  : value.toLocaleString(),
                name.charAt(0).toUpperCase() + name.slice(1),
              ]}
              cursor={{ fill: 'hsl(var(--primary) / 0.05)' }}
            />
            <Legend
              wrapperStyle={chartTheme.legend.wrapperStyle}
              iconType="circle"
            />
            <Bar
              dataKey="spend"
              name="Spend"
              fill="url(#spendGradient)"
              radius={[4, 4, 0, 0]}
              animationDuration={chartTheme.animation.duration}
            />
            <Bar
              dataKey="revenue"
              name="Revenue"
              fill="url(#revenueGradient)"
              radius={[4, 4, 0, 0]}
              animationDuration={chartTheme.animation.duration}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export function PlatformPerformanceChart({
  data,
  loading,
  onRefresh,
  ...props
}: PlatformPerformanceChartProps) {
  if (loading) {
    return <ChartSkeleton height={props.height} />
  }

  return (
    <ErrorBoundary
      fallback={<ChartErrorFallback onRetry={onRefresh} height={props.height} />}
    >
      <PlatformPerformanceChartInner data={data} {...props} />
    </ErrorBoundary>
  )
}

export default PlatformPerformanceChart
