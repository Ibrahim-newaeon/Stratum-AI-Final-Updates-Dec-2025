/**
 * Empty State Component
 * Displays helpful messages when there's no data to show
 */

import React from 'react'
import {
  SearchX,
  Filter,
  BarChart3,
  FileX,
  Inbox,
  RefreshCw,
  Plus
} from 'lucide-react'
import { cn } from '@/lib/utils'

type EmptyStateVariant = 'no-data' | 'no-results' | 'no-filters' | 'error' | 'empty'

interface EmptyStateProps {
  variant?: EmptyStateVariant
  title?: string
  description?: string
  icon?: React.ReactNode
  action?: {
    label: string
    onClick: () => void
    variant?: 'primary' | 'secondary'
  }
  secondaryAction?: {
    label: string
    onClick: () => void
  }
  className?: string
}

const defaultContent: Record<EmptyStateVariant, { icon: React.ReactNode; title: string; description: string }> = {
  'no-data': {
    icon: <BarChart3 className="w-6 h-6" aria-hidden="true" />,
    title: 'No data available',
    description: 'There\'s no data to display yet. Data will appear here once available.',
  },
  'no-results': {
    icon: <SearchX className="w-6 h-6" aria-hidden="true" />,
    title: 'No results found',
    description: 'No items match your current filters. Try adjusting your search criteria.',
  },
  'no-filters': {
    icon: <Filter className="w-6 h-6" aria-hidden="true" />,
    title: 'No filters selected',
    description: 'Select at least one filter to view data.',
  },
  'error': {
    icon: <FileX className="w-6 h-6" aria-hidden="true" />,
    title: 'Unable to load data',
    description: 'Something went wrong while loading the data. Please try again.',
  },
  'empty': {
    icon: <Inbox className="w-6 h-6" aria-hidden="true" />,
    title: 'Nothing here yet',
    description: 'This section is empty. Get started by adding your first item.',
  },
}

export function EmptyState({
  variant = 'no-data',
  title,
  description,
  icon,
  action,
  secondaryAction,
  className,
}: EmptyStateProps) {
  const defaults = defaultContent[variant]

  return (
    <div className={cn(
      'flex flex-col items-center justify-center py-12 px-6 text-center',
      className
    )}>
      <div className="w-14 h-14 rounded-full bg-muted flex items-center justify-center mb-4 text-muted-foreground">
        {icon || defaults.icon}
      </div>

      <h3 className="text-lg font-semibold text-foreground mb-2">
        {title || defaults.title}
      </h3>

      <p className="text-sm text-muted-foreground max-w-sm mb-6">
        {description || defaults.description}
      </p>

      <div className="flex items-center gap-3">
        {action && (
          <button
            onClick={action.onClick}
            className={cn(
              'inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
              'active:scale-[0.98]',
              action.variant === 'secondary'
                ? 'border bg-background hover:bg-muted'
                : 'bg-primary text-primary-foreground hover:bg-primary/90'
            )}
          >
            {variant === 'error' && <RefreshCw className="w-4 h-4 mr-2" aria-hidden="true" />}
            {variant === 'empty' && <Plus className="w-4 h-4 mr-2" aria-hidden="true" />}
            {action.label}
          </button>
        )}

        {secondaryAction && (
          <button
            onClick={secondaryAction.onClick}
            className="text-sm text-primary hover:underline focus:outline-none focus-visible:underline transition-colors"
          >
            {secondaryAction.label}
          </button>
        )}
      </div>
    </div>
  )
}

// Specific empty states for common scenarios
export function NoFilterResultsState({
  onClearFilters,
  filterCount
}: {
  onClearFilters: () => void
  filterCount?: number
}) {
  return (
    <EmptyState
      variant="no-results"
      title="No campaigns match your filters"
      description={
        filterCount
          ? `${filterCount} active filters are hiding all results. Try removing some filters to see more data.`
          : 'Your current filter combination returned no results.'
      }
      action={{
        label: 'Clear all filters',
        onClick: onClearFilters,
        variant: 'secondary',
      }}
    />
  )
}

export function NoCampaignsState({ onCreateCampaign }: { onCreateCampaign?: () => void }) {
  return (
    <EmptyState
      variant="empty"
      title="No campaigns yet"
      description="Create your first campaign to start tracking performance and optimizing your marketing spend."
      action={onCreateCampaign ? {
        label: 'Create campaign',
        onClick: onCreateCampaign,
      } : undefined}
    />
  )
}

export function NoChartDataState({ onRefresh }: { onRefresh?: () => void }) {
  return (
    <EmptyState
      variant="no-data"
      icon={<BarChart3 className="w-6 h-6" />}
      title="No chart data"
      description="There's not enough data to display this chart. Try selecting a different date range."
      action={onRefresh ? {
        label: 'Refresh',
        onClick: onRefresh,
        variant: 'secondary',
      } : undefined}
      className="min-h-[200px]"
    />
  )
}

export function LoadErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <EmptyState
      variant="error"
      action={{
        label: 'Try again',
        onClick: onRetry,
      }}
    />
  )
}

export default EmptyState
