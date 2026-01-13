/**
 * Stratum AI - Tenant Campaigns List
 *
 * Lists all campaigns for the tenant with filtering and actions.
 */

import { useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  PlusIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import { useCampaigns } from '@/api/hooks'

interface Campaign {
  id: string
  name: string
  platform: string
  status: 'active' | 'paused' | 'draft' | 'ended'
  spend: number
  roas: number
  conversions: number
  lastUpdated: string
}

// Mock data for demo
const mockCampaigns: Campaign[] = [
  { id: '1', name: 'Summer Sale 2024', platform: 'Meta', status: 'active', spend: 5420, roas: 4.2, conversions: 234, lastUpdated: '2h ago' },
  { id: '2', name: 'Retargeting - Cart Abandoners', platform: 'Google', status: 'active', spend: 3200, roas: 5.8, conversions: 156, lastUpdated: '4h ago' },
  { id: '3', name: 'Brand Awareness Q1', platform: 'Meta', status: 'paused', spend: 8900, roas: 2.1, conversions: 89, lastUpdated: '1d ago' },
  { id: '4', name: 'Product Launch - Winter Collection', platform: 'TikTok', status: 'draft', spend: 0, roas: 0, conversions: 0, lastUpdated: '2d ago' },
]

const statusColors = {
  active: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  paused: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  draft: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
  ended: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
}

export default function TenantCampaigns() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  // Fetch campaigns from API
  const { data: campaignsData } = useCampaigns()

  // Transform API data or fall back to mock
  const campaigns = useMemo((): Campaign[] => {
    if (campaignsData?.items && campaignsData.items.length > 0) {
      return campaignsData.items.map((c: any) => ({
        id: c.id?.toString() || c.campaign_id?.toString() || '',
        name: c.name || c.campaign_name || '',
        platform: c.platform || 'Unknown',
        status: c.status?.toLowerCase() || 'active',
        spend: c.spend || 0,
        roas: c.roas || (c.spend > 0 ? c.revenue / c.spend : 0),
        conversions: c.conversions || 0,
        lastUpdated: c.updated_at ? getRelativeTime(c.updated_at) : '—',
      }))
    }
    return mockCampaigns
  }, [campaignsData])

  // Helper function to get relative time
  function getRelativeTime(dateStr: string): string {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    if (diffHours < 1) return 'just now'
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ago`
  }

  const filteredCampaigns = campaigns.filter((campaign) => {
    const matchesSearch = campaign.name.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'all' || campaign.status === statusFilter
    return matchesSearch && matchesStatus
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Campaigns</h1>
          <p className="text-muted-foreground">Manage your advertising campaigns</p>
        </div>
        <Link
          to={`/app/${tenantId}/campaigns/new`}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
        >
          <PlusIcon className="h-5 w-5" />
          Create Campaign
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search campaigns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
        </div>
        <div className="flex items-center gap-2">
          <FunnelIcon className="h-5 w-5 text-muted-foreground" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="draft">Draft</option>
            <option value="ended">Ended</option>
          </select>
        </div>
      </div>

      {/* Campaigns Table */}
      <div className="rounded-xl border bg-card shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Campaign</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Platform</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Spend</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">ROAS</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Conversions</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredCampaigns.map((campaign) => (
                <tr key={campaign.id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-6 py-4">
                    <Link
                      to={`/app/${tenantId}/campaigns/drafts/${campaign.id}`}
                      className="font-medium hover:text-primary transition-colors"
                    >
                      {campaign.name}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">{campaign.platform}</td>
                  <td className="px-6 py-4">
                    <span className={cn('px-2 py-1 text-xs font-medium rounded-full', statusColors[campaign.status])}>
                      {campaign.status.charAt(0).toUpperCase() + campaign.status.slice(1)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right text-sm">${campaign.spend.toLocaleString()}</td>
                  <td className="px-6 py-4 text-right text-sm">
                    <span className={campaign.roas >= 3 ? 'text-emerald-600 dark:text-emerald-400' : campaign.roas < 2 ? 'text-red-600 dark:text-red-400' : ''}>
                      {campaign.roas > 0 ? `${campaign.roas}x` : '-'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right text-sm">{campaign.conversions > 0 ? campaign.conversions.toLocaleString() : '-'}</td>
                  <td className="px-6 py-4 text-right text-sm text-muted-foreground">{campaign.lastUpdated}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredCampaigns.length === 0 && (
          <div className="px-6 py-12 text-center">
            <p className="text-muted-foreground">No campaigns found</p>
            <Link
              to={`/app/${tenantId}/campaigns/new`}
              className="inline-flex items-center gap-2 mt-4 text-primary hover:underline"
            >
              <PlusIcon className="h-4 w-4" />
              Create your first campaign
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
