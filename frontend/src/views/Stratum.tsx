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
} from 'lucide-react'
import { cn, formatCurrency, formatPercent, formatCompactNumber } from '@/lib/utils'
import { SimulateSlider } from '@/components/widgets/SimulateSlider'
import { useInsights, useRecommendations, useAnomalies, useLivePredictions } from '@/api/hooks'
import { useTenantStore } from '@/stores/tenantStore'

// Mock AI insights with extended details
const mockInsights = [
  {
    id: 1,
    type: 'opportunity',
    priority: 'high',
    title: 'High-performing audience segment identified',
    description: 'Users aged 25-34 in urban areas show 45% higher conversion rate. Consider increasing budget allocation.',
    impact: '+$12,500 estimated monthly revenue',
    campaign: 'Summer Sale 2024',
    // Extended details for modal
    fullDescription: 'Our AI analysis has identified a high-value audience segment that is significantly outperforming other demographics. Users aged 25-34 in urban metropolitan areas are converting at 4.2% compared to the campaign average of 2.9%. This segment also shows higher average order values ($127 vs $89) and lower cost per acquisition ($18 vs $31).',
    metrics: {
      conversionRate: { current: 4.2, average: 2.9, change: 45 },
      avgOrderValue: { current: 127, average: 89, change: 43 },
      cpa: { current: 18, average: 31, change: -42 },
      audienceSize: 245000,
      potentialReach: 890000,
    },
    recommendations: [
      'Increase budget allocation by 30% for this segment',
      'Create dedicated ad creatives for urban millennials',
      'Test lookalike audiences based on this segment',
      'Implement retargeting campaigns for non-converters',
    ],
    historicalData: [
      { date: 'Week 1', performance: 2.8 },
      { date: 'Week 2', performance: 3.1 },
      { date: 'Week 3', performance: 3.6 },
      { date: 'Week 4', performance: 4.2 },
    ],
    confidence: 92,
    detectedAt: '2 hours ago',
  },
  {
    id: 2,
    type: 'warning',
    priority: 'medium',
    title: 'Creative fatigue detected',
    description: 'Banner "Summer_v3" has been shown 2.3M times. CTR dropped 23% in the last 7 days.',
    impact: '-$3,200 estimated loss if unchanged',
    campaign: 'Brand Awareness Q4',
    fullDescription: 'The creative asset "Summer_v3" has reached saturation with your target audience. Frequency has exceeded optimal levels (7.2 vs recommended 4.0), and engagement metrics are declining rapidly. Immediate creative refresh is recommended to prevent further performance degradation.',
    metrics: {
      impressions: { current: 2300000, threshold: 1500000, change: 53 },
      ctr: { current: 1.8, previous: 2.3, change: -23 },
      frequency: { current: 7.2, optimal: 4.0, change: 80 },
      estimatedLoss: 3200,
    },
    recommendations: [
      'Pause current creative immediately',
      'Rotate in 2-3 new creative variants',
      'A/B test new creatives with fresh audiences',
      'Set up automated creative rotation rules',
    ],
    historicalData: [
      { date: 'Week 1', performance: 2.4 },
      { date: 'Week 2', performance: 2.3 },
      { date: 'Week 3', performance: 2.1 },
      { date: 'Week 4', performance: 1.8 },
    ],
    confidence: 88,
    detectedAt: '6 hours ago',
  },
  {
    id: 3,
    type: 'suggestion',
    priority: 'low',
    title: 'Optimal bidding time identified',
    description: 'Historical data shows 18% better CPC between 6-9 PM. Consider dayparting adjustments.',
    impact: '+$890 estimated monthly savings',
    campaign: 'All campaigns',
    fullDescription: 'Analysis of 90 days of bidding data reveals consistent patterns in cost efficiency. Evening hours (6-9 PM local time) show significantly lower competition and better conversion rates. Implementing dayparting could reduce your overall CPC while maintaining conversion volume.',
    metrics: {
      cpcPeak: { current: 2.45, offPeak: 2.01, savings: 18 },
      conversionsPeak: { current: 312, projected: 298, change: -4 },
      monthlySavings: 890,
      optimalHours: '6PM - 9PM',
    },
    recommendations: [
      'Increase bids by 15% during 6-9 PM',
      'Reduce bids by 20% during 2-5 AM',
      'Set up automated dayparting rules',
      'Monitor for 2 weeks before full rollout',
    ],
    historicalData: [
      { date: '6AM', performance: 2.8 },
      { date: '12PM', performance: 2.4 },
      { date: '6PM', performance: 2.0 },
      { date: '9PM', performance: 2.1 },
    ],
    confidence: 76,
    detectedAt: '1 day ago',
  },
]

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

// Mock prediction data
const mockPredictionData = Array.from({ length: 14 }, (_, i) => {
  const date = new Date()
  date.setDate(date.getDate() + i - 7)
  const isPast = i < 7
  return {
    date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    actual: isPast ? 4500 + Math.random() * 1500 + i * 100 : null,
    predicted: 4200 + Math.random() * 800 + i * 150,
    lowerBound: 3800 + Math.random() * 500 + i * 120,
    upperBound: 4800 + Math.random() * 800 + i * 180,
  }
})

// Mock attribution data
const mockAttributionData = [
  { name: 'First Touch', value: 35, color: '#0ea5e9' },
  { name: 'Last Touch', value: 28, color: '#10b981' },
  { name: 'Linear', value: 22, color: '#f59e0b' },
  { name: 'Time Decay', value: 15, color: '#8b5cf6' },
]

// Mock anomaly data with extended details
const mockAnomalies = [
  {
    id: 1,
    date: 'Nov 28',
    metric: 'CTR',
    value: 4.2,
    expected: 2.8,
    deviation: '+50%',
    type: 'positive',
    // Extended details
    fullDescription: 'Click-through rate spiked significantly above the expected baseline. This anomaly was detected across multiple ad groups in your "Summer Sale 2024" campaign. The spike correlates with a viral social media mention of your brand.',
    campaign: 'Summer Sale 2024',
    adGroup: 'Urban Millennials',
    platform: 'Meta',
    severity: 'high',
    historicalData: [
      { date: 'Nov 22', value: 2.6 },
      { date: 'Nov 23', value: 2.7 },
      { date: 'Nov 24', value: 2.9 },
      { date: 'Nov 25', value: 2.8 },
      { date: 'Nov 26', value: 3.1 },
      { date: 'Nov 27', value: 3.4 },
      { date: 'Nov 28', value: 4.2 },
    ],
    possibleCauses: [
      'Viral social media mention detected on Twitter/X',
      'Competitor went offline during this period',
      'New creative variant showing strong engagement',
      'Seasonal trend alignment',
    ],
    suggestedActions: [
      'Scale budget by 25% to capitalize on momentum',
      'Create lookalike audience from engaged users',
      'Document successful creative for future campaigns',
      'Set up automated scaling rules for similar events',
    ],
    relatedMetrics: {
      impressions: { value: 125000, change: 12 },
      clicks: { value: 5250, change: 68 },
      conversions: { value: 312, change: 45 },
      spend: { value: 2450, change: 15 },
    },
    detectedAt: '2 hours ago',
    confidence: 94,
  },
  {
    id: 2,
    date: 'Nov 26',
    metric: 'CPA',
    value: 28.5,
    expected: 18.2,
    deviation: '+56%',
    type: 'negative',
    fullDescription: 'Cost per acquisition increased sharply, indicating potential issues with audience targeting or ad relevance. This spike occurred primarily in the "Brand Awareness Q4" campaign, specifically in the retargeting ad group.',
    campaign: 'Brand Awareness Q4',
    adGroup: 'Retargeting - Cart Abandoners',
    platform: 'Google Ads',
    severity: 'critical',
    historicalData: [
      { date: 'Nov 20', value: 17.8 },
      { date: 'Nov 21', value: 18.1 },
      { date: 'Nov 22', value: 18.5 },
      { date: 'Nov 23', value: 19.2 },
      { date: 'Nov 24', value: 22.1 },
      { date: 'Nov 25', value: 25.3 },
      { date: 'Nov 26', value: 28.5 },
    ],
    possibleCauses: [
      'Audience fatigue in retargeting segment',
      'Increased competition during Black Friday period',
      'Landing page performance degradation detected',
      'Ad relevance score dropped from 8 to 5',
    ],
    suggestedActions: [
      'Pause underperforming ad groups immediately',
      'Refresh creative assets in retargeting campaigns',
      'Review and optimize landing page load time',
      'Adjust bid strategy to target CPA mode',
    ],
    relatedMetrics: {
      impressions: { value: 89000, change: -5 },
      clicks: { value: 1890, change: -18 },
      conversions: { value: 66, change: -34 },
      spend: { value: 1881, change: 8 },
    },
    detectedAt: '1 day ago',
    confidence: 89,
  },
  {
    id: 3,
    date: 'Nov 24',
    metric: 'Conversions',
    value: 156,
    expected: 89,
    deviation: '+75%',
    type: 'positive',
    fullDescription: 'Conversion volume exceeded expectations by a significant margin. This surge was driven by strong performance in the "Holiday Promotions" campaign, particularly from email retargeting and organic search traffic.',
    campaign: 'Holiday Promotions',
    adGroup: 'Email Retargeting',
    platform: 'Multi-channel',
    severity: 'medium',
    historicalData: [
      { date: 'Nov 18', value: 78 },
      { date: 'Nov 19', value: 82 },
      { date: 'Nov 20', value: 85 },
      { date: 'Nov 21', value: 91 },
      { date: 'Nov 22', value: 112 },
      { date: 'Nov 23', value: 134 },
      { date: 'Nov 24', value: 156 },
    ],
    possibleCauses: [
      'Black Friday early access promotion launched',
      'Email campaign achieved 45% open rate',
      'Organic search rankings improved for key terms',
      'Referral traffic spike from partner website',
    ],
    suggestedActions: [
      'Extend promotion period by 48 hours',
      'Increase inventory allocation for top products',
      'Send follow-up email to engaged non-converters',
      'Document winning email subject lines',
    ],
    relatedMetrics: {
      impressions: { value: 234000, change: 28 },
      clicks: { value: 12400, change: 42 },
      revenue: { value: 18720, change: 82 },
      roas: { value: 4.8, change: 35 },
    },
    detectedAt: '3 days ago',
    confidence: 91,
  },
]

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

export function Stratum() {
  const { t } = useTranslation()
  const [selectedTimeframe, setSelectedTimeframe] = useState('7d')
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(null)
  const [appliedInsights, setAppliedInsights] = useState<number[]>([])
  const [selectedAnomaly, setSelectedAnomaly] = useState<Anomaly | null>(null)
  const [reviewedAnomalies, setReviewedAnomalies] = useState<number[]>([])

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
    return mockInsights
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
    return mockAnomalies
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
    }
    setSelectedAnomaly(null)
    // Here you would typically make an API call to create alert rule or mark as reviewed
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
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockPredictionData}>
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
          <div className="flex items-center gap-6">
            <div className="w-48 h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={mockAttributionData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {mockAttributionData.map((entry, index) => (
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
              {mockAttributionData.map((item) => (
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
        </div>

        {/* Anomaly Detection */}
        <div className="rounded-xl border bg-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">{t('stratum.anomalyDetection')}</h3>
            <span className="text-xs text-muted-foreground">Last 7 days</span>
          </div>

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
        </div>
      </div>

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
    </div>
  )
}

export default Stratum
