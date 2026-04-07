/**
 * Audit Logs (Super Admin View)
 *
 * System-wide audit trail for compliance and debugging
 * Shows user actions, system events, and API activity
 */

import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { useAuditLogs } from '@/api/hooks'
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowDownTrayIcon,
  ClockIcon,
  UserIcon,
  ServerIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline'

type LogCategory = 'all' | 'user' | 'system' | 'security' | 'api'
type LogSeverity = 'info' | 'warning' | 'error' | 'critical'

interface AuditLog {
  id: string
  timestamp: Date
  category: LogCategory
  severity: LogSeverity
  action: string
  description: string
  actor: {
    type: 'user' | 'system' | 'api'
    id: string
    name: string
  }
  target: {
    type: string
    id: string
    name: string
  } | null
  metadata: Record<string, unknown>
  ipAddress: string | null
  userAgent: string | null
}

export default function Audit() {
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<LogCategory>('all')
  const [severityFilter, setSeverityFilter] = useState<LogSeverity | 'all'>('all')
  const [expandedLog, setExpandedLog] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  })
  const [currentPage, setCurrentPage] = useState(1)
  const [exportFeedback, setExportFeedback] = useState<string | null>(null)
  const itemsPerPage = 10

  const { data: auditLogsData, isLoading } = useAuditLogs({
    startDate: dateRange.start,
    endDate: dateRange.end,
    action: categoryFilter !== 'all' ? categoryFilter : undefined,
  })

  // Map API data to component format
  const auditLogs: AuditLog[] = auditLogsData?.items?.map((log) => ({
    id: log.id,
    timestamp: new Date(log.timestamp),
    category: (log.severity === 'critical' || log.severity === 'error' ? 'security' : 'user') as LogCategory,
    severity: log.severity as LogSeverity,
    action: log.action,
    description: log.details,
    actor: {
      type: 'user' as const,
      id: log.userId,
      name: log.userName ?? 'User',
    },
    target: log.tenantId ? { type: 'tenant', id: String(log.tenantId), name: log.tenantName ?? 'Unknown' } : null,
    metadata: log.metadata ?? {},
    ipAddress: log.ipAddress ?? null,
    userAgent: log.userAgent ?? null,
  })) ?? [
    {
      id: '1',
      timestamp: new Date(Date.now() - 5 * 60 * 1000),
      category: 'user' as LogCategory,
      severity: 'info' as LogSeverity,
      action: 'user.login',
      description: 'User logged in successfully',
      actor: { type: 'user' as const, id: 'u1', name: 'john@example.com' },
      target: null,
      metadata: { method: 'email', mfaUsed: false },
      ipAddress: '192.168.1.100',
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    },
    {
      id: '2',
      timestamp: new Date(Date.now() - 15 * 60 * 1000),
      category: 'security' as LogCategory,
      severity: 'warning' as LogSeverity,
      action: 'auth.failed_login',
      description: 'Failed login attempt - invalid password',
      actor: { type: 'user' as const, id: 'unknown', name: 'admin@example.com' },
      target: null,
      metadata: { attempts: 3 },
      ipAddress: '203.0.113.45',
      userAgent: 'curl/7.64.1',
    },
    {
      id: '3',
      timestamp: new Date(Date.now() - 30 * 60 * 1000),
      category: 'system' as LogCategory,
      severity: 'info' as LogSeverity,
      action: 'autopilot.mode_change',
      description: 'Autopilot mode changed from normal to limited',
      actor: { type: 'system' as const, id: 'autopilot', name: 'Autopilot Engine' },
      target: { type: 'tenant', id: 't1', name: 'Fashion Forward' },
      metadata: { previousMode: 'normal', newMode: 'limited', reason: 'emq_degraded' },
      ipAddress: null,
      userAgent: null,
    },
    {
      id: '4',
      timestamp: new Date(Date.now() - 45 * 60 * 1000),
      category: 'api' as LogCategory,
      severity: 'error' as LogSeverity,
      action: 'api.rate_limit',
      description: 'API rate limit exceeded',
      actor: { type: 'api' as const, id: 'api-key-123', name: 'Integration API Key' },
      target: { type: 'endpoint', id: '/api/v1/campaigns', name: 'Campaigns API' },
      metadata: { limit: 1000, period: '1h', exceeded_by: 150 },
      ipAddress: '10.0.0.50',
      userAgent: 'StratumSDK/1.0',
    },
    {
      id: '5',
      timestamp: new Date(Date.now() - 60 * 60 * 1000),
      category: 'user' as LogCategory,
      severity: 'info' as LogSeverity,
      action: 'campaign.update',
      description: 'Campaign budget updated',
      actor: { type: 'user' as const, id: 'u2', name: 'sarah@example.com' },
      target: { type: 'campaign', id: 'c123', name: 'Summer Sale 2024' },
      metadata: { previousBudget: 5000, newBudget: 7500 },
      ipAddress: '192.168.1.101',
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    },
    {
      id: '6',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
      category: 'security' as LogCategory,
      severity: 'critical' as LogSeverity,
      action: 'auth.suspicious_activity',
      description: 'Multiple failed login attempts from different locations',
      actor: { type: 'user' as const, id: 'unknown', name: 'admin@company.com' },
      target: null,
      metadata: { locations: ['US', 'RU', 'CN'], attemptCount: 15, timeWindow: '10m' },
      ipAddress: 'Multiple',
      userAgent: 'Various',
    },
    {
      id: '7',
      timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000),
      category: 'system' as LogCategory,
      severity: 'info' as LogSeverity,
      action: 'sync.completed',
      description: 'Platform data sync completed successfully',
      actor: { type: 'system' as const, id: 'sync-engine', name: 'Data Sync Engine' },
      target: { type: 'platform', id: 'meta', name: 'Meta' },
      metadata: { recordsProcessed: 15420, duration: '45s' },
      ipAddress: null,
      userAgent: null,
    },
  ]

  // Filter logs
  const filteredLogs = auditLogs.filter((log) => {
    if (categoryFilter !== 'all' && log.category !== categoryFilter) return false
    if (severityFilter !== 'all' && log.severity !== severityFilter) return false
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      return (
        log.action.toLowerCase().includes(query) ||
        log.description.toLowerCase().includes(query) ||
        log.actor.name.toLowerCase().includes(query) ||
        log.target?.name.toLowerCase().includes(query)
      )
    }
    return true
  })

  const getCategoryIcon = (category: LogCategory) => {
    switch (category) {
      case 'user':
        return <UserIcon className="w-4 h-4" />
      case 'system':
        return <ServerIcon className="w-4 h-4" />
      case 'security':
        return <ShieldCheckIcon className="w-4 h-4" />
      case 'api':
        return <DocumentTextIcon className="w-4 h-4" />
      default:
        return <ClockIcon className="w-4 h-4" />
    }
  }

  const getSeverityColor = (severity: LogSeverity) => {
    switch (severity) {
      case 'info':
        return 'text-text-muted bg-surface-tertiary'
      case 'warning':
        return 'text-warning bg-warning/10'
      case 'error':
        return 'text-danger bg-danger/10'
      case 'critical':
        return 'text-danger bg-danger/20 animate-pulse'
    }
  }

  const formatTimestamp = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const mins = Math.floor(diff / 60000)

    if (mins < 60) return `${mins}m ago`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h ago`

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const handleExport = () => {
    try {
      // Prepare CSV content
      const headers = ['Timestamp', 'Category', 'Severity', 'Action', 'Description', 'Actor', 'Target', 'IP Address', 'User Agent']
      const csvRows = [headers.join(',')]

      filteredLogs.forEach((log) => {
        const row = [
          log.timestamp.toISOString(),
          log.category,
          log.severity,
          log.action,
          `"${log.description.replace(/"/g, '""')}"`,
          `"${log.actor.name}"`,
          log.target ? `"${log.target.type}: ${log.target.name}"` : '',
          log.ipAddress || '',
          `"${(log.userAgent || '').replace(/"/g, '""')}"`,
        ]
        csvRows.push(row.join(','))
      })

      const csvContent = csvRows.join('\n')
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      setExportFeedback(`Successfully exported ${filteredLogs.length} logs`)
      setTimeout(() => setExportFeedback(null), 3000)
    } catch (error) {
      setExportFeedback('Failed to export logs. Please try again.')
      setTimeout(() => setExportFeedback(null), 3000)
    }
  }

  // Pagination calculations
  const totalPages = Math.ceil(filteredLogs.length / itemsPerPage)
  const paginatedLogs = filteredLogs.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  )

  const handlePreviousPage = () => {
    setCurrentPage((prev) => Math.max(1, prev - 1))
  }

  const handleNextPage = () => {
    setCurrentPage((prev) => Math.min(totalPages, prev + 1))
  }

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [searchQuery, categoryFilter, severityFilter, dateRange.start, dateRange.end])

  // Stats
  const stats = {
    total: auditLogs.length,
    warnings: auditLogs.filter((l) => l.severity === 'warning').length,
    errors: auditLogs.filter((l) => l.severity === 'error').length,
    critical: auditLogs.filter((l) => l.severity === 'critical').length,
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Audit Logs</h1>
          <p className="text-text-muted">System-wide activity and security logs</p>
        </div>
        <div className="flex items-center gap-3">
          {exportFeedback && (
            <span className={cn(
              'text-sm px-3 py-1 rounded-lg',
              exportFeedback.includes('Successfully') ? 'text-success bg-success/10' : 'text-danger bg-danger/10'
            )}>
              {exportFeedback}
            </span>
          )}
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-text-secondary hover:text-white transition-colors"
          >
            <ArrowDownTrayIcon className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">Total Events</div>
          <div className="text-2xl font-bold text-white">{stats.total}</div>
        </div>
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">Warnings</div>
          <div className="text-2xl font-bold text-warning">{stats.warnings}</div>
        </div>
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">Errors</div>
          <div className="text-2xl font-bold text-danger">{stats.errors}</div>
        </div>
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">Critical</div>
          <div className="text-2xl font-bold text-danger">{stats.critical}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
          <input
            type="text"
            placeholder="Search logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-white placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-stratum-500"
          />
        </div>

        {/* Date Range */}
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={dateRange.start}
            onChange={(e) => setDateRange((d) => ({ ...d, start: e.target.value }))}
            className="px-3 py-2 rounded-lg bg-surface-secondary border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-stratum-500"
          />
          <span className="text-text-muted">to</span>
          <input
            type="date"
            value={dateRange.end}
            onChange={(e) => setDateRange((d) => ({ ...d, end: e.target.value }))}
            className="px-3 py-2 rounded-lg bg-surface-secondary border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-stratum-500"
          />
        </div>

        {/* Category Filter */}
        <div className="flex items-center gap-2">
          <FunnelIcon className="w-4 h-4 text-text-muted" />
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value as LogCategory)}
            className="px-3 py-2 rounded-lg bg-surface-secondary border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-stratum-500"
          >
            <option value="all">All Categories</option>
            <option value="user">User Actions</option>
            <option value="system">System Events</option>
            <option value="security">Security</option>
            <option value="api">API Activity</option>
          </select>
        </div>

        {/* Severity Filter */}
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value as LogSeverity | 'all')}
          className="px-3 py-2 rounded-lg bg-surface-secondary border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-stratum-500"
        >
          <option value="all">All Severities</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
          <option value="critical">Critical</option>
        </select>
      </div>

      {/* Logs List */}
      <div className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-text-muted">Loading audit logs...</div>
        ) : filteredLogs.length === 0 ? (
          <div className="p-8 text-center text-text-muted">No logs found matching your filters.</div>
        ) : (
          <div className="divide-y divide-white/5">
            {paginatedLogs.map((log) => (
              <div key={log.id} className="hover:bg-white/5 transition-colors">
                <button
                  onClick={() => setExpandedLog(expandedLog === log.id ? null : log.id)}
                  className="w-full p-4 text-left"
                >
                  <div className="flex items-start gap-4">
                    {/* Category Icon */}
                    <div
                      className={cn(
                        'p-2 rounded-lg',
                        log.category === 'security'
                          ? 'bg-warning/10 text-warning'
                          : 'bg-surface-tertiary text-text-muted'
                      )}
                    >
                      {getCategoryIcon(log.category)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-sm text-stratum-400">{log.action}</span>
                        <span
                          className={cn(
                            'px-2 py-0.5 rounded-full text-xs font-medium',
                            getSeverityColor(log.severity)
                          )}
                        >
                          {log.severity}
                        </span>
                      </div>
                      <p className="text-white">{log.description}</p>
                      <div className="flex items-center gap-4 mt-2 text-sm text-text-muted">
                        <span className="flex items-center gap-1">
                          <UserIcon className="w-3 h-3" />
                          {log.actor.name}
                        </span>
                        {log.target && (
                          <span>
                            → {log.target.type}: {log.target.name}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <ClockIcon className="w-3 h-3" />
                          {formatTimestamp(log.timestamp)}
                        </span>
                      </div>
                    </div>

                    {/* Expand Icon */}
                    <div className="text-text-muted">
                      {expandedLog === log.id ? (
                        <ChevronUpIcon className="w-5 h-5" />
                      ) : (
                        <ChevronDownIcon className="w-5 h-5" />
                      )}
                    </div>
                  </div>
                </button>

                {/* Expanded Details */}
                {expandedLog === log.id && (
                  <div className="px-4 pb-4 ml-14">
                    <div className="p-4 rounded-lg bg-surface-tertiary space-y-3">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-text-muted">Timestamp:</span>
                          <span className="text-white ml-2">
                            {log.timestamp.toLocaleString()}
                          </span>
                        </div>
                        {log.ipAddress && (
                          <div>
                            <span className="text-text-muted">IP Address:</span>
                            <span className="text-white ml-2 font-mono">{log.ipAddress}</span>
                          </div>
                        )}
                        <div>
                          <span className="text-text-muted">Actor Type:</span>
                          <span className="text-white ml-2 capitalize">{log.actor.type}</span>
                        </div>
                        <div>
                          <span className="text-text-muted">Actor ID:</span>
                          <span className="text-white ml-2 font-mono">{log.actor.id}</span>
                        </div>
                      </div>

                      {log.userAgent && (
                        <div className="text-sm">
                          <span className="text-text-muted">User Agent:</span>
                          <p className="text-white font-mono text-xs mt-1 break-all">
                            {log.userAgent}
                          </p>
                        </div>
                      )}

                      {Object.keys(log.metadata).length > 0 && (
                        <div className="text-sm">
                          <span className="text-text-muted">Metadata:</span>
                          <pre className="text-white font-mono text-xs mt-1 p-2 rounded bg-surface-primary overflow-x-auto">
                            {JSON.stringify(log.metadata, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm text-text-muted">
        <span>
          Showing {paginatedLogs.length > 0 ? (currentPage - 1) * itemsPerPage + 1 : 0}-
          {Math.min(currentPage * itemsPerPage, filteredLogs.length)} of {filteredLogs.length} logs
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={handlePreviousPage}
            disabled={currentPage === 1}
            className={cn(
              'px-3 py-1 rounded bg-surface-secondary transition-colors',
              currentPage === 1
                ? 'opacity-50 cursor-not-allowed'
                : 'hover:bg-surface-tertiary'
            )}
          >
            Previous
          </button>
          <span className="px-2">
            Page {currentPage} of {totalPages || 1}
          </span>
          <button
            onClick={handleNextPage}
            disabled={currentPage >= totalPages}
            className={cn(
              'px-3 py-1 rounded bg-surface-secondary transition-colors',
              currentPage >= totalPages
                ? 'opacity-50 cursor-not-allowed'
                : 'hover:bg-surface-tertiary'
            )}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
