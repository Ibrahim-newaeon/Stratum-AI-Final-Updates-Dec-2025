/**
 * ActivityVolumeChart - Bar/Area chart for activity volume over time
 *
 * Uses Recharts BarChart with gradient fill.
 * Used in Tenant Audit Log for daily activity visualization.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';

interface ActivityVolumeChartProps {
  data: { date: string; count: number }[];
  height?: number;
  color?: string;
}

export function ActivityVolumeChart({
  data,
  height = 200,
  color = 'hsl(var(--accent))',
}: ActivityVolumeChartProps) {
  const formatDate = (date: string) => {
    const d = new Date(date);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
        <defs>
          <linearGradient id="activityGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.8} />
            <stop offset="100%" stopColor={color} stopOpacity={0.3} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--foreground) / 0.05)" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
            fontSize: 12,
            color: 'hsl(var(--foreground))',
          }}
          labelFormatter={(label) => formatDate(String(label))}
          formatter={(value) => [String(value), 'Events']}
        />
        <Bar dataKey="count" fill="url(#activityGradient)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default ActivityVolumeChart;
