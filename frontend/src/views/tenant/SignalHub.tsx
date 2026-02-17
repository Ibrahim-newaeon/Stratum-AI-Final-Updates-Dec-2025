/**
 * Signal Hub (Data/Analytics Team View)
 *
 * Primary goal: Diagnose signal issues, recover fast, reduce volatility
 * Shows signal diagnostics, incident drill-down, recovery metrics
 */

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  EmqScoreCard,
  EmqTimeline,
  VolatilityBadge,
  ConfidenceBandBadge,
  type TimelineEvent,
} from '@/components/shared'
import {
  useEmqScore,
  useEmqVolatility,
  useEmqIncidents,
} from '@/api/hooks'
import {
  ClockIcon,
  ExclamationCircleIcon,
  ChartBarIcon,
  BugAntIcon,
  CheckCircleIcon,
  ArrowPathIcon,
  SignalIcon,
  WifiIcon,
  CloudIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { useToast } from '@/components/ui/use-toast'

interface PlatformSignal {
  platform: string
  status: 'healthy' | 'degraded' | 'critical'
  freshness: number
  dataLoss: number
  variance: number
  errors: number
  lastSync: Date
  activeIncidents: number
}

interface IncidentDetail {
  id: string
  platform: string
  title: string
  description: string
  driver: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  openedAt: Date
  resolvedAt: Date | null
  mttr: number | null // Mean Time To Recover in hours
  rootCause: string | null
  actions: { action: string; completedAt: Date | null }[]
}

export default function SignalHub() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const tid = parseInt(tenantId || '1', 10)
  const { toast } = useToast()

  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null)
  const [selectedIncident, setSelectedIncident] = useState<string | null>(null)
  const [resolvedIncidents, setResolvedIncidents] = useState<Set<string>>(new Set())
  const [incidentNotes, setIncidentNotes] = useState<Record<string, string[]>>({})
  const [noteModalOpen, setNoteModalOpen] = useState<string | null>(null)
  const [noteInput, setNoteInput] = useState('')
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Date range
  const dateRange = {
    start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  }

  // Fetch data
  const { data: emqData, refetch: refetchEmq } = useEmqScore(tid)
  const { data: volatilityData, refetch: refetchVolatility } = useEmqVolatility(tid)
  const { data: incidentsData, refetch: refetchIncidents } = useEmqIncidents(tid, dateRange.start, dateRange.end)

  const emqScore = emqData?.score ?? 85
  const svi = volatilityData?.svi ?? 25

  // Sample platform signals
  const platformSignals: PlatformSignal[] = [
    {
      platform: 'Meta',
      status: 'degraded',
      freshness: 92,
      dataLoss: 82,
      variance: 65,
      errors: 98,
      lastSync: new Date(Date.now() - 15 * 60 * 1000),
      activeIncidents: 1,
    },
    {
      platform: 'Google',
      status: 'healthy',
      freshness: 98,
      dataLoss: 96,
      variance: 94,
      errors: 99,
      lastSync: new Date(Date.now() - 5 * 60 * 1000),
      activeIncidents: 0,
    },
    {
      platform: 'TikTok',
      status: 'healthy',
      freshness: 95,
      dataLoss: 93,
      variance: 88,
      errors: 97,
      lastSync: new Date(Date.now() - 10 * 60 * 1000),
      activeIncidents: 0,
    },
    {
      platform: 'Snapchat',
      status: 'critical',
      freshness: 45,
      dataLoss: 78,
      variance: 55,
      errors: 82,
      lastSync: new Date(Date.now() - 4 * 60 * 60 * 1000),
      activeIncidents: 2,
    },
    {
      platform: 'GA4',
      status: 'healthy',
      freshness: 97,
      dataLoss: 95,
      variance: 91,
      errors: 99,
      lastSync: new Date(Date.now() - 3 * 60 * 1000),
      activeIncidents: 0,
    },
  ]

  // Sample incidents
  const incidents: IncidentDetail[] = [
    {
      id: '1',
      platform: 'Meta',
      title: 'Conversion tracking variance',
      description: 'Meta conversions 18% lower than GA4 attribution',
      driver: 'variance',
      severity: 'high',
      openedAt: new Date(Date.now() - 4 * 60 * 60 * 1000),
      resolvedAt: null,
      mttr: null,
      rootCause: null,
      actions: [
        { action: 'Verify pixel implementation', completedAt: null },
        { action: 'Check CAPI configuration', completedAt: null },
        { action: 'Review attribution windows', completedAt: null },
      ],
    },
    {
      id: '2',
      platform: 'Snapchat',
      title: 'API connection timeout',
      description: 'Snapchat API returning 504 errors intermittently',
      driver: 'freshness',
      severity: 'critical',
      openedAt: new Date(Date.now() - 6 * 60 * 60 * 1000),
      resolvedAt: null,
      mttr: null,
      rootCause: null,
      actions: [
        { action: 'Check API credentials', completedAt: new Date(Date.now() - 5 * 60 * 60 * 1000) },
        { action: 'Contact Snapchat support', completedAt: null },
      ],
    },
  ]

  const timeline: TimelineEvent[] = incidentsData?.map((i) => ({
    id: i.id,
    type: i.type,
    title: i.title,
    description: i.description ?? undefined,
    timestamp: new Date(i.timestamp),
    platform: i.platform ?? undefined,
    severity: i.severity,
    recoveryHours: i.recoveryHours ?? undefined,
    emqImpact: i.emqImpact ?? undefined,
  })) ?? []

  const getStatusColor = (status: PlatformSignal['status']) => {
    switch (status) {
      case 'healthy': return 'text-success bg-success/10 border-success/20'
      case 'degraded': return 'text-warning bg-warning/10 border-warning/20'
      case 'critical': return 'text-danger bg-danger/10 border-danger/20'
    }
  }

  const formatLastSync = (date: Date) => {
    const mins = Math.floor((Date.now() - date.getTime()) / 60000)
    if (mins < 60) return `${mins}m ago`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h ago`
    return `${Math.floor(hours / 24)}d ago`
  }

  // Handler: Mark incident as resolved
  const handleMarkResolved = (incidentId: string, incidentTitle: string) => {
    setResolvedIncidents((prev) => {
      const next = new Set(prev)
      next.add(incidentId)
      return next
    })
    setSelectedIncident(null)
    toast({
      title: 'Incident Resolved',
      description: `"${incidentTitle}" has been marked as resolved.`,
    })
  }

  // Handler: Add note to incident
  const handleAddNote = (incidentId: string) => {
    if (!noteInput.trim()) return
    setIncidentNotes((prev) => ({
      ...prev,
      [incidentId]: [...(prev[incidentId] || []), noteInput.trim()],
    }))
    setNoteInput('')
    setNoteModalOpen(null)
    toast({
      title: 'Note Added',
      description: 'Your note has been added to the incident.',
    })
  }

  // Handler: Refresh all data
  const handleRefreshAll = async () => {
    setIsRefreshing(true)
    try {
      await Promise.all([refetchEmq(), refetchVolatility(), refetchIncidents()])
      toast({
        title: 'Data Refreshed',
        description: 'All signal data has been refreshed.',
      })
    } catch {
      toast({
        title: 'Refresh Failed',
        description: 'Failed to refresh data. Please try again.',
        variant: 'destructive',
      })
    } finally {
      setIsRefreshing(false)
    }
  }

  // Filter out resolved incidents from display
  const activeIncidents = incidents.filter(
    (i) => !i.resolvedAt && !resolvedIncidents.has(i.id)
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Signal Hub</h1>
          <p className="text-text-muted">Diagnose signal issues, recover fast</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-secondary border border-white/10">
            <SignalIcon className="w-5 h-5 text-stratum-400" />
            <span className="text-white font-semibold">{emqScore}</span>
            <span className="text-text-muted">EMQ</span>
          </div>
          <div data-tour="volatility-badge">
            <VolatilityBadge svi={svi} showValue />
          </div>
          <button
            onClick={handleRefreshAll}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-text-secondary hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ArrowPathIcon className={cn("w-4 h-4", isRefreshing && "animate-spin")} />
            {isRefreshing ? 'Refreshing...' : 'Refresh All'}
          </button>
        </div>
      </div>

      {/* Platform Signal Cards */}
      <div data-tour="platform-signals" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {platformSignals.map((signal) => (
          <button
            key={signal.platform}
            onClick={() => setSelectedPlatform(
              selectedPlatform === signal.platform ? null : signal.platform
            )}
            className={cn(
              'p-4 rounded-xl border transition-all text-left',
              selectedPlatform === signal.platform
                ? 'ring-2 ring-stratum-500'
                : 'hover:border-white/20',
              getStatusColor(signal.status)
            )}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="font-semibold text-white">{signal.platform}</span>
              {signal.activeIncidents > 0 && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-danger/20 text-danger">
                  {signal.activeIncidents} active
                </span>
              )}
            </div>

            {/* Mini metrics */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center gap-1">
                <ClockIcon className="w-3 h-3" />
                <span className={signal.freshness >= 90 ? 'text-success' : signal.freshness >= 70 ? 'text-warning' : 'text-danger'}>
                  {signal.freshness}%
                </span>
              </div>
              <div className="flex items-center gap-1">
                <ExclamationCircleIcon className="w-3 h-3" />
                <span className={signal.dataLoss >= 90 ? 'text-success' : signal.dataLoss >= 70 ? 'text-warning' : 'text-danger'}>
                  {signal.dataLoss}%
                </span>
              </div>
              <div className="flex items-center gap-1">
                <ChartBarIcon className="w-3 h-3" />
                <span className={signal.variance >= 90 ? 'text-success' : signal.variance >= 70 ? 'text-warning' : 'text-danger'}>
                  {signal.variance}%
                </span>
              </div>
              <div className="flex items-center gap-1">
                <BugAntIcon className="w-3 h-3" />
                <span className={signal.errors >= 90 ? 'text-success' : signal.errors >= 70 ? 'text-warning' : 'text-danger'}>
                  {signal.errors}%
                </span>
              </div>
            </div>

            <div className="mt-3 pt-3 border-t border-white/10 text-xs text-text-muted">
              Last sync: {formatLastSync(signal.lastSync)}
            </div>
          </button>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left - EMQ Score & Drivers */}
        <div className="lg:col-span-2 space-y-6">
          <div data-tour="emq-drivers">
            <EmqScoreCard
              score={emqScore}
              previousScore={emqData?.previousScore ?? 82}
              showDrivers
            />
          </div>

          {/* Active Incidents */}
          <div data-tour="active-incidents" className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-danger/10">
                  <ExclamationCircleIcon className="w-5 h-5 text-danger" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Active Incidents</h3>
                  <p className="text-sm text-text-muted">
                    {activeIncidents.length} open
                  </p>
                </div>
              </div>
            </div>

            <div className="divide-y divide-white/5">
              {activeIncidents.map((incident) => (
                <div
                  key={incident.id}
                  className={cn(
                    'p-4 transition-colors cursor-pointer hover:bg-white/5',
                    selectedIncident === incident.id && 'bg-white/5'
                  )}
                  onClick={() => setSelectedIncident(
                    selectedIncident === incident.id ? null : incident.id
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs bg-surface-tertiary text-text-muted px-2 py-0.5 rounded">
                          {incident.platform}
                        </span>
                        <span className={cn(
                          'text-xs px-2 py-0.5 rounded',
                          incident.severity === 'critical' && 'bg-danger/10 text-danger',
                          incident.severity === 'high' && 'bg-orange-500/10 text-orange-400',
                          incident.severity === 'medium' && 'bg-warning/10 text-warning',
                        )}>
                          {incident.severity}
                        </span>
                      </div>
                      <h4 className="font-medium text-white">{incident.title}</h4>
                      <p className="text-sm text-text-muted mt-1">{incident.description}</p>
                    </div>
                    <span className="text-xs text-text-muted">
                      {formatLastSync(incident.openedAt)}
                    </span>
                  </div>

                  {/* Expanded incident details */}
                  {selectedIncident === incident.id && (
                    <div className="mt-4 pt-4 border-t border-white/10 space-y-3">
                      <div className="text-sm">
                        <span className="text-text-muted">Driver:</span>{' '}
                        <span className="text-white capitalize">{incident.driver}</span>
                      </div>
                      <div data-tour="resolution-steps">
                        <span className="text-sm text-text-muted block mb-2">Resolution steps:</span>
                        <div className="space-y-2">
                          {incident.actions.map((a, i) => (
                            <div key={i} className="flex items-center gap-2 text-sm">
                              {a.completedAt ? (
                                <CheckCircleIcon className="w-4 h-4 text-success" />
                              ) : (
                                <div className="w-4 h-4 rounded-full border border-white/20" />
                              )}
                              <span className={a.completedAt ? 'text-text-muted line-through' : 'text-white'}>
                                {a.action}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleMarkResolved(incident.id, incident.title)
                          }}
                          className="flex-1 py-2 rounded-lg bg-success/10 text-success text-sm font-medium hover:bg-success/20 transition-colors"
                        >
                          Mark Resolved
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setNoteModalOpen(incident.id)
                          }}
                          className="py-2 px-4 rounded-lg bg-surface-tertiary text-text-secondary text-sm hover:text-white transition-colors"
                        >
                          Add Note
                        </button>
                      </div>
                      {/* Display existing notes */}
                      {incidentNotes[incident.id]?.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-white/10">
                          <span className="text-sm text-text-muted block mb-2">Notes:</span>
                          <div className="space-y-1">
                            {incidentNotes[incident.id].map((note, idx) => (
                              <div key={idx} className="text-sm text-white bg-surface-tertiary px-3 py-2 rounded">
                                {note}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right - Timeline & Metrics */}
        <div className="space-y-6">
          {/* Recovery Metrics */}
          <div data-tour="recovery-metrics" className="rounded-2xl bg-surface-secondary border border-white/10 p-4">
            <h3 className="font-semibold text-white mb-4">Recovery Metrics</h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-text-muted">Avg MTTR</span>
                  <span className="text-white font-medium">2.4 hours</span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                  <div className="h-full w-2/3 bg-success rounded-full" />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-text-muted">Resolution Rate</span>
                  <span className="text-white font-medium">92%</span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                  <div className="h-full w-[92%] bg-success rounded-full" />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-text-muted">Repeat Incidents</span>
                  <span className="text-warning font-medium">15%</span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                  <div className="h-full w-[15%] bg-warning rounded-full" />
                </div>
              </div>
            </div>
          </div>

          {/* Timeline */}
          <EmqTimeline events={timeline} maxEvents={8} />
        </div>
      </div>

      {/* Add Note Modal */}
      {noteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-surface-secondary rounded-xl border border-white/10 p-6 w-full max-w-md mx-4 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Add Note</h3>
              <button
                onClick={() => {
                  setNoteModalOpen(null)
                  setNoteInput('')
                }}
                className="p-1 rounded-lg hover:bg-white/10 transition-colors"
              >
                <XMarkIcon className="w-5 h-5 text-text-muted" />
              </button>
            </div>
            <textarea
              value={noteInput}
              onChange={(e) => setNoteInput(e.target.value)}
              placeholder="Enter your note..."
              className="w-full h-32 px-3 py-2 rounded-lg bg-surface-tertiary border border-white/10 text-white placeholder:text-text-muted resize-none focus:outline-none focus:ring-2 focus:ring-stratum-500"
              autoFocus
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => {
                  setNoteModalOpen(null)
                  setNoteInput('')
                }}
                className="flex-1 py-2 rounded-lg bg-surface-tertiary text-text-secondary hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleAddNote(noteModalOpen)}
                disabled={!noteInput.trim()}
                className="flex-1 py-2 rounded-lg bg-stratum-500 text-white font-medium hover:bg-stratum-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add Note
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
