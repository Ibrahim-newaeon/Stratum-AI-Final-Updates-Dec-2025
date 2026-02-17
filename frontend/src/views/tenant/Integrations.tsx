/**
 * Stratum AI - CRM Integrations Page
 *
 * Manages HubSpot and other CRM connections, contacts, deals, and writeback settings.
 */

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  useCRMConnections,
  useTriggerCRMSync,
  useCRMContacts,
  useCRMDeals,
  usePipelineSummary,
  useWritebackConfig,
  useUpdateWritebackConfig,
} from '@/api/hooks'
import {
  ArrowPathIcon,
  LinkIcon,
  UserGroupIcon,
  CurrencyDollarIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

type TabType = 'overview' | 'contacts' | 'deals' | 'writeback'

export default function Integrations() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const [activeTab, setActiveTab] = useState<TabType>('overview')

  const { data: connections, isLoading: loadingConnections } = useCRMConnections()
  const { data: pipelineSummary } = usePipelineSummary()
  const { data: contacts } = useCRMContacts({ limit: 10 })
  const { data: deals } = useCRMDeals({ limit: 10 })
  const { data: writebackConfig } = useWritebackConfig()
  const triggerSync = useTriggerCRMSync()
  const updateWriteback = useUpdateWritebackConfig()

  const hubspotConnection = connections?.find((c) => c.provider === 'hubspot')

  const tabs = [
    { id: 'overview' as TabType, label: 'Overview' },
    { id: 'contacts' as TabType, label: 'Contacts' },
    { id: 'deals' as TabType, label: 'Deals' },
    { id: 'writeback' as TabType, label: 'Writeback' },
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <CheckCircleIcon className="h-5 w-5 text-emerald-500" />
      case 'error':
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      case 'syncing':
        return <ArrowPathIcon className="h-5 w-5 text-blue-500 animate-spin" />
      default:
        return <ExclamationTriangleIcon className="h-5 w-5 text-amber-500" />
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">CRM Integrations</h1>
          <p className="text-muted-foreground">
            Connect and manage your CRM platforms for enhanced attribution and data sync
          </p>
        </div>
        {hubspotConnection && (
          <button
            onClick={() => triggerSync.mutate(hubspotConnection.id)}
            disabled={triggerSync.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            <ArrowPathIcon className={cn('h-4 w-4', triggerSync.isPending && 'animate-spin')} />
            Sync Now
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-4 py-2 border-b-2 font-medium text-sm transition-colors',
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Connection Status */}
          <div className="rounded-xl border bg-card p-6 shadow-card">
            <h2 className="text-lg font-semibold mb-4">Connection Status</h2>
            {loadingConnections ? (
              <div className="animate-pulse h-20 bg-muted rounded-lg" />
            ) : hubspotConnection ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-lg bg-orange-100 dark:bg-orange-900/20">
                    <LinkIcon className="h-6 w-6 text-orange-600" />
                  </div>
                  <div>
                    <p className="font-medium">HubSpot</p>
                    <p className="text-sm text-muted-foreground">
                      Portal: {hubspotConnection.portalName || hubspotConnection.portalId}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {getStatusIcon(hubspotConnection.status)}
                  <span className="text-sm capitalize">{hubspotConnection.status}</span>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <LinkIcon className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                <p className="text-muted-foreground">No CRM connected</p>
                <button className="mt-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90">
                  Connect HubSpot
                </button>
              </div>
            )}
          </div>

          {/* Summary Cards */}
          {hubspotConnection && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/20">
                    <UserGroupIcon className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total Contacts</p>
                    <p className="text-2xl font-bold">{hubspotConnection.totalContacts.toLocaleString()}</p>
                  </div>
                </div>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-900/20">
                    <CurrencyDollarIcon className="h-5 w-5 text-emerald-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total Deals</p>
                    <p className="text-2xl font-bold">{hubspotConnection.totalDeals.toLocaleString()}</p>
                  </div>
                </div>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/20">
                    <ArrowPathIcon className="h-5 w-5 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Last Sync</p>
                    <p className="text-lg font-medium">
                      {hubspotConnection.lastSyncAt
                        ? new Date(hubspotConnection.lastSyncAt).toLocaleString()
                        : 'Never'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Pipeline Summary */}
          {pipelineSummary && (
            <div className="rounded-xl border bg-card p-6 shadow-card">
              <h2 className="text-lg font-semibold mb-4">Pipeline Overview</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Total Value</p>
                  <p className="text-xl font-bold">${pipelineSummary.totalValue.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Avg Deal Size</p>
                  <p className="text-xl font-bold">${pipelineSummary.avgDealSize.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Conversion Rate</p>
                  <p className="text-xl font-bold">{(pipelineSummary.conversionRate * 100).toFixed(1)}%</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Deals</p>
                  <p className="text-xl font-bold">{pipelineSummary.totalDeals}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Contacts Tab */}
      {activeTab === 'contacts' && (
        <div className="rounded-xl border bg-card shadow-card overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium">Contact</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Company</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Stage</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Touchpoints</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Deal Value</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {contacts?.items.map((contact) => (
                <tr key={contact.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium">
                        {contact.firstName} {contact.lastName}
                      </p>
                      <p className="text-sm text-muted-foreground">{contact.email}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm">{contact.company || '-'}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 rounded-full text-xs bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300">
                      {contact.lifecycleStage || 'Lead'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">{contact.touchpointCount}</td>
                  <td className="px-4 py-3 text-right text-sm font-medium">
                    ${contact.totalDealValue.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Deals Tab */}
      {activeTab === 'deals' && (
        <div className="rounded-xl border bg-card shadow-card overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium">Deal</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Stage</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Close Date</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {deals?.items.map((deal) => (
                <tr key={deal.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <p className="font-medium">{deal.dealName}</p>
                    <p className="text-sm text-muted-foreground">{deal.pipeline}</p>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'px-2 py-1 rounded-full text-xs',
                        deal.stage === 'won' && 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300',
                        deal.stage === 'lost' && 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300',
                        !['won', 'lost'].includes(deal.stage) && 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                      )}
                    >
                      {deal.stage}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {deal.closeDate ? new Date(deal.closeDate).toLocaleDateString() : '-'}
                  </td>
                  <td className="px-4 py-3 text-right font-medium">
                    {deal.currency} {deal.amount.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Writeback Tab */}
      {activeTab === 'writeback' && (
        <div className="space-y-6">
          <div className="rounded-xl border bg-card p-6 shadow-card">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold">HubSpot Writeback</h2>
                <p className="text-sm text-muted-foreground">
                  Automatically sync attribution data back to HubSpot properties
                </p>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={writebackConfig?.enabled || false}
                  onChange={(e) => updateWriteback.mutate({ enabled: e.target.checked })}
                  className="w-5 h-5 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-sm font-medium">Enable Writeback</span>
              </label>
            </div>

            {writebackConfig?.enabled && (
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-muted/50">
                  <h3 className="font-medium mb-2">Property Mappings</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">First Touch Channel</span>
                      <span>stratum_first_touch_channel</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Last Touch Channel</span>
                      <span>stratum_last_touch_channel</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Attributed Revenue</span>
                      <span>stratum_attributed_revenue</span>
                    </div>
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-muted/50">
                  <h3 className="font-medium mb-2">Sync Status</h3>
                  <div className="flex items-center gap-2">
                    <CheckCircleIcon className="h-5 w-5 text-emerald-500" />
                    <span className="text-sm">
                      Last synced: {writebackConfig.lastSyncAt
                        ? new Date(writebackConfig.lastSyncAt).toLocaleString()
                        : 'Never'}
                    </span>
                  </div>
                  {writebackConfig.errorCount > 0 && (
                    <p className="text-sm text-amber-600 mt-2">
                      {writebackConfig.errorCount} sync errors
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
