import { useMemo } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { cn } from '@/lib/utils'
import { useDashboardSimulation } from '@/contexts/DashboardSimulationContext'

interface ChartWidgetProps {
  type: 'revenue' | 'spend' | 'performance'
  className?: string
}

// Analytics Design System chart styling
const chartStyle = {
  grid: { stroke: 'rgba(255,255,255,0.08)', strokeDasharray: '3 3' },
  axis: { fill: '#A7AABB', fontSize: 12 },
  tooltip: {
    backgroundColor: '#0A0A0A',
    border: '1px solid rgba(255,255,255,0.10)',
    borderRadius: '12px',
  },
}

export function ChartWidget({ type, className }: ChartWidgetProps) {
  const { dailyTrend } = useDashboardSimulation()

  const chartData = useMemo(() => {
    if (!dailyTrend || dailyTrend.length === 0) return []

    if (type === 'performance') {
      return dailyTrend.map((d) => ({
        name: d.date,
        clicks: d.clicks,
        conversions: d.conversions,
      }))
    }

    return dailyTrend.map((d) => ({
      name: d.date,
      value: type === 'revenue' ? d.revenue : d.spend,
    }))
  }, [dailyTrend, type])

  if (chartData.length === 0) {
    return (
      <div className={cn('h-full p-4 flex items-center justify-center', className)}>
        <div className="animate-pulse h-32 w-full bg-muted rounded" />
      </div>
    )
  }

  if (type === 'performance') {
    return (
      <div className={cn('h-full p-4 motion-chart-sweep', className)}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid {...chartStyle.grid} />
            <XAxis dataKey="name" tick={chartStyle.axis} tickLine={false} axisLine={false} />
            <YAxis tick={chartStyle.axis} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={chartStyle.tooltip} />
            <Bar dataKey="clicks" fill="#a855f7" radius={[4, 4, 0, 0]} />
            <Bar dataKey="conversions" fill="#22C55E" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  const color = type === 'revenue' ? '#22C55E' : '#a855f7'

  return (
    <div className={cn('h-full p-4 motion-chart-sweep', className)}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
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
