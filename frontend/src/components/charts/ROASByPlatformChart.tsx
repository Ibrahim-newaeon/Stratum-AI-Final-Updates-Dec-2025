/**
 * ROAS by Platform Chart
 * Horizontal bar chart showing ROAS comparison across platforms
 */

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { chartFormatters, chartTheme } from '@/lib/chartTheme';
import { PlatformSummary } from '@/types/dashboard';
import { ChartSkeleton } from '@/components/ui/Skeleton';
import { NoChartDataState } from '@/components/ui/EmptyState';
import { ChartErrorFallback, ErrorBoundary } from '@/components/ui/ErrorBoundary';

interface ROASByPlatformChartProps {
  data: PlatformSummary[];
  loading?: boolean;
  height?: number;
  title?: string;
  targetROAS?: number;
  onRefresh?: () => void;
}

function ROASByPlatformChartInner({
  data,
  height = 300,
  title = 'ROAS by Platform',
  targetROAS = 3.0,
}: Omit<ROASByPlatformChartProps, 'loading' | 'onRefresh'>) {
  if (!data || data.length === 0) {
    return <NoChartDataState />;
  }

  // Sort by ROAS descending for better visualization
  const sortedData = [...data].sort((a, b) => b.roas - a.roas);

  return (
    <div className="rounded-xl border bg-card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-foreground">{title}</h3>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="w-2 h-2 rounded-full bg-amber-500" />
          <span>Target: {targetROAS}x</span>
        </div>
      </div>
      <div style={{ height }} role="img" aria-label={`${title} showing ROAS values`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={sortedData}
            layout="vertical"
            margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
          >
            <defs>
              {sortedData.map((entry, index) => (
                <linearGradient
                  key={`gradient-${index}`}
                  id={`roasGradient-${index}`}
                  x1="0"
                  y1="0"
                  x2="1"
                  y2="0"
                >
                  <stop
                    offset="0%"
                    stopColor={
                      entry.roas >= targetROAS
                        ? chartTheme.colors.success
                        : chartTheme.colors.warning
                    }
                    stopOpacity={0.8}
                  />
                  <stop
                    offset="100%"
                    stopColor={
                      entry.roas >= targetROAS
                        ? chartTheme.colors.success
                        : chartTheme.colors.warning
                    }
                    stopOpacity={1}
                  />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid
              strokeDasharray={chartTheme.grid.strokeDasharray}
              className="stroke-muted"
              opacity={chartTheme.grid.opacity}
              horizontal={false}
            />
            <XAxis
              type="number"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              domain={[0, Math.max(5, Math.ceil(Math.max(...data.map((d) => d.roas)) + 0.5))]}
              tickFormatter={(value) => `${value}x`}
              className="text-muted-foreground"
            />
            <YAxis
              dataKey="platform"
              type="category"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              width={100}
              className="text-muted-foreground"
            />
            <Tooltip
              contentStyle={chartTheme.tooltip.contentStyle}
              formatter={((value: number) => [chartFormatters.roas(value), 'ROAS']) as any}
              cursor={{ fill: 'hsl(var(--primary) / 0.05)' }}
            />
            <ReferenceLine
              x={targetROAS}
              stroke={chartTheme.colors.warning}
              strokeDasharray="4 4"
              strokeWidth={2}
            />
            <Bar
              dataKey="roas"
              name="ROAS"
              radius={[0, 4, 4, 0]}
              animationDuration={chartTheme.animation.duration}
            >
              {sortedData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={
                    entry.roas >= targetROAS ? chartTheme.colors.success : chartTheme.colors.warning
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function ROASByPlatformChart({
  data,
  loading,
  onRefresh,
  ...props
}: ROASByPlatformChartProps) {
  if (loading) {
    return <ChartSkeleton height={props.height} />;
  }

  return (
    <ErrorBoundary fallback={<ChartErrorFallback onRetry={onRefresh} height={props.height} />}>
      <ROASByPlatformChartInner data={data} {...props} />
    </ErrorBoundary>
  );
}

export default ROASByPlatformChart;
