import { useState } from 'react'
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
} from 'lucide-react'
import { cn, formatCurrency, formatPercent, formatCompactNumber } from '@/lib/utils'
import { SimulateSlider } from '@/components/widgets/SimulateSlider'
import { SmartTooltip } from '@/components/guide/SmartTooltip'
import { InfoIcon } from '@/components/ui/InfoIcon'

// Mock AI insights
const mockInsights = [
  {
    id: 1,
    type: 'opportunity',
    priority: 'high',
    title: 'High-performing audience segment identified',
    description: 'Users aged 25-34 in urban areas show 45% higher conversion rate. Consider increasing budget allocation.',
    impact: '+$12,500 estimated monthly revenue',
    campaign: 'Summer Sale 2024',
  },
  {
    id: 2,
    type: 'warning',
    priority: 'medium',
    title: 'Creative fatigue detected',
    description: 'Banner "Summer_v3" has been shown 2.3M times. CTR dropped 23% in the last 7 days.',
    impact: '-$3,200 estimated loss if unchanged',
    campaign: 'Brand Awareness Q4',
  },
  {
    id: 3,
    type: 'suggestion',
    priority: 'low',
    title: 'Optimal bidding time identified',
    description: 'Historical data shows 18% better CPC between 6-9 PM. Consider dayparting adjustments.',
    impact: '+$890 estimated monthly savings',
    campaign: 'All campaigns',
  },
]

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

// Mock anomaly data
const mockAnomalies = [
  { date: 'Nov 28', metric: 'CTR', value: 4.2, expected: 2.8, deviation: '+50%', type: 'positive' },
  { date: 'Nov 26', metric: 'CPA', value: 28.5, expected: 18.2, deviation: '+56%', type: 'negative' },
  { date: 'Nov 24', metric: 'Conversions', value: 156, expected: 89, deviation: '+75%', type: 'positive' },
]

export function Stratum() {
  const { t } = useTranslation()
  const [selectedTimeframe, setSelectedTimeframe] = useState('7d')

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
          <button className="p-2 rounded-lg border hover:bg-muted transition-colors">
            <RefreshCw className="w-4 h-4" />
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
          {mockInsights.map((insight) => (
            <div
              key={insight.id}
              className="p-4 rounded-lg border bg-background hover:shadow-md transition-shadow cursor-pointer"
            >
              <div className="flex items-start justify-between mb-2">
                {getInsightIcon(insight.type)}
                {getPriorityBadge(insight.priority)}
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
                <ArrowRight className="w-4 h-4 text-muted-foreground" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Revenue Forecast */}
        <div className="lg:col-span-2 rounded-xl border bg-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold">{t('stratum.revenueForecast')}</h3>
                <SmartTooltip
                  content="AI-powered revenue predictions based on historical trends. Shaded area shows confidence interval for forecasted values."
                  position="right"
                  trigger="click"
                >
                  <InfoIcon size={14} aria-label="Revenue forecast information" />
                </SmartTooltip>
              </div>
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
          <div className="flex items-center gap-2 mb-4">
            <h3 className="font-semibold">{t('stratum.attributionModel')}</h3>
            <SmartTooltip
              content="Shows how credit for conversions is distributed across different attribution models. Compare first-touch, last-touch, linear, and time decay approaches."
              position="right"
              trigger="click"
            >
              <InfoIcon size={14} aria-label="Attribution model information" />
            </SmartTooltip>
          </div>
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
            <div className="flex items-center gap-2">
              <h3 className="font-semibold">{t('stratum.anomalyDetection')}</h3>
              <SmartTooltip
                content="AI-detected unusual metric values. Green indicates positive anomalies (outperformance), red indicates negative anomalies requiring attention."
                position="right"
                trigger="click"
              >
                <InfoIcon size={14} aria-label="Anomaly detection information" />
              </SmartTooltip>
            </div>
            <span className="text-xs text-muted-foreground">Last 7 days</span>
          </div>

          <div className="space-y-3">
            {mockAnomalies.map((anomaly, i) => (
              <div
                key={i}
                className={cn(
                  'p-3 rounded-lg border-l-4',
                  anomaly.type === 'positive'
                    ? 'bg-green-500/10 border-green-500'
                    : 'bg-red-500/10 border-red-500'
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {anomaly.type === 'positive' ? (
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-red-500" />
                    )}
                    <span className="font-medium text-sm">{anomaly.metric}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">{anomaly.date}</span>
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
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Stratum
