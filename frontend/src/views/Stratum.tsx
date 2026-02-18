import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import {
  Brain,
  Sparkles,
  Target,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Lightbulb,
  ArrowRight,
  RefreshCw,
  Settings,
  Loader2,
  X,
  DollarSign,
  Users,
  BarChart3,
  Clock,
  Zap,
  Bell,
  Mail,
  MessageSquare,
  Trash2,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react'
import { cn, formatCurrency, formatPercent, formatCompactNumber } from '@/lib/utils'
import { SimulateSlider } from '@/components/widgets/SimulateSlider'
import { useInsights, useRecommendations, useAnomalies, useLivePredictions } from '@/api/hooks'
import { useTenantStore } from '@/stores/tenantStore'

// (Mock data removed — insights come from useInsights() API hook)

// Type for insight
interface Insight {
  id: number
  type: string
  priority: string
  title: string
  description: string
  impact: string
  campaign: string
  fullDescription?: string
  metrics?: Record<string, any>
  recommendations?: string[]
  historicalData?: Array<{ date: string; performance: number }>
  confidence?: number
  detectedAt?: string
}

// (Mock prediction & attribution data removed — data comes from API hooks)

// Type for anomaly
interface Anomaly {
  id: number
  date: string
  metric: string
  value: number
  expected: number
  deviation: string
  type: string
  fullDescription?: string
  campaign?: string
  adGroup?: string
  platform?: string
  severity?: string
  historicalData?: Array<{ date: string; value: number }>
  possibleCauses?: string[]
  suggestedActions?: string[]
  relatedMetrics?: Record<string, { value: number; change: number }>
  detectedAt?: string
  confidence?: number
}

// Insight Detail Modal Component
function InsightDetailModal({
  insight,
  onClose,
  onApply
}: {
  insight: Insight | null
  onClose: () => void
  onApply: (insight: Insight) => void
}) {
  const [isApplying, setIsApplying] = useState(false)

  if (!insight) return null

  const handleApply = async () => {
    setIsApplying(true)
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500))
    onApply(insight)
    setIsApplying(false)
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'opportunity': return 'text-green-500 bg-green-500/10'
      case 'warning': return 'text-amber-500 bg-amber-500/10'
      case 'suggestion': return 'text-blue-500 bg-blue-500/10'
      default: return 'text-primary bg-primary/10'
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'opportunity': return <Lightbulb className="w-5 h-5" />
      case 'warning': return <AlertTriangle className="w-5 h-5" />
      case 'suggestion': return <Sparkles className="w-5 h-5" />
      default: return <Brain className="w-5 h-5" />
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Slide-over Panel */}
      <div className="relative w-full max-w-xl h-full bg-background shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="sticky top-0 bg-background border-b px-6 py-4 flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className={cn('p-2 rounded-lg', getTypeColor(insight.type))}>
              {getTypeIcon(insight.type)}
            </div>
            <div>
              <h2 className="font-semibold text-lg">{insight.title}</h2>
              <div className="flex items-center gap-2 mt-1">
                <span className={cn(
                  'px-2 py-0.5 rounded-full text-xs font-medium',
                  insight.priority === 'high' ? 'bg-red-500/10 text-red-500' :
                  insight.priority === 'medium' ? 'bg-amber-500/10 text-amber-500' :
                  'bg-blue-500/10 text-blue-500'
                )}>
                  {insight.priority.charAt(0).toUpperCase() + insight.priority.slice(1)} Priority
                </span>
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {insight.detectedAt || 'Recently'}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Campaign Badge */}
          <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
            <Target className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm">Campaign: <span className="font-medium">{insight.campaign}</span></span>
          </div>

          {/* Full Description */}
          <div>
            <h3 className="font-medium mb-2 flex items-center gap-2">
              <Brain className="w-4 h-4 text-primary" />
              AI Analysis
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {insight.fullDescription || insight.description}
            </p>
          </div>

          {/* Impact */}
          <div className="p-4 rounded-lg border bg-card">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Estimated Impact</span>
              <span className={cn(
                'text-lg font-bold',
                insight.impact.startsWith('+') ? 'text-green-500' : 'text-red-500'
              )}>
                {insight.impact}
              </span>
            </div>
            {insight.confidence && (
              <div className="mt-3 pt-3 border-t">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">AI Confidence</span>
                  <span className="font-medium">{insight.confidence}%</span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all"
                    style={{ width: `${insight.confidence}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Key Metrics */}
          {insight.metrics && (
            <div>
              <h3 className="font-medium mb-3 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-primary" />
                Key Metrics
              </h3>
              <div className="grid grid-cols-2 gap-3">
                {insight.type === 'opportunity' && insight.metrics.conversionRate && (
                  <>
                    <div className="p-3 rounded-lg border bg-card">
                      <p className="text-xs text-muted-foreground">Conversion Rate</p>
                      <p className="text-lg font-semibold">{insight.metrics.conversionRate.current}%</p>
                      <p className="text-xs text-green-500">+{insight.metrics.conversionRate.change}% vs avg</p>
                    </div>
                    <div className="p-3 rounded-lg border bg-card">
                      <p className="text-xs text-muted-foreground">Avg Order Value</p>
                      <p className="text-lg font-semibold">${insight.metrics.avgOrderValue.current}</p>
                      <p className="text-xs text-green-500">+{insight.metrics.avgOrderValue.change}% vs avg</p>
                    </div>
                    <div className="p-3 rounded-lg border bg-card">
                      <p className="text-xs text-muted-foreground">Cost Per Acquisition</p>
                      <p className="text-lg font-semibold">${insight.metrics.cpa.current}</p>
                      <p className="text-xs text-green-500">{insight.metrics.cpa.change}% vs avg</p>
                    </div>
                    <div className="p-3 rounded-lg border bg-card">
                      <p className="text-xs text-muted-foreground">Audience Size</p>
                      <p className="text-lg font-semibold">{formatCompactNumber(insight.metrics.audienceSize)}</p>
                      <p className="text-xs text-muted-foreground">{formatCompactNumber(insight.metrics.potentialReach)} potential</p>
                    </div>
                  </>
                )}
                {insight.type === 'warning' && insight.metrics.ctr && (
                  <>
                    <div className="p-3 rounded-lg border bg-card">
                      <p className="text-xs text-muted-foreground">Current CTR</p>
                      <p className="text-lg font-semibold">{insight.metrics.ctr.current}%</p>
                      <p className="text-xs text-red-500">{insight.metrics.ctr.change}% decline</p>
                    </div>
                    <div className="p-3 rounded-lg border bg-card">
                      <p className="text-xs text-muted-foreground">Frequency</p>
                      <p className="text-lg font-semibold">{insight.metrics.frequency.current}x</p>
                      <p className="text-xs text-amber-500">Optimal: {insight.metrics.frequency.optimal}x</p>
                    </div>
                    <div className="p-3 rounded-lg border bg-card">
                      <p className="text-xs text-muted-foreground">Total Impressions</p>
                      <p className="text-lg font-semibold">{formatCompactNumber(insight.metrics.impressions.current)}</p>
                      <p className="text-xs text-muted-foreground">Threshold: {formatCompactNumber(insight.metrics.impressions.threshold)}</p>
                    </div>
                    <div className="p-3 rounded-lg border bg-card">
                      <p className="text-xs text-muted-foreground">Est. Weekly Loss</p>
                      <p className="text-lg font-semibold text-red-500">-${formatCompactNumber(insight.metrics.estimatedLoss)}</p>
                      <p className="text-xs text-muted-foreground">If unchanged</p>
                    </div>
                  </>
                )}
                {insight.type === 'suggestion' && insight.metrics.cpcPeak && (
                  <>
                    <div className="p-3 rounded-lg border bg-card">
                      <p className="text-xs text-muted-foreground">Peak CPC</p>
                      <p className="text-lg font-semibold">${insight.metrics.cpcPeak.current}</p>
                      <p className="text-xs text-muted-foreground">During busy hours</p>
                    </div>
                    <div className="p-3 rounded-lg border bg-card">
                      <p className="text-xs text-muted-foreground">Off-Peak CPC</p>
                      <p className="text-lg font-semibold">${insight.metrics.cpcPeak.offPeak}</p>
                      <p className="text-xs text-green-500">{insight.metrics.cpcPeak.savings}% savings</p>
                    </div>
                    <div className="p-3 rounded-lg border bg-card">
                      <p className="text-xs text-muted-foreground">Optimal Hours</p>
                      <p className="text-lg font-semibold">{insight.metrics.optimalHours}</p>
                      <p className="text-xs text-muted-foreground">Local time</p>
                    </div>
                    <div className="p-3 rounded-lg border bg-card">
                      <p className="text-xs text-muted-foreground">Monthly Savings</p>
                      <p className="text-lg font-semibold text-green-500">+${insight.metrics.monthlySavings}</p>
                      <p className="text-xs text-muted-foreground">Estimated</p>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Performance Trend */}
          {insight.historicalData && (
            <div>
              <h3 className="font-medium mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" />
                Performance Trend
              </h3>
              <div className="h-[120px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={insight.historicalData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '0.5rem',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="performance"
                      stroke={insight.type === 'warning' ? '#ef4444' : '#10b981'}
                      strokeWidth={2}
                      dot={{ fill: insight.type === 'warning' ? '#ef4444' : '#10b981', strokeWidth: 0, r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Recommendations */}
          {insight.recommendations && (
            <div>
              <h3 className="font-medium mb-3 flex items-center gap-2">
                <Zap className="w-4 h-4 text-primary" />
                Recommended Actions
              </h3>
              <ul className="space-y-2">
                {insight.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="sticky bottom-0 bg-background border-t px-6 py-4 flex items-center gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 rounded-lg border hover:bg-muted transition-colors"
          >
            Dismiss
          </button>
          <button
            onClick={handleApply}
            disabled={isApplying}
            className={cn(
              'flex-1 px-4 py-2.5 rounded-lg font-medium transition-colors flex items-center justify-center gap-2',
              insight.type === 'warning'
                ? 'bg-amber-500 hover:bg-amber-600 text-white'
                : 'bg-primary hover:bg-primary/90 text-primary-foreground'
            )}
          >
            {isApplying ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Applying...
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                {insight.type === 'warning' ? 'Fix Issue' : 'Apply Recommendation'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// Anomaly Detail Modal Component
function AnomalyDetailModal({
  anomaly,
  onClose,
  onAction
}: {
  anomaly: Anomaly | null
  onClose: () => void
  onAction: (anomaly: Anomaly, action: string) => void
}) {
  const [selectedAction, setSelectedAction] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  if (!anomaly) return null

  const handleAction = async (action: string) => {
    setSelectedAction(action)
    setIsProcessing(true)
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500))
    onAction(anomaly, action)
    setIsProcessing(false)
    setSelectedAction(null)
  }

  const isPositive = anomaly.type === 'positive'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Slide-over Panel */}
      <div className="relative w-full max-w-xl h-full bg-background shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className={cn(
          'sticky top-0 border-b px-6 py-4 flex items-start justify-between',
          isPositive ? 'bg-green-500/5' : 'bg-red-500/5'
        )}>
          <div className="flex items-start gap-3">
            <div className={cn(
              'p-2 rounded-lg',
              isPositive ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'
            )}>
              {isPositive ? (
                <TrendingUp className="w-5 h-5" />
              ) : (
                <AlertTriangle className="w-5 h-5" />
              )}
            </div>
            <div>
              <h2 className="font-semibold text-lg">
                {anomaly.metric} Anomaly Detected
              </h2>
              <div className="flex items-center gap-2 mt-1">
                <span className={cn(
                  'px-2 py-0.5 rounded-full text-xs font-medium',
                  isPositive ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'
                )}>
                  {isPositive ? 'Positive' : 'Negative'} Anomaly
                </span>
                <span className={cn(
                  'px-2 py-0.5 rounded-full text-xs font-medium',
                  anomaly.severity === 'critical' ? 'bg-red-500/10 text-red-500' :
                  anomaly.severity === 'high' ? 'bg-amber-500/10 text-amber-500' :
                  'bg-blue-500/10 text-blue-500'
                )}>
                  {anomaly.severity?.charAt(0).toUpperCase()}{anomaly.severity?.slice(1)} Severity
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Detection Info */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="text-xs text-muted-foreground">Detected</p>
              <p className="font-medium flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {anomaly.detectedAt || anomaly.date}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="text-xs text-muted-foreground">Platform</p>
              <p className="font-medium">{anomaly.platform || 'Multi-channel'}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="text-xs text-muted-foreground">Campaign</p>
              <p className="font-medium">{anomaly.campaign || 'All Campaigns'}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="text-xs text-muted-foreground">Ad Group</p>
              <p className="font-medium">{anomaly.adGroup || 'All Ad Groups'}</p>
            </div>
          </div>

          {/* Metric Comparison */}
          <div className={cn(
            'p-4 rounded-lg border',
            isPositive ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'
          )}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium">{anomaly.metric} Value</span>
              <span className={cn(
                'text-2xl font-bold',
                isPositive ? 'text-green-500' : 'text-red-500'
              )}>
                {anomaly.deviation}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Actual</p>
                <p className="text-lg font-semibold">{anomaly.value}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Expected</p>
                <p className="text-lg font-semibold text-muted-foreground">{anomaly.expected}</p>
              </div>
            </div>
            {anomaly.confidence && (
              <div className="mt-3 pt-3 border-t border-current/10">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Detection Confidence</span>
                  <span className="font-medium">{anomaly.confidence}%</span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-background overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all',
                      isPositive ? 'bg-green-500' : 'bg-red-500'
                    )}
                    style={{ width: `${anomaly.confidence}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Full Description */}
          <div>
            <h3 className="font-medium mb-2 flex items-center gap-2">
              <Brain className="w-4 h-4 text-primary" />
              AI Analysis
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {anomaly.fullDescription || `${anomaly.metric} showed a ${anomaly.deviation} deviation from expected values.`}
            </p>
          </div>

          {/* Historical Trend */}
          {anomaly.historicalData && (
            <div>
              <h3 className="font-medium mb-3 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-primary" />
                7-Day Trend
              </h3>
              <div className="h-[140px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={anomaly.historicalData}>
                    <defs>
                      <linearGradient id={`gradient-${anomaly.id}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={isPositive ? '#10b981' : '#ef4444'} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={isPositive ? '#10b981' : '#ef4444'} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '0.5rem',
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke={isPositive ? '#10b981' : '#ef4444'}
                      strokeWidth={2}
                      fill={`url(#gradient-${anomaly.id})`}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Related Metrics */}
          {anomaly.relatedMetrics && (
            <div>
              <h3 className="font-medium mb-3 flex items-center gap-2">
                <Target className="w-4 h-4 text-primary" />
                Related Metrics
              </h3>
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(anomaly.relatedMetrics).map(([key, data]) => (
                  <div key={key} className="p-3 rounded-lg border bg-card">
                    <p className="text-xs text-muted-foreground capitalize">{key}</p>
                    <p className="text-lg font-semibold">
                      {key === 'spend' || key === 'revenue' ? '$' : ''}{formatCompactNumber(data.value)}
                    </p>
                    <p className={cn(
                      'text-xs',
                      data.change > 0 ? 'text-green-500' : 'text-red-500'
                    )}>
                      {data.change > 0 ? '+' : ''}{data.change}%
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Possible Causes */}
          {anomaly.possibleCauses && (
            <div>
              <h3 className="font-medium mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                Possible Causes
              </h3>
              <ul className="space-y-2">
                {anomaly.possibleCauses.map((cause, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <span className="w-5 h-5 rounded-full bg-muted flex items-center justify-center text-xs flex-shrink-0">
                      {idx + 1}
                    </span>
                    <span>{cause}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggested Actions */}
          {anomaly.suggestedActions && (
            <div>
              <h3 className="font-medium mb-3 flex items-center gap-2">
                <Zap className="w-4 h-4 text-primary" />
                Suggested Actions
              </h3>
              <ul className="space-y-2">
                {anomaly.suggestedActions.map((action, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className={cn(
                      'w-4 h-4 mt-0.5 flex-shrink-0',
                      isPositive ? 'text-green-500' : 'text-amber-500'
                    )} />
                    <span>{action}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="sticky bottom-0 bg-background border-t px-6 py-4 flex items-center gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 rounded-lg border hover:bg-muted transition-colors"
          >
            Dismiss
          </button>
          <button
            onClick={() => handleAction('reviewed')}
            disabled={isProcessing}
            className="flex-1 px-4 py-2.5 rounded-lg border hover:bg-muted transition-colors flex items-center justify-center gap-2"
          >
            {isProcessing && selectedAction === 'reviewed' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <CheckCircle2 className="w-4 h-4" />
            )}
            Mark Reviewed
          </button>
          <button
            onClick={() => handleAction('alert')}
            disabled={isProcessing}
            className={cn(
              'flex-1 px-4 py-2.5 rounded-lg font-medium transition-colors flex items-center justify-center gap-2',
              isPositive
                ? 'bg-green-500 hover:bg-green-600 text-white'
                : 'bg-amber-500 hover:bg-amber-600 text-white'
            )}
          >
            {isProcessing && selectedAction === 'alert' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Zap className="w-4 h-4" />
            )}
            Create Alert Rule
          </button>
        </div>
      </div>
    </div>
  )
}

// Alert Rule interface
interface AlertRule {
  id?: string
  name: string
  metric: string
  condition: 'above' | 'below' | 'change_above' | 'change_below'
  threshold: number
  frequency: 'realtime' | 'hourly' | 'daily'
  channels: {
    email: boolean
    whatsapp: boolean
    inApp: boolean
    slack: boolean
  }
  enabled: boolean
}

// Alert Configuration Modal Component
function AlertConfigurationModal({
  anomaly,
  existingAlert,
  mode = 'create',
  onClose,
  onSave
}: {
  anomaly?: Anomaly | null
  existingAlert?: AlertRule | null
  mode?: 'create' | 'edit' | 'duplicate'
  onClose: () => void
  onSave: (rule: AlertRule, isEdit: boolean) => void
}) {
  const [isSaving, setIsSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Initialize alert rule based on mode
  const getInitialAlertRule = (): AlertRule => {
    if (existingAlert) {
      if (mode === 'duplicate') {
        return {
          ...existingAlert,
          id: undefined, // Remove ID for duplicate
          name: `Copy of ${existingAlert.name}`,
        }
      }
      return { ...existingAlert }
    }
    if (anomaly) {
      return {
        name: `${anomaly.metric} Alert`,
        metric: anomaly.metric || 'CTR',
        condition: anomaly.type === 'negative' ? 'below' : 'above',
        threshold: anomaly.expected || 0,
        frequency: 'realtime',
        channels: {
          email: true,
          whatsapp: false,
          inApp: true,
          slack: false,
        },
        enabled: true,
      }
    }
    return {
      name: 'New Alert',
      metric: 'CTR',
      condition: 'above',
      threshold: 0,
      frequency: 'realtime',
      channels: {
        email: true,
        whatsapp: false,
        inApp: true,
        slack: false,
      },
      enabled: true,
    }
  }

  const [alertRule, setAlertRule] = useState<AlertRule>(getInitialAlertRule())
  const [originalName] = useState(existingAlert?.name || '')

  if (!anomaly && !existingAlert) return null

  const handleSave = async () => {
    // Validate duplicate - must have changes
    if (mode === 'duplicate' && !hasChanges) {
      setError('Please modify the alert before saving. Duplicate rules are not allowed.')
      return
    }

    // Check if name is still the same as original for duplicates
    if (mode === 'duplicate' && alertRule.name === `Copy of ${originalName}`) {
      setError('Please change the alert name before saving.')
      return
    }

    setError(null)
    setIsSaving(true)
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500))
    onSave(alertRule, mode === 'edit')
    setIsSaving(false)
  }

  // Track changes for duplicate validation
  const handleFieldChange = (updates: Partial<AlertRule>) => {
    setAlertRule(prev => ({ ...prev, ...updates }))
    setHasChanges(true)
    setError(null)
  }

  const updateChannel = (channel: keyof AlertRule['channels']) => {
    setAlertRule(prev => ({
      ...prev,
      channels: {
        ...prev.channels,
        [channel]: !prev.channels[channel],
      }
    }))
    setHasChanges(true)
    setError(null)
  }

  const getModalTitle = () => {
    switch (mode) {
      case 'edit': return 'Edit Alert Rule'
      case 'duplicate': return 'Duplicate Alert Rule'
      default: return 'Create Alert Rule'
    }
  }

  const getButtonText = () => {
    switch (mode) {
      case 'edit': return 'Save Changes'
      case 'duplicate': return 'Create Duplicate'
      default: return 'Create Alert Rule'
    }
  }

  const metrics = [
    'CTR', 'CPA', 'CPC', 'CPM', 'ROAS', 'Conversions',
    'Impressions', 'Clicks', 'Spend', 'Revenue'
  ]

  const conditions = [
    { value: 'above', label: 'Goes above' },
    { value: 'below', label: 'Goes below' },
    { value: 'change_above', label: 'Changes by more than +' },
    { value: 'change_below', label: 'Changes by more than -' },
  ]

  const frequencies = [
    { value: 'realtime', label: 'Real-time', description: 'Instant notification' },
    { value: 'hourly', label: 'Hourly', description: 'Digest every hour' },
    { value: 'daily', label: 'Daily', description: 'Daily summary' },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal Panel */}
      <div className="relative w-full max-w-lg bg-background rounded-xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="border-b px-6 py-4 flex items-center justify-between bg-primary/5">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Bell className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-semibold text-lg">{getModalTitle()}</h2>
              <p className="text-xs text-muted-foreground">
                {mode === 'duplicate'
                  ? 'Modify the alert before saving'
                  : 'Get notified when metrics exceed thresholds'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5 max-h-[60vh] overflow-y-auto">
          {/* Error Message */}
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-500 text-sm">
              {error}
            </div>
          )}

          {/* Duplicate Warning */}
          {mode === 'duplicate' && (
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-600 text-sm">
              You must modify the alert name or settings before saving to avoid duplicate rules.
            </div>
          )}

          {/* Alert Name */}
          <div>
            <label className="block text-sm font-medium mb-2">Alert Name</label>
            <input
              type="text"
              value={alertRule.name}
              onChange={(e) => handleFieldChange({ name: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition-all"
              placeholder="e.g., CTR Drop Alert"
            />
          </div>

          {/* Metric Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Metric to Monitor</label>
            <select
              value={alertRule.metric}
              onChange={(e) => handleFieldChange({ metric: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition-all"
            >
              {metrics.map(metric => (
                <option key={metric} value={metric}>{metric}</option>
              ))}
            </select>
          </div>

          {/* Condition and Threshold */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Condition</label>
              <select
                value={alertRule.condition}
                onChange={(e) => handleFieldChange({
                  condition: e.target.value as AlertRule['condition']
                })}
                className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition-all"
              >
                {conditions.map(cond => (
                  <option key={cond.value} value={cond.value}>{cond.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">
                Threshold {alertRule.condition.includes('change') ? '(%)' : ''}
              </label>
              <input
                type="number"
                value={alertRule.threshold}
                onChange={(e) => handleFieldChange({
                  threshold: parseFloat(e.target.value) || 0
                })}
                className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition-all"
                step={alertRule.condition.includes('change') ? '1' : '0.1'}
              />
            </div>
          </div>

          {/* Alert Preview */}
          <div className="p-4 rounded-lg border bg-muted/50">
            <p className="text-sm text-muted-foreground mb-1">Alert will trigger when:</p>
            <p className="font-medium">
              {alertRule.metric}{' '}
              <span className="text-primary">
                {conditions.find(c => c.value === alertRule.condition)?.label.toLowerCase()}
              </span>{' '}
              <span className="text-primary font-bold">
                {alertRule.threshold}{alertRule.condition.includes('change') ? '%' : ''}
              </span>
            </p>
          </div>

          {/* Notification Frequency */}
          <div>
            <label className="block text-sm font-medium mb-2">Check Frequency</label>
            <div className="grid grid-cols-3 gap-2">
              {frequencies.map(freq => (
                <button
                  key={freq.value}
                  onClick={() => {
                    handleFieldChange({ frequency: freq.value as AlertRule['frequency'] })
                  }}
                  className={cn(
                    'p-3 rounded-lg border text-center transition-all',
                    alertRule.frequency === freq.value
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'hover:bg-muted'
                  )}
                >
                  <p className="font-medium text-sm">{freq.label}</p>
                  <p className="text-xs text-muted-foreground">{freq.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Notification Channels */}
          <div>
            <label className="block text-sm font-medium mb-2">Notification Channels</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => updateChannel('email')}
                className={cn(
                  'flex items-center gap-3 p-3 rounded-lg border transition-all',
                  alertRule.channels.email
                    ? 'border-primary bg-primary/10'
                    : 'hover:bg-muted'
                )}
              >
                <div className={cn(
                  'p-2 rounded-lg',
                  alertRule.channels.email ? 'bg-primary text-primary-foreground' : 'bg-muted'
                )}>
                  <Mail className="w-4 h-4" />
                </div>
                <div className="text-left">
                  <p className="font-medium text-sm">Email</p>
                  <p className="text-xs text-muted-foreground">Get email alerts</p>
                </div>
                {alertRule.channels.email && (
                  <CheckCircle2 className="w-4 h-4 text-primary ml-auto" />
                )}
              </button>

              <button
                onClick={() => updateChannel('whatsapp')}
                className={cn(
                  'flex items-center gap-3 p-3 rounded-lg border transition-all',
                  alertRule.channels.whatsapp
                    ? 'border-primary bg-primary/10'
                    : 'hover:bg-muted'
                )}
              >
                <div className={cn(
                  'p-2 rounded-lg',
                  alertRule.channels.whatsapp ? 'bg-green-500 text-white' : 'bg-muted'
                )}>
                  <MessageSquare className="w-4 h-4" />
                </div>
                <div className="text-left">
                  <p className="font-medium text-sm">WhatsApp</p>
                  <p className="text-xs text-muted-foreground">WhatsApp messages</p>
                </div>
                {alertRule.channels.whatsapp && (
                  <CheckCircle2 className="w-4 h-4 text-green-500 ml-auto" />
                )}
              </button>

              <button
                onClick={() => updateChannel('inApp')}
                className={cn(
                  'flex items-center gap-3 p-3 rounded-lg border transition-all',
                  alertRule.channels.inApp
                    ? 'border-primary bg-primary/10'
                    : 'hover:bg-muted'
                )}
              >
                <div className={cn(
                  'p-2 rounded-lg',
                  alertRule.channels.inApp ? 'bg-primary text-primary-foreground' : 'bg-muted'
                )}>
                  <Bell className="w-4 h-4" />
                </div>
                <div className="text-left">
                  <p className="font-medium text-sm">In-App</p>
                  <p className="text-xs text-muted-foreground">Push notifications</p>
                </div>
                {alertRule.channels.inApp && (
                  <CheckCircle2 className="w-4 h-4 text-primary ml-auto" />
                )}
              </button>

              <button
                onClick={() => updateChannel('slack')}
                className={cn(
                  'flex items-center gap-3 p-3 rounded-lg border transition-all',
                  alertRule.channels.slack
                    ? 'border-primary bg-primary/10'
                    : 'hover:bg-muted'
                )}
              >
                <div className={cn(
                  'p-2 rounded-lg',
                  alertRule.channels.slack ? 'bg-primary text-primary-foreground' : 'bg-muted'
                )}>
                  <MessageSquare className="w-4 h-4" />
                </div>
                <div className="text-left">
                  <p className="font-medium text-sm">Slack</p>
                  <p className="text-xs text-muted-foreground">Channel alerts</p>
                </div>
                {alertRule.channels.slack && (
                  <CheckCircle2 className="w-4 h-4 text-primary ml-auto" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="border-t px-6 py-4 flex items-center gap-3 bg-muted/30">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 rounded-lg border hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || !alertRule.name.trim()}
            className="flex-1 px-4 py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {mode === 'edit' ? 'Saving...' : 'Creating...'}
              </>
            ) : (
              <>
                <Bell className="w-4 h-4" />
                {getButtonText()}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export function Stratum() {
  const { t } = useTranslation()
  const [selectedTimeframe, setSelectedTimeframe] = useState('7d')
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(null)
  const [appliedInsights, setAppliedInsights] = useState<number[]>([])
  const [selectedAnomaly, setSelectedAnomaly] = useState<Anomaly | null>(null)
  const [reviewedAnomalies, setReviewedAnomalies] = useState<number[]>([])
  const [alertConfigAnomaly, setAlertConfigAnomaly] = useState<Anomaly | null>(null)
  const [editingAlert, setEditingAlert] = useState<AlertRule | null>(null)
  const [alertModalMode, setAlertModalMode] = useState<'create' | 'edit' | 'duplicate'>('create')
  const [createdAlerts, setCreatedAlerts] = useState<AlertRule[]>([])

  // Get tenant ID from tenant store
  const tenantId = useTenantStore((state) => state.tenantId) ?? 1

  // Fetch data from API
  const { data: insightsData, isLoading: insightsLoading, refetch: refetchInsights } = useInsights(tenantId)
  const { data: recommendationsData } = useRecommendations(tenantId)
  const { data: anomaliesData, isLoading: anomaliesLoading } = useAnomalies(tenantId)
  const { data: predictionsData } = useLivePredictions(tenantId)

  // Transform API insights or fall back to mock
  const insights = useMemo(() => {
    if (insightsData?.items && insightsData.items.length > 0) {
      return insightsData.items.slice(0, 3).map((i: any, idx: number) => ({
        id: i.id || idx + 1,
        type: i.type || i.insight_type || 'suggestion',
        priority: i.priority || 'medium',
        title: i.title || '',
        description: i.description || '',
        impact: i.impact || i.expected_impact || '+$0 estimated',
        campaign: i.campaign || i.campaign_name || 'All campaigns',
      }))
    }
    return []
  }, [insightsData])

  // Transform API anomalies or fall back to mock
  const anomalies = useMemo(() => {
    if (anomaliesData?.items && anomaliesData.items.length > 0) {
      return anomaliesData.items.slice(0, 3).map((a: any) => ({
        date: new Date(a.detected_at || a.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        metric: a.metric || a.metric_name || 'Unknown',
        value: a.actual_value || a.value || 0,
        expected: a.expected_value || a.expected || 0,
        deviation: a.deviation ? `${a.deviation > 0 ? '+' : ''}${(a.deviation * 100).toFixed(0)}%` : '0%',
        type: a.is_positive || a.type === 'positive' ? 'positive' : 'negative',
      }))
    }
    return []
  }, [anomaliesData])

  // Handle refresh
  const handleRefresh = () => {
    refetchInsights()
  }

  // Handle insight card click
  const handleInsightClick = (insight: Insight) => {
    setSelectedInsight(insight)
  }

  // Handle apply recommendation
  const handleApplyRecommendation = (insight: Insight) => {
    setAppliedInsights(prev => [...prev, insight.id])
    setSelectedInsight(null)
    // Here you would typically make an API call to apply the recommendation
    // For now, we just track it locally
  }

  // Handle anomaly card click
  const handleAnomalyClick = (anomaly: Anomaly) => {
    setSelectedAnomaly(anomaly)
  }

  // Handle anomaly action
  const handleAnomalyAction = (anomaly: Anomaly, action: string) => {
    if (action === 'reviewed') {
      setReviewedAnomalies(prev => [...prev, anomaly.id])
      setSelectedAnomaly(null)
    } else if (action === 'alert') {
      // Close anomaly modal and open alert configuration modal
      setSelectedAnomaly(null)
      setAlertConfigAnomaly(anomaly)
    }
  }

  // Handle alert rule save
  const handleSaveAlertRule = (rule: AlertRule, isEdit: boolean) => {
    if (isEdit && rule.id) {
      // Update existing alert
      setCreatedAlerts(prev => prev.map(alert =>
        alert.id === rule.id ? rule : alert
      ))
      console.log('Alert rule updated:', rule)
    } else {
      // Create new alert
      const ruleWithId = { ...rule, id: `alert-${Date.now()}` }
      setCreatedAlerts(prev => [...prev, ruleWithId])
      console.log('Alert rule created:', ruleWithId)
    }
    // Close modal and reset state
    setAlertConfigAnomaly(null)
    setEditingAlert(null)
    setAlertModalMode('create')
  }

  // Handle edit alert
  const handleEditAlert = (alert: AlertRule) => {
    setEditingAlert(alert)
    setAlertModalMode('edit')
  }

  // Handle duplicate alert
  const handleDuplicateAlert = (alert: AlertRule) => {
    setEditingAlert(alert)
    setAlertModalMode('duplicate')
  }

  // Handle toggle alert enabled/disabled
  const handleToggleAlert = (alertId: string) => {
    setCreatedAlerts(prev => prev.map(alert =>
      alert.id === alertId ? { ...alert, enabled: !alert.enabled } : alert
    ))
  }

  // Handle delete alert
  const handleDeleteAlert = (alertId: string) => {
    setCreatedAlerts(prev => prev.filter(alert => alert.id !== alertId))
  }

  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'opportunity':
        return <Lightbulb className="w-5 h-5 text-green-500" />
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-amber-500" />
      case 'suggestion':
        return <Sparkles className="w-5 h-5 text-primary" />
      default:
        return <Brain className="w-5 h-5" />
    }
  }

  const getPriorityBadge = (priority: string) => {
    const styles = {
      high: 'bg-red-500/10 text-red-500',
      medium: 'bg-amber-500/10 text-amber-500',
      low: 'bg-blue-500/10 text-blue-500',
    }
    return (
      <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', styles[priority as keyof typeof styles])}>
        {priority.charAt(0).toUpperCase() + priority.slice(1)}
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Brain className="w-7 h-7 text-primary" />
            {t('stratum.title')}
          </h1>
          <p className="text-muted-foreground">{t('stratum.subtitle')}</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex rounded-lg border overflow-hidden">
            {['24h', '7d', '30d', '90d'].map((tf) => (
              <button
                key={tf}
                onClick={() => setSelectedTimeframe(tf)}
                className={cn(
                  'px-4 py-2 text-sm transition-colors',
                  selectedTimeframe === tf
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-muted'
                )}
              >
                {tf}
              </button>
            ))}
          </div>
          <button
            onClick={handleRefresh}
            disabled={insightsLoading}
            className="p-2 rounded-lg border hover:bg-muted transition-colors disabled:opacity-50"
          >
            {insightsLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          </button>
          <button className="p-2 rounded-lg border hover:bg-muted transition-colors">
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* AI Insights */}
      <div className="rounded-xl border bg-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            {t('stratum.aiInsights')}
          </h3>
          <button className="text-sm text-primary hover:underline">
            {t('common.viewAll')}
          </button>
        </div>

        {insightsLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
            <span className="ml-2 text-sm text-muted-foreground">Loading insights...</span>
          </div>
        ) : insights.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {insights.map((insight) => {
              const isApplied = appliedInsights.includes(insight.id)
              return (
                <div
                  key={insight.id}
                  onClick={() => !isApplied && handleInsightClick(insight as Insight)}
                  className={cn(
                    'p-4 rounded-lg border bg-background transition-all cursor-pointer',
                    isApplied
                      ? 'opacity-60 cursor-default border-green-500/50'
                      : 'hover:shadow-md hover:border-primary/50'
                  )}
                >
                  <div className="flex items-start justify-between mb-2">
                    {isApplied ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500" />
                    ) : (
                      getInsightIcon(insight.type)
                    )}
                    {isApplied ? (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-500">
                        Applied
                      </span>
                    ) : (
                      getPriorityBadge(insight.priority)
                    )}
                  </div>
                  <h4 className="font-medium text-sm mb-1">{insight.title}</h4>
                  <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
                    {insight.description}
                  </p>
                  <div className="flex items-center justify-between">
                    <span
                      className={cn(
                        'text-xs font-medium',
                        insight.impact.startsWith('+') ? 'text-green-500' : 'text-red-500'
                      )}
                    >
                      {insight.impact}
                    </span>
                    {!isApplied && <ArrowRight className="w-4 h-4 text-muted-foreground" />}
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Sparkles className="w-10 h-10 text-muted-foreground/40 mb-3" />
            <p className="text-sm text-muted-foreground">No insights available yet.</p>
          </div>
        )}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Revenue Forecast */}
        <div className="lg:col-span-2 rounded-xl border bg-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold">{t('stratum.revenueForecast')}</h3>
              <p className="text-xs text-muted-foreground">
                {t('stratum.forecastDescription')}
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-primary" />
                <span className="text-muted-foreground">Actual</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-muted-foreground">Predicted</span>
              </div>
            </div>
          </div>

          <div className="h-[300px]">
            {predictionsData?.items?.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={predictionsData.items.map((item: any) => ({
                  date: item.date,
                  actual: item.actual ?? item.actual_value ?? null,
                  predicted: item.predicted ?? item.predicted_value ?? null,
                  lowerBound: item.lowerBound ?? item.lower_bound ?? null,
                  upperBound: item.upperBound ?? item.upper_bound ?? null,
                }))}>
                  <defs>
                    <linearGradient id="colorPredicted" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value) => `$${formatCompactNumber(value)}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '0.5rem',
                    }}
                    formatter={(value: number) => [formatCurrency(value), '']}
                  />
                  {/* Confidence interval */}
                  <Area
                    type="monotone"
                    dataKey="upperBound"
                    stroke="transparent"
                    fill="#10b981"
                    fillOpacity={0.1}
                  />
                  <Area
                    type="monotone"
                    dataKey="lowerBound"
                    stroke="transparent"
                    fill="#fff"
                    fillOpacity={1}
                  />
                  {/* Predicted line */}
                  <Line
                    type="monotone"
                    dataKey="predicted"
                    stroke="#10b981"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                  />
                  {/* Actual line */}
                  <Line
                    type="monotone"
                    dataKey="actual"
                    stroke="#0ea5e9"
                    strokeWidth={2}
                    dot={{ fill: '#0ea5e9', strokeWidth: 0, r: 3 }}
                    connectNulls={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-6">
                <TrendingUp className="w-10 h-10 text-muted-foreground/40 mb-3" />
                <p className="text-sm text-muted-foreground max-w-xs">
                  No forecast data available yet. Connect your ad platforms to see AI-powered revenue predictions.
                </p>
              </div>
            )}
          </div>

          <div className="mt-4 grid grid-cols-3 gap-4 pt-4 border-t">
            <div>
              <p className="text-xs text-muted-foreground">{t('stratum.forecastedRevenue')}</p>
              <p className="text-lg font-semibold">$156,890</p>
              <p className="text-xs text-green-500">+12.4% vs last period</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">{t('stratum.confidence')}</p>
              <p className="text-lg font-semibold">87%</p>
              <p className="text-xs text-muted-foreground">High confidence</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">{t('stratum.modelAccuracy')}</p>
              <p className="text-lg font-semibold">94.2%</p>
              <p className="text-xs text-muted-foreground">Last 30 days</p>
            </div>
          </div>
        </div>

        {/* What-If Simulator */}
        <SimulateSlider />
      </div>

      {/* Second Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Attribution Model */}
        <div className="rounded-xl border bg-card p-5">
          <h3 className="font-semibold mb-4">{t('stratum.attributionModel')}</h3>
          {([] as Array<{ name: string; value: number; color: string }>).length > 0 ? (
            <div className="flex items-center gap-6">
              <div className="w-48 h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={[]}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {([] as Array<{ name: string; value: number; color: string }>).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '0.5rem',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex-1 space-y-3">
                {([] as Array<{ name: string; value: number; color: string }>).map((item) => (
                  <div key={item.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: item.color }}
                      />
                      <span className="text-sm">{item.name}</span>
                    </div>
                    <span className="font-medium">{item.value}%</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-48 flex flex-col items-center justify-center text-center p-6">
              <Target className="w-10 h-10 text-muted-foreground/40 mb-3" />
              <p className="text-sm text-muted-foreground max-w-xs">
                No attribution data available yet. Attribution insights will appear once campaign data is collected.
              </p>
            </div>
          )}
        </div>

        {/* Anomaly Detection */}
        <div className="rounded-xl border bg-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">{t('stratum.anomalyDetection')}</h3>
            <span className="text-xs text-muted-foreground">Last 7 days</span>
          </div>

          {anomaliesLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span className="ml-2 text-sm text-muted-foreground">Loading anomalies...</span>
            </div>
          ) : anomalies.length > 0 ? (
            <div className="space-y-3">
              {anomalies.map((anomaly, i) => {
                const isReviewed = reviewedAnomalies.includes(anomaly.id)
                return (
                  <div
                    key={anomaly.id || i}
                    onClick={() => !isReviewed && handleAnomalyClick(anomaly as Anomaly)}
                    className={cn(
                      'p-3 rounded-lg border-l-4 transition-all',
                      anomaly.type === 'positive'
                        ? 'bg-green-500/10 border-green-500'
                        : 'bg-red-500/10 border-red-500',
                      isReviewed
                        ? 'opacity-60 cursor-default'
                        : 'cursor-pointer hover:shadow-md'
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {isReviewed ? (
                          <CheckCircle2 className="w-4 h-4 text-muted-foreground" />
                        ) : anomaly.type === 'positive' ? (
                          <CheckCircle2 className="w-4 h-4 text-green-500" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-red-500" />
                        )}
                        <span className="font-medium text-sm">{anomaly.metric}</span>
                        {isReviewed && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-muted text-muted-foreground">
                            Reviewed
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">{anomaly.date}</span>
                        {!isReviewed && <ArrowRight className="w-3 h-3 text-muted-foreground" />}
                      </div>
                    </div>
                    <div className="mt-2 flex items-center justify-between text-sm">
                      <div>
                        <span className="text-muted-foreground">Actual: </span>
                        <span className="font-medium">{anomaly.value}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Expected: </span>
                        <span className="font-medium">{anomaly.expected}</span>
                      </div>
                      <span
                        className={cn(
                          'font-semibold',
                          anomaly.type === 'positive' ? 'text-green-500' : 'text-red-500'
                        )}
                      >
                      {anomaly.deviation}
                    </span>
                  </div>
                </div>
                )
              })}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <AlertTriangle className="w-10 h-10 text-muted-foreground/40 mb-3" />
              <p className="text-sm text-muted-foreground">No anomalies detected recently.</p>
            </div>
          )}
        </div>
      </div>

      {/* Active Alerts Section */}
      {createdAlerts.length > 0 && (
        <div className="rounded-xl border bg-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold flex items-center gap-2">
              <Bell className="w-5 h-5 text-primary" />
              Active Alerts
              <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-medium">
                {createdAlerts.length}
              </span>
            </h3>
          </div>

          <div className="space-y-3">
            {createdAlerts.map((alert) => {
              const conditionLabel = {
                above: 'goes above',
                below: 'goes below',
                change_above: 'changes by more than +',
                change_below: 'changes by more than -',
              }[alert.condition]

              const activeChannels = Object.entries(alert.channels)
                .filter(([_, enabled]) => enabled)
                .map(([channel]) => channel)

              return (
                <div
                  key={alert.id}
                  className={cn(
                    'p-4 rounded-lg border transition-all',
                    alert.enabled ? 'bg-background' : 'bg-muted/50 opacity-60'
                  )}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-medium text-sm truncate">{alert.name}</h4>
                        <span className={cn(
                          'px-2 py-0.5 rounded-full text-xs font-medium',
                          alert.enabled ? 'bg-green-500/10 text-green-500' : 'bg-muted text-muted-foreground'
                        )}>
                          {alert.enabled ? 'Active' : 'Paused'}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        <span className="font-medium text-foreground">{alert.metric}</span>
                        {' '}{conditionLabel}{' '}
                        <span className="font-medium text-foreground">
                          {alert.threshold}{alert.condition.includes('change') ? '%' : ''}
                        </span>
                      </p>
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {alert.frequency === 'realtime' ? 'Real-time' :
                           alert.frequency === 'hourly' ? 'Hourly' : 'Daily'}
                        </span>
                        <div className="flex items-center gap-1">
                          {activeChannels.map(channel => (
                            <span
                              key={channel}
                              className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-muted capitalize"
                            >
                              {channel === 'inApp' ? 'In-App' : channel}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleEditAlert(alert)
                        }}
                        className="px-3 py-1.5 rounded-lg text-xs font-medium border border-primary/30 text-primary bg-primary/10 hover:bg-primary/20 transition-colors"
                      >
                        Edit
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDuplicateAlert(alert)
                        }}
                        className="px-3 py-1.5 rounded-lg text-xs font-medium border border-blue-500/30 text-blue-500 bg-blue-500/10 hover:bg-blue-500/20 transition-colors"
                      >
                        Duplicate
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleToggleAlert(alert.id!)
                        }}
                        className={cn(
                          'px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors',
                          alert.enabled
                            ? 'bg-green-500/10 text-green-600 border-green-500/30 hover:bg-green-500/20'
                            : 'bg-muted text-muted-foreground border-muted hover:bg-muted/80'
                        )}
                      >
                        {alert.enabled ? 'Pause' : 'Resume'}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteAlert(alert.id!)
                        }}
                        className="px-3 py-1.5 rounded-lg text-xs font-medium border border-red-500/30 text-red-500 bg-red-500/10 hover:bg-red-500/20 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Insight Detail Modal */}
      {selectedInsight && (
        <InsightDetailModal
          insight={selectedInsight}
          onClose={() => setSelectedInsight(null)}
          onApply={handleApplyRecommendation}
        />
      )}

      {/* Anomaly Detail Modal */}
      {selectedAnomaly && (
        <AnomalyDetailModal
          anomaly={selectedAnomaly}
          onClose={() => setSelectedAnomaly(null)}
          onAction={handleAnomalyAction}
        />
      )}

      {/* Alert Configuration Modal */}
      {(alertConfigAnomaly || editingAlert) && (
        <AlertConfigurationModal
          anomaly={alertConfigAnomaly}
          existingAlert={editingAlert}
          mode={alertModalMode}
          onClose={() => {
            setAlertConfigAnomaly(null)
            setEditingAlert(null)
            setAlertModalMode('create')
          }}
          onSave={handleSaveAlertRule}
        />
      )}
    </div>
  )
}

export default Stratum
