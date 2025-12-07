import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { cn } from '@/lib/utils'

interface ChartWidgetProps {
  type: 'revenue' | 'spend' | 'performance'
  className?: string
}

const mockRevenueData = [
  { name: 'Mon', value: 24000 },
  { name: 'Tue', value: 28000 },
  { name: 'Wed', value: 25000 },
  { name: 'Thu', value: 32000 },
  { name: 'Fri', value: 35000 },
  { name: 'Sat', value: 29000 },
  { name: 'Sun', value: 31000 },
]

const mockSpendData = [
  { name: 'Mon', value: 6500 },
  { name: 'Tue', value: 7200 },
  { name: 'Wed', value: 6800 },
  { name: 'Thu', value: 8100 },
  { name: 'Fri', value: 8500 },
  { name: 'Sat', value: 7000 },
  { name: 'Sun', value: 7800 },
]

const mockPerformanceData = [
  { name: 'Mon', clicks: 3400, conversions: 240 },
  { name: 'Tue', clicks: 3800, conversions: 280 },
  { name: 'Wed', clicks: 3200, conversions: 220 },
  { name: 'Thu', clicks: 4100, conversions: 310 },
  { name: 'Fri', clicks: 4500, conversions: 350 },
  { name: 'Sat', clicks: 3700, conversions: 260 },
  { name: 'Sun', clicks: 4000, conversions: 290 },
]

export function ChartWidget({ type, className }: ChartWidgetProps) {
  if (type === 'performance') {
    return (
      <div className={cn('h-full p-4', className)}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={mockPerformanceData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="name" className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
            <YAxis className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
              }}
            />
            <Bar dataKey="clicks" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
            <Bar dataKey="conversions" fill="#22c55e" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  const data = type === 'revenue' ? mockRevenueData : mockSpendData
  const color = type === 'revenue' ? '#22c55e' : 'hsl(var(--primary))'

  return (
    <div className={cn('h-full p-4', className)}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id={`gradient-${type}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis dataKey="name" className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
          <YAxis className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
            }}
            formatter={(value: number) => [`$${value.toLocaleString()}`, type === 'revenue' ? 'Revenue' : 'Spend']}
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
  )
}
