/**
 * Stratum AI - Insights Panel Component
 *
 * Displays AI-generated insights and recommendations with Quantum Ember styling.
 * Features motion animations and priority-based presentation.
 */

import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Lightbulb,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  RefreshCw,
  DollarSign,
  Eye,
  Zap,
  ChevronRight,
  Clock,
  CheckCircle2,
  X,
} from 'lucide-react'
import { useTenantRecommendations, type Recommendation } from '../api/hooks'
import { useToast } from '@/components/ui/use-toast'

interface InsightsPanelProps {
  tenantId: number
  className?: string
  maxItems?: number
  onApply?: (recommendationId: string, action: string) => void | Promise<void>
  onViewAllInsights?: () => void
  insightsPath?: string
}

// Quantum Ember accent colors
const quantumEmberAccent = {
  primary: 'from-orange-500 to-amber-500',
  secondary: 'from-rose-500 to-orange-500',
  tertiary: 'from-amber-400 to-yellow-500',
}

const typeConfig = {
  scale: {
    icon: TrendingUp,
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-50 dark:bg-emerald-900/20',
    borderColor: 'border-l-emerald-500',
    label: 'Scale Opportunity',
  },
  watch: {
    icon: Eye,
    color: 'text-amber-500',
    bgColor: 'bg-amber-50 dark:bg-amber-900/20',
    borderColor: 'border-l-amber-500',
    label: 'Monitor',
  },
  fix: {
    icon: AlertCircle,
    color: 'text-red-500',
    bgColor: 'bg-red-50 dark:bg-red-900/20',
    borderColor: 'border-l-red-500',
    label: 'Needs Attention',
  },
  pause: {
    icon: TrendingDown,
    color: 'text-gray-500',
    bgColor: 'bg-gray-50 dark:bg-gray-900/20',
    borderColor: 'border-l-gray-500',
    label: 'Consider Pausing',
  },
  creative_refresh: {
    icon: RefreshCw,
    color: 'text-purple-500',
    bgColor: 'bg-purple-50 dark:bg-purple-900/20',
    borderColor: 'border-l-purple-500',
    label: 'Creative Refresh',
  },
  budget_shift: {
    icon: DollarSign,
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    borderColor: 'border-l-blue-500',
    label: 'Budget Optimization',
  },
}

const priorityLabels = {
  1: { label: 'Critical', color: 'text-red-600 bg-red-100 dark:bg-red-900/30' },
  2: { label: 'High', color: 'text-orange-600 bg-orange-100 dark:bg-orange-900/30' },
  3: { label: 'Medium', color: 'text-amber-600 bg-amber-100 dark:bg-amber-900/30' },
  4: { label: 'Low', color: 'text-blue-600 bg-blue-100 dark:bg-blue-900/30' },
  5: { label: 'Info', color: 'text-gray-600 bg-gray-100 dark:bg-gray-900/30' },
}

const InsightCard: React.FC<{
  recommendation: Recommendation
  index: number
  onDismiss?: (id: string) => void
  onApply?: (id: string, action: string) => void
}> = ({ recommendation, index, onDismiss, onApply }) => {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isApplying, setIsApplying] = useState(false)

  const config = typeConfig[recommendation.type as keyof typeof typeConfig] || typeConfig.watch
  const Icon = config.icon
  const priority = priorityLabels[recommendation.priority as keyof typeof priorityLabels] || priorityLabels[3]

  const handleApply = async (actionType: string) => {
    setIsApplying(true)
    onApply?.(recommendation.id, actionType)
    // Simulate API call
    setTimeout(() => setIsApplying(false), 1000)
  }

  return (
    <div
      className={`
        motion-enter relative overflow-hidden rounded-xl border-l-4 ${config.borderColor}
        bg-card shadow-card hover:shadow-lg transition-all duration-300
        ${isExpanded ? 'ring-2 ring-primary/20' : ''}
      `}
      style={{
        animationDelay: `${index * 100}ms`,
      }}
    >
      {/* Quantum Ember accent gradient */}
      <div
        className={`absolute top-0 right-0 w-24 h-24 bg-gradient-to-br ${quantumEmberAccent.primary} opacity-5 rounded-bl-full`}
      />

      <div className="p-4">
        {/* Header */}
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${config.bgColor}`}>
            <Icon className={`h-5 w-5 ${config.color}`} />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${priority.color}`}>
                {priority.label}
              </span>
              <span className="text-xs text-muted-foreground">{config.label}</span>
            </div>

            <h4 className="font-medium text-foreground line-clamp-1">
              {recommendation.title}
            </h4>

            <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
              {recommendation.description}
            </p>
          </div>

          <button
            onClick={() => onDismiss?.(recommendation.id)}
            className="p-1 text-muted-foreground hover:text-foreground transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            aria-label="Dismiss insight"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {/* Impact estimate */}
        {(recommendation.roas_impact || recommendation.impact_estimate) && (
          <div className="mt-3 flex items-center gap-4">
            {recommendation.roas_impact && (
              <div className="flex items-center gap-1.5">
                <Zap className="h-4 w-4 text-amber-500" />
                <span className="text-sm font-medium text-amber-600 dark:text-amber-400">
                  +{(recommendation.roas_impact * 100).toFixed(0)}% ROAS
                </span>
              </div>
            )}
            {recommendation.impact_estimate && (
              <span className="text-sm text-muted-foreground">
                {recommendation.impact_estimate}
              </span>
            )}
            <div className="flex items-center gap-1 ml-auto text-xs text-muted-foreground">
              <Clock className="h-3 w-3" aria-hidden="true" />
              <span>{new Date(recommendation.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        )}

        {/* Confidence indicator */}
        {recommendation.confidence > 0 && (
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-muted-foreground">Confidence</span>
              <span className="font-medium text-foreground">
                {(recommendation.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${quantumEmberAccent.primary}`}
                style={{ width: `${recommendation.confidence * 100}%` }}
                role="progressbar"
                aria-valuenow={recommendation.confidence * 100}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
          </div>
        )}

        {/* Expand/collapse toggle */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-3 flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors focus:outline-none focus-visible:underline"
          aria-expanded={isExpanded}
        >
          <ChevronRight
            className={`h-4 w-4 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
            aria-hidden="true"
          />
          {isExpanded ? 'Hide actions' : 'Show actions'}
        </button>

        {/* Expanded actions */}
        {isExpanded && recommendation.actions && recommendation.actions.length > 0 && (
          <div className="mt-4 pt-4 border-t border-border motion-enter">
            <p className="text-xs font-medium text-muted-foreground mb-2">
              Recommended Actions
            </p>
            <div className="space-y-2">
              {recommendation.actions.map((action, idx) => (
                <button
                  key={idx}
                  onClick={() => handleApply(action.action)}
                  disabled={isApplying}
                  className={`
                    w-full flex items-center justify-between px-3 py-2 rounded-lg
                    border border-border bg-background
                    hover:bg-muted transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed
                    focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                  `}
                >
                  <span className="text-sm text-foreground">
                    {action.label}
                  </span>
                  {isApplying ? (
                    <RefreshCw className="h-4 w-4 text-muted-foreground animate-spin" aria-label="Applying..." />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-hidden="true" />
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export const InsightsPanel: React.FC<InsightsPanelProps> = ({
  tenantId,
  className = '',
  maxItems = 5,
  onApply,
  onViewAllInsights,
  insightsPath = '/insights',
}) => {
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set())
  const navigate = useNavigate()
  const { toast } = useToast()

  const { data: recommendations, isLoading, error, refetch } = useTenantRecommendations(
    tenantId,
    undefined,
    { limit: maxItems + dismissedIds.size }
  )

  const handleDismiss = (id: string) => {
    setDismissedIds((prev) => new Set([...prev, id]))
    toast({
      title: 'Insight dismissed',
      description: 'The insight has been removed from your list.',
    })
  }

  const handleApply = async (id: string, action: string) => {
    try {
      if (onApply) {
        await onApply(id, action)
      }
      toast({
        title: 'Action applied',
        description: `Successfully applied "${action}" for the recommendation.`,
      })
    } catch (error) {
      toast({
        title: 'Action failed',
        description: error instanceof Error ? error.message : 'Failed to apply action. Please try again.',
        variant: 'destructive',
      })
    }
  }

  const handleViewAllInsights = () => {
    if (onViewAllInsights) {
      onViewAllInsights()
    } else {
      navigate(insightsPath)
    }
  }

  const visibleRecommendations = recommendations
    ?.filter((r) => !dismissedIds.has(r.id))
    .slice(0, maxItems)

  if (isLoading) {
    return (
      <div className={`rounded-xl border bg-card shadow-card p-6 ${className}`}>
        <div className="flex items-center gap-2 mb-4">
          <Lightbulb className="h-5 w-5 text-amber-500" aria-hidden="true" />
          <h3 className="text-lg font-semibold text-foreground">AI Insights</h3>
        </div>
        <div className="space-y-4" aria-busy="true" aria-label="Loading insights">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-24 rounded-xl" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`rounded-xl border bg-card shadow-card p-6 ${className}`}>
        <div className="text-center py-8" role="alert">
          <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" aria-hidden="true" />
          <p className="text-muted-foreground">Failed to load insights</p>
          <button
            onClick={() => refetch()}
            className="mt-2 text-sm text-primary hover:underline focus:outline-none focus-visible:underline"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={`rounded-xl border bg-card shadow-card overflow-hidden ${className}`}>
      {/* Header with Quantum Ember gradient */}
      <div className="relative px-6 py-4 border-b border-border">
        <div
          className={`absolute inset-0 bg-gradient-to-r ${quantumEmberAccent.primary} opacity-5`}
        />
        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`p-1.5 rounded-lg bg-gradient-to-br ${quantumEmberAccent.primary}`}>
              <Lightbulb className="h-5 w-5 text-white" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">
                AI Insights
              </h3>
              <p className="text-xs text-muted-foreground">
                Powered by Quantum Ember Analytics
              </p>
            </div>
          </div>

          <button
            onClick={() => refetch()}
            className="p-2 text-muted-foreground hover:text-foreground transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            aria-label="Refresh insights"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Insights list */}
      <div className="p-4 space-y-4 max-h-[600px] overflow-y-auto">
        {visibleRecommendations && visibleRecommendations.length > 0 ? (
          visibleRecommendations.map((recommendation, index) => (
            <InsightCard
              key={recommendation.id}
              recommendation={recommendation}
              index={index}
              onDismiss={handleDismiss}
              onApply={handleApply}
            />
          ))
        ) : (
          <div className="text-center py-8">
            <CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto mb-3" aria-hidden="true" />
            <p className="text-foreground font-medium">All caught up!</p>
            <p className="text-sm text-muted-foreground mt-1">
              No new insights at this time
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      {visibleRecommendations && visibleRecommendations.length > 0 && (
        <div className="px-6 py-3 border-t border-border bg-muted/30">
          <button
            onClick={handleViewAllInsights}
            className="text-sm text-primary hover:text-primary/80 font-medium transition-colors focus:outline-none focus-visible:underline"
          >
            View all insights
          </button>
        </div>
      )}
    </div>
  )
}

export default InsightsPanel
