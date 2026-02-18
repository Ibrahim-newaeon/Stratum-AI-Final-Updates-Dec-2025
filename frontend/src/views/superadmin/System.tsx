/**
 * System Health (Super Admin View)
 *
 * Pipeline health, API status, queue monitoring, and system metrics
 */

import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { useSystemHealth } from '@/api/hooks'
import {
  ServerIcon,
  CpuChipIcon,
  CircleStackIcon,
  CloudIcon,
  SignalIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  ArrowPathIcon,
  ChartBarIcon,
  BoltIcon,
} from '@heroicons/react/24/outline'

type ServiceStatus = 'healthy' | 'degraded' | 'down'
type QueueStatus = 'running' | 'paused' | 'stalled'

interface Service {
  id: string
  name: string
  status: ServiceStatus
  uptime: number
  latency: number
  lastCheck: Date
  version: string
}

interface QueueInfo {
  id: string
  name: string
  status: QueueStatus
  pending: number
  processing: number
  completed: number
  failed: number
  avgProcessTime: number
}

interface PlatformConnector {
  platform: string
  status: ServiceStatus
  lastSync: Date
  syncDuration: number
  errors: number
  recordsProcessed: number
}

export default function System() {
  const [refreshing, setRefreshing] = useState(false)
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const [queueStates, setQueueStates] = useState<Record<string, QueueStatus>>({})
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({})
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean
    type: 'pause' | 'resume' | 'retry'
    queueId: string
    queueName: string
  } | null>(null)

  // Fetch system health from API
  const { data: healthData, refetch, isLoading: _isLoading } = useSystemHealth()

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setLastRefresh(new Date())
      refetch()
    }, 30000)
    return () => clearInterval(interval)
  }, [refetch])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await refetch()
      setLastRefresh(new Date())
    } finally {
      setRefreshing(false)
    }
  }

  // Handle queue pause/resume toggle
  const handleQueueToggle = (queueId: string, queueName: string, currentStatus: QueueStatus) => {
    const actionType = currentStatus === 'running' ? 'pause' : 'resume'
    setConfirmDialog({
      open: true,
      type: actionType,
      queueId,
      queueName,
    })
  }

  // Handle retry failed jobs
  const handleRetryFailed = (queueId: string, queueName: string) => {
    setConfirmDialog({
      open: true,
      type: 'retry',
      queueId,
      queueName,
    })
  }

  // Execute confirmed action
  const handleConfirmAction = async () => {
    if (!confirmDialog) return

    const { type, queueId, queueName } = confirmDialog
    const loadingKey = `${type}-${queueId}`

    setActionLoading(prev => ({ ...prev, [loadingKey]: true }))
    setConfirmDialog(null)

    try {
      // Simulate API call - replace with actual API integration
      await new Promise(resolve => setTimeout(resolve, 1000))

      if (type === 'pause') {
        setQueueStates(prev => ({ ...prev, [queueId]: 'paused' }))
        console.log(`Queue "${queueName}" paused successfully`)
      } else if (type === 'resume') {
        setQueueStates(prev => ({ ...prev, [queueId]: 'running' }))
        console.log(`Queue "${queueName}" resumed successfully`)
      } else if (type === 'retry') {
        console.log(`Retrying failed jobs in queue "${queueName}"`)
        // Trigger refetch to get updated queue status
        await refetch()
      }
    } catch (error) {
      console.error(`Failed to ${type} queue "${queueName}":`, error)
    } finally {
      setActionLoading(prev => ({ ...prev, [loadingKey]: false }))
    }
  }

  // Get effective queue status (local override or from data)
  const getEffectiveQueueStatus = (queue: QueueInfo): QueueStatus => {
    return queueStates[queue.id] ?? queue.status
  }

  // Default mock data for fallback
  const mockServices: Service[] = [
    { id: 'api', name: 'API Gateway', status: 'healthy', uptime: 99.99, latency: 45, lastCheck: new Date(), version: '2.4.1' },
    { id: 'auth', name: 'Auth Service', status: 'healthy', uptime: 99.95, latency: 32, lastCheck: new Date(), version: '1.8.0' },
    { id: 'sync', name: 'Sync Engine', status: 'degraded', uptime: 98.5, latency: 1250, lastCheck: new Date(), version: '3.1.2' },
    { id: 'ml', name: 'ML Pipeline', status: 'healthy', uptime: 99.8, latency: 890, lastCheck: new Date(), version: '2.0.0' },
    { id: 'db', name: 'Database Cluster', status: 'healthy', uptime: 99.99, latency: 12, lastCheck: new Date(), version: 'PostgreSQL 15' },
    { id: 'cache', name: 'Cache Layer', status: 'healthy', uptime: 99.99, latency: 2, lastCheck: new Date(), version: 'Redis 7.0' },
  ]

  const mockQueues: QueueInfo[] = [
    { id: 'sync', name: 'Platform Sync', status: 'running', pending: 45, processing: 12, completed: 15420, failed: 3, avgProcessTime: 2.5 },
    { id: 'notifications', name: 'Notifications', status: 'running', pending: 8, processing: 2, completed: 8932, failed: 0, avgProcessTime: 0.3 },
    { id: 'reports', name: 'Report Generation', status: 'running', pending: 15, processing: 3, completed: 1245, failed: 2, avgProcessTime: 45 },
    { id: 'ml-inference', name: 'ML Inference', status: 'running', pending: 120, processing: 8, completed: 45678, failed: 12, avgProcessTime: 1.2 },
  ]

  const mockConnectors: PlatformConnector[] = [
    { platform: 'Meta', status: 'healthy', lastSync: new Date(Date.now() - 5 * 60 * 1000), syncDuration: 45, errors: 0, recordsProcessed: 125000 },
    { platform: 'Google', status: 'healthy', lastSync: new Date(Date.now() - 3 * 60 * 1000), syncDuration: 32, errors: 0, recordsProcessed: 89000 },
    { platform: 'TikTok', status: 'degraded', lastSync: new Date(Date.now() - 15 * 60 * 1000), syncDuration: 180, errors: 5, recordsProcessed: 45000 },
    { platform: 'Snapchat', status: 'down', lastSync: new Date(Date.now() - 2 * 60 * 60 * 1000), syncDuration: 0, errors: 15, recordsProcessed: 0 },
    { platform: 'LinkedIn', status: 'healthy', lastSync: new Date(Date.now() - 8 * 60 * 1000), syncDuration: 28, errors: 0, recordsProcessed: 12000 },
  ]

  const mockSystemMetrics = {
    cpu: 42,
    memory: 68,
    disk: 35,
    network: 125,
    activeConnections: 1250,
    requestsPerMinute: 4520,
    errorRate: 0.02,
  }

  // Use API data or fallback to mock data
  const services: Service[] = healthData?.services?.map(s => ({
    id: s.name.toLowerCase().replace(/\s+/g, '-'),
    name: s.name,
    status: s.status,
    uptime: s.uptime,
    latency: s.latency,
    lastCheck: new Date(),
    version: s.version,
  })) ?? mockServices

  const queues: QueueInfo[] = healthData?.queues?.map(q => ({
    id: q.name.toLowerCase().replace(/\s+/g, '-'),
    name: q.name,
    status: q.status,
    pending: q.pending,
    processing: q.processing,
    completed: q.completed,
    failed: q.failed,
    avgProcessTime: q.avgProcessTime,
  })) ?? mockQueues

  const connectors: PlatformConnector[] = healthData?.connectors?.map(c => ({
    platform: c.platform,
    status: c.status,
    lastSync: new Date(c.lastSync),
    syncDuration: 0,
    errors: c.errors,
    recordsProcessed: c.recordsProcessed,
  })) ?? mockConnectors

  const systemMetrics = healthData?.metrics ?? mockSystemMetrics

  const getStatusColor = (status: ServiceStatus | QueueStatus) => {
    switch (status) {
      case 'healthy':
      case 'running':
        return 'text-success'
      case 'degraded':
      case 'paused':
        return 'text-warning'
      case 'down':
      case 'stalled':
        return 'text-danger'
    }
  }

  const getStatusBg = (status: ServiceStatus | QueueStatus) => {
    switch (status) {
      case 'healthy':
      case 'running':
        return 'bg-success/10'
      case 'degraded':
      case 'paused':
        return 'bg-warning/10'
      case 'down':
      case 'stalled':
        return 'bg-danger/10'
    }
  }

  const getStatusIcon = (status: ServiceStatus) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon className="w-5 h-5 text-success" />
      case 'degraded':
        return <ExclamationTriangleIcon className="w-5 h-5 text-warning" />
      case 'down':
        return <ExclamationTriangleIcon className="w-5 h-5 text-danger" />
    }
  }

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
    return `${Math.floor(seconds / 3600)}h`
  }

  const formatTime = (date: Date) => {
    const mins = Math.floor((Date.now() - date.getTime()) / 60000)
    if (mins < 1) return 'Just now'
    if (mins < 60) return `${mins}m ago`
    const hours = Math.floor(mins / 60)
    return `${hours}h ago`
  }

  const overallStatus: ServiceStatus =
    services.some(s => s.status === 'down') || connectors.some(c => c.status === 'down')
      ? 'down'
      : services.some(s => s.status === 'degraded') || connectors.some(c => c.status === 'degraded')
        ? 'degraded'
        : 'healthy'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">System Health</h1>
          <p className="text-text-muted">Pipeline and infrastructure monitoring</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-text-muted text-sm">
            <ClockIcon className="w-4 h-4" />
            Last updated: {formatTime(lastRefresh)}
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-text-secondary hover:text-white transition-colors',
              refreshing && 'opacity-50 cursor-not-allowed'
            )}
          >
            <ArrowPathIcon className={cn('w-4 h-4', refreshing && 'animate-spin')} />
            Refresh
          </button>
        </div>
      </div>

      {/* Overall Status Banner */}
      <div
        className={cn(
          'flex items-center gap-4 p-4 rounded-xl border',
          overallStatus === 'healthy' && 'bg-success/5 border-success/20',
          overallStatus === 'degraded' && 'bg-warning/5 border-warning/20',
          overallStatus === 'down' && 'bg-danger/5 border-danger/20'
        )}
      >
        {getStatusIcon(overallStatus)}
        <div>
          <span className={cn('font-semibold', getStatusColor(overallStatus))}>
            {overallStatus === 'healthy' && 'All Systems Operational'}
            {overallStatus === 'degraded' && 'Some Systems Degraded'}
            {overallStatus === 'down' && 'System Issues Detected'}
          </span>
          <p className="text-sm text-text-muted">
            {services.filter(s => s.status === 'healthy').length}/{services.length} services healthy,{' '}
            {connectors.filter(c => c.status === 'healthy').length}/{connectors.length} connectors online
          </p>
        </div>
      </div>

      {/* System Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-2 text-text-muted text-sm mb-2">
            <CpuChipIcon className="w-4 h-4" />
            CPU
          </div>
          <div className={cn('text-2xl font-bold', systemMetrics.cpu > 80 ? 'text-danger' : 'text-white')}>
            {systemMetrics.cpu}%
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-2 text-text-muted text-sm mb-2">
            <CircleStackIcon className="w-4 h-4" />
            Memory
          </div>
          <div className={cn('text-2xl font-bold', systemMetrics.memory > 85 ? 'text-warning' : 'text-white')}>
            {systemMetrics.memory}%
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-2 text-text-muted text-sm mb-2">
            <ServerIcon className="w-4 h-4" />
            Disk
          </div>
          <div className="text-2xl font-bold text-white">{systemMetrics.disk}%</div>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-2 text-text-muted text-sm mb-2">
            <CloudIcon className="w-4 h-4" />
            Network
          </div>
          <div className="text-2xl font-bold text-white">{systemMetrics.network} Mbps</div>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-2 text-text-muted text-sm mb-2">
            <SignalIcon className="w-4 h-4" />
            Connections
          </div>
          <div className="text-2xl font-bold text-white">
            {systemMetrics.activeConnections.toLocaleString()}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-2 text-text-muted text-sm mb-2">
            <BoltIcon className="w-4 h-4" />
            Requests/min
          </div>
          <div className="text-2xl font-bold text-white">
            {systemMetrics.requestsPerMinute.toLocaleString()}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-2 text-text-muted text-sm mb-2">
            <ExclamationTriangleIcon className="w-4 h-4" />
            Error Rate
          </div>
          <div className={cn('text-2xl font-bold', systemMetrics.errorRate > 1 ? 'text-danger' : 'text-success')}>
            {systemMetrics.errorRate}%
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Services */}
        <div className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
          <div className="flex items-center gap-3 p-4 border-b border-white/10">
            <ServerIcon className="w-5 h-5 text-stratum-400" />
            <h2 className="font-semibold text-white">Core Services</h2>
          </div>
          <div className="divide-y divide-white/5">
            {services.map((service) => (
              <div key={service.id} className="p-4 hover:bg-white/5 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(service.status)}
                    <div>
                      <div className="font-medium text-white">{service.name}</div>
                      <div className="text-xs text-text-muted">v{service.version}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6 text-sm">
                    <div className="text-right">
                      <div className="text-text-muted">Uptime</div>
                      <div className="text-white">{service.uptime}%</div>
                    </div>
                    <div className="text-right">
                      <div className="text-text-muted">Latency</div>
                      <div className={cn(service.latency > 1000 ? 'text-warning' : 'text-white')}>
                        {service.latency}ms
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Platform Connectors */}
        <div className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
          <div className="flex items-center gap-3 p-4 border-b border-white/10">
            <CloudIcon className="w-5 h-5 text-stratum-400" />
            <h2 className="font-semibold text-white">Platform Connectors</h2>
          </div>
          <div className="divide-y divide-white/5">
            {connectors.map((connector) => (
              <div key={connector.platform} className="p-4 hover:bg-white/5 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(connector.status)}
                    <div>
                      <div className="font-medium text-white">{connector.platform}</div>
                      <div className="text-xs text-text-muted">
                        Last sync: {formatTime(connector.lastSync)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6 text-sm">
                    <div className="text-right">
                      <div className="text-text-muted">Records</div>
                      <div className="text-white">{connector.recordsProcessed.toLocaleString()}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-text-muted">Errors</div>
                      <div className={cn(connector.errors > 0 ? 'text-danger' : 'text-success')}>
                        {connector.errors}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Job Queues */}
      <div className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
        <div className="flex items-center gap-3 p-4 border-b border-white/10">
          <ChartBarIcon className="w-5 h-5 text-stratum-400" />
          <h2 className="font-semibold text-white">Job Queues</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left p-4 text-text-muted font-medium">Queue</th>
                <th className="text-left p-4 text-text-muted font-medium">Status</th>
                <th className="text-right p-4 text-text-muted font-medium">Pending</th>
                <th className="text-right p-4 text-text-muted font-medium">Processing</th>
                <th className="text-right p-4 text-text-muted font-medium">Completed</th>
                <th className="text-right p-4 text-text-muted font-medium">Failed</th>
                <th className="text-right p-4 text-text-muted font-medium">Avg Time</th>
                <th className="text-left p-4 text-text-muted font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {queues.map((queue) => {
                const effectiveStatus = getEffectiveQueueStatus(queue)
                const isPauseLoading = actionLoading[`pause-${queue.id}`]
                const isResumeLoading = actionLoading[`resume-${queue.id}`]
                const isRetryLoading = actionLoading[`retry-${queue.id}`]
                const isToggleLoading = isPauseLoading || isResumeLoading

                return (
                  <tr key={queue.id} className="hover:bg-white/5 transition-colors">
                    <td className="p-4 font-medium text-white">{queue.name}</td>
                    <td className="p-4">
                      <span
                        className={cn(
                          'px-2 py-1 rounded-full text-xs font-medium',
                          getStatusColor(effectiveStatus),
                          getStatusBg(effectiveStatus)
                        )}
                      >
                        {effectiveStatus}
                      </span>
                    </td>
                    <td className="p-4 text-right text-white">{queue.pending}</td>
                    <td className="p-4 text-right text-stratum-400">{queue.processing}</td>
                    <td className="p-4 text-right text-success">{queue.completed.toLocaleString()}</td>
                    <td className="p-4 text-right">
                      <span className={queue.failed > 0 ? 'text-danger' : 'text-text-muted'}>
                        {queue.failed}
                      </span>
                    </td>
                    <td className="p-4 text-right text-text-muted">{formatDuration(queue.avgProcessTime)}</td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleQueueToggle(queue.id, queue.name, effectiveStatus)}
                          disabled={isToggleLoading}
                          className={cn(
                            'text-text-muted hover:text-white text-sm transition-colors',
                            isToggleLoading && 'opacity-50 cursor-not-allowed'
                          )}
                        >
                          {isToggleLoading ? (
                            <span className="flex items-center gap-1">
                              <ArrowPathIcon className="w-3 h-3 animate-spin" />
                              {isPauseLoading ? 'Pausing...' : 'Resuming...'}
                            </span>
                          ) : (
                            effectiveStatus === 'running' ? 'Pause' : 'Resume'
                          )}
                        </button>
                        {queue.failed > 0 && (
                          <button
                            onClick={() => handleRetryFailed(queue.id, queue.name)}
                            disabled={isRetryLoading}
                            className={cn(
                              'text-warning hover:text-white text-sm transition-colors',
                              isRetryLoading && 'opacity-50 cursor-not-allowed'
                            )}
                          >
                            {isRetryLoading ? (
                              <span className="flex items-center gap-1">
                                <ArrowPathIcon className="w-3 h-3 animate-spin" />
                                Retrying...
                              </span>
                            ) : (
                              'Retry Failed'
                            )}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation Dialog */}
      {confirmDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setConfirmDialog(null)}
          />
          {/* Dialog */}
          <div className="relative bg-surface-secondary border border-white/10 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              {confirmDialog.type === 'retry' ? (
                <ArrowPathIcon className="w-6 h-6 text-warning" />
              ) : confirmDialog.type === 'pause' ? (
                <ExclamationTriangleIcon className="w-6 h-6 text-warning" />
              ) : (
                <CheckCircleIcon className="w-6 h-6 text-success" />
              )}
              <h3 className="text-lg font-semibold text-white">
                {confirmDialog.type === 'pause' && 'Pause Queue'}
                {confirmDialog.type === 'resume' && 'Resume Queue'}
                {confirmDialog.type === 'retry' && 'Retry Failed Jobs'}
              </h3>
            </div>
            <p className="text-text-secondary mb-6">
              {confirmDialog.type === 'pause' && (
                <>
                  Are you sure you want to pause the <span className="font-medium text-white">{confirmDialog.queueName}</span> queue?
                  This will stop processing new jobs until resumed.
                </>
              )}
              {confirmDialog.type === 'resume' && (
                <>
                  Are you sure you want to resume the <span className="font-medium text-white">{confirmDialog.queueName}</span> queue?
                  Job processing will continue immediately.
                </>
              )}
              {confirmDialog.type === 'retry' && (
                <>
                  Are you sure you want to retry all failed jobs in the <span className="font-medium text-white">{confirmDialog.queueName}</span> queue?
                  This will re-queue all failed jobs for processing.
                </>
              )}
            </p>
            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setConfirmDialog(null)}
                className="px-4 py-2 rounded-lg text-text-secondary hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAction}
                className={cn(
                  'px-4 py-2 rounded-lg font-medium transition-colors',
                  confirmDialog.type === 'pause' && 'bg-warning/20 text-warning hover:bg-warning/30',
                  confirmDialog.type === 'resume' && 'bg-success/20 text-success hover:bg-success/30',
                  confirmDialog.type === 'retry' && 'bg-stratum-500/20 text-stratum-400 hover:bg-stratum-500/30'
                )}
              >
                {confirmDialog.type === 'pause' && 'Pause Queue'}
                {confirmDialog.type === 'resume' && 'Resume Queue'}
                {confirmDialog.type === 'retry' && 'Retry Jobs'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
