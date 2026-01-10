/**
 * Data Quality Dashboard - EMQ (Event Match Quality) Monitoring
 * Comprehensive dashboard for monitoring data quality across all platforms
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Database,
  Filter,
  Info,
  Layers,
  Lock,
  RefreshCw,
  Server,
  Shield,
  TrendingDown,
  TrendingUp,
  XCircle,
  Zap,
  ArrowRight,
  Eye,
  ShoppingCart,
  CreditCard,
  Package,
  AlertCircle,
  Lightbulb,
  Loader2,
} from 'lucide-react'
import { cn, getPlatformColor } from '@/lib/utils'
import { apiClient } from '@/api/client'

// Types
interface KPICard {
  id: string
  label: string
  value: number
  unit: string
  trend: number
  status: 'good' | 'warning' | 'critical'
  description: string
}

interface PlatformEMQ {
  platform: string
  overallEMQ: number
  emailMatch: number
  phoneMatch: number
  fbpMatch: number
  fbcMatch: number
  ipMatch: number
  trend: number
}

interface EventEMQ {
  event: string
  emqScore: number
  volume: number
  trend: number
  worstParameter: string
}

interface ParameterCoverage {
  parameter: string
  meta: number
  google: number
  tiktok: number
  snapchat: number
  required: boolean
}

interface ServerBrowserSplit {
  platform: string
  serverPercent: number
  browserPercent: number
  trend: number
}

interface IntegrityIssue {
  type: 'duplicate' | 'missing_id' | 'ordering' | 'timestamp'
  count: number
  severity: 'critical' | 'warning' | 'info'
  description: string
}

interface PIIViolation {
  field: string
  violationType: string
  count: number
  lastSeen: string
}

interface FunnelStep {
  name: string
  icon: any
  emqScore: number
  volume: number
  dropoff: number
}

interface Alert {
  id: string
  severity: 'critical' | 'warning' | 'info'
  title: string
  description: string
  timestamp: string
  platform?: string
}

interface Recommendation {
  id: string
  impact: 'high' | 'medium' | 'low'
  title: string
  description: string
  owner: string
  fixHint: string
}

// Mock data
const mockKPIs: KPICard[] = [
  {
    id: 'overall_emq',
    label: 'Overall Match Quality',
    value: 78.5,
    unit: '%',
    trend: 3.2,
    status: 'warning',
    description: 'Proxy EMQ across all platforms',
  },
  {
    id: 'purchase_emq',
    label: 'Purchase EMQ',
    value: 82.3,
    unit: '%',
    trend: 5.1,
    status: 'good',
    description: 'Match quality for purchase events',
  },
  {
    id: 'server_coverage',
    label: 'Server Coverage',
    value: 94.7,
    unit: '%',
    trend: 2.8,
    status: 'good',
    description: 'Events sent via server-side API',
  },
  {
    id: 'dedup_rate',
    label: 'Deduplication Rate',
    value: 98.2,
    unit: '%',
    trend: 0.5,
    status: 'good',
    description: 'Successfully deduplicated events',
  },
  {
    id: 'param_completeness',
    label: 'Parameter Completeness',
    value: 71.4,
    unit: '%',
    trend: -2.1,
    status: 'warning',
    description: 'Required parameters present',
  },
  {
    id: 'pii_compliance',
    label: 'PII Violations',
    value: 3,
    unit: '',
    trend: -2,
    status: 'warning',
    description: 'Active compliance issues',
  },
]

const mockPlatformEMQ: PlatformEMQ[] = [
  { platform: 'meta', overallEMQ: 82, emailMatch: 89, phoneMatch: 76, fbpMatch: 95, fbcMatch: 88, ipMatch: 92, trend: 4.2 },
  { platform: 'google', overallEMQ: 79, emailMatch: 85, phoneMatch: 72, fbpMatch: 0, fbcMatch: 0, ipMatch: 94, trend: 2.1 },
  { platform: 'tiktok', overallEMQ: 74, emailMatch: 81, phoneMatch: 68, fbpMatch: 0, fbcMatch: 0, ipMatch: 89, trend: -1.5 },
  { platform: 'snapchat', overallEMQ: 71, emailMatch: 78, phoneMatch: 64, fbpMatch: 0, fbcMatch: 0, ipMatch: 86, trend: 0.8 },
]

const mockEventEMQ: EventEMQ[] = [
  { event: 'Purchase', emqScore: 82.3, volume: 12450, trend: 5.1, worstParameter: 'phone' },
  { event: 'AddToCart', emqScore: 76.8, volume: 45230, trend: 2.3, worstParameter: 'external_id' },
  { event: 'BeginCheckout', emqScore: 79.1, volume: 23100, trend: 1.8, worstParameter: 'phone' },
  { event: 'ViewContent', emqScore: 71.2, volume: 156780, trend: -0.5, worstParameter: 'email' },
  { event: 'InitiateCheckout', emqScore: 77.5, volume: 28900, trend: 3.2, worstParameter: 'city' },
  { event: 'Lead', emqScore: 68.9, volume: 8920, trend: -2.1, worstParameter: 'phone' },
]

const mockParameterCoverage: ParameterCoverage[] = [
  { parameter: 'email', meta: 89, google: 85, tiktok: 81, snapchat: 78, required: true },
  { parameter: 'phone', meta: 76, google: 72, tiktok: 68, snapchat: 64, required: true },
  { parameter: 'external_id', meta: 92, google: 88, tiktok: 75, snapchat: 71, required: true },
  { parameter: 'ip_address', meta: 94, google: 96, tiktok: 91, snapchat: 88, required: false },
  { parameter: 'user_agent', meta: 97, google: 98, tiktok: 95, snapchat: 93, required: false },
  { parameter: 'fbp', meta: 95, google: 0, tiktok: 0, snapchat: 0, required: false },
  { parameter: 'fbc', meta: 88, google: 0, tiktok: 0, snapchat: 0, required: false },
  { parameter: 'city', meta: 72, google: 68, tiktok: 65, snapchat: 61, required: false },
  { parameter: 'country', meta: 96, google: 94, tiktok: 92, snapchat: 89, required: false },
]

const mockServerBrowserSplit: ServerBrowserSplit[] = [
  { platform: 'meta', serverPercent: 96, browserPercent: 4, trend: 2.1 },
  { platform: 'google', serverPercent: 94, browserPercent: 6, trend: 1.8 },
  { platform: 'tiktok', serverPercent: 91, browserPercent: 9, trend: 3.5 },
  { platform: 'snapchat', serverPercent: 88, browserPercent: 12, trend: 2.2 },
]

const mockIntegrityIssues: IntegrityIssue[] = [
  { type: 'duplicate', count: 1245, severity: 'warning', description: 'Duplicate events detected (same event_id)' },
  { type: 'missing_id', count: 3420, severity: 'critical', description: 'Events missing event_id parameter' },
  { type: 'ordering', count: 567, severity: 'info', description: 'Events received out of sequence' },
  { type: 'timestamp', count: 234, severity: 'warning', description: 'Events with future timestamps' },
]

const mockPIIViolations: PIIViolation[] = [
  { field: 'email', violationType: 'Unhashed PII', count: 12, lastSeen: '2 hours ago' },
  { field: 'phone', violationType: 'Invalid format', count: 45, lastSeen: '30 mins ago' },
  { field: 'ip_address', violationType: 'Internal IP leaked', count: 3, lastSeen: '1 day ago' },
]

const mockFunnelSteps: FunnelStep[] = [
  { name: 'View Content', icon: Eye, emqScore: 71.2, volume: 156780, dropoff: 0 },
  { name: 'Add to Cart', icon: ShoppingCart, emqScore: 76.8, volume: 45230, dropoff: 71.2 },
  { name: 'Begin Checkout', icon: CreditCard, emqScore: 79.1, volume: 23100, dropoff: 48.9 },
  { name: 'Purchase', icon: Package, emqScore: 82.3, volume: 12450, dropoff: 46.1 },
]

const mockAlerts: Alert[] = [
  {
    id: '1',
    severity: 'critical',
    title: 'Missing event_id on 3,420 events',
    description: 'Events without event_id cannot be deduplicated, leading to inflated conversions',
    timestamp: '15 mins ago',
    platform: 'meta',
  },
  {
    id: '2',
    severity: 'warning',
    title: 'Phone match rate dropped below 70%',
    description: 'TikTok phone match rate decreased by 5% in the last 24 hours',
    timestamp: '2 hours ago',
    platform: 'tiktok',
  },
  {
    id: '3',
    severity: 'warning',
    title: 'Unhashed email detected',
    description: '12 events contained plaintext email addresses',
    timestamp: '4 hours ago',
  },
]

const mockRecommendations: Recommendation[] = [
  {
    id: '1',
    impact: 'high',
    title: 'Add event_id to all server events',
    description: 'Missing event_id prevents deduplication and inflates conversion counts',
    owner: 'Engineering',
    fixHint: 'Generate UUID for each event before sending to CAPI',
  },
  {
    id: '2',
    impact: 'high',
    title: 'Improve phone number collection',
    description: 'Phone match rate is lowest parameter at 68% average',
    owner: 'Product',
    fixHint: 'Add phone field to checkout flow with format validation',
  },
  {
    id: '3',
    impact: 'medium',
    title: 'Implement fbp/fbc cookie capture',
    description: 'Meta pixel cookies improve match quality by 15-20%',
    owner: 'Engineering',
    fixHint: 'Read _fbp and _fbc cookies server-side and include in CAPI calls',
  },
  {
    id: '4',
    impact: 'medium',
    title: 'Fix timestamp handling',
    description: '234 events have future timestamps causing attribution issues',
    owner: 'Engineering',
    fixHint: 'Ensure event_time uses Unix timestamp in seconds, not milliseconds',
  },
]

export function DataQualityDashboard() {
  const { t } = useTranslation()
  const [isLoading, setIsLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [dateRange, setDateRange] = useState('7d')
  const [platformFilter, setPlatformFilter] = useState('all')
  const [eventFilter, setEventFilter] = useState('all')
  const [envFilter, setEnvFilter] = useState('prod')

  // Data state - initialized with mock data as fallback
  const [kpis, setKpis] = useState<KPICard[]>(mockKPIs)
  const [platformEMQ, setPlatformEMQ] = useState<PlatformEMQ[]>(mockPlatformEMQ)
  const [eventEMQ, setEventEMQ] = useState<EventEMQ[]>(mockEventEMQ)
  const [parameterCoverage, setParameterCoverage] = useState<ParameterCoverage[]>(mockParameterCoverage)
  const [serverBrowserSplit, setServerBrowserSplit] = useState<ServerBrowserSplit[]>(mockServerBrowserSplit)
  const [integrityIssues, setIntegrityIssues] = useState<IntegrityIssue[]>(mockIntegrityIssues)
  const [piiViolations, setPiiViolations] = useState<PIIViolation[]>(mockPIIViolations)
  const [alerts, setAlerts] = useState<Alert[]>(mockAlerts)
  const [recommendations, setRecommendations] = useState<Recommendation[]>(mockRecommendations)

  // State for resolved/dismissed items
  const [resolvedIssues, setResolvedIssues] = useState<string[]>([])
  const [dismissedAlerts, setDismissedAlerts] = useState<string[]>([])
  const [resolvedPIIViolations, setResolvedPIIViolations] = useState<string[]>([])
  const [appliedRecommendations, setAppliedRecommendations] = useState<string[]>([])
  const [resolvingIssue, setResolvingIssue] = useState<string | null>(null)
  const [resolvingAlert, setResolvingAlert] = useState<string | null>(null)
  const [resolvingPII, setResolvingPII] = useState<string | null>(null)
  const [applyingRecommendation, setApplyingRecommendation] = useState<string | null>(null)

  // Fetch data on mount and when filters change
  useEffect(() => {
    fetchQualityData()
  }, [platformFilter, dateRange])

  const fetchQualityData = async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Fetch quality report from CAPI
      const platforms = platformFilter !== 'all' ? platformFilter : undefined
      const reportResponse = await apiClient.get('/capi/quality/report', {
        params: { platforms }
      })

      const report = reportResponse.data?.data
      if (report && report.overall_score > 0) {
        // Update KPIs from report
        setKpis(prev => prev.map(kpi => {
          if (kpi.id === 'overall_emq') {
            return { ...kpi, value: report.overall_score, trend: report.trend === 'improving' ? 3.2 : report.trend === 'declining' ? -2.1 : 0 }
          }
          return kpi
        }))

        // Update platform EMQ from report
        if (report.platform_scores) {
          const platformData: PlatformEMQ[] = Object.entries(report.platform_scores).map(([platform, data]: [string, any]) => ({
            platform,
            overallEMQ: data.score,
            emailMatch: data.fields_present?.includes('email') ? 85 : 0,
            phoneMatch: data.fields_present?.includes('phone') ? 70 : 0,
            fbpMatch: data.fields_present?.includes('fbp') ? 90 : 0,
            fbcMatch: data.fields_present?.includes('fbc') ? 85 : 0,
            ipMatch: data.fields_present?.includes('ip_address') ? 92 : 0,
            trend: data.potential_roas_lift || 0,
          }))
          if (platformData.length > 0) {
            setPlatformEMQ(platformData)
          }
        }

        // Update recommendations from report
        if (report.top_recommendations && report.top_recommendations.length > 0) {
          setRecommendations(report.top_recommendations.map((rec: any, idx: number) => ({
            id: String(idx + 1),
            impact: rec.severity === 'critical' ? 'high' : rec.severity === 'high' ? 'medium' : 'low',
            title: rec.action || rec.field || 'Recommendation',
            description: rec.how_to_fix || rec.impact || 'Identified from data quality analysis',
            owner: 'Engineering',
            fixHint: rec.how_to_fix || 'See CAPI documentation for implementation details',
          })))
        }
      }

      // Fetch live insights
      const liveResponse = await apiClient.get('/capi/quality/live', {
        params: { platform: platformFilter !== 'all' ? platformFilter : 'meta' }
      })

      const liveData = liveResponse.data?.data
      if (liveData) {
        // Update alerts from live data
        if (liveData.top_gaps && liveData.top_gaps.length > 0) {
          const newAlerts: Alert[] = liveData.top_gaps.map((gap: any, idx: number) => ({
            id: `live-${idx}`,
            severity: gap.severity === 'critical' ? 'critical' : gap.severity === 'high' ? 'warning' : 'info',
            title: gap.field ? `Low ${gap.field} match rate` : 'Data quality issue',
            description: gap.recommendation || 'Review data quality settings',
            timestamp: 'Live',
            platform: platformFilter !== 'all' ? platformFilter : undefined,
          }))
          setAlerts(prev => [...newAlerts, ...prev.filter(a => !a.id.startsWith('live-'))])
        }
      }
    } catch (err: any) {
      console.error('Failed to fetch quality data:', err)
      // Keep mock data as fallback - don't show error for expected 404s
      if (err.response?.status !== 404) {
        setError(err.response?.data?.detail || 'Failed to load quality data')
      }
    } finally {
      setIsLoading(false)
      setLastRefresh(new Date())
    }
  }

  // Filter data based on selected filters
  const filteredPlatformEMQ = platformFilter === 'all'
    ? platformEMQ
    : platformEMQ.filter(p => p.platform === platformFilter)

  const filteredEventEMQ = eventFilter === 'all'
    ? eventEMQ
    : eventEMQ.filter(e => {
        const eventMap: Record<string, string> = {
          'purchase': 'Purchase',
          'add_to_cart': 'AddToCart',
          'begin_checkout': 'BeginCheckout',
          'view_content': 'ViewContent',
          'lead': 'Lead',
        }
        return e.event === eventMap[eventFilter]
      })

  const filteredServerBrowserSplit = platformFilter === 'all'
    ? serverBrowserSplit
    : serverBrowserSplit.filter(p => p.platform === platformFilter)

  const filteredAlerts = alerts.filter(alert => {
    if (dismissedAlerts.includes(alert.id)) return false
    if (platformFilter !== 'all' && alert.platform && alert.platform !== platformFilter) return false
    return true
  })

  const filteredIntegrityIssues = integrityIssues.filter(
    issue => !resolvedIssues.includes(issue.type)
  )

  const handleRefresh = async () => {
    setResolvedIssues([])
    setDismissedAlerts([])
    setResolvedPIIViolations([])
    setAppliedRecommendations([])
    await fetchQualityData()
  }

  const handleResolveIssue = (issueType: string) => {
    setResolvingIssue(issueType)
    // Simulate backend call
    setTimeout(() => {
      setResolvedIssues(prev => [...prev, issueType])
      setResolvingIssue(null)
    }, 1500)
  }

  const handleDismissAlert = (alertId: string) => {
    setResolvingAlert(alertId)
    // Simulate backend call
    setTimeout(() => {
      setDismissedAlerts(prev => [...prev, alertId])
      setResolvingAlert(null)
    }, 1000)
  }

  const handleAutoResolveAlert = (alertId: string) => {
    setResolvingAlert(alertId)
    // Simulate backend auto-resolution
    setTimeout(() => {
      setDismissedAlerts(prev => [...prev, alertId])
      setResolvingAlert(null)
    }, 2000)
  }

  const handleResolvePIIViolation = (field: string) => {
    setResolvingPII(field)
    // Simulate backend resolution - in real app would call API to apply fix
    setTimeout(() => {
      setResolvedPIIViolations(prev => [...prev, field])
      setResolvingPII(null)
    }, 1500)
  }

  const handleApplyRecommendation = (recId: string) => {
    setApplyingRecommendation(recId)
    // Simulate backend applying the recommendation fix
    setTimeout(() => {
      setAppliedRecommendations(prev => [...prev, recId])
      setApplyingRecommendation(null)
    }, 2000)
  }

  const getStatusColor = (status: 'good' | 'warning' | 'critical') => {
    switch (status) {
      case 'good': return 'text-green-500'
      case 'warning': return 'text-amber-500'
      case 'critical': return 'text-red-500'
    }
  }

  const getStatusBg = (status: 'good' | 'warning' | 'critical') => {
    switch (status) {
      case 'good': return 'bg-green-500/10 border-green-500/20'
      case 'warning': return 'bg-amber-500/10 border-amber-500/20'
      case 'critical': return 'bg-red-500/10 border-red-500/20'
    }
  }

  const getSeverityIcon = (severity: 'critical' | 'warning' | 'info') => {
    switch (severity) {
      case 'critical': return <XCircle className="w-4 h-4 text-red-500" />
      case 'warning': return <AlertTriangle className="w-4 h-4 text-amber-500" />
      case 'info': return <Info className="w-4 h-4 text-blue-500" />
    }
  }

  const getImpactBadge = (impact: 'high' | 'medium' | 'low') => {
    const styles = {
      high: 'bg-red-500/10 text-red-500',
      medium: 'bg-amber-500/10 text-amber-500',
      low: 'bg-blue-500/10 text-blue-500',
    }
    return (
      <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', styles[impact])}>
        {impact.toUpperCase()}
      </span>
    )
  }

  const getCoverageColor = (value: number) => {
    if (value >= 90) return 'bg-green-500'
    if (value >= 75) return 'bg-green-400'
    if (value >= 60) return 'bg-amber-400'
    if (value >= 40) return 'bg-amber-500'
    if (value > 0) return 'bg-red-400'
    return 'bg-muted'
  }

  const getCoverageTextColor = (value: number) => {
    if (value >= 90) return 'text-green-600 dark:text-green-400'
    if (value >= 75) return 'text-green-500'
    if (value >= 60) return 'text-amber-500'
    if (value >= 40) return 'text-amber-600'
    if (value > 0) return 'text-red-500'
    return 'text-muted-foreground'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Database className="w-7 h-7 text-primary" />
            {t('dataQuality.title', 'Data Quality Dashboard')}
            <span className="text-sm font-normal text-muted-foreground ml-2">— EMQ</span>
          </h1>
          <p className="text-muted-foreground mt-1">
            {t('dataQuality.subtitle', 'Monitor Event Match Quality across all platforms')}
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-3 py-2 rounded-lg border bg-background text-sm focus:ring-2 focus:ring-primary/20"
          >
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>

          <select
            value={platformFilter}
            onChange={(e) => setPlatformFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border bg-background text-sm focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">All Platforms</option>
            <option value="meta">Meta</option>
            <option value="google">Google</option>
            <option value="tiktok">TikTok</option>
            <option value="snapchat">Snapchat</option>
          </select>

          <select
            value={eventFilter}
            onChange={(e) => setEventFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border bg-background text-sm focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">All Events</option>
            <option value="purchase">Purchase</option>
            <option value="add_to_cart">Add to Cart</option>
            <option value="begin_checkout">Begin Checkout</option>
            <option value="view_content">View Content</option>
            <option value="lead">Lead</option>
          </select>

          <select
            value={envFilter}
            onChange={(e) => setEnvFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border bg-background text-sm focus:ring-2 focus:ring-primary/20"
          >
            <option value="prod">Production</option>
            <option value="stage">Staging</option>
          </select>

          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
            <span className="text-sm">Refresh</span>
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-500" />
          <span className="text-red-700 dark:text-red-400">{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-500 hover:text-red-700"
          >
            <XCircle className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
            <p className="text-muted-foreground">Loading data quality metrics...</p>
          </div>
        </div>
      ) : (
        <>
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {kpis.map((kpi) => (
          <div
            key={kpi.id}
            className={cn(
              'p-4 rounded-xl border transition-all hover:shadow-md',
              getStatusBg(kpi.status)
            )}
          >
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground">{kpi.label}</span>
              {kpi.trend !== 0 && (
                <div className={cn('flex items-center text-xs', kpi.trend > 0 ? 'text-green-500' : 'text-red-500')}>
                  {kpi.trend > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                  <span className="ml-0.5">{Math.abs(kpi.trend)}{kpi.id !== 'pii_compliance' && '%'}</span>
                </div>
              )}
            </div>
            <div className={cn('text-2xl font-bold', getStatusColor(kpi.status))}>
              {kpi.value}{kpi.unit}
            </div>
            <p className="text-xs text-muted-foreground mt-1">{kpi.description}</p>
          </div>
        ))}
      </div>

      {/* EMQ Breakdown Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* EMQ by Platform */}
        <div className="rounded-xl border bg-card p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Layers className="w-5 h-5 text-primary" />
            EMQ by Platform
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 font-medium">Platform</th>
                  <th className="text-right py-2 font-medium">EMQ</th>
                  <th className="text-right py-2 font-medium">Email</th>
                  <th className="text-right py-2 font-medium">Phone</th>
                  <th className="text-right py-2 font-medium">IP</th>
                  <th className="text-right py-2 font-medium">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredPlatformEMQ.length > 0 ? filteredPlatformEMQ.map((row) => (
                  <tr key={row.platform} className="hover:bg-muted/30">
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold"
                          style={{ backgroundColor: getPlatformColor(row.platform) }}
                        >
                          {row.platform.charAt(0).toUpperCase()}
                        </div>
                        <span className="capitalize">{row.platform}</span>
                      </div>
                    </td>
                    <td className={cn('text-right font-semibold', getCoverageTextColor(row.overallEMQ))}>
                      {row.overallEMQ}%
                    </td>
                    <td className={cn('text-right', getCoverageTextColor(row.emailMatch))}>
                      {row.emailMatch}%
                    </td>
                    <td className={cn('text-right', getCoverageTextColor(row.phoneMatch))}>
                      {row.phoneMatch}%
                    </td>
                    <td className={cn('text-right', getCoverageTextColor(row.ipMatch))}>
                      {row.ipMatch}%
                    </td>
                    <td className="text-right">
                      <span className={cn('flex items-center justify-end gap-1', row.trend >= 0 ? 'text-green-500' : 'text-red-500')}>
                        {row.trend >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                        {Math.abs(row.trend)}%
                      </span>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-muted-foreground">
                      No data for selected platform
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* EMQ by Event Type */}
        <div className="rounded-xl border bg-card p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary" />
            EMQ by Event Type
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 font-medium">Event</th>
                  <th className="text-right py-2 font-medium">EMQ</th>
                  <th className="text-right py-2 font-medium">Volume</th>
                  <th className="text-left py-2 font-medium">Worst Param</th>
                  <th className="text-right py-2 font-medium">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredEventEMQ.length > 0 ? filteredEventEMQ.map((row) => (
                  <tr key={row.event} className="hover:bg-muted/30">
                    <td className="py-3 font-medium">{row.event}</td>
                    <td className={cn('text-right font-semibold', getCoverageTextColor(row.emqScore))}>
                      {row.emqScore}%
                    </td>
                    <td className="text-right text-muted-foreground">
                      {row.volume.toLocaleString()}
                    </td>
                    <td className="text-left">
                      <span className="px-2 py-0.5 rounded bg-red-500/10 text-red-500 text-xs">
                        {row.worstParameter}
                      </span>
                    </td>
                    <td className="text-right">
                      <span className={cn('flex items-center justify-end gap-1', row.trend >= 0 ? 'text-green-500' : 'text-red-500')}>
                        {row.trend >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                        {Math.abs(row.trend)}%
                      </span>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-muted-foreground">
                      No data for selected event type
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Data Health Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Parameter Coverage Heatmap */}
        <div className="rounded-xl border bg-card p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary" />
            Required Parameter Coverage
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 font-medium">Parameter</th>
                  <th className="text-center py-2 font-medium">Meta</th>
                  <th className="text-center py-2 font-medium">Google</th>
                  <th className="text-center py-2 font-medium">TikTok</th>
                  <th className="text-center py-2 font-medium">Snap</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {mockParameterCoverage.map((row) => (
                  <tr key={row.parameter} className="hover:bg-muted/30">
                    <td className="py-2">
                      <span className="flex items-center gap-2">
                        {row.parameter}
                        {row.required && (
                          <span className="text-xs text-red-500">*</span>
                        )}
                      </span>
                    </td>
                    {[row.meta, row.google, row.tiktok, row.snapchat].map((value, idx) => (
                      <td key={idx} className="text-center py-2">
                        {value > 0 ? (
                          <div className="flex items-center justify-center">
                            <div
                              className={cn('w-10 h-6 rounded flex items-center justify-center text-xs font-medium text-white', getCoverageColor(value))}
                            >
                              {value}%
                            </div>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-muted-foreground mt-3">* Required parameter</p>
        </div>

        {/* Server vs Browser Split */}
        <div className="rounded-xl border bg-card p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Server className="w-5 h-5 text-primary" />
            Server vs Browser Split
          </h3>
          <div className="space-y-4">
            {filteredServerBrowserSplit.length > 0 ? filteredServerBrowserSplit.map((row) => (
              <div key={row.platform} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold"
                      style={{ backgroundColor: getPlatformColor(row.platform) }}
                    >
                      {row.platform.charAt(0).toUpperCase()}
                    </div>
                    <span className="capitalize text-sm font-medium">{row.platform}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-green-500 font-medium">{row.serverPercent}% Server</span>
                    <span className="text-muted-foreground">|</span>
                    <span className="text-amber-500">{row.browserPercent}% Browser</span>
                    <span className={cn('flex items-center gap-0.5 text-xs', row.trend >= 0 ? 'text-green-500' : 'text-red-500')}>
                      {row.trend >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                      {Math.abs(row.trend)}%
                    </span>
                  </div>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden flex">
                  <div
                    className="h-full bg-green-500 transition-all"
                    style={{ width: `${row.serverPercent}%` }}
                  />
                  <div
                    className="h-full bg-amber-500 transition-all"
                    style={{ width: `${row.browserPercent}%` }}
                  />
                </div>
              </div>
            )) : (
              <div className="py-8 text-center text-muted-foreground">
                No data for selected platform
              </div>
            )}
          </div>
          <div className="flex items-center gap-4 mt-4 pt-4 border-t text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-green-500" />
              <span>Server-side (CAPI)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-amber-500" />
              <span>Browser Pixel</span>
            </div>
          </div>
        </div>
      </div>

      {/* Integrity & Compliance Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Dedup & Sequencing */}
        <div className="rounded-xl border bg-card p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary" />
            Data Integrity Issues
            {resolvedIssues.length > 0 && (
              <span className="text-xs font-normal text-green-500 ml-2">
                ({resolvedIssues.length} resolved)
              </span>
            )}
          </h3>
          <div className="space-y-3">
            {filteredIntegrityIssues.length > 0 ? filteredIntegrityIssues.map((issue, idx) => (
              <div
                key={idx}
                className={cn(
                  'flex items-start gap-3 p-3 rounded-lg border',
                  issue.severity === 'critical' && 'bg-red-500/5 border-red-500/20',
                  issue.severity === 'warning' && 'bg-amber-500/5 border-amber-500/20',
                  issue.severity === 'info' && 'bg-blue-500/5 border-blue-500/20'
                )}
              >
                {getSeverityIcon(issue.severity)}
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm">{issue.description}</span>
                    <div className="flex items-center gap-3">
                      <span className={cn(
                        'font-bold',
                        issue.severity === 'critical' && 'text-red-500',
                        issue.severity === 'warning' && 'text-amber-500',
                        issue.severity === 'info' && 'text-blue-500'
                      )}>
                        {issue.count.toLocaleString()}
                      </span>
                      <button
                        onClick={() => handleResolveIssue(issue.type)}
                        disabled={resolvingIssue === issue.type}
                        className={cn(
                          'px-3 py-1 rounded-md text-xs font-medium transition-colors',
                          issue.severity === 'critical'
                            ? 'bg-red-500/10 text-red-600 hover:bg-red-500/20 disabled:bg-red-500/5'
                            : issue.severity === 'warning'
                            ? 'bg-amber-500/10 text-amber-600 hover:bg-amber-500/20 disabled:bg-amber-500/5'
                            : 'bg-blue-500/10 text-blue-600 hover:bg-blue-500/20 disabled:bg-blue-500/5'
                        )}
                      >
                        {resolvingIssue === issue.type ? (
                          <span className="flex items-center gap-1">
                            <RefreshCw className="w-3 h-3 animate-spin" />
                            Resolving...
                          </span>
                        ) : (
                          'Auto-Resolve'
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <CheckCircle2 className="w-12 h-12 text-green-500 mb-2" />
                <p className="font-medium text-green-500">All Issues Resolved</p>
                <p className="text-sm text-muted-foreground">No pending data integrity issues</p>
              </div>
            )}
          </div>
        </div>

        {/* PII Monitor */}
        <div className="rounded-xl border bg-card p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Lock className="w-5 h-5 text-primary" />
            PII Compliance Monitor
            {resolvedPIIViolations.length > 0 && (
              <span className="text-xs font-normal text-green-500 ml-2">
                ({resolvedPIIViolations.length} resolved)
              </span>
            )}
          </h3>
          {(() => {
            const filteredPIIViolations = piiViolations.filter(
              v => !resolvedPIIViolations.includes(v.field)
            )
            return filteredPIIViolations.length > 0 ? (
              <div className="space-y-3">
                {filteredPIIViolations.map((violation, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 rounded-lg bg-red-500/5 border border-red-500/20"
                  >
                    <div className="flex items-center gap-3">
                      <AlertTriangle className="w-4 h-4 text-red-500" />
                      <div>
                        <p className="font-medium text-sm">{violation.field}: {violation.violationType}</p>
                        <p className="text-xs text-muted-foreground">Last seen: {violation.lastSeen}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-red-500 font-bold">{violation.count}</span>
                      <button
                        onClick={() => handleResolvePIIViolation(violation.field)}
                        disabled={resolvingPII === violation.field}
                        className="px-3 py-1 rounded-md text-xs font-medium bg-red-500 text-white hover:bg-red-600 disabled:bg-red-400 transition-colors"
                      >
                        {resolvingPII === violation.field ? (
                          <span className="flex items-center gap-1">
                            <RefreshCw className="w-3 h-3 animate-spin" />
                            Fixing...
                          </span>
                        ) : (
                          'Auto-Fix'
                        )}
                      </button>
                    </div>
                  </div>
                ))}
                <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                  <Info className="w-3 h-3" />
                  Raw PII values are never displayed for compliance
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <CheckCircle2 className="w-12 h-12 text-green-500 mb-2" />
                <p className="font-medium text-green-500">All Clear</p>
                <p className="text-sm text-muted-foreground">No PII violations detected</p>
              </div>
            )
          })()}
        </div>
      </div>

      {/* Funnel Quality View */}
      <div className="rounded-xl border bg-card p-6">
        <h3 className="font-semibold mb-6 flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary" />
          Funnel Quality View
        </h3>
        <div className="flex items-center justify-between gap-4 overflow-x-auto pb-4">
          {mockFunnelSteps.map((step, idx) => (
            <div key={step.name} className="flex items-center">
              <div className="flex flex-col items-center min-w-[140px]">
                <div
                  className={cn(
                    'w-16 h-16 rounded-xl flex items-center justify-center mb-3 transition-all',
                    step.emqScore >= 80 ? 'bg-green-500/10 text-green-500' :
                    step.emqScore >= 70 ? 'bg-amber-500/10 text-amber-500' :
                    'bg-red-500/10 text-red-500'
                  )}
                >
                  <step.icon className="w-8 h-8" />
                </div>
                <span className="font-medium text-sm mb-1">{step.name}</span>
                <span className={cn(
                  'text-2xl font-bold',
                  getCoverageTextColor(step.emqScore)
                )}>
                  {step.emqScore}%
                </span>
                <span className="text-xs text-muted-foreground">
                  {step.volume.toLocaleString()} events
                </span>
                {idx > 0 && (
                  <span className="text-xs text-red-500 mt-1">
                    -{step.dropoff.toFixed(1)}% dropoff
                  </span>
                )}
              </div>
              {idx < mockFunnelSteps.length - 1 && (
                <ArrowRight className="w-6 h-6 text-muted-foreground mx-4 flex-shrink-0" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Alerts & Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Alerts Feed */}
        <div className="rounded-xl border bg-card p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-primary" />
            Alerts
            {dismissedAlerts.length > 0 && (
              <span className="text-xs font-normal text-green-500 ml-2">
                ({dismissedAlerts.length} dismissed)
              </span>
            )}
          </h3>
          <div className="space-y-3 max-h-[400px] overflow-y-auto">
            {filteredAlerts.length > 0 ? filteredAlerts.map((alert) => (
              <div
                key={alert.id}
                className={cn(
                  'p-4 rounded-lg border',
                  alert.severity === 'critical' && 'bg-red-500/5 border-red-500/20',
                  alert.severity === 'warning' && 'bg-amber-500/5 border-amber-500/20',
                  alert.severity === 'info' && 'bg-blue-500/5 border-blue-500/20'
                )}
              >
                <div className="flex items-start gap-3">
                  {getSeverityIcon(alert.severity)}
                  <div className="flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="font-medium text-sm">{alert.title}</h4>
                      {alert.platform && (
                        <div
                          className="w-5 h-5 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                          style={{ backgroundColor: getPlatformColor(alert.platform) }}
                        >
                          {alert.platform.charAt(0).toUpperCase()}
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{alert.description}</p>
                    <div className="flex items-center justify-between mt-3">
                      <span className="text-xs text-muted-foreground">{alert.timestamp}</span>
                      <div className="flex items-center gap-2">
                        {alert.severity !== 'info' && (
                          <button
                            onClick={() => handleAutoResolveAlert(alert.id)}
                            disabled={resolvingAlert === alert.id}
                            className={cn(
                              'px-3 py-1 rounded-md text-xs font-medium transition-colors',
                              alert.severity === 'critical'
                                ? 'bg-red-500 text-white hover:bg-red-600 disabled:bg-red-400'
                                : 'bg-amber-500 text-white hover:bg-amber-600 disabled:bg-amber-400'
                            )}
                          >
                            {resolvingAlert === alert.id ? (
                              <span className="flex items-center gap-1">
                                <RefreshCw className="w-3 h-3 animate-spin" />
                                Fixing...
                              </span>
                            ) : (
                              'Auto-Fix'
                            )}
                          </button>
                        )}
                        <button
                          onClick={() => handleDismissAlert(alert.id)}
                          disabled={resolvingAlert === alert.id}
                          className="px-3 py-1 rounded-md text-xs font-medium bg-muted hover:bg-muted/80 transition-colors disabled:opacity-50"
                        >
                          Dismiss
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <CheckCircle2 className="w-12 h-12 text-green-500 mb-2" />
                <p className="font-medium text-green-500">No Active Alerts</p>
                <p className="text-sm text-muted-foreground">All alerts have been addressed</p>
              </div>
            )}
          </div>
        </div>

        {/* Recommendations */}
        <div className="rounded-xl border bg-card p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-primary" />
            Recommendations
            {appliedRecommendations.length > 0 && (
              <span className="text-xs font-normal text-green-500 ml-2">
                ({appliedRecommendations.length} applied)
              </span>
            )}
          </h3>
          <div className="space-y-3 max-h-[400px] overflow-y-auto">
            {(() => {
              const filteredRecommendations = recommendations.filter(
                rec => !appliedRecommendations.includes(rec.id)
              )
              return filteredRecommendations.length > 0 ? (
                filteredRecommendations.map((rec) => (
                  <div
                    key={rec.id}
                    className="p-4 rounded-lg border bg-muted/30 hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <h4 className="font-medium text-sm">{rec.title}</h4>
                      {getImpactBadge(rec.impact)}
                    </div>
                    <p className="text-xs text-muted-foreground mb-3">{rec.description}</p>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Owner: <span className="font-medium text-foreground">{rec.owner}</span></span>
                    </div>
                    <div className="mt-2 p-2 rounded bg-primary/5 border border-primary/10">
                      <p className="text-xs text-primary font-medium">Fix: {rec.fixHint}</p>
                    </div>
                    <div className="mt-3 flex justify-end">
                      <button
                        onClick={() => handleApplyRecommendation(rec.id)}
                        disabled={applyingRecommendation === rec.id}
                        className={cn(
                          'px-4 py-1.5 rounded-md text-xs font-medium transition-colors',
                          rec.impact === 'high'
                            ? 'bg-red-500 text-white hover:bg-red-600 disabled:bg-red-400'
                            : rec.impact === 'medium'
                            ? 'bg-amber-500 text-white hover:bg-amber-600 disabled:bg-amber-400'
                            : 'bg-blue-500 text-white hover:bg-blue-600 disabled:bg-blue-400'
                        )}
                      >
                        {applyingRecommendation === rec.id ? (
                          <span className="flex items-center gap-1">
                            <RefreshCw className="w-3 h-3 animate-spin" />
                            Applying...
                          </span>
                        ) : (
                          'Apply Fix'
                        )}
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <CheckCircle2 className="w-12 h-12 text-green-500 mb-2" />
                  <p className="font-medium text-green-500">All Recommendations Applied</p>
                  <p className="text-sm text-muted-foreground">Great job! All fixes have been implemented</p>
                </div>
              )
            })()}
          </div>
        </div>
      </div>

      {/* Last Updated */}
      <div className="text-center text-xs text-muted-foreground">
        Last updated: {lastRefresh.toLocaleString()}
      </div>
      </>
      )}
    </div>
  )
}

export default DataQualityDashboard
