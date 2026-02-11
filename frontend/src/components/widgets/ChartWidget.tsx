import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { cn } from '@/lib/utils';

interface ChartWidgetProps {
  type: 'revenue' | 'spend' | 'performance';
  className?: string;
}

const mockRevenueData = [
  { name: 'Mon', value: 24000 },
  { name: 'Tue', value: 28000 },
  { name: 'Wed', value: 25000 },
  { name: 'Thu', value: 32000 },
  { name: 'Fri', value: 35000 },
  { name: 'Sat', value: 29000 },
  { name: 'Sun', value: 31000 },
];

const mockSpendData = [
  { name: 'Mon', value: 6500 },
  { name: 'Tue', value: 7200 },
  { name: 'Wed', value: 6800 },
  { name: 'Thu', value: 8100 },
  { name: 'Fri', value: 8500 },
  { name: 'Sat', value: 7000 },
  { name: 'Sun', value: 7800 },
];

const mockPerformanceData = [
  { name: 'Mon', clicks: 3400, conversions: 240 },
  { name: 'Tue', clicks: 3800, conversions: 280 },
  { name: 'Wed', clicks: 3200, conversions: 220 },
  { name: 'Thu', clicks: 4100, conversions: 310 },
  { name: 'Fri', clicks: 4500, conversions: 350 },
  { name: 'Sat', clicks: 3700, conversions: 260 },
  { name: 'Sun', clicks: 4000, conversions: 290 },
];

// Analytics Design System chart styling
const chartStyle = {
  grid: { stroke: 'rgba(255,255,255,0.08)', strokeDasharray: '3 3' },
  axis: { fill: '#A7AABB', fontSize: 12 },
  tooltip: {
    backgroundColor: '#0A0A0A',
    border: '1px solid rgba(255,255,255,0.10)',
    borderRadius: '12px',
  },
};

export function ChartWidget({ type, className }: ChartWidgetProps) {
  if (type === 'performance') {
    return (
      <div className={cn('h-full p-4 motion-chart-sweep', className)}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={mockPerformanceData}>
            <CartesianGrid {...chartStyle.grid} />
            <XAxis dataKey="name" tick={chartStyle.axis} tickLine={false} axisLine={false} />
            <YAxis tick={chartStyle.axis} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={chartStyle.tooltip} />
            <Bar dataKey="clicks" fill="#a855f7" radius={[4, 4, 0, 0]} />
            <Bar dataKey="conversions" fill="#22C55E" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  const data = type === 'revenue' ? mockRevenueData : mockSpendData;
  const color = type === 'revenue' ? '#22C55E' : '#a855f7';

  return (
    <div className={cn('h-full p-4 motion-chart-sweep', className)}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id={`gradient-${type}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid {...chartStyle.grid} />
          <XAxis dataKey="name" tick={chartStyle.axis} tickLine={false} axisLine={false} />
          <YAxis tick={chartStyle.axis} tickLine={false} axisLine={false} />
          <Tooltip
            contentStyle={chartStyle.tooltip}
            formatter={((value: number) => [
              `$${value.toLocaleString()}`,
              type === 'revenue' ? 'Revenue' : 'Spend',
            ]) as any}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            fill={`url(#gradient-${type})`}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
