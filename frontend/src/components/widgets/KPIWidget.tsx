import { TrendingUp, TrendingDown, DollarSign, ShoppingCart, Eye, Target, Percent } from 'lucide-react'
import { cn, formatCurrency, formatCompactNumber, formatPercent } from '@/lib/utils'
import { useDashboardSimulation } from '@/contexts/DashboardSimulationContext'

interface KPIWidgetProps {
  type: 'spend' | 'revenue' | 'roas' | 'conversions' | 'ctr' | 'impressions'
  className?: string
}

const config = {
  spend: { label: 'Total Spend', icon: DollarSign, format: (v: number) => formatCurrency(v), color: 'text-blue-500' },
  revenue: { label: 'Revenue', icon: DollarSign, format: (v: number) => formatCurrency(v), color: 'text-green-500' },
  roas: { label: 'ROAS', icon: Target, format: (v: number) => `${v.toFixed(2)}x`, color: 'text-purple-500' },
  conversions: { label: 'Conversions', icon: ShoppingCart, format: (v: number) => formatCompactNumber(v), color: 'text-amber-500' },
  ctr: { label: 'CTR', icon: Percent, format: (v: number) => formatPercent(v), color: 'text-cyan-500' },
  impressions: { label: 'Impressions', icon: Eye, format: (v: number) => formatCompactNumber(v), color: 'text-pink-500' },
}

function getKPIData(type: string, kpis: NonNullable<ReturnType<typeof useDashboardSimulation>['kpis']>): { value: number; change: number } {
  switch (type) {
    case 'spend':
      return { value: kpis.totalSpend, change: kpis.spendDelta ?? 0 }
    case 'revenue':
      return { value: kpis.totalRevenue, change: kpis.revenueDelta ?? 0 }
    case 'roas':
      return { value: kpis.overallROAS, change: kpis.roasDelta ?? 0 }
    case 'conversions':
      return { value: kpis.totalConversions, change: kpis.conversionsDelta ?? 0 }
    case 'ctr':
      return { value: kpis.avgCTR, change: Math.round((kpis.avgCTR * 0.05) * 10) / 10 }
    case 'impressions':
      return { value: kpis.totalImpressions, change: Math.round((kpis.totalImpressions > 0 ? 8.7 : 0) * 10) / 10 }
    default:
      return { value: 0, change: 0 }
  }
}

export function KPIWidget({ type, className }: KPIWidgetProps) {
  const { kpis } = useDashboardSimulation()
  const cfg = config[type]
  const Icon = cfg.icon

  if (!kpis) {
    return (
      <div className={cn('h-full p-4 flex items-center justify-center', className)}>
        <div className="animate-pulse h-12 w-24 bg-muted rounded" />
      </div>
    )
  }

  const data = getKPIData(type, kpis)
  const trend = data.change >= 0 ? 'up' : 'down'

  return (
    <div className={cn('h-full p-4 flex flex-col justify-between', className)}>
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{cfg.label}</span>
        <Icon className={cn('w-5 h-5', cfg.color)} />
      </div>

      <div className="mt-2">
        <p className="text-2xl font-bold tabular-nums">{cfg.format(data.value)}</p>
        <div className="flex items-center gap-1 mt-1">
          {trend === 'up' ? (
            <TrendingUp className="w-4 h-4 text-green-500" />
          ) : (
            <TrendingDown className="w-4 h-4 text-red-500" />
          )}
          <span className={cn('text-sm font-medium', trend === 'up' ? 'text-green-500' : 'text-red-500')}>
            {data.change > 0 ? '+' : ''}{data.change}%
          </span>
          <span className="text-xs text-muted-foreground">vs last period</span>
        </div>
      </div>
    </div>
  )
}
