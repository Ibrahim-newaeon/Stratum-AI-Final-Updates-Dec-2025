/**
 * Stratum AI - Dead Letter Queue Page
 *
 * Dedicated view for managing CAPI failed events with retry capabilities.
 */

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from '@/api/client'
import {
  ArrowPathIcon,
  TrashIcon,
  EyeIcon,
  FunnelIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  DocumentMagnifyingGlassIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

// Types
type DLQStatus = 'pending' | 'retrying' | 'failed' | 'resolved'
type Platform = 'meta' | 'google' | 'tiktok' | 'snapchat' | 'linkedin'

interface DLQEntry {
  id: string
  tenantId: number
  eventId: string
  eventType: string
  platform: Platform
  status: DLQStatus
  payload: Record<string, any>
  errorMessage: string
  errorCode?: string
  retryCount: number
  maxRetries: number
  firstFailedAt: string
  lastRetryAt?: string
  resolvedAt?: string
  createdAt: string
}

interface DLQStats {
  total: number
  pending: number
  retrying: number
  failed: number
  resolved: number
  byPlatform: Record<Platform, number>
  avgRetryCount: number
  oldestEntry: string
}

// API Functions
const dlqApi = {
  getEntries: async (params?: { status?: DLQStatus; platform?: Platform; limit?: number; offset?: number }) => {
    const response = await apiClient.get<ApiResponse<DLQEntry[]>>('/capi/dead-letter-queue', { params })
    return response.data.data
  },

  getEntry: async (entryId: string) => {
    const response = await apiClient.get<ApiResponse<DLQEntry>>(`/capi/dead-letter-queue/${entryId}`)
    return response.data.data
  },

  getStats: async () => {
    const response = await apiClient.get<ApiResponse<DLQStats>>('/capi/dead-letter-queue/stats')
    return response.data.data
  },

  retryEntry: async (entryId: string) => {
    const response = await apiClient.post<ApiResponse<DLQEntry>>(`/capi/dead-letter-queue/${entryId}/retry`)
    return response.data.data
  },

  retryAll: async (params?: { status?: DLQStatus; platform?: Platform }) => {
    const response = await apiClient.post<ApiResponse<{ queued: number }>>('/capi/dead-letter-queue/retry-all', params)
    return response.data.data
  },

  resolveEntry: async (entryId: string, reason: string) => {
    const response = await apiClient.post<ApiResponse<DLQEntry>>(`/capi/dead-letter-queue/${entryId}/resolve`, { reason })
    return response.data.data
  },

  deleteEntry: async (entryId: string) => {
    const response = await apiClient.delete<ApiResponse<void>>(`/capi/dead-letter-queue/${entryId}`)
    return response.data
  },

  purgeResolved: async (olderThan: number) => {
    const response = await apiClient.post<ApiResponse<{ deleted: number }>>('/capi/dead-letter-queue/purge', { olderThan })
    return response.data.data
  },
}

// Hooks
function useDLQEntries(params?: { status?: DLQStatus; platform?: Platform; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ['dlq', 'entries', params],
    queryFn: () => dlqApi.getEntries(params),
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  })
}

function useDLQStats() {
  return useQuery({
    queryKey: ['dlq', 'stats'],
    queryFn: dlqApi.getStats,
    refetchInterval: 30000,
  })
}

function useRetryEntry() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: dlqApi.retryEntry,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dlq'] })
    },
  })
}

function useRetryAll() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: dlqApi.retryAll,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dlq'] })
    },
  })
}

function useResolveEntry() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ entryId, reason }: { entryId: string; reason: string }) =>
      dlqApi.resolveEntry(entryId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dlq'] })
    },
  })
}

function useDeleteEntry() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: dlqApi.deleteEntry,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dlq'] })
    },
  })
}

// Status colors
const statusColors: Record<DLQStatus, string> = {
  pending: 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300',
  retrying: 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
  failed: 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300',
  resolved: 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300',
}

const platformColors: Record<Platform, string> = {
  meta: 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
  google: 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-300',
  tiktok: 'bg-pink-100 dark:bg-pink-900/20 text-pink-700 dark:text-pink-300',
  snapchat: 'bg-yellow-100 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300',
  linkedin: 'bg-sky-100 dark:bg-sky-900/20 text-sky-700 dark:text-sky-300',
}

export default function DeadLetterQueue() {
  const { tenantId: _tenantId } = useParams<{ tenantId: string }>()
  const [filterStatus, setFilterStatus] = useState<DLQStatus | ''>('')
  const [filterPlatform, setFilterPlatform] = useState<Platform | ''>('')
  const [selectedEntry, setSelectedEntry] = useState<DLQEntry | null>(null)
  const [showPayloadModal, setShowPayloadModal] = useState(false)

  const { data: stats, isLoading: _loadingStats } = useDLQStats()
  const { data: entries, isLoading: _loadingEntries } = useDLQEntries({
    status: filterStatus || undefined,
    platform: filterPlatform || undefined,
    limit: 100,
  })

  const retryEntry = useRetryEntry()
  const retryAll = useRetryAll()
  const resolveEntry = useResolveEntry()
  const deleteEntry = useDeleteEntry()

  const handleRetryAll = () => {
    if (window.confirm('Are you sure you want to retry all pending and failed entries?')) {
      retryAll.mutate({
        status: filterStatus || undefined,
        platform: filterPlatform || undefined,
      })
    }
  }

  const handleResolve = (entry: DLQEntry) => {
    const reason = window.prompt('Enter resolution reason:')
    if (reason) {
      resolveEntry.mutate({ entryId: entry.id, reason })
    }
  }

  const handleDelete = (entry: DLQEntry) => {
    if (window.confirm('Are you sure you want to delete this entry? This cannot be undone.')) {
      deleteEntry.mutate(entry.id)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dead Letter Queue</h1>
          <p className="text-muted-foreground">
            Manage failed CAPI events and retry delivery
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleRetryAll}
            disabled={retryAll.isPending || !entries?.length}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted disabled:opacity-50"
          >
            <ArrowPathIcon className={cn('h-4 w-4', retryAll.isPending && 'animate-spin')} />
            Retry All
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="rounded-xl border bg-card p-4 shadow-card">
            <div className="flex items-center gap-2">
              <DocumentMagnifyingGlassIcon className="h-5 w-5 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Total</p>
            </div>
            <p className="text-2xl font-bold mt-1">{stats.total.toLocaleString()}</p>
          </div>
          <div className="rounded-xl border bg-card p-4 shadow-card">
            <div className="flex items-center gap-2">
              <ClockIcon className="h-5 w-5 text-amber-500" />
              <p className="text-sm text-muted-foreground">Pending</p>
            </div>
            <p className="text-2xl font-bold mt-1 text-amber-600">{stats.pending.toLocaleString()}</p>
          </div>
          <div className="rounded-xl border bg-card p-4 shadow-card">
            <div className="flex items-center gap-2">
              <ArrowPathIcon className="h-5 w-5 text-blue-500" />
              <p className="text-sm text-muted-foreground">Retrying</p>
            </div>
            <p className="text-2xl font-bold mt-1 text-blue-600">{stats.retrying.toLocaleString()}</p>
          </div>
          <div className="rounded-xl border bg-card p-4 shadow-card">
            <div className="flex items-center gap-2">
              <XCircleIcon className="h-5 w-5 text-red-500" />
              <p className="text-sm text-muted-foreground">Failed</p>
            </div>
            <p className="text-2xl font-bold mt-1 text-red-600">{stats.failed.toLocaleString()}</p>
          </div>
          <div className="rounded-xl border bg-card p-4 shadow-card">
            <div className="flex items-center gap-2">
              <CheckCircleIcon className="h-5 w-5 text-emerald-500" />
              <p className="text-sm text-muted-foreground">Resolved</p>
            </div>
            <p className="text-2xl font-bold mt-1 text-emerald-600">{stats.resolved.toLocaleString()}</p>
          </div>
        </div>
      )}

      {/* Platform Breakdown */}
      {stats && (
        <div className="rounded-xl border bg-card p-6 shadow-card">
          <h3 className="font-semibold mb-4">Failures by Platform</h3>
          <div className="flex gap-4 flex-wrap">
            {Object.entries(stats.byPlatform).map(([platform, count]) => (
              <div
                key={platform}
                className={cn(
                  'px-4 py-2 rounded-lg flex items-center gap-2',
                  platformColors[platform as Platform]
                )}
              >
                <span className="font-medium capitalize">{platform}</span>
                <span className="text-lg font-bold">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4 p-4 rounded-xl border bg-card">
        <FunnelIcon className="h-5 w-5 text-muted-foreground" />
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as DLQStatus | '')}
          className="px-3 py-2 rounded-lg border bg-background"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="retrying">Retrying</option>
          <option value="failed">Failed</option>
          <option value="resolved">Resolved</option>
        </select>
        <select
          value={filterPlatform}
          onChange={(e) => setFilterPlatform(e.target.value as Platform | '')}
          className="px-3 py-2 rounded-lg border bg-background"
        >
          <option value="">All Platforms</option>
          <option value="meta">Meta</option>
          <option value="google">Google</option>
          <option value="tiktok">TikTok</option>
          <option value="snapchat">Snapchat</option>
          <option value="linkedin">LinkedIn</option>
        </select>
      </div>

      {/* Entries Table */}
      <div className="rounded-xl border bg-card shadow-card overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium">Event</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Platform</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Error</th>
              <th className="px-4 py-3 text-center text-sm font-medium">Retries</th>
              <th className="px-4 py-3 text-center text-sm font-medium">Status</th>
              <th className="px-4 py-3 text-left text-sm font-medium">First Failed</th>
              <th className="px-4 py-3 text-right text-sm font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {entries?.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center">
                  <CheckCircleIcon className="h-12 w-12 mx-auto text-emerald-500 mb-3" />
                  <p className="text-lg font-medium">No Failed Events</p>
                  <p className="text-muted-foreground">All CAPI events are being delivered successfully</p>
                </td>
              </tr>
            ) : (
              entries?.map((entry) => (
                <tr key={entry.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <p className="font-medium">{entry.eventType}</p>
                    <p className="text-xs text-muted-foreground font-mono">{entry.eventId.slice(0, 12)}...</p>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn('px-2 py-1 rounded text-xs capitalize', platformColors[entry.platform])}>
                      {entry.platform}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-sm text-red-600 dark:text-red-400 truncate max-w-xs">
                      {entry.errorMessage}
                    </p>
                    {entry.errorCode && (
                      <p className="text-xs text-muted-foreground">Code: {entry.errorCode}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={cn(
                      'font-medium',
                      entry.retryCount >= entry.maxRetries ? 'text-red-600' : ''
                    )}>
                      {entry.retryCount}/{entry.maxRetries}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={cn('px-2 py-1 rounded-full text-xs', statusColors[entry.status])}>
                      {entry.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {new Date(entry.firstFailedAt).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <button
                        onClick={() => {
                          setSelectedEntry(entry)
                          setShowPayloadModal(true)
                        }}
                        className="p-2 rounded hover:bg-muted"
                        title="View Payload"
                      >
                        <EyeIcon className="h-4 w-4" />
                      </button>
                      {entry.status !== 'resolved' && (
                        <button
                          onClick={() => retryEntry.mutate(entry.id)}
                          disabled={retryEntry.isPending}
                          className="p-2 rounded hover:bg-muted text-blue-600"
                          title="Retry"
                        >
                          <ArrowPathIcon className={cn('h-4 w-4', retryEntry.isPending && 'animate-spin')} />
                        </button>
                      )}
                      {entry.status !== 'resolved' && (
                        <button
                          onClick={() => handleResolve(entry)}
                          className="p-2 rounded hover:bg-muted text-emerald-600"
                          title="Mark Resolved"
                        >
                          <CheckCircleIcon className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(entry)}
                        className="p-2 rounded hover:bg-muted text-red-600"
                        title="Delete"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Payload Modal */}
      {showPayloadModal && selectedEntry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card rounded-xl shadow-lg max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden">
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="font-semibold">Event Payload</h3>
              <button
                onClick={() => setShowPayloadModal(false)}
                className="p-2 rounded hover:bg-muted"
              >
                <XCircleIcon className="h-5 w-5" />
              </button>
            </div>
            <div className="p-4 overflow-auto max-h-[60vh]">
              <div className="mb-4">
                <p className="text-sm text-muted-foreground">Event ID</p>
                <p className="font-mono text-sm">{selectedEntry.eventId}</p>
              </div>
              <div className="mb-4">
                <p className="text-sm text-muted-foreground">Event Type</p>
                <p className="font-medium">{selectedEntry.eventType}</p>
              </div>
              <div className="mb-4">
                <p className="text-sm text-muted-foreground">Error Message</p>
                <p className="text-red-600">{selectedEntry.errorMessage}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-2">Payload</p>
                <pre className="bg-muted rounded-lg p-4 overflow-auto text-xs font-mono">
                  {JSON.stringify(selectedEntry.payload, null, 2)}
                </pre>
              </div>
            </div>
            <div className="p-4 border-t flex justify-end gap-2">
              <button
                onClick={() => setShowPayloadModal(false)}
                className="px-4 py-2 rounded-lg border hover:bg-muted"
              >
                Close
              </button>
              <button
                onClick={() => {
                  retryEntry.mutate(selectedEntry.id)
                  setShowPayloadModal(false)
                }}
                disabled={selectedEntry.status === 'resolved'}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                Retry Event
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
