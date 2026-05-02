/**
 * Chart — themed wrapper around recharts.
 *
 * Goals:
 * - Strict design tokens for colors / grid / axes (per theme).
 * - First-class loading / empty / error states (no caller branching).
 * - Multi-series defaults: ember (primary) + cyan (info), then accent.
 * - Responsive container (parent sets height).
 *
 * Currently exposes <LineChart> and <AreaChart> wrappers — additional
 * chart kinds can land here without leaking recharts internals to callers.
 */

import { type ReactNode, useMemo } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart as RLineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Area,
  AreaChart as RAreaChart,
} from 'recharts';
import { cn } from '@/lib/utils';

export interface ChartSeries {
  /** Object key in `data` rows. */
  dataKey: string;
  /** Display name in legend / tooltip. */
  name: string;
  /** Override default series color (CSS var or hex). */
  color?: string;
}

export interface ChartProps<T extends object = Record<string, unknown>> {
  data: T[];
  series: ChartSeries[];
  /** Column to use for the X axis. */
  xKey: string;
  /** Format X-axis tick labels. */
  xFormat?: (value: unknown) => string;
  /** Format Y-axis tick labels. */
  yFormat?: (value: number) => string;
  /** Format tooltip values. */
  tooltipFormat?: (value: number, series: ChartSeries) => string;
  loading?: boolean;
  /** Text shown when data is empty. Default "No data yet." */
  emptyMessage?: string;
  error?: string;
  /** Hide the legend (e.g. single-series sparklines). */
  hideLegend?: boolean;
  /** Hide axes for sparkline-style charts. */
  hideAxes?: boolean;
  className?: string;
  /** Container height. Defaults to 280. */
  height?: number;
}

const DEFAULT_PALETTE = [
  'hsl(var(--primary))',
  'hsl(var(--info))',
  'hsl(var(--accent))',
  'hsl(var(--secondary))',
  'hsl(var(--success))',
];

const tooltipStyle = {
  background: 'hsl(var(--card))',
  border: '1px solid hsl(var(--border))',
  borderRadius: '12px',
  padding: '8px 12px',
  fontSize: '12px',
  color: 'hsl(var(--foreground))',
  fontFamily: 'Geist Mono, monospace',
  letterSpacing: '0.02em',
  boxShadow: '0 8px 24px rgba(0, 0, 0, 0.32)',
};

const axisTickStyle = {
  fill: 'hsl(var(--muted-foreground))',
  fontSize: 10.5,
  fontFamily: 'Geist Mono, monospace',
  letterSpacing: '0.06em',
};

interface ChartShellProps {
  loading?: boolean;
  error?: string;
  empty?: boolean;
  emptyMessage: string;
  height: number;
  className?: string;
  children: ReactNode;
}

function ChartShell({
  loading,
  error,
  empty,
  emptyMessage,
  height,
  className,
  children,
}: ChartShellProps) {
  if (loading) {
    return (
      <div
        role="status"
        aria-label="Loading chart"
        className={cn(
          'w-full rounded-xl bg-muted/40 animate-pulse',
          className
        )}
        style={{ height }}
      />
    );
  }
  if (error) {
    return (
      <div
        role="alert"
        className={cn(
          'w-full rounded-xl border border-danger/30 bg-danger/5',
          'flex items-center justify-center text-meta text-danger',
          className
        )}
        style={{ height }}
      >
        {error}
      </div>
    );
  }
  if (empty) {
    return (
      <div
        className={cn(
          'w-full rounded-xl border border-dashed border-border',
          'flex items-center justify-center text-meta text-muted-foreground uppercase tracking-[0.06em]',
          className
        )}
        style={{ height }}
      >
        {emptyMessage}
      </div>
    );
  }
  return (
    <div className={cn('w-full', className)} style={{ height }}>
      {children}
    </div>
  );
}

function resolveColor(series: ChartSeries, idx: number): string {
  return series.color ?? DEFAULT_PALETTE[idx % DEFAULT_PALETTE.length];
}

export function LineChart<T extends object>({
  data,
  series,
  xKey,
  xFormat,
  yFormat,
  tooltipFormat,
  loading,
  emptyMessage = 'No data yet.',
  error,
  hideLegend,
  hideAxes,
  className,
  height = 280,
}: ChartProps<T>) {
  const isEmpty = !loading && !error && (!data || data.length === 0);

  // Memo so recharts doesn't re-render on every parent re-render.
  const lines = useMemo(
    () =>
      series.map((s, idx) => {
        const color = resolveColor(s, idx);
        return (
          <Line
            key={s.dataKey}
            type="monotone"
            dataKey={s.dataKey}
            name={s.name}
            stroke={color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0, fill: color }}
            isAnimationActive={false}
          />
        );
      }),
    [series]
  );

  return (
    <ChartShell
      loading={loading}
      error={error}
      empty={isEmpty}
      emptyMessage={emptyMessage}
      height={height}
      className={className}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RLineChart data={data} margin={{ top: 12, right: 12, bottom: 4, left: 4 }}>
          {!hideAxes && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--border))"
              vertical={false}
            />
          )}
          {!hideAxes && (
            <XAxis
              dataKey={xKey}
              tick={axisTickStyle}
              tickFormatter={xFormat as (v: unknown) => string}
              axisLine={false}
              tickLine={false}
              dy={6}
            />
          )}
          {!hideAxes && (
            <YAxis
              tick={axisTickStyle}
              tickFormatter={yFormat}
              axisLine={false}
              tickLine={false}
              dx={-4}
            />
          )}
          <Tooltip
            contentStyle={tooltipStyle}
            cursor={{ stroke: 'hsl(var(--border))', strokeWidth: 1 }}
            formatter={(value, _name, item) => {
              const dataKey = (item as { dataKey?: string } | undefined)?.dataKey;
              const s = series.find((x) => x.dataKey === dataKey);
              if (!s) return [String(value), ''];
              const numeric = typeof value === 'number' ? value : Number(value);
              const formatted = tooltipFormat
                ? tooltipFormat(numeric, s)
                : String(value);
              return [formatted, s.name];
            }}
          />
          {!hideLegend && (
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{
                fontSize: 11.5,
                fontFamily: 'Geist Mono, monospace',
                color: 'hsl(var(--muted-foreground))',
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
              }}
            />
          )}
          {lines}
        </RLineChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}

export function AreaChart<T extends object>({
  data,
  series,
  xKey,
  xFormat,
  yFormat,
  tooltipFormat,
  loading,
  emptyMessage = 'No data yet.',
  error,
  hideLegend,
  hideAxes,
  className,
  height = 280,
}: ChartProps<T>) {
  const isEmpty = !loading && !error && (!data || data.length === 0);

  const areas = useMemo(
    () =>
      series.map((s, idx) => {
        const color = resolveColor(s, idx);
        const gradientId = `chart-area-grad-${s.dataKey}-${idx}`;
        return (
          <Area
            key={s.dataKey}
            type="monotone"
            dataKey={s.dataKey}
            name={s.name}
            stroke={color}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            isAnimationActive={false}
          />
        );
      }),
    [series]
  );

  return (
    <ChartShell
      loading={loading}
      error={error}
      empty={isEmpty}
      emptyMessage={emptyMessage}
      height={height}
      className={className}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RAreaChart data={data} margin={{ top: 12, right: 12, bottom: 4, left: 4 }}>
          <defs>
            {series.map((s, idx) => {
              const color = resolveColor(s, idx);
              const gradientId = `chart-area-grad-${s.dataKey}-${idx}`;
              return (
                <linearGradient key={gradientId} id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              );
            })}
          </defs>
          {!hideAxes && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--border))"
              vertical={false}
            />
          )}
          {!hideAxes && (
            <XAxis
              dataKey={xKey}
              tick={axisTickStyle}
              tickFormatter={xFormat as (v: unknown) => string}
              axisLine={false}
              tickLine={false}
              dy={6}
            />
          )}
          {!hideAxes && (
            <YAxis
              tick={axisTickStyle}
              tickFormatter={yFormat}
              axisLine={false}
              tickLine={false}
              dx={-4}
            />
          )}
          <Tooltip
            contentStyle={tooltipStyle}
            cursor={{ stroke: 'hsl(var(--border))', strokeWidth: 1 }}
            formatter={(value, _name, item) => {
              const dataKey = (item as { dataKey?: string } | undefined)?.dataKey;
              const s = series.find((x) => x.dataKey === dataKey);
              if (!s) return [String(value), ''];
              const numeric = typeof value === 'number' ? value : Number(value);
              const formatted = tooltipFormat
                ? tooltipFormat(numeric, s)
                : String(value);
              return [formatted, s.name];
            }}
          />
          {!hideLegend && (
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{
                fontSize: 11.5,
                fontFamily: 'Geist Mono, monospace',
                color: 'hsl(var(--muted-foreground))',
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
              }}
            />
          )}
          {areas}
        </RAreaChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
