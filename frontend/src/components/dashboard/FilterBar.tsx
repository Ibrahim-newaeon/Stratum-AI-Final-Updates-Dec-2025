/**
 * Filter Bar Component
 * Responsive filter controls for dashboard
 */

import React, { useState } from 'react'
import { Filter, X, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { DashboardFilters } from '@/types/dashboard'

interface FilterBarProps {
  filters: DashboardFilters
  onChange: (filters: Partial<DashboardFilters>) => void
  platforms: string[]
  regions: string[]
  className?: string
}

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onChange,
  platforms,
  regions,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false)

  // Handle date range change
  const handleDateChange = (type: 'start' | 'end', value: string) => {
    const newDateRange = { ...filters.dateRange }
    newDateRange[type] = new Date(value)
    onChange({ dateRange: newDateRange })
  }

  // Handle platform toggle
  const togglePlatform = (platform: string) => {
    const newPlatforms = filters.platforms.includes(platform)
      ? filters.platforms.filter((p) => p !== platform)
      : [...filters.platforms, platform]
    onChange({ platforms: newPlatforms })
  }

  // Handle region toggle
  const toggleRegion = (region: string) => {
    const newRegions = filters.regions.includes(region)
      ? filters.regions.filter((r) => r !== region)
      : [...filters.regions, region]
    onChange({ regions: newRegions })
  }

  // Select all / clear all
  const selectAllPlatforms = () => onChange({ platforms })
  const clearAllPlatforms = () => onChange({ platforms: [] })
  const selectAllRegions = () => onChange({ regions })
  const clearAllRegions = () => onChange({ regions: [] })

  // Quick date presets
  const applyDatePreset = (preset: string) => {
    const end = new Date()
    let start = new Date()

    switch (preset) {
      case 'today':
        start = new Date()
        break
      case '7days':
        start = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
        break
      case '30days':
        start = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
        break
      case '90days':
        start = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000)
        break
      case 'thisMonth':
        start = new Date(end.getFullYear(), end.getMonth(), 1)
        break
      case 'lastMonth':
        start = new Date(end.getFullYear(), end.getMonth() - 1, 1)
        end.setDate(0)
        break
    }

    onChange({ dateRange: { start, end } })
  }

  return (
    <div className={className}>
      {/* Mobile Filter Toggle */}
      <div className="lg:hidden mb-4">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full flex items-center justify-between px-4 py-3 bg-card border rounded-lg shadow-sm"
        >
          <div className="flex items-center">
            <Filter className="h-5 w-5 mr-2 text-muted-foreground" />
            <span className="font-medium text-foreground">Filters</span>
            <span className="ml-2 px-2 py-1 text-xs bg-primary/10 text-primary rounded-full">
              {filters.platforms.length + filters.regions.length}
            </span>
          </div>
          <ChevronDown
            className={cn('h-5 w-5 text-muted-foreground transition-transform', isOpen && 'rotate-180')}
          />
        </button>
      </div>

      {/* Filter Content */}
      <div
        className={cn(
          'lg:block bg-card border rounded-lg p-6 shadow-sm',
          isOpen ? 'block' : 'hidden'
        )}
      >
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Date Range */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Date Range</label>

            {/* Quick Presets */}
            <div className="flex flex-wrap gap-2 mb-3">
              {['7days', '30days', '90days'].map((preset) => (
                <button
                  key={preset}
                  onClick={() => applyDatePreset(preset)}
                  className="px-3 py-1 text-xs font-medium rounded-full bg-muted text-muted-foreground hover:bg-primary/10 hover:text-primary transition-colors"
                >
                  {preset === '7days'
                    ? 'Last 7 Days'
                    : preset === '30days'
                      ? 'Last 30 Days'
                      : 'Last 90 Days'}
                </button>
              ))}
            </div>

            {/* Custom Date Inputs */}
            <div className="space-y-2">
              <input
                type="date"
                value={filters.dateRange.start.toISOString().split('T')[0]}
                onChange={(e) => handleDateChange('start', e.target.value)}
                max={filters.dateRange.end.toISOString().split('T')[0]}
                className="w-full px-3 py-2 border rounded-md bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
              <input
                type="date"
                value={filters.dateRange.end.toISOString().split('T')[0]}
                onChange={(e) => handleDateChange('end', e.target.value)}
                min={filters.dateRange.start.toISOString().split('T')[0]}
                max={new Date().toISOString().split('T')[0]}
                className="w-full px-3 py-2 border rounded-md bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
            </div>
          </div>

          {/* Platform Filter */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-foreground">Platforms</label>
              <div className="flex gap-2">
                <button
                  onClick={selectAllPlatforms}
                  className="text-xs text-primary hover:underline"
                >
                  All
                </button>
                <button
                  onClick={clearAllPlatforms}
                  className="text-xs text-muted-foreground hover:underline"
                >
                  Clear
                </button>
              </div>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {platforms.map((platform) => (
                <label
                  key={platform}
                  className="flex items-center cursor-pointer hover:bg-muted/50 p-2 rounded transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={filters.platforms.includes(platform)}
                    onChange={() => togglePlatform(platform)}
                    className="h-4 w-4 text-primary focus:ring-primary border-border rounded"
                  />
                  <span className="ml-2 text-sm text-foreground">{platform}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Region Filter */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-foreground">Regions</label>
              <div className="flex gap-2">
                <button onClick={selectAllRegions} className="text-xs text-primary hover:underline">
                  All
                </button>
                <button
                  onClick={clearAllRegions}
                  className="text-xs text-muted-foreground hover:underline"
                >
                  Clear
                </button>
              </div>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {regions.map((region) => (
                <label
                  key={region}
                  className="flex items-center cursor-pointer hover:bg-muted/50 p-2 rounded transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={filters.regions.includes(region)}
                    onChange={() => toggleRegion(region)}
                    className="h-4 w-4 text-primary focus:ring-primary border-border rounded"
                  />
                  <span className="ml-2 text-sm text-foreground">{region}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Active Filters Summary */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Active Filters</label>
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground">
                <span className="font-semibold">{filters.platforms.length}</span> platforms selected
              </div>
              <div className="text-xs text-muted-foreground">
                <span className="font-semibold">{filters.regions.length}</span> regions selected
              </div>
              <div className="text-xs text-muted-foreground">
                <span className="font-semibold">
                  {Math.ceil(
                    (filters.dateRange.end.getTime() - filters.dateRange.start.getTime()) /
                      (1000 * 60 * 60 * 24)
                  )}
                </span>{' '}
                days period
              </div>

              {/* Clear All Button */}
              <button
                onClick={() => {
                  clearAllPlatforms()
                  clearAllRegions()
                }}
                className="mt-4 w-full flex items-center justify-center px-4 py-2 border rounded-md text-sm font-medium text-foreground bg-background hover:bg-muted transition-colors"
              >
                <X className="h-4 w-4 mr-2" />
                Clear All Filters
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default FilterBar
