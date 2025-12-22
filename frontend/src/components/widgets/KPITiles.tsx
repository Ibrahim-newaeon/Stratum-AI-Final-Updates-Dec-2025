import { useTranslation } from 'react-i18next'
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  MousePointerClick,
  Eye,
  Target,
  ShoppingCart,
  BarChart3,
} from 'lucide-react'
import { cn, formatCurrency, formatPercent, formatCompactNumber } from '@/lib/utils'
import { SmartTooltip } from '../guide/SmartTooltip'
import { InfoIcon } from '../ui/InfoIcon'

interface KPIData {
  spend: number
  spendChange: number
  revenue: number
  revenueChange: number
  roas: number
  roasChange: number
  impressions: number
  impressionsChange: number
  clicks: number
  clicksChange: number
  ctr: number
  ctrChange: number
  conversions: number
  conversionsChange: number
  cpa: number
  cpaChange: number
}

interface KPITilesProps {
  data: KPIData
  isLoading?: boolean
  className?: string
}

interface TileProps {
  title: string
  value: string | number
  change: number
  icon: React.ReactNode
  iconBg: string
  tooltip: string
  invertChangeColor?: boolean
}

function KPITile({
  title,
  value,
  change,
  icon,
  iconBg,
  tooltip,
  invertChangeColor = false,
}: TileProps) {
  const isPositive = invertChangeColor ? change < 0 : change > 0
  const isNegative = invertChangeColor ? change > 0 : change < 0

  return (
    <div className="p-4 rounded-xl border bg-card hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-1">
          <span className="text-sm text-muted-foreground font-medium">
            {title}
          </span>
          <SmartTooltip content={tooltip} position="top" trigger="click">
            <InfoIcon size={12} aria-label={`${title} information`} />
          </SmartTooltip>
        </div>
        <div className={cn('p-2 rounded-lg', iconBg)}>{icon}</div>
      </div>
      <div className="space-y-1">
        <p className="text-2xl font-bold">{value}</p>
        <div
          className={cn(
            'flex items-center gap-1 text-sm',
            isPositive && 'text-green-500',
            isNegative && 'text-red-500',
            !isPositive && !isNegative && 'text-muted-foreground'
          )}
        >
          {change !== 0 && (
            <>
              {isPositive ? (
                <TrendingUp className="w-4 h-4" />
              ) : (
                <TrendingDown className="w-4 h-4" />
              )}
              <span>
                {change > 0 ? '+' : ''}
                {formatPercent(change)}
              </span>
              <span className="text-muted-foreground text-xs">vs last period</span>
            </>
          )}
          {change === 0 && <span className="text-muted-foreground">No change</span>}
        </div>
      </div>
    </div>
  )
}

function KPITileSkeleton() {
  return (
    <div className="p-4 rounded-xl border bg-card animate-pulse">
      <div className="flex items-start justify-between mb-3">
        <div className="h-4 w-16 bg-muted rounded" />
        <div className="h-9 w-9 bg-muted rounded-lg" />
      </div>
      <div className="space-y-2">
        <div className="h-8 w-24 bg-muted rounded" />
        <div className="h-4 w-20 bg-muted rounded" />
      </div>
    </div>
  )
}

export function KPITiles({ data, isLoading, className }: KPITilesProps) {
  const { t } = useTranslation()

  if (isLoading) {
    return (
      <div id="kpi-tiles" className={cn('grid grid-cols-2 md:grid-cols-4 gap-4', className)}>
        {Array.from({ length: 8 }).map((_, i) => (
          <KPITileSkeleton key={i} />
        ))}
      </div>
    )
  }

  const tiles: TileProps[] = [
    {
      title: t('kpi.spend'),
      value: formatCurrency(data.spend),
      change: data.spendChange,
      icon: <DollarSign className="w-5 h-5 text-orange-500" />,
      iconBg: 'bg-orange-500/10',
      tooltip: t('kpi.spendTooltip'),
      invertChangeColor: true, // Higher spend = potentially bad
    },
    {
      title: t('kpi.revenue'),
      value: formatCurrency(data.revenue),
      change: data.revenueChange,
      icon: <TrendingUp className="w-5 h-5 text-green-500" />,
      iconBg: 'bg-green-500/10',
      tooltip: t('kpi.revenueTooltip'),
    },
    {
      title: 'ROAS',
      value: `${data.roas.toFixed(2)}x`,
      change: data.roasChange,
      icon: <Target className="w-5 h-5 text-primary" />,
      iconBg: 'bg-primary/10',
      tooltip: t('kpi.roasTooltip'),
    },
    {
      title: t('kpi.impressions'),
      value: formatCompactNumber(data.impressions),
      change: data.impressionsChange,
      icon: <Eye className="w-5 h-5 text-purple-500" />,
      iconBg: 'bg-purple-500/10',
      tooltip: t('kpi.impressionsTooltip'),
    },
    {
      title: t('kpi.clicks'),
      value: formatCompactNumber(data.clicks),
      change: data.clicksChange,
      icon: <MousePointerClick className="w-5 h-5 text-blue-500" />,
      iconBg: 'bg-blue-500/10',
      tooltip: t('kpi.clicksTooltip'),
    },
    {
      title: 'CTR',
      value: formatPercent(data.ctr),
      change: data.ctrChange,
      icon: <BarChart3 className="w-5 h-5 text-cyan-500" />,
      iconBg: 'bg-cyan-500/10',
      tooltip: t('kpi.ctrTooltip'),
    },
    {
      title: t('kpi.conversions'),
      value: formatCompactNumber(data.conversions),
      change: data.conversionsChange,
      icon: <ShoppingCart className="w-5 h-5 text-emerald-500" />,
      iconBg: 'bg-emerald-500/10',
      tooltip: t('kpi.conversionsTooltip'),
    },
    {
      title: 'CPA',
      value: formatCurrency(data.cpa),
      change: data.cpaChange,
      icon: <DollarSign className="w-5 h-5 text-rose-500" />,
      iconBg: 'bg-rose-500/10',
      tooltip: t('kpi.cpaTooltip'),
      invertChangeColor: true, // Lower CPA = better
    },
  ]

  return (
    <div id="kpi-tiles" className={cn('grid grid-cols-2 md:grid-cols-4 gap-4', className)}>
      {tiles.map((tile) => (
        <KPITile key={tile.title} {...tile} />
      ))}
    </div>
  )
}

// Compact variant for sidebar or smaller spaces
export function KPITilesCompact({ data, className }: KPITilesProps) {
  const { t } = useTranslation()

  const mainKPIs = [
    { label: 'ROAS', value: `${data.roas.toFixed(2)}x`, change: data.roasChange },
    { label: t('kpi.spend'), value: formatCurrency(data.spend), change: data.spendChange, invert: true },
    { label: t('kpi.conversions'), value: formatCompactNumber(data.conversions), change: data.conversionsChange },
  ]

  return (
    <div className={cn('space-y-2', className)}>
      {mainKPIs.map((kpi) => (
        <div key={kpi.label} className="flex items-center justify-between p-2 rounded-lg bg-muted/50">
          <span className="text-sm text-muted-foreground">{kpi.label}</span>
          <div className="flex items-center gap-2">
            <span className="font-semibold">{kpi.value}</span>
            <span
              className={cn(
                'text-xs',
                (kpi.invert ? kpi.change < 0 : kpi.change > 0) && 'text-green-500',
                (kpi.invert ? kpi.change > 0 : kpi.change < 0) && 'text-red-500'
              )}
            >
              {kpi.change > 0 ? '+' : ''}
              {formatPercent(kpi.change)}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}

export default KPITiles
