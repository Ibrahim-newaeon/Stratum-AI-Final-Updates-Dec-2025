/**
 * Daily Performance Trend Chart
 * Area chart showing revenue and spend trends over time
 */

import {
  Area,
  AreaChart,
  Brush,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { chartFormatters, chartTheme } from '@/lib/chartTheme';
import { DailyPerformance } from '@/types/dashboard';
import { AreaChartSkeleton } from '@/components/ui/Skeleton';
import { NoChartDataState } from '@/components/ui/EmptyState';
import { ChartErrorFallback, ErrorBoundary } from '@/components/ui/ErrorBoundary';

interface DailyTrendChartProps {
  data: DailyPerformance[];
  loading?: boolean;
  height?: number;
  title?: string;
  showBrush?: boolean;
  metrics?: ('revenue' | 'spend' | 'conversions')[];
  onRefresh?: () => void;
}

function DailyTrendChartInner({
  data,
  height = 300,
  title = 'Daily Performance Trend',
  showBrush = false,
  metrics = ['revenue', 'spend'],
}: Omit<DailyTrendChartProps, 'loading' | 'onRefresh'>) {
  if (!data || data.length === 0) {
    return <NoChartDataState />;
  }

  const metricConfig = {
    revenue: {
      color: chartTheme.colors.revenue,
      gradientId: 'colorRevenue',
      name: 'Revenue',
    },
    spend: {
      color: chartTheme.colors.spend,
      gradientId: 'colorSpend',
      name: 'Spend',
    },
    conversions: {
      color: chartTheme.colors.conversions,
      gradientId: 'colorConversions',
      name: 'Conversions',
    },
  };

  return (
    <div className="rounded-xl border bg-card p-6">
      <h3 className="text-lg font-semibold text-foreground mb-4">{title}</h3>
      <div style={{ height }} role="img" aria-label={`${title} showing daily trends`}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 10, right: 10, left: 0, bottom: showBrush ? 30 : 0 }}
          >
            <defs>
              {metrics.map((metric) => (
                <linearGradient
                  key={metricConfig[metric].gradientId}
                  id={metricConfig[metric].gradientId}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="5%" stopColor={metricConfig[metric].color} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={metricConfig[metric].color} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid
              strokeDasharray={chartTheme.grid.strokeDasharray}
              className="stroke-muted"
              opacity={chartTheme.grid.opacity}
            />
            <XAxis
              dataKey="date"
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
              formatter={(value: number, name: string) => {
                if (name === 'Conversions') return [value.toLocaleString(), name];
                return [chartFormatters.currency(value), name];
              }}
              cursor={{ stroke: 'hsl(var(--primary))', strokeWidth: 1, strokeDasharray: '4 4' }}
            />
            <Legend wrapperStyle={chartTheme.legend.wrapperStyle} iconType="circle" />
            {metrics.map((metric) => (
              <Area
                key={metric}
                type="monotone"
                dataKey={metric}
                name={metricConfig[metric].name}
                stroke={metricConfig[metric].color}
                strokeWidth={2}
                fillOpacity={1}
                fill={`url(#${metricConfig[metric].gradientId})`}
                animationDuration={chartTheme.animation.duration}
              />
            ))}
            {showBrush && (
              <Brush
                dataKey="date"
                height={20}
                stroke="hsl(var(--primary))"
                fill="hsl(var(--muted))"
                tickFormatter={(value) => value}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function DailyTrendChart({ data, loading, onRefresh, ...props }: DailyTrendChartProps) {
  if (loading) {
    return <AreaChartSkeleton height={props.height} />;
  }

  return (
    <ErrorBoundary fallback={<ChartErrorFallback onRetry={onRefresh} height={props.height} />}>
      <DailyTrendChartInner data={data} {...props} />
    </ErrorBoundary>
  );
}

export default DailyTrendChart;
