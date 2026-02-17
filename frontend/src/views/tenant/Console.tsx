/**
 * Media Buyer Console
 *
 * Primary goal: Optimize fast but safely; know exactly what is allowed today
 * Always-visible header with EMQ, Confidence, Autopilot mode & allowed actions
 */

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  ConfidenceBandBadge,
  AutopilotModeBanner,
  ActionCard,
  BudgetAtRiskChip,
  type Action,
  type AutopilotMode,
} from '@/components/shared'
import {
  useEmqScore,
  useAutopilotState,
} from '@/api/hooks'
import { useTenantRecommendations } from '@/api/hooks'
import {
  SparklesIcon,
  ExclamationTriangleIcon,
  ArrowTrendingUpIcon,
  WrenchScrewdriverIcon,
  CheckCircleIcon,
  ClockIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'

type ActionTab = 'all' | 'opportunities' | 'risks' | 'fixes'

export default function Console() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const tid = parseInt(tenantId || '1', 10)

  const [activeTab, setActiveTab] = useState<ActionTab>('all')
  const [appliedActions, setAppliedActions] = useState<Set<string>>(new Set())
  const [dismissedActions, setDismissedActions] = useState<Set<string>>(new Set())

  // Fetch data
  const { data: emqData } = useEmqScore(tid)
  const { data: autopilotData } = useAutopilotState(tid)
  const { data: recommendationsData } = useTenantRecommendations(tid.toString())

  const emqScore = emqData?.score ?? 85
  const autopilotMode: AutopilotMode = autopilotData?.mode ?? 'normal'
  const budgetAtRisk = autopilotData?.budgetAtRisk ?? 0

  // Sample actions data
  const allActions: Action[] = [
    {
      id: '1',
      type: 'opportunity',
      title: 'Scale "Summer Sale" campaign by 20%',
      description: 'Campaign has maintained 5.2x ROAS over the past 14 days with consistent performance.',
      platform: 'Meta',
      campaign: 'Summer Sale 2024',
      confidence: 94,
      estimatedImpact: { metric: 'Revenue', value: 8500, unit: '$' },
      status: 'pending',
      priority: 1,
      createdAt: new Date(),
    },
    {
      id: '2',
      type: 'opportunity',
      title: 'Activate lookalike audience',
      description: 'New 1% lookalike ready based on high-value purchasers segment.',
      platform: 'Meta',
      campaign: 'Prospecting - LAL',
      confidence: 88,
      estimatedImpact: { metric: 'Reach', value: 45, unit: '%' },
      status: 'pending',
      priority: 2,
      createdAt: new Date(),
    },
    {
      id: '3',
      type: 'risk',
      title: 'Pause underperforming ad set',
      description: 'Ad set "Broad Interest" has 0.6x ROAS over last 7 days, burning budget.',
      platform: 'Meta',
      campaign: 'Awareness Campaign',
      confidence: 91,
      estimatedImpact: { metric: 'Savings', value: 1200, unit: '$' },
      status: 'pending',
      priority: 1,
      createdAt: new Date(),
    },
    {
      id: '4',
      type: 'risk',
      title: 'Creative fatigue detected',
      description: 'Top creative "Product Hero" CTR dropped 35% in last 3 days.',
      platform: 'TikTok',
      campaign: 'TikTok Conversions',
      confidence: 86,
      estimatedImpact: { metric: 'CTR', value: -0.5, unit: '%' },
      status: 'pending',
      priority: 2,
      createdAt: new Date(),
    },
    {
      id: '5',
      type: 'fix',
      title: 'Review conversion tracking',
      description: 'Meta pixel showing 18% variance from GA4 - verify implementation.',
      platform: 'Meta',
      confidence: 78,
      estimatedImpact: { metric: 'EMQ', value: 8, unit: 'pts' },
      status: 'pending',
      priority: 1,
      createdAt: new Date(),
    },
  ]

  // Filter actions
  const filteredActions = allActions
    .filter(a => !appliedActions.has(a.id) && !dismissedActions.has(a.id))
    .filter(a => {
      if (activeTab === 'all') return true
      if (activeTab === 'opportunities') return a.type === 'opportunity'
      if (activeTab === 'risks') return a.type === 'risk'
      if (activeTab === 'fixes') return a.type === 'fix'
      return true
    })

  // Mode restrictions
  const isFrozen = autopilotMode === 'frozen'
  const isCutsOnly = autopilotMode === 'cuts_only'

  const canApplyAction = (action: Action): boolean => {
    if (isFrozen) return false
    if (isCutsOnly && action.type === 'opportunity') return false
    return true
  }

  const handleApply = (action: Action) => {
    setAppliedActions(new Set([...appliedActions, action.id]))
  }

  const handleDismiss = (action: Action) => {
    setDismissedActions(new Set([...dismissedActions, action.id]))
  }

  const tabs = [
    { id: 'all' as const, label: 'All Actions', count: allActions.length },
    { id: 'opportunities' as const, label: 'Opportunities', icon: ArrowTrendingUpIcon, count: allActions.filter(a => a.type === 'opportunity').length },
    { id: 'risks' as const, label: 'Risks', icon: ExclamationTriangleIcon, count: allActions.filter(a => a.type === 'risk').length },
    { id: 'fixes' as const, label: 'Fixes', icon: WrenchScrewdriverIcon, count: allActions.filter(a => a.type === 'fix').length },
  ]

  return (
    <div className="space-y-6">
      {/* Always Visible Header */}
      <div data-tour="console-header" className="sticky top-0 z-10 bg-surface-primary pb-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-white">Daily Console</h1>
            <p className="text-text-muted">Optimize fast, but safely</p>
          </div>
          <div className="flex items-center gap-4">
            {/* EMQ Score */}
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-secondary border border-white/10">
              <span className="text-2xl font-bold text-white">{emqScore}</span>
              <div className="flex flex-col">
                <span className="text-xs text-text-muted">EMQ</span>
                <ConfidenceBandBadge score={emqScore} size="sm" />
              </div>
            </div>

            {/* Autopilot Mode */}
            <AutopilotModeBanner mode={autopilotMode} compact />

            {/* Budget at Risk */}
            {budgetAtRisk > 0 && (
              <BudgetAtRiskChip amount={budgetAtRisk} />
            )}
          </div>
        </div>

        {/* Mode Warning Banner */}
        {(isFrozen || isCutsOnly) && (
          <div data-tour="allowed-actions" className={cn(
            'flex items-center gap-3 p-3 rounded-xl',
            isFrozen ? 'bg-danger/10 text-danger' : 'bg-warning/10 text-warning'
          )}>
            <ExclamationTriangleIcon className="w-5 h-5" />
            <div>
              <span className="font-medium">
                {isFrozen ? 'Autopilot Frozen' : 'Cuts Only Mode'}
              </span>
              <span className="text-sm opacity-80 ml-2">
                {isFrozen
                  ? 'All automation paused. Focus on fixing data issues.'
                  : 'Only pause and reduction actions are allowed.'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-2 border-b border-white/10 pb-4">
        {tabs.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
                activeTab === tab.id
                  ? 'bg-stratum-500/10 text-stratum-400'
                  : 'text-text-muted hover:text-white hover:bg-white/5'
              )}
            >
              {Icon && <Icon className="w-4 h-4" />}
              {tab.label}
              <span className={cn(
                'text-xs px-2 py-0.5 rounded-full',
                activeTab === tab.id ? 'bg-stratum-500/20' : 'bg-surface-tertiary'
              )}>
                {tab.count}
              </span>
            </button>
          )
        })}
      </div>

      {/* Actions Grid */}
      <div data-tour="action-cards" className="grid gap-4">
        {filteredActions.length > 0 ? (
          filteredActions.map((action) => (
            <div key={action.id} data-tour={action.type === 'fix' ? 'fix-first' : undefined}>
              <ActionCard
                action={action}
                disabled={!canApplyAction(action)}
                onApply={handleApply}
                onDismiss={handleDismiss}
                showControls
              />
            </div>
          ))
        ) : (
          <div className="text-center py-16">
            <div className="w-16 h-16 rounded-full bg-success/10 flex items-center justify-center mx-auto mb-4">
              <CheckCircleIcon className="w-8 h-8 text-success" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">All caught up!</h3>
            <p className="text-text-muted">
              No pending actions in this category. Check back later.
            </p>
          </div>
        )}
      </div>

      {/* Applied/Dismissed Summary */}
      {(appliedActions.size > 0 || dismissedActions.size > 0) && (
        <div className="flex items-center gap-4 pt-4 border-t border-white/10">
          {appliedActions.size > 0 && (
            <div className="flex items-center gap-2 text-success text-sm">
              <CheckCircleIcon className="w-4 h-4" />
              {appliedActions.size} applied today
            </div>
          )}
          {dismissedActions.size > 0 && (
            <div className="flex items-center gap-2 text-text-muted text-sm">
              <XMarkIcon className="w-4 h-4" />
              {dismissedActions.size} dismissed
            </div>
          )}
        </div>
      )}
    </div>
  )
}
