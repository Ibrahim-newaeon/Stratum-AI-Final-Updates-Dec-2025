import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeft,
  ExternalLink,
  Pause,
  Play,
  RefreshCw,
  Loader2,
  TrendingUp,
  TrendingDown,
  DollarSign,
  MousePointerClick,
  Eye,
  Target,
  BarChart3,
  Calendar,
  AlertCircle,
} from 'lucide-react'
import { cn, formatCurrency, formatPercent, formatCompactNumber, getPlatformColor } from '@/lib/utils'
import { useCampaign, usePauseCampaign, useActivateCampaign, useSyncCampaign } from '@/api/hooks'
import { usePriceMetrics } from '@/hooks/usePriceMetrics'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

function CampaignDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { showPriceMetrics } = usePriceMetrics()

  const { data: campaign, isLoading, isError, error } = useCampaign(id || '')
  const pauseCampaign = usePauseCampaign()
  const activateCampaign = useActivateCampaign()
  const syncCampaign = useSyncCampaign()

  const handleBack = () => {
    navigate('/dashboard/campaigns')
  }

  const handleToggleStatus = async () => {
    if (!campaign) return
    if (campaign.status === 'active') {
      await pauseCampaign.mutateAsync(campaign.id)
    } else if (campaign.status === 'paused') {
      await activateCampaign.mutateAsync(campaign.id)
    }
  }

  const handleSync = async () => {
    if (!campaign) return
    await syncCampaign.mutateAsync(campaign.id)
  }

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      active: 'bg-green-500/10 text-green-500',
      paused: 'bg-amber-500/10 text-amber-500',
      completed: 'bg-blue-500/10 text-blue-500',
      draft: 'bg-gray-500/10 text-gray-500',
      error: 'bg-red-500/10 text-red-500',
    }
    return (
      <span className={cn('px-3 py-1 rounded-full text-sm font-medium', styles[status] || styles.draft)}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const getPlatformBadge = (platform: string) => {
    const logoMap: Record<string, string> = {
      meta: '/icons/meta.svg',
      google: '/icons/google.svg',
      tiktok: '/icons/tiktok.svg',
      snapchat: '/icons/snapchat.svg',
    }
    const logo = logoMap[platform.toLowerCase()]
    if (logo) {
      return (
        <img
          src={logo}
          alt={platform}
          className="w-8 h-8 rounded-full"
          title={platform.charAt(0).toUpperCase() + platform.slice(1)}
        />
      )
    }
    return (
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold"
        style={{ backgroundColor: getPlatformColor(platform) }}
        title={platform.charAt(0).toUpperCase() + platform.slice(1)}
      >
        {platform.charAt(0).toUpperCase()}
      </div>
    )
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" label="Loading campaign details..." />
      </div>
    )
  }

  // Error state
  if (isError || !campaign) {
    return (
      <div className="space-y-6">
        <button
          onClick={handleBack}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>{t('common.back', 'Back to Campaigns')}</span>
        </button>

        <div className="flex flex-col items-center justify-center p-12 rounded-xl border bg-card">
          <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
          <h3 className="text-lg font-semibold mb-2">Campaign not found</h3>
          <p className="text-muted-foreground text-center max-w-md mb-6">
            {error instanceof Error
              ? error.message
              : 'The campaign you are looking for does not exist or you do not have permission to view it.'}
          </p>
          <button
            onClick={handleBack}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            Return to Campaigns
          </button>
        </div>
      </div>
    )
  }

  const metrics = campaign.metrics

  return (
    <div className="space-y-6">
      {/* Back button */}
      <button
        onClick={handleBack}
        className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Campaigns</span>
      </button>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          {getPlatformBadge(campaign.platform)}
          <div>
            <h1 className="text-2xl font-bold">{campaign.name}</h1>
            <div className="flex items-center gap-3 mt-1">
              {getStatusBadge(campaign.status)}
              <span className="text-sm text-muted-foreground capitalize">{campaign.platform}</span>
              {campaign.objective && (
                <span className="text-sm text-muted-foreground capitalize">
                  {campaign.objective}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleSync}
            disabled={syncCampaign.isPending}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border hover:bg-muted transition-colors text-sm disabled:opacity-50"
            title="Sync campaign data"
          >
            {syncCampaign.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Sync
          </button>

          {(campaign.status === 'active' || campaign.status === 'paused') && (
            <button
              onClick={handleToggleStatus}
              disabled={pauseCampaign.isPending || activateCampaign.isPending}
              className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-lg transition-colors text-sm disabled:opacity-50',
                campaign.status === 'active'
                  ? 'bg-amber-500/10 text-amber-500 hover:bg-amber-500/20'
                  : 'bg-green-500/10 text-green-500 hover:bg-green-500/20'
              )}
            >
              {pauseCampaign.isPending || activateCampaign.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : campaign.status === 'active' ? (
                <Pause className="w-4 h-4" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              {campaign.status === 'active' ? 'Pause' : 'Activate'}
            </button>
          )}
        </div>
      </div>

      {/* Metrics Grid */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {showPriceMetrics && (
            <div className="rounded-xl border bg-card p-5">
              <div className="flex items-center gap-2 text-muted-foreground mb-2">
                <DollarSign className="w-4 h-4" />
                <span className="text-sm font-medium">Spend</span>
              </div>
              <p className="text-2xl font-bold">{formatCurrency(metrics.spend)}</p>
            </div>
          )}

          {showPriceMetrics && (
            <div className="rounded-xl border bg-card p-5">
              <div className="flex items-center gap-2 text-muted-foreground mb-2">
                <TrendingUp className="w-4 h-4" />
                <span className="text-sm font-medium">Revenue</span>
              </div>
              <p className="text-2xl font-bold text-green-500">{formatCurrency(metrics.revenue)}</p>
            </div>
          )}

          {showPriceMetrics && (
            <div className="rounded-xl border bg-card p-5">
              <div className="flex items-center gap-2 text-muted-foreground mb-2">
                <BarChart3 className="w-4 h-4" />
                <span className="text-sm font-medium">ROAS</span>
              </div>
              <p
                className={cn(
                  'text-2xl font-bold',
                  metrics.roas >= 4 && 'text-green-500',
                  metrics.roas >= 3 && metrics.roas < 4 && 'text-primary',
                  metrics.roas < 3 && 'text-amber-500'
                )}
              >
                {metrics.roas.toFixed(2)}x
              </p>
            </div>
          )}

          <div className="rounded-xl border bg-card p-5">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Target className="w-4 h-4" />
              <span className="text-sm font-medium">Conversions</span>
            </div>
            <p className="text-2xl font-bold">{formatCompactNumber(metrics.conversions)}</p>
          </div>

          <div className="rounded-xl border bg-card p-5">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Eye className="w-4 h-4" />
              <span className="text-sm font-medium">Impressions</span>
            </div>
            <p className="text-2xl font-bold">{formatCompactNumber(metrics.impressions)}</p>
          </div>

          <div className="rounded-xl border bg-card p-5">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <MousePointerClick className="w-4 h-4" />
              <span className="text-sm font-medium">Clicks</span>
            </div>
            <p className="text-2xl font-bold">{formatCompactNumber(metrics.clicks)}</p>
          </div>

          <div className="rounded-xl border bg-card p-5">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <ExternalLink className="w-4 h-4" />
              <span className="text-sm font-medium">CTR</span>
            </div>
            <p className="text-2xl font-bold">{formatPercent(metrics.ctr)}</p>
          </div>

          {showPriceMetrics && (
            <div className="rounded-xl border bg-card p-5">
              <div className="flex items-center gap-2 text-muted-foreground mb-2">
                <TrendingDown className="w-4 h-4" />
                <span className="text-sm font-medium">CPA</span>
              </div>
              <p className="text-2xl font-bold">{formatCurrency(metrics.cpa)}</p>
            </div>
          )}
        </div>
      )}

      {/* Campaign Details Card */}
      <div className="rounded-xl border bg-card p-6">
        <h2 className="text-lg font-semibold mb-4">Campaign Details</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
          <div className="flex items-center justify-between py-2 border-b border-border/50">
            <span className="text-muted-foreground text-sm">Platform</span>
            <span className="font-medium capitalize">{campaign.platform}</span>
          </div>

          <div className="flex items-center justify-between py-2 border-b border-border/50">
            <span className="text-muted-foreground text-sm">Status</span>
            {getStatusBadge(campaign.status)}
          </div>

          {campaign.objective && (
            <div className="flex items-center justify-between py-2 border-b border-border/50">
              <span className="text-muted-foreground text-sm">Objective</span>
              <span className="font-medium capitalize">{campaign.objective}</span>
            </div>
          )}

          {showPriceMetrics && campaign.budget != null && (
            <div className="flex items-center justify-between py-2 border-b border-border/50">
              <span className="text-muted-foreground text-sm">Budget</span>
              <span className="font-medium">
                {formatCurrency(campaign.budget, campaign.currency || 'USD')}
              </span>
            </div>
          )}

          {showPriceMetrics && campaign.dailyBudget != null && (
            <div className="flex items-center justify-between py-2 border-b border-border/50">
              <span className="text-muted-foreground text-sm">Daily Budget</span>
              <span className="font-medium">
                {formatCurrency(campaign.dailyBudget, campaign.currency || 'USD')}
              </span>
            </div>
          )}

          {campaign.startDate && (
            <div className="flex items-center justify-between py-2 border-b border-border/50">
              <span className="text-muted-foreground text-sm flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" /> Start Date
              </span>
              <span className="font-medium">
                {new Date(campaign.startDate).toLocaleDateString()}
              </span>
            </div>
          )}

          {campaign.endDate && (
            <div className="flex items-center justify-between py-2 border-b border-border/50">
              <span className="text-muted-foreground text-sm flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" /> End Date
              </span>
              <span className="font-medium">
                {new Date(campaign.endDate).toLocaleDateString()}
              </span>
            </div>
          )}

          {campaign.lastSyncedAt && (
            <div className="flex items-center justify-between py-2 border-b border-border/50">
              <span className="text-muted-foreground text-sm">Last Synced</span>
              <span className="font-medium">
                {new Date(campaign.lastSyncedAt).toLocaleString()}
              </span>
            </div>
          )}

          {campaign.createdAt && (
            <div className="flex items-center justify-between py-2 border-b border-border/50">
              <span className="text-muted-foreground text-sm">Created</span>
              <span className="font-medium">
                {new Date(campaign.createdAt).toLocaleDateString()}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* CPC and Reach (if available) */}
      {metrics && (metrics.cpc != null || metrics.reach != null || metrics.frequency != null) && (
        <div className="rounded-xl border bg-card p-6">
          <h2 className="text-lg font-semibold mb-4">Additional Metrics</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {showPriceMetrics && metrics.cpc != null && (
              <div className="flex items-center justify-between py-2 border-b border-border/50">
                <span className="text-muted-foreground text-sm">Cost Per Click</span>
                <span className="font-medium">{formatCurrency(metrics.cpc)}</span>
              </div>
            )}
            {metrics.reach != null && (
              <div className="flex items-center justify-between py-2 border-b border-border/50">
                <span className="text-muted-foreground text-sm">Reach</span>
                <span className="font-medium">{formatCompactNumber(metrics.reach)}</span>
              </div>
            )}
            {metrics.frequency != null && (
              <div className="flex items-center justify-between py-2 border-b border-border/50">
                <span className="text-muted-foreground text-sm">Frequency</span>
                <span className="font-medium">{metrics.frequency.toFixed(2)}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default CampaignDetail
