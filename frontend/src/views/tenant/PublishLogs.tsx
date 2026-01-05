/**
 * Stratum AI - Publish Logs Page
 *
 * Audit log of all campaign publish attempts with status and details.
 */

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowPathIcon,
  EyeIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import { useRetryPublish } from '@/api/campaignBuilder'

type PublishStatus = 'success' | 'failed' | 'pending' | 'retrying'

interface PublishLog {
  id: string
  draftId: string
  draftName: string
  platform: string
  status: PublishStatus
  platformCampaignId?: string
  errorMessage?: string
  publishedAt: string
  publishedBy: string
  retryCount: number
}

const mockLogs: PublishLog[] = [
  {
    id: '1',
    draftId: 'd1',
    draftName: 'Summer Sale 2024',
    platform: 'meta',
    status: 'success',
    platformCampaignId: 'camp_123456789',
    publishedAt: '2024-01-20T10:30:00Z',
    publishedBy: 'Ahmed Al-Saud',
    retryCount: 0,
  },
  {
    id: '2',
    draftId: 'd2',
    draftName: 'Retargeting - Cart Abandoners',
    platform: 'google',
    status: 'success',
    platformCampaignId: '987654321',
    publishedAt: '2024-01-19T14:00:00Z',
    publishedBy: 'Sara Mohammed',
    retryCount: 0,
  },
  {
    id: '3',
    draftId: 'd3',
    draftName: 'Brand Awareness Q1',
    platform: 'meta',
    status: 'failed',
    errorMessage: 'Invalid targeting: Location "XYZ" not found',
    publishedAt: '2024-01-18T09:15:00Z',
    publishedBy: 'Omar Hassan',
    retryCount: 2,
  },
  {
    id: '4',
    draftId: 'd4',
    draftName: 'Product Launch - Winter',
    platform: 'tiktok',
    status: 'pending',
    publishedAt: '2024-01-20T11:00:00Z',
    publishedBy: 'Fatima Al-Ali',
    retryCount: 0,
  },
]

const statusConfig: Record<PublishStatus, { icon: any; label: string; color: string }> = {
  success: { icon: CheckCircleIcon, label: 'Published', color: 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30' },
  failed: { icon: XCircleIcon, label: 'Failed', color: 'text-red-600 bg-red-100 dark:bg-red-900/30' },
  pending: { icon: ClockIcon, label: 'Pending', color: 'text-amber-600 bg-amber-100 dark:bg-amber-900/30' },
  retrying: { icon: ArrowPathIcon, label: 'Retrying', color: 'text-blue-600 bg-blue-100 dark:bg-blue-900/30' },
}

export default function PublishLogs() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const [logs] = useState(mockLogs)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedLog, setSelectedLog] = useState<PublishLog | null>(null)

  const retryPublish = useRetryPublish(Number(tenantId))

  const filteredLogs = logs.filter(log =>
    statusFilter === 'all' || log.status === statusFilter
  )

  const handleRetry = async (logId: string) => {
    try {
      await retryPublish.mutateAsync(logId)
      alert('Retry initiated successfully')
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred'
      alert(`Failed to retry publish: ${errorMessage}`)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Publish Logs</h1>
        <p className="text-muted-foreground">
          History of all campaign publish attempts
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <FunnelIcon className="h-5 w-5 text-muted-foreground" />
        <div className="flex gap-2">
          {['all', 'success', 'failed', 'pending'].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={cn(
                'px-3 py-1.5 text-sm rounded-lg transition-colors',
                statusFilter === status
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted hover:bg-muted/80'
              )}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Logs Table */}
      <div className="rounded-xl border bg-card shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Campaign
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Platform
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Platform ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Published By
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredLogs.map((log) => {
                const status = statusConfig[log.status]
                const StatusIcon = status.icon

                return (
                  <tr key={log.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-6 py-4">
                      <span className="font-medium">{log.draftName}</span>
                    </td>
                    <td className="px-6 py-4 text-sm capitalize">
                      {log.platform}
                    </td>
                    <td className="px-6 py-4">
                      <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full', status.color)}>
                        <StatusIcon className="h-3 w-3" />
                        {status.label}
                      </span>
                      {log.retryCount > 0 && (
                        <span className="ml-2 text-xs text-muted-foreground">
                          ({log.retryCount} retries)
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-muted-foreground">
                      {log.platformCampaignId || '-'}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {log.publishedBy}
                    </td>
                    <td className="px-6 py-4 text-sm text-muted-foreground">
                      {new Date(log.publishedAt).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setSelectedLog(log)}
                          className="p-1.5 rounded-lg hover:bg-accent transition-colors"
                          title="View Details"
                        >
                          <EyeIcon className="h-4 w-4" />
                        </button>
                        {log.status === 'failed' && (
                          <button
                            onClick={() => handleRetry(log.id)}
                            disabled={retryPublish.isPending}
                            className="p-1.5 rounded-lg hover:bg-accent transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Retry"
                          >
                            <ArrowPathIcon className={cn('h-4 w-4', retryPublish.isPending && 'animate-spin')} />
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

        {filteredLogs.length === 0 && (
          <div className="px-6 py-12 text-center">
            <ClockIcon className="h-12 w-12 mx-auto text-muted-foreground" />
            <p className="mt-4 text-muted-foreground">No publish logs found</p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="p-6 border-b">
              <h3 className="text-lg font-semibold">Publish Log Details</h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Campaign</p>
                <p className="font-medium">{selectedLog.draftName}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Platform</p>
                <p className="font-medium capitalize">{selectedLog.platform}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full', statusConfig[selectedLog.status].color)}>
                  {statusConfig[selectedLog.status].label}
                </span>
              </div>
              {selectedLog.platformCampaignId && (
                <div>
                  <p className="text-sm text-muted-foreground">Platform Campaign ID</p>
                  <p className="font-mono text-sm">{selectedLog.platformCampaignId}</p>
                </div>
              )}
              {selectedLog.errorMessage && (
                <div>
                  <p className="text-sm text-muted-foreground">Error Message</p>
                  <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/20 p-3 rounded-lg">
                    {selectedLog.errorMessage}
                  </p>
                </div>
              )}
              <div>
                <p className="text-sm text-muted-foreground">Published By</p>
                <p className="font-medium">{selectedLog.publishedBy}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Timestamp</p>
                <p className="font-medium">{new Date(selectedLog.publishedAt).toLocaleString()}</p>
              </div>
            </div>
            <div className="p-6 border-t bg-muted/30">
              <button
                onClick={() => setSelectedLog(null)}
                className="w-full px-4 py-2 rounded-lg border hover:bg-accent transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
