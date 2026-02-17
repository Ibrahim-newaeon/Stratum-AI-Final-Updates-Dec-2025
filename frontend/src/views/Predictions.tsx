/**
 * Predictions Dashboard
 *
 * AI-powered performance predictions and budget optimization
 * Shows live predictions, scenario simulator, and optimization recommendations
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import { useLivePredictions, useBudgetOptimization, usePredictionAlerts } from '@/api/hooks'
import { ConfidenceBandBadge } from '@/components/shared'
import {
  SparklesIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  CurrencyDollarIcon,
  AdjustmentsHorizontalIcon,
  PlayIcon,
  ArrowPathIcon,
  LightBulbIcon,
  BeakerIcon,
} from '@heroicons/react/24/outline'

interface Prediction {
  id: string
  campaign: string
  platform: string
  metric: string
  currentValue: number
  predictedValue: number
  confidence: number
  trend: 'up' | 'down' | 'stable'
  horizon: string // e.g., "7d", "30d"
  updatedAt: Date
}

interface OptimizationRecommendation {
  id: string
  title: string
  description: string
  currentBudget: number
  recommendedBudget: number
  expectedImpact: {
    metric: string
    change: number
    unit: string
  }
  confidence: number
  priority: 'high' | 'medium' | 'low'
}

interface Scenario {
  id: string
  name: string
  budgetChange: number
  predictedRoas: number
  predictedRevenue: number
  confidence: number
}

export function Predictions() {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<'predictions' | 'optimization' | 'scenarios'>('predictions')
  const [timeHorizon, setTimeHorizon] = useState<'7d' | '30d' | '90d'>('30d')
  const [selectedCampaign, setSelectedCampaign] = useState<string>('all')

  const { data: predictionsData, isLoading: predictionsLoading } = useLivePredictions()
  const { data: optimizationData } = useBudgetOptimization()
  const { data: alertsData } = usePredictionAlerts()

  // Sample predictions
  const predictions: Prediction[] = predictionsData?.map((p) => ({
    id: p.campaignId,
    campaign: `Campaign ${p.campaignId}`,
    platform: 'Meta',
    metric: 'ROAS',
    currentValue: 3.2,
    predictedValue: p.predictedRoas ?? 3.5,
    confidence: p.confidence ?? 85,
    trend: (p.predictedRoas ?? 0) > 3.2 ? 'up' : 'down',
    horizon: '30d',
    updatedAt: new Date(),
  })) ?? [
    {
      id: '1',
      campaign: 'Summer Sale 2024',
      platform: 'Meta',
      metric: 'ROAS',
      currentValue: 3.2,
      predictedValue: 3.8,
      confidence: 92,
      trend: 'up' as const,
      horizon: '30d',
      updatedAt: new Date(Date.now() - 30 * 60 * 1000),
    },
    {
      id: '2',
      campaign: 'Brand Awareness Q4',
      platform: 'Google',
      metric: 'ROAS',
      currentValue: 2.8,
      predictedValue: 2.5,
      confidence: 78,
      trend: 'down' as const,
      horizon: '30d',
      updatedAt: new Date(Date.now() - 45 * 60 * 1000),
    },
    {
      id: '3',
      campaign: 'TikTok Conversions',
      platform: 'TikTok',
      metric: 'CPA',
      currentValue: 28,
      predictedValue: 24,
      confidence: 85,
      trend: 'up' as const,
      horizon: '30d',
      updatedAt: new Date(Date.now() - 60 * 60 * 1000),
    },
    {
      id: '4',
      campaign: 'Retargeting Campaign',
      platform: 'Meta',
      metric: 'Conversions',
      currentValue: 450,
      predictedValue: 520,
      confidence: 88,
      trend: 'up' as const,
      horizon: '30d',
      updatedAt: new Date(Date.now() - 90 * 60 * 1000),
    },
  ]

  const optimizations: OptimizationRecommendation[] = optimizationData?.recommendations?.map((r) => ({
    id: r.campaignId,
    title: `Optimize ${r.campaignId}`,
    description: r.action,
    currentBudget: r.currentBudget,
    recommendedBudget: r.suggestedBudget,
    expectedImpact: {
      metric: 'ROAS',
      change: r.expectedRoasChange,
      unit: '%',
    },
    confidence: 85,
    priority: 'high' as const,
  })) ?? [
    {
      id: '1',
      title: 'Increase Summer Sale budget',
      description: 'Campaign is performing above target ROAS and has room to scale',
      currentBudget: 5000,
      recommendedBudget: 7500,
      expectedImpact: { metric: 'Revenue', change: 45, unit: '%' },
      confidence: 91,
      priority: 'high' as const,
    },
    {
      id: '2',
      title: 'Reduce Brand Awareness spend',
      description: 'ROAS trending down, recommend reducing budget to maintain efficiency',
      currentBudget: 3000,
      recommendedBudget: 2000,
      expectedImpact: { metric: 'ROAS', change: 15, unit: '%' },
      confidence: 82,
      priority: 'medium' as const,
    },
    {
      id: '3',
      title: 'Reallocate to Retargeting',
      description: 'High conversion rates suggest budget reallocation opportunity',
      currentBudget: 2000,
      recommendedBudget: 3500,
      expectedImpact: { metric: 'Conversions', change: 60, unit: '%' },
      confidence: 87,
      priority: 'high' as const,
    },
  ]

  const scenarios: Scenario[] = [
    { id: '1', name: 'Conservative', budgetChange: -20, predictedRoas: 3.8, predictedRevenue: 145000, confidence: 92 },
    { id: '2', name: 'Current', budgetChange: 0, predictedRoas: 3.5, predictedRevenue: 168000, confidence: 88 },
    { id: '3', name: 'Aggressive', budgetChange: 30, predictedRoas: 3.2, predictedRevenue: 205000, confidence: 75 },
    { id: '4', name: 'Maximum Growth', budgetChange: 50, predictedRoas: 2.9, predictedRevenue: 240000, confidence: 62 },
  ]

  const alerts = alertsData ?? [
    { id: '1', type: 'warning', message: 'Brand Awareness Q4 ROAS predicted to drop 10% in next 7 days' },
    { id: '2', type: 'opportunity', message: 'Summer Sale 2024 has scaling potential - consider budget increase' },
  ]

  const formatValue = (value: number, metric: string) => {
    if (metric === 'ROAS') return `${value.toFixed(1)}x`
    if (metric === 'CPA') return `$${value.toFixed(0)}`
    if (metric === 'Revenue' || metric === 'Spend') return `$${(value / 1000).toFixed(0)}K`
    return value.toLocaleString()
  }

  const formatChange = (current: number, predicted: number) => {
    const change = ((predicted - current) / current) * 100
    return { value: Math.abs(change).toFixed(1), isPositive: change >= 0 }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 85) return 'text-green-500'
    if (confidence >= 70) return 'text-amber-500'
    return 'text-red-500'
  }

  const tabs = [
    { id: 'predictions' as const, label: 'Live Predictions', icon: ChartBarIcon },
    { id: 'optimization' as const, label: 'Budget Optimization', icon: CurrencyDollarIcon },
    { id: 'scenarios' as const, label: 'Scenario Simulator', icon: BeakerIcon },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <SparklesIcon className="w-7 h-7 text-primary" />
            AI Predictions
          </h1>
          <p className="text-muted-foreground">Machine learning powered performance forecasts</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={timeHorizon}
            onChange={(e) => setTimeHorizon(e.target.value as typeof timeHorizon)}
            className="px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="7d">Next 7 days</option>
            <option value="30d">Next 30 days</option>
            <option value="90d">Next 90 days</option>
          </select>
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors">
            <ArrowPathIcon className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={cn(
                'flex items-center gap-3 p-3 rounded-xl border',
                alert.type === 'warning' && 'bg-amber-500/5 border-amber-500/20',
                alert.type === 'opportunity' && 'bg-green-500/5 border-green-500/20'
              )}
            >
              {alert.type === 'warning' ? (
                <ExclamationTriangleIcon className="w-5 h-5 text-amber-500" />
              ) : (
                <LightBulbIcon className="w-5 h-5 text-green-500" />
              )}
              <span className={alert.type === 'warning' ? 'text-amber-700' : 'text-green-700'}>
                {alert.message}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b pb-4">
        {tabs.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
                activeTab === tab.id
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              )}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Predictions Tab */}
      {activeTab === 'predictions' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Performance Predictions</h2>
            <select
              value={selectedCampaign}
              onChange={(e) => setSelectedCampaign(e.target.value)}
              className="px-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="all">All Campaigns</option>
              {predictions.map((p) => (
                <option key={p.id} value={p.id}>{p.campaign}</option>
              ))}
            </select>
          </div>

          <div className="grid gap-4">
            {predictions
              .filter((p) => selectedCampaign === 'all' || p.id === selectedCampaign)
              .map((prediction) => {
                const change = formatChange(prediction.currentValue, prediction.predictedValue)
                return (
                  <div
                    key={prediction.id}
                    className="p-4 rounded-xl border bg-card hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold">{prediction.campaign}</h3>
                          <span className="px-2 py-0.5 rounded bg-muted text-xs">
                            {prediction.platform}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {prediction.metric} prediction for next {prediction.horizon}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <ConfidenceBandBadge score={prediction.confidence} size="sm" />
                        <span className={cn('text-sm font-medium', getConfidenceColor(prediction.confidence))}>
                          {prediction.confidence}% confidence
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-8">
                      <div>
                        <div className="text-sm text-muted-foreground">Current</div>
                        <div className="text-2xl font-bold">
                          {formatValue(prediction.currentValue, prediction.metric)}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {prediction.trend === 'up' ? (
                          <ArrowTrendingUpIcon className="w-6 h-6 text-green-500" />
                        ) : prediction.trend === 'down' ? (
                          <ArrowTrendingDownIcon className="w-6 h-6 text-red-500" />
                        ) : (
                          <div className="w-6 h-0.5 bg-muted-foreground" />
                        )}
                      </div>

                      <div>
                        <div className="text-sm text-muted-foreground">Predicted</div>
                        <div className="flex items-center gap-2">
                          <span className="text-2xl font-bold">
                            {formatValue(prediction.predictedValue, prediction.metric)}
                          </span>
                          <span className={cn(
                            'text-sm font-medium',
                            change.isPositive ? 'text-green-500' : 'text-red-500'
                          )}>
                            {change.isPositive ? '+' : '-'}{change.value}%
                          </span>
                        </div>
                      </div>

                      <div className="ml-auto text-sm text-muted-foreground">
                        <ClockIcon className="w-4 h-4 inline mr-1" />
                        Updated {Math.floor((Date.now() - prediction.updatedAt.getTime()) / 60000)}m ago
                      </div>
                    </div>
                  </div>
                )
              })}
          </div>
        </div>
      )}

      {/* Optimization Tab */}
      {activeTab === 'optimization' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Budget Optimization</h2>
              <p className="text-sm text-muted-foreground">
                AI-recommended budget adjustments to maximize performance
              </p>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Potential Revenue Gain:</span>
                <span className="ml-2 text-green-500 font-semibold">+$24,500</span>
              </div>
              <div>
                <span className="text-muted-foreground">Avg Confidence:</span>
                <span className="ml-2 font-semibold">87%</span>
              </div>
            </div>
          </div>

          <div className="grid gap-4">
            {optimizations.map((opt) => (
              <div
                key={opt.id}
                className={cn(
                  'p-4 rounded-xl border bg-card',
                  opt.priority === 'high' && 'border-green-500/30'
                )}
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold">{opt.title}</h3>
                      <span className={cn(
                        'px-2 py-0.5 rounded text-xs font-medium',
                        opt.priority === 'high' && 'bg-green-500/10 text-green-500',
                        opt.priority === 'medium' && 'bg-amber-500/10 text-amber-500',
                        opt.priority === 'low' && 'bg-muted text-muted-foreground'
                      )}>
                        {opt.priority} priority
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground">{opt.description}</p>
                  </div>
                  <span className={cn('text-sm font-medium', getConfidenceColor(opt.confidence))}>
                    {opt.confidence}% confidence
                  </span>
                </div>

                <div className="flex items-center gap-8 mb-4">
                  <div>
                    <div className="text-sm text-muted-foreground">Current Budget</div>
                    <div className="text-xl font-bold">${opt.currentBudget.toLocaleString()}</div>
                  </div>
                  <div className="text-xl text-muted-foreground">→</div>
                  <div>
                    <div className="text-sm text-muted-foreground">Recommended</div>
                    <div className={cn(
                      'text-xl font-bold',
                      opt.recommendedBudget > opt.currentBudget ? 'text-green-500' : 'text-amber-500'
                    )}>
                      ${opt.recommendedBudget.toLocaleString()}
                    </div>
                  </div>
                  <div className="ml-auto">
                    <div className="text-sm text-muted-foreground">Expected Impact</div>
                    <div className="text-xl font-bold text-green-500">
                      +{opt.expectedImpact.change}{opt.expectedImpact.unit} {opt.expectedImpact.metric}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
                    <CheckCircleIcon className="w-4 h-4" />
                    Apply
                  </button>
                  <button className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors">
                    Dismiss
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Scenarios Tab */}
      {activeTab === 'scenarios' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Scenario Simulator</h2>
              <p className="text-sm text-muted-foreground">
                Explore different budget scenarios and their predicted outcomes
              </p>
            </div>
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
              <PlayIcon className="w-4 h-4" />
              Create Custom Scenario
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {scenarios.map((scenario) => (
              <div
                key={scenario.id}
                className={cn(
                  'p-4 rounded-xl border bg-card hover:shadow-md transition-shadow cursor-pointer',
                  scenario.name === 'Current' && 'ring-2 ring-primary'
                )}
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold">{scenario.name}</h3>
                  <span className={cn(
                    'px-2 py-0.5 rounded text-xs',
                    scenario.budgetChange > 0 && 'bg-green-500/10 text-green-500',
                    scenario.budgetChange < 0 && 'bg-amber-500/10 text-amber-500',
                    scenario.budgetChange === 0 && 'bg-primary/10 text-primary'
                  )}>
                    {scenario.budgetChange > 0 ? '+' : ''}{scenario.budgetChange}% budget
                  </span>
                </div>

                <div className="space-y-3">
                  <div>
                    <div className="text-sm text-muted-foreground">Predicted ROAS</div>
                    <div className="text-xl font-bold">{scenario.predictedRoas.toFixed(1)}x</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Predicted Revenue</div>
                    <div className="text-xl font-bold">${(scenario.predictedRevenue / 1000).toFixed(0)}K</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className={cn(
                          'h-full rounded-full',
                          scenario.confidence >= 80 ? 'bg-green-500' :
                          scenario.confidence >= 60 ? 'bg-amber-500' : 'bg-red-500'
                        )}
                        style={{ width: `${scenario.confidence}%` }}
                      />
                    </div>
                    <span className="text-sm text-muted-foreground">{scenario.confidence}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="p-4 rounded-xl border bg-muted/50">
            <div className="flex items-center gap-3 mb-2">
              <AdjustmentsHorizontalIcon className="w-5 h-5 text-primary" />
              <h3 className="font-medium">Custom Budget Simulator</h3>
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              Adjust the budget slider to see predicted outcomes
            </p>
            <div className="flex items-center gap-4">
              <span className="text-sm">-50%</span>
              <input
                type="range"
                min="-50"
                max="100"
                defaultValue="0"
                className="flex-1 h-2 bg-muted rounded-full appearance-none cursor-pointer"
              />
              <span className="text-sm">+100%</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Predictions
