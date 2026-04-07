/**
 * Stratum AI - Tenant Overview Page
 *
 * Dashboard overview for a specific tenant showing key metrics,
 * recent activity, and quick access to campaign builder features.
 */

import { useParams } from 'react-router-dom'
import { usePriceMetrics } from '@/hooks/usePriceMetrics'
import { useTenantStore } from '@/stores/tenantStore'
import {
  ChartBarIcon,
  CurrencyDollarIcon,
  UserGroupIcon,
  ArrowTrendingUpIcon,
  LinkIcon,
  PlusCircleIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value: string
  change?: string
  changeType?: 'positive' | 'negative' | 'neutral'
  icon: React.ComponentType<{ className?: string }>
}

function MetricCard({ title, value, change, changeType = 'neutral', icon: Icon }: MetricCardProps) {
  return (
    <div className="rounded-xl border bg-card p-6 shadow-card">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
          </div>
        </div>
        {change && (
          <span
            className={cn(
              'text-sm font-medium',
              changeType === 'positive' && 'text-emerald-600',
              changeType === 'negative' && 'text-red-600',
              changeType === 'neutral' && 'text-muted-foreground'
            )}
          >
            {change}
          </span>
        )}
      </div>
    </div>
  )
}

export default function TenantOverview() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const { showPriceMetrics } = usePriceMetrics()
  const { tenant } = useTenantStore()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Tenant Overview</h1>
        <p className="text-muted-foreground">
          {tenant?.name || `Tenant ${tenantId}`} - Campaign management dashboard
        </p>
      </div>

      {/* Key Metrics */}
      <div className={cn(
        'grid grid-cols-1 md:grid-cols-2 gap-4',
        showPriceMetrics && 'lg:grid-cols-4'
      )}>
        <MetricCard
          title="Active Campaigns"
          value="12"
          change="+2 this week"
          changeType="positive"
          icon={ChartBarIcon}
        />
        {showPriceMetrics && (
        <MetricCard
          title="Total Spend"
          value="$45,230"
          change="+15% vs last month"
          changeType="positive"
          icon={CurrencyDollarIcon}
        />
        )}
        {showPriceMetrics && (
        <MetricCard
          title="Total ROAS"
          value="4.2x"
          change="+0.3x vs baseline"
          changeType="positive"
          icon={ArrowTrendingUpIcon}
        />
        )}
        <MetricCard
          title="Connected Accounts"
          value="5"
          icon={UserGroupIcon}
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="rounded-xl border bg-card p-6 shadow-card">
          <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-3">
            <a
              href={`/app/${tenantId}/campaigns/connect`}
              className="flex items-center gap-3 p-4 rounded-lg border hover:bg-accent transition-colors"
            >
              <LinkIcon className="h-5 w-5 text-primary" />
              <span className="text-sm font-medium">Connect Platform</span>
            </a>
            <a
              href={`/app/${tenantId}/campaigns/new`}
              className="flex items-center gap-3 p-4 rounded-lg border hover:bg-accent transition-colors"
            >
              <PlusCircleIcon className="h-5 w-5 text-primary" />
              <span className="text-sm font-medium">Create Campaign</span>
            </a>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="rounded-xl border bg-card p-6 shadow-card">
          <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
          <div className="space-y-3">
            <div className="flex items-center gap-3 text-sm">
              <div className="h-2 w-2 rounded-full bg-emerald-500" />
              <span className="text-muted-foreground">Campaign "Summer Sale" published</span>
              <span className="text-xs text-muted-foreground ml-auto">2h ago</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <div className="h-2 w-2 rounded-full bg-blue-500" />
              <span className="text-muted-foreground">Meta Ads account connected</span>
              <span className="text-xs text-muted-foreground ml-auto">1d ago</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <div className="h-2 w-2 rounded-full bg-amber-500" />
              <span className="text-muted-foreground">Draft "Q1 Retargeting" saved</span>
              <span className="text-xs text-muted-foreground ml-auto">2d ago</span>
            </div>
          </div>
        </div>
      </div>

      {/* Platform Status */}
      <div className="rounded-xl border bg-card p-6 shadow-card">
        <h2 className="text-lg font-semibold mb-4">Connected Platforms</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { name: 'Meta Ads', status: 'connected', accounts: 2 },
            { name: 'Google Ads', status: 'connected', accounts: 1 },
            { name: 'TikTok Ads', status: 'disconnected', accounts: 0 },
            { name: 'Snapchat Ads', status: 'disconnected', accounts: 0 },
          ].map((platform) => (
            <div
              key={platform.name}
              className={cn(
                'p-4 rounded-lg border',
                platform.status === 'connected' ? 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800' : 'bg-muted/50'
              )}
            >
              <p className="font-medium text-sm">{platform.name}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {platform.status === 'connected'
                  ? `${platform.accounts} account${platform.accounts !== 1 ? 's' : ''}`
                  : 'Not connected'}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
