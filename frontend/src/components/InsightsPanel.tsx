/**
 * Stratum AI - Insights Panel Component
 *
 * Displays AI-generated insights and recommendations with Quantum Ember styling.
 * Features motion animations and priority-based presentation.
 */

import React, { useState } from 'react'
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

interface InsightsPanelProps {
  tenantId: number
  className?: string
  maxItems?: number
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
        bg-white dark:bg-gray-800 shadow-card hover:shadow-lg transition-all duration-300
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
              <span className="text-xs text-gray-500 dark:text-gray-400">{config.label}</span>
            </div>

            <h4 className="font-medium text-gray-900 dark:text-white line-clamp-1">
              {recommendation.title}
            </h4>

            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
              {recommendation.description}
            </p>
          </div>

          <button
            onClick={() => onDismiss?.(recommendation.id)}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            <X className="h-4 w-4" />
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
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {recommendation.impact_estimate}
              </span>
            )}
            <div className="flex items-center gap-1 ml-auto text-xs text-gray-400">
              <Clock className="h-3 w-3" />
              <span>{new Date(recommendation.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        )}

        {/* Confidence indicator */}
        {recommendation.confidence > 0 && (
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-gray-500 dark:text-gray-400">Confidence</span>
              <span className="font-medium text-gray-700 dark:text-gray-300">
                {(recommendation.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${quantumEmberAccent.primary}`}
                style={{ width: `${recommendation.confidence * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Expand/collapse toggle */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-3 flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
        >
          <ChevronRight
            className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
          />
          {isExpanded ? 'Hide actions' : 'Show actions'}
        </button>

        {/* Expanded actions */}
        {isExpanded && recommendation.actions && recommendation.actions.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700 motion-card">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
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
                    border border-gray-200 dark:border-gray-600
                    hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed
                  `}
                >
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {action.label}
                  </span>
                  {isApplying ? (
                    <RefreshCw className="h-4 w-4 text-gray-400 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
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
}) => {
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set())

  const { data: recommendations, isLoading, error, refetch } = useTenantRecommendations(
    tenantId,
    undefined,
    { limit: maxItems + dismissedIds.size }
  )

  const handleDismiss = (id: string) => {
    setDismissedIds((prev) => new Set([...prev, id]))
  }

  const handleApply = (id: string, action: string) => {
    console.log(`Applying action ${action} for recommendation ${id}`)
    // In production, this would call the API
  }

  const visibleRecommendations = recommendations
    ?.filter((r) => !dismissedIds.has(r.id))
    .slice(0, maxItems)

  if (isLoading) {
    return (
      <div className={`rounded-xl border bg-card shadow-card p-6 ${className}`}>
        <div className="flex items-center gap-2 mb-4">
          <Lightbulb className="h-5 w-5 text-amber-500" />
          <h3 className="text-lg font-semibold">AI Insights</h3>
        </div>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-24 bg-gray-200 dark:bg-gray-700 rounded-xl" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`rounded-xl border bg-card shadow-card p-6 ${className}`}>
        <div className="text-center py-8">
          <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
          <p className="text-gray-500 dark:text-gray-400">Failed to load insights</p>
          <button
            onClick={() => refetch()}
            className="mt-2 text-sm text-primary hover:underline"
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
      <div className="relative px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div
          className={`absolute inset-0 bg-gradient-to-r ${quantumEmberAccent.primary} opacity-5`}
        />
        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`p-1.5 rounded-lg bg-gradient-to-br ${quantumEmberAccent.primary}`}>
              <Lightbulb className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                AI Insights
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Powered by Quantum Ember Analytics
              </p>
            </div>
          </div>

          <button
            onClick={() => refetch()}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            title="Refresh insights"
          >
            <RefreshCw className="h-4 w-4" />
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
            <CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto mb-3" />
            <p className="text-gray-600 dark:text-gray-400 font-medium">All caught up!</p>
            <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">
              No new insights at this time
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      {visibleRecommendations && visibleRecommendations.length > 0 && (
        <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          <button className="text-sm text-primary hover:text-primary/80 font-medium transition-colors">
            View all insights
          </button>
        </div>
      )}
    </div>
  )
}

export default InsightsPanel
