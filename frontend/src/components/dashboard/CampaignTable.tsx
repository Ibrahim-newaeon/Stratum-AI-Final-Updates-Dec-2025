/**
 * Campaign Table Component
 * Displays campaign performance data in a sortable, filterable table
 */

import React, { useState, useMemo } from 'react'
import { ArrowUp, ArrowDown, Filter, Search } from 'lucide-react'
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

  // Sort campaigns
  const sortedCampaigns = useMemo(() => {
    const sorted = [...campaigns].sort((a, b) => {
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

    // Filter by search term
    if (searchTerm) {
      return sorted.filter(
        (campaign) =>
          campaign.campaign_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          campaign.platform.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    return sorted
  }, [campaigns, sortConfig, searchTerm])

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

  return (
    <div className="w-full">
      {/* Search Bar */}
      <div className="px-6 py-4 border-b">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search campaigns..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setCurrentPage(1)
              }}
              className="w-full pl-10 pr-4 py-2 border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            />
          </div>
          <button className="inline-flex items-center px-4 py-2 border rounded-lg text-sm font-medium text-foreground bg-background hover:bg-muted transition-colors">
            <Filter className="h-5 w-5 mr-2" />
            Filter
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-border">
          <thead className="bg-muted/50">
            <tr>
              <ColumnHeader label="Campaign Name" sortKey="campaign_name" />
              <ColumnHeader label="Platform" sortKey="platform" />
              <ColumnHeader label="Spend" sortKey="spend" align="right" />
              <ColumnHeader label="Revenue" sortKey="revenue" align="right" />
              <ColumnHeader label="ROAS" sortKey="roas" align="center" />
              <ColumnHeader label="CPA" sortKey="cpa" align="right" />
              <ColumnHeader label="Conversions" sortKey="conversions" align="center" />
              <ColumnHeader label="CTR" sortKey="ctr" align="center" />
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
                <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-center">
                  {campaign.ctr.toFixed(2)}%
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
