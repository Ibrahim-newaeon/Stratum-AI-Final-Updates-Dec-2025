import { TrendingUp, TrendingDown, DollarSign, ShoppingCart, Eye, MousePointer, Target, Percent } from 'lucide-react'
import { cn, formatCurrency, formatCompactNumber, formatPercent } from '@/lib/utils'

interface KPIWidgetProps {
  type: 'spend' | 'revenue' | 'roas' | 'conversions' | 'ctr' | 'impressions'
  className?: string
}

const mockData = {
  spend: { value: 45678, change: 12.5, trend: 'up' as const },
  revenue: { value: 156789, change: 18.2, trend: 'up' as const },
  roas: { value: 3.43, change: 5.1, trend: 'up' as const },
  conversions: { value: 2847, change: -3.2, trend: 'down' as const },
  ctr: { value: 2.84, change: 0.3, trend: 'up' as const },
  impressions: { value: 12500000, change: 8.7, trend: 'up' as const },
}

const config = {
  spend: { label: 'Total Spend', icon: DollarSign, format: (v: number) => formatCurrency(v), color: 'text-blue-500' },
  revenue: { label: 'Revenue', icon: DollarSign, format: (v: number) => formatCurrency(v), color: 'text-green-500' },
  roas: { label: 'ROAS', icon: Target, format: (v: number) => `${v.toFixed(2)}x`, color: 'text-purple-500' },
  conversions: { label: 'Conversions', icon: ShoppingCart, format: (v: number) => formatCompactNumber(v), color: 'text-amber-500' },
  ctr: { label: 'CTR', icon: Percent, format: (v: number) => formatPercent(v), color: 'text-cyan-500' },
  impressions: { label: 'Impressions', icon: Eye, format: (v: number) => formatCompactNumber(v), color: 'text-pink-500' },
}

export function KPIWidget({ type, className }: KPIWidgetProps) {
  const data = mockData[type]
  const cfg = config[type]
  const Icon = cfg.icon

  return (
    <div className={cn('h-full p-4 flex flex-col justify-between', className)}>
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{cfg.label}</span>
        <Icon className={cn('w-5 h-5', cfg.color)} />
      </div>

      <div className="mt-2">
        <p className="text-2xl font-bold tabular-nums">{cfg.format(data.value)}</p>
        <div className="flex items-center gap-1 mt-1">
          {data.trend === 'up' ? (
            <TrendingUp className="w-4 h-4 text-green-500" />
          ) : (
            <TrendingDown className="w-4 h-4 text-red-500" />
          )}
          <span className={cn('text-sm font-medium', data.trend === 'up' ? 'text-green-500' : 'text-red-500')}>
            {data.change > 0 ? '+' : ''}{data.change}%
          </span>
          <span className="text-xs text-muted-foreground">vs last period</span>
        </div>
      </div>
    </div>
  )
}
