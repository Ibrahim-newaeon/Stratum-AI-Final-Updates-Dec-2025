/**
 * Live Predictions Widget
 * Displays real-time ML predictions and portfolio health
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Brain,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Activity,
  AlertCircle,
  CheckCircle,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { SmartTooltip } from '../guide/SmartTooltip'
import { InfoIcon } from '../ui/InfoIcon'

interface CampaignAnalysis {
  campaign_id: number
  campaign_name: string
  platform: string
  health_score: number
  status: string
  current_roas: number
  recommendations: Array<{
    type: string
    action: string
    priority: string
    expected_impact: string
  }>
}

interface PortfolioAnalysis {
  portfolio_roas: number
  avg_health_score: number
  campaign_count: number
  total_spend: number
  total_revenue: number
  potential_uplift?: {
    optimistic: number
    conservative: number
    expected: number
  }
}

interface LivePredictionsWidgetProps {
  className?: string
}

const getHealthColor = (score: number) => {
  if (score >= 70) return 'text-green-500'
  if (score >= 40) return 'text-amber-500'
  return 'text-red-500'
}

const getHealthBg = (score: number) => {
  if (score >= 70) return 'bg-green-500/10'
  if (score >= 40) return 'bg-amber-500/10'
  return 'bg-red-500/10'
}

const getHealthStatus = (score: number) => {
  if (score >= 70) return 'Healthy'
  if (score >= 40) return 'Needs Attention'
  return 'Critical'
}

export function LivePredictionsWidget({ className }: LivePredictionsWidgetProps) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [portfolio, setPortfolio] = useState<PortfolioAnalysis | null>(null)
  const [campaigns, setCampaigns] = useState<CampaignAnalysis[]>([])
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchPredictions = async (forceRefresh = false) => {
    try {
      if (forceRefresh) {
        setRefreshing(true)
      }

      const response = await fetch(`/api/v1/predictions/live${forceRefresh ? '?refresh=true' : ''}`)
      const data = await response.json()

      if (data.success && data.data?.prediction) {
        const prediction = data.data.prediction
        setPortfolio({
          portfolio_roas: prediction.portfolio_roas || 0,
          avg_health_score: prediction.avg_health_score || 0,
          campaign_count: prediction.campaign_count || 0,
          total_spend: prediction.total_spend || 0,
          total_revenue: prediction.total_revenue || 0,
          potential_uplift: prediction.potential_uplift,
        })
        setCampaigns(prediction.campaign_analyses || [])
        setLastUpdated(new Date(data.data.generated_at))
        setError(null)
      } else if (data.data?.message === 'No campaigns found') {
        setPortfolio(null)
        setCampaigns([])
        setError(null)
      }
    } catch (err) {
      console.error('Failed to fetch predictions:', err)
      setError('Failed to load predictions')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchPredictions()
    // Refresh every 5 minutes
    const interval = setInterval(() => fetchPredictions(), 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  const handleRefresh = () => {
    fetchPredictions(true)
  }

  if (loading) {
    return (
      <div className={cn('rounded-xl border bg-card p-6', className)}>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-muted rounded w-1/3" />
          <div className="h-20 bg-muted rounded" />
          <div className="h-32 bg-muted rounded" />
        </div>
      </div>
    )
  }

  return (
    <div className={cn('rounded-xl border bg-card overflow-hidden', className)}>
      {/* Header */}
      <div className="px-6 py-4 border-b bg-gradient-to-r from-primary/5 to-transparent">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Brain className="w-5 h-5 text-primary" />
            </div>
            <div className="flex items-center gap-2">
              <div>
                <h3 className="font-semibold text-foreground">Live Predictions</h3>
                <p className="text-xs text-muted-foreground">
                  {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : 'AI-powered insights'}
                </p>
              </div>
              <SmartTooltip
                content="ML-powered predictions based on historical performance. Refreshes every 5 minutes."
                position="right"
                trigger="click"
              >
                <InfoIcon size={14} aria-label="Live Predictions information" />
              </SmartTooltip>
            </div>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 hover:bg-muted rounded-lg transition-colors disabled:opacity-50"
            title="Refresh predictions"
          >
            <RefreshCw className={cn('w-4 h-4', refreshing && 'animate-spin')} />
          </button>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {error ? (
          <div className="flex items-center gap-3 p-4 bg-red-500/10 rounded-lg text-red-500">
            <AlertCircle className="w-5 h-5" />
            <span className="text-sm">{error}</span>
          </div>
        ) : !portfolio ? (
          <div className="text-center py-8 text-muted-foreground">
            <Brain className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No campaigns to analyze</p>
            <p className="text-sm mt-1">Create campaigns to see predictions</p>
          </div>
        ) : (
          <>
            {/* Portfolio Health */}
            <div className="grid grid-cols-2 gap-4">
              <div className={cn('p-4 rounded-lg', getHealthBg(portfolio.avg_health_score))}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1">
                    <span className="text-sm text-muted-foreground">Portfolio Health</span>
                    <SmartTooltip
                      content="Aggregate health score based on ROAS, spend efficiency, and trend analysis."
                      position="top"
                      trigger="click"
                    >
                      <InfoIcon size={12} aria-label="Portfolio Health information" />
                    </SmartTooltip>
                  </div>
                  <Activity className={cn('w-4 h-4', getHealthColor(portfolio.avg_health_score))} />
                </div>
                <div className={cn('text-2xl font-bold', getHealthColor(portfolio.avg_health_score))}>
                  {portfolio.avg_health_score.toFixed(0)}%
                </div>
                <div className={cn('text-xs font-medium mt-1', getHealthColor(portfolio.avg_health_score))}>
                  {getHealthStatus(portfolio.avg_health_score)}
                </div>
              </div>

              <div className="p-4 rounded-lg bg-primary/5">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1">
                    <span className="text-sm text-muted-foreground">Portfolio ROAS</span>
                    <SmartTooltip
                      content="Weighted ROAS across all active campaigns. Above 2x is generally healthy."
                      position="top"
                      trigger="click"
                    >
                      <InfoIcon size={12} aria-label="Portfolio ROAS information" />
                    </SmartTooltip>
                  </div>
                  {portfolio.portfolio_roas >= 2 ? (
                    <TrendingUp className="w-4 h-4 text-green-500" />
                  ) : (
                    <TrendingDown className="w-4 h-4 text-amber-500" />
                  )}
                </div>
                <div className="text-2xl font-bold text-foreground">
                  {portfolio.portfolio_roas.toFixed(2)}x
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {portfolio.campaign_count} campaigns
                </div>
              </div>
            </div>

            {/* Potential Uplift */}
            {portfolio.potential_uplift && (
              <div className="p-4 rounded-lg bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/20">
                <div className="flex items-center gap-2 mb-3">
                  <Zap className="w-4 h-4 text-green-500" />
                  <span className="font-medium text-sm">Potential Revenue Uplift</span>
                  <SmartTooltip
                    content="Predicted revenue gain from implementing ML recommendations. Range shows confidence interval."
                    position="right"
                    trigger="click"
                  >
                    <InfoIcon size={12} aria-label="Potential Uplift information" />
                  </SmartTooltip>
                  <span className="text-[10px] px-1.5 py-0.5 bg-indigo-500/20 text-indigo-400 rounded font-medium">
                    Predicted
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-lg font-semibold text-foreground">
                      +${(portfolio.potential_uplift.conservative / 1000).toFixed(1)}k
                    </div>
                    <div className="text-xs text-muted-foreground">Conservative</div>
                  </div>
                  <div>
                    <div className="text-lg font-semibold text-green-500">
                      +${(portfolio.potential_uplift.expected / 1000).toFixed(1)}k
                    </div>
                    <div className="text-xs text-muted-foreground">Expected</div>
                  </div>
                  <div>
                    <div className="text-lg font-semibold text-foreground">
                      +${(portfolio.potential_uplift.optimistic / 1000).toFixed(1)}k
                    </div>
                    <div className="text-xs text-muted-foreground">Optimistic</div>
                  </div>
                </div>
              </div>
            )}

            {/* Campaign Health List */}
            <div>
              <h4 className="text-sm font-medium text-foreground mb-3">Campaign Health</h4>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {campaigns.slice(0, 5).map((campaign) => (
                  <div
                    key={campaign.campaign_id}
                    className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={cn(
                        'w-2 h-2 rounded-full flex-shrink-0',
                        campaign.health_score >= 70 ? 'bg-green-500' :
                        campaign.health_score >= 40 ? 'bg-amber-500' : 'bg-red-500'
                      )} />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">
                          {campaign.campaign_name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {campaign.platform} • ROAS: {campaign.current_roas.toFixed(2)}x
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        'text-sm font-medium',
                        getHealthColor(campaign.health_score)
                      )}>
                        {campaign.health_score.toFixed(0)}%
                      </span>
                      {campaign.health_score >= 70 ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : campaign.health_score >= 40 ? (
                        <AlertCircle className="w-4 h-4 text-amber-500" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-red-500" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default LivePredictionsWidget
