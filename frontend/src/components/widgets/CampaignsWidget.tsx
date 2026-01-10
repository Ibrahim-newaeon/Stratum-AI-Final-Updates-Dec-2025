import { TrendingUp, TrendingDown } from 'lucide-react'
import { cn, formatCurrency, getPlatformColor } from '@/lib/utils'

interface CampaignsWidgetProps {
  className?: string
}

const mockCampaigns = [
  { id: 1, name: 'Summer Sale 2024', platform: 'google', roas: 4.2, spend: 12450, trend: 'up' },
  { id: 2, name: 'Brand Awareness Q4', platform: 'meta', roas: 3.8, spend: 8900, trend: 'up' },
  { id: 3, name: 'Retargeting - Cart', platform: 'meta', roas: 5.2, spend: 3200, trend: 'up' },
  { id: 4, name: 'TikTok Influencer', platform: 'tiktok', roas: 3.0, spend: 7800, trend: 'down' },
]

export function CampaignsWidget({ className }: CampaignsWidgetProps) {
  return (
    <div className={cn('h-full p-4 overflow-auto', className)}>
      <div className="space-y-3">
        {mockCampaigns.map((campaign) => (
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
