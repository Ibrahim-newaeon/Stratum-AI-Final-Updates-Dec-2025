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
  color = '#00c7be',
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
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          tick={{ fontSize: 11, fill: 'rgba(245,245,247,0.4)' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: 'rgba(245,245,247,0.4)' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: 'rgba(11, 18, 21, 0.95)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '8px',
            fontSize: 12,
            color: 'rgba(245,245,247,0.92)',
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
