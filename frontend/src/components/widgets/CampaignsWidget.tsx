import { useMemo } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { cn, formatCurrency, getPlatformColor } from '@/lib/utils'
import { useDashboardSimulation } from '@/contexts/DashboardSimulationContext'

interface CampaignsWidgetProps {
  className?: string
}

export function CampaignsWidget({ className }: CampaignsWidgetProps) {
  const { campaigns } = useDashboardSimulation()

  const topCampaigns = useMemo(() => {
    if (!campaigns || campaigns.length === 0) return []

    return campaigns
      .filter((c) => c.status === 'Active')
      .sort((a, b) => b.roas - a.roas)
      .slice(0, 5)
      .map((c) => ({
        id: c.campaign_id,
        name: c.campaign_name,
        platform: c.platform.replace(' Ads', '').toLowerCase(),
        roas: c.roas,
        spend: c.spend,
        trend: c.roas >= 3.5 ? 'up' : c.roas < 2.0 ? 'down' : 'stable',
      }))
  }, [campaigns])

  if (topCampaigns.length === 0) {
    return (
      <div className={cn('h-full p-4 flex items-center justify-center', className)}>
        <div className="animate-pulse space-y-3 w-full">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 bg-muted rounded" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className={cn('h-full p-4 overflow-auto', className)}>
      <div className="space-y-3">
        {topCampaigns.map((campaign) => (
          <div
            key={campaign.id}
            className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
          >
            <div className="flex items-center gap-3">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold"
                style={{ backgroundColor: getPlatformColor(campaign.platform) }}
              >
                {campaign.platform.charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="font-medium text-sm">{campaign.name}</p>
                <p className="text-xs text-muted-foreground">{formatCurrency(campaign.spend)} spent</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={cn(
                'font-semibold text-sm',
                campaign.roas >= 4 && 'text-emerald-500 dark:text-emerald-400',
                campaign.roas >= 3 && campaign.roas < 4 && 'text-primary',
                campaign.roas < 3 && 'text-amber-500 dark:text-amber-400'
              )}>
                {campaign.roas.toFixed(1)}x
              </span>
              {campaign.trend === 'up' && <TrendingUp className="w-4 h-4 text-emerald-500 dark:text-emerald-400" aria-label="Trending up" />}
              {campaign.trend === 'down' && <TrendingDown className="w-4 h-4 text-red-500 dark:text-red-400" aria-label="Trending down" />}
              {campaign.trend === 'stable' && <div className="w-4 h-0.5 bg-muted-foreground" aria-label="Stable" />}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
