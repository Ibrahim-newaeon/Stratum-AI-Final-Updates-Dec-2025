/**
 * Campaign Table Component
 * Displays campaign performance data in a sortable, filterable table
 */

import React, { useState, useMemo } from 'react'
import { ArrowUp, ArrowDown, Filter, Search, X, ChevronDown } from 'lucide-react'
import { cn, formatCurrency } from '@/lib/utils'
import { Campaign, TableSortConfig } from '@/types/dashboard'

interface CampaignTableProps {
  campaigns: Campaign[]
  onCampaignClick?: (campaignId: string) => void
  pageSize?: number
}

export const CampaignTable: React.FC<CampaignTableProps> = ({
  campaigns,
  onCampaignClick,
  pageSize = 10,
}) => {
  const [sortConfig, setSortConfig] = useState<TableSortConfig>({
    key: 'roas',
    direction: 'desc',
  })
  const [currentPage, setCurrentPage] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')
  const [showFilterMenu, setShowFilterMenu] = useState(false)
  const [platformFilter, setPlatformFilter] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string | null>(null)

  // Get unique platforms and statuses from campaigns
  const uniquePlatforms = useMemo(() =>
    [...new Set(campaigns.map(c => c.platform))].sort(),
    [campaigns]
  )
  const uniqueStatuses = useMemo(() =>
    [...new Set(campaigns.map(c => c.status))].sort(),
    [campaigns]
  )

  // Count active filters
  const activeFilterCount = (platformFilter ? 1 : 0) + (statusFilter ? 1 : 0)

  // Sort and filter campaigns
  const sortedCampaigns = useMemo(() => {
    let filtered = [...campaigns]

    // Apply platform filter
    if (platformFilter) {
      filtered = filtered.filter(c => c.platform === platformFilter)
    }

    // Apply status filter
    if (statusFilter) {
      filtered = filtered.filter(c => c.status === statusFilter)
    }

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(
        (campaign) =>
          campaign.campaign_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          campaign.platform.toLowerCase().includes(searchTerm.toLowerCase()) ||
          (campaign.account_id && campaign.account_id.toLowerCase().includes(searchTerm.toLowerCase()))
      )
    }

    // Sort
    return filtered.sort((a, b) => {
      const aValue = a[sortConfig.key as keyof Campaign]
      const bValue = b[sortConfig.key as keyof Campaign]

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue
      }

      const aString = String(aValue).toLowerCase()
      const bString = String(bValue).toLowerCase()

      if (sortConfig.direction === 'asc') {
        return aString.localeCompare(bString)
      } else {
        return bString.localeCompare(aString)
      }
    })
  }, [campaigns, sortConfig, searchTerm, platformFilter, statusFilter])

  // Pagination
  const totalPages = Math.ceil(sortedCampaigns.length / pageSize)
  const paginatedCampaigns = sortedCampaigns.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  )

  // Handle sort
  const handleSort = (key: string) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc',
    }))
  }

  // Get ROAS color
  const getROASColor = (roas: number) => {
    if (roas >= 3.0) return 'text-green-600 dark:text-green-400 font-bold'
    if (roas >= 2.0) return 'text-green-500 dark:text-green-500'
    if (roas >= 1.0) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  // Column header component
  const ColumnHeader: React.FC<{
    label: string
    sortKey: string
    align?: 'left' | 'center' | 'right'
  }> = ({ label, sortKey, align = 'left' }) => {
    const isSorted = sortConfig.key === sortKey
    const alignClass =
      align === 'center' ? 'text-center' : align === 'right' ? 'text-right' : 'text-left'

    return (
      <th
        onClick={() => handleSort(sortKey)}
        className={cn(
          'px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider cursor-pointer hover:bg-muted/50 transition-colors',
          alignClass
        )}
      >
        <div
          className={cn(
            'flex items-center gap-1',
            align === 'center' ? 'justify-center' : align === 'right' ? 'justify-end' : 'justify-start'
          )}
        >
          {label}
          {isSorted &&
            (sortConfig.direction === 'asc' ? (
              <ArrowUp className="h-4 w-4" />
            ) : (
              <ArrowDown className="h-4 w-4" />
            ))}
        </div>
      </th>
    )
  }

  // Clear all filters
  const clearFilters = () => {
    setPlatformFilter(null)
    setStatusFilter(null)
    setSearchTerm('')
    setCurrentPage(1)
  }

  return (
    <div className="w-full">
      {/* Search Bar */}
      <div className="px-6 py-4 border-b">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search campaigns, platforms, or account IDs..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setCurrentPage(1)
              }}
              className="w-full pl-10 pr-4 py-2 border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            />
          </div>
          <div className="relative">
            <button
              onClick={() => setShowFilterMenu(!showFilterMenu)}
              className={cn(
                "inline-flex items-center px-4 py-2 border rounded-lg text-sm font-medium transition-colors",
                activeFilterCount > 0
                  ? "bg-primary text-primary-foreground border-primary"
                  : "text-foreground bg-background hover:bg-muted"
              )}
            >
              <Filter className="h-4 w-4 mr-2" />
              Filter
              {activeFilterCount > 0 && (
                <span className="ml-2 px-1.5 py-0.5 text-xs bg-white/20 rounded-full">
                  {activeFilterCount}
                </span>
              )}
              <ChevronDown className={cn("h-4 w-4 ml-1 transition-transform", showFilterMenu && "rotate-180")} />
            </button>

            {/* Filter Dropdown */}
            {showFilterMenu && (
              <div className="absolute right-0 top-full mt-2 w-64 bg-card border rounded-lg shadow-lg z-50 p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-medium text-sm">Filters</span>
                  {activeFilterCount > 0 && (
                    <button
                      onClick={clearFilters}
                      className="text-xs text-primary hover:underline"
                    >
                      Clear all
                    </button>
                  )}
                </div>

                {/* Platform Filter */}
                <div className="mb-4">
                  <label className="block text-xs font-medium text-muted-foreground mb-1">Platform</label>
                  <select
                    value={platformFilter || ''}
                    onChange={(e) => {
                      setPlatformFilter(e.target.value || null)
                      setCurrentPage(1)
                    }}
                    className="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="">All Platforms</option>
                    {uniquePlatforms.map(p => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>

                {/* Status Filter */}
                <div className="mb-4">
                  <label className="block text-xs font-medium text-muted-foreground mb-1">Status</label>
                  <select
                    value={statusFilter || ''}
                    onChange={(e) => {
                      setStatusFilter(e.target.value || null)
                      setCurrentPage(1)
                    }}
                    className="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="">All Statuses</option>
                    {uniqueStatuses.map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={() => setShowFilterMenu(false)}
                  className="w-full py-2 text-sm font-medium bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
                >
                  Apply Filters
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Active Filters Display */}
        {activeFilterCount > 0 && (
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            <span className="text-xs text-muted-foreground">Active filters:</span>
            {platformFilter && (
              <span className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-primary/10 text-primary rounded-full">
                {platformFilter}
                <button onClick={() => setPlatformFilter(null)} className="hover:text-primary/70">
                  <X className="h-3 w-3" />
                </button>
              </span>
            )}
            {statusFilter && (
              <span className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-primary/10 text-primary rounded-full">
                {statusFilter}
                <button onClick={() => setStatusFilter(null)} className="hover:text-primary/70">
                  <X className="h-3 w-3" />
                </button>
              </span>
            )}
          </div>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-border">
          <thead className="bg-muted/50">
            <tr>
              <ColumnHeader label="Campaign Name" sortKey="campaign_name" />
              <ColumnHeader label="Account" sortKey="account_id" />
              <ColumnHeader label="Platform" sortKey="platform" />
              <ColumnHeader label="Spend" sortKey="spend" align="right" />
              <ColumnHeader label="Revenue" sortKey="revenue" align="right" />
              <ColumnHeader label="ROAS" sortKey="roas" align="center" />
              <ColumnHeader label="CPA" sortKey="cpa" align="right" />
              <ColumnHeader label="Conversions" sortKey="conversions" align="center" />
            </tr>
          </thead>
          <tbody className="bg-card divide-y divide-border">
            {paginatedCampaigns.map((campaign) => (
              <tr
                key={campaign.campaign_id}
                onClick={() => onCampaignClick?.(campaign.campaign_id)}
                className="hover:bg-muted/50 cursor-pointer transition-colors"
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-foreground">{campaign.campaign_name}</div>
                  <div className="text-xs text-muted-foreground">
                    {campaign.campaign_type} &bull; {campaign.region}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {campaign.account_id ? (
                    <div className="text-sm">
                      <span className="font-mono text-xs bg-muted px-2 py-1 rounded">
                        {campaign.account_id.replace('act_', '')}
                      </span>
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-primary/10 text-primary">
                    {campaign.platform}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                  {formatCurrency(campaign.spend)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                  {formatCurrency(campaign.revenue)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <span className={cn('text-sm font-semibold', getROASColor(campaign.roas))}>
                    {campaign.roas.toFixed(2)}x
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                  {formatCurrency(campaign.cpa)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-center">
                  {campaign.conversions.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-6 py-4 border-t flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Showing {(currentPage - 1) * pageSize + 1} to{' '}
            {Math.min(currentPage * pageSize, sortedCampaigns.length)} of {sortedCampaigns.length}{' '}
            campaigns
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="px-4 py-2 border rounded-lg text-sm font-medium text-foreground bg-background hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>
            <span className="px-4 py-2 text-sm text-foreground">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              className="px-4 py-2 border rounded-lg text-sm font-medium text-foreground bg-background hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default CampaignTable
