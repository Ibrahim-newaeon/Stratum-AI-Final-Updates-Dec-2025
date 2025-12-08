/**
 * Regional Breakdown Chart
 * Pie/Donut chart showing performance distribution by region
 */

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { chartTheme } from '@/lib/chartTheme'
import { PieChartSkeleton } from '@/components/ui/Skeleton'
import { NoChartDataState } from '@/components/ui/EmptyState'
import { ErrorBoundary, ChartErrorFallback } from '@/components/ui/ErrorBoundary'

interface RegionalData {
  name: string
  value: number
  color?: string
}

interface RegionalBreakdownChartProps {
  data: RegionalData[]
  loading?: boolean
  height?: number
  title?: string
  innerRadius?: number
  outerRadius?: number
  showLabels?: boolean
  onRefresh?: () => void
}

// Custom legend renderer
const CustomLegend = ({ payload }: { payload?: Array<{ value: string; color: string; payload: RegionalData }> }) => {
  if (!payload) return null

  return (
    <ul className="flex flex-wrap justify-center gap-x-4 gap-y-2 mt-4">
      {payload.map((entry, index) => (
        <li key={index} className="flex items-center gap-2 text-sm">
          <span
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-muted-foreground">
            {entry.value}
          </span>
          <span className="font-medium text-foreground">
            {entry.payload.value}%
          </span>
        </li>
      ))}
    </ul>
  )
}

function RegionalBreakdownChartInner({
  data,
  height = 300,
  title = 'Performance by Region',
  innerRadius = 60,
  outerRadius = 100,
}: Omit<RegionalBreakdownChartProps, 'loading' | 'onRefresh' | 'showLabels'>) {
  if (!data || data.length === 0) {
    return <NoChartDataState />
  }

  // Assign colors if not provided
  const chartData = data.map((item, index) => ({
    ...item,
    color: item.color || chartTheme.regionColors[index % chartTheme.regionColors.length],
  }))

  return (
    <div className="rounded-xl border bg-card p-6">
      <h3 className="text-lg font-semibold text-foreground mb-4">{title}</h3>
      <div style={{ height }} role="img" aria-label={`${title} showing regional distribution`}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="45%"
              innerRadius={innerRadius}
              outerRadius={outerRadius}
              paddingAngle={2}
              dataKey="value"
              animationDuration={chartTheme.animation.duration}
              animationBegin={0}
            >
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color}
                  stroke="hsl(var(--card))"
                  strokeWidth={2}
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={chartTheme.tooltip.contentStyle}
              formatter={(value: number) => [`${value}%`, 'Share']}
            />
            <Legend
              content={<CustomLegend />}
              verticalAlign="bottom"
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export function RegionalBreakdownChart({
  data,
  loading,
  onRefresh,
  ...props
}: RegionalBreakdownChartProps) {
  if (loading) {
    return <PieChartSkeleton height={props.height} />
  }

  return (
    <ErrorBoundary
      fallback={<ChartErrorFallback onRetry={onRefresh} height={props.height} />}
    >
      <RegionalBreakdownChartInner data={data} {...props} />
    </ErrorBoundary>
  )
}

export default RegionalBreakdownChart
