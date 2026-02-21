import { useMemo } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { cn, getPlatformColor } from '@/lib/utils'
import { useDashboardSimulation } from '@/contexts/DashboardSimulationContext'

interface PlatformBreakdownWidgetProps {
  className?: string
}

export function PlatformBreakdownWidget({ className }: PlatformBreakdownWidgetProps) {
  const { platformSummary } = useDashboardSimulation()

  const chartData = useMemo(() => {
    if (!platformSummary || platformSummary.length === 0) return []

    const totalSpend = platformSummary.reduce((sum, p) => sum + p.spend, 0)
    if (totalSpend === 0) return []

    return platformSummary.map((p) => ({
      name: p.platform.replace(' Ads', ''),
      value: Math.round(p.spend / totalSpend * 100),
      color: getPlatformColor(p.platform.replace(' Ads', '').toLowerCase()),
    }))
  }, [platformSummary])

  if (chartData.length === 0) {
    return (
      <div className={cn('h-full p-4 flex items-center justify-center', className)}>
        <div className="animate-pulse h-32 w-32 bg-muted rounded-full" />
      </div>
    )
  }

  return (
    <div className={cn('h-full p-4', className)}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
            }}
            formatter={(value: number) => [`${value}%`, 'Share']}
          />
          <Legend
            verticalAlign="bottom"
            height={36}
            formatter={(value) => <span className="text-xs text-foreground">{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
