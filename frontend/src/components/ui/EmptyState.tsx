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
    icon: <BarChart3 className="w-6 h-6" />,
    title: 'No data available',
    description: 'There\'s no data to display yet. Data will appear here once available.',
  },
  'no-results': {
    icon: <SearchX className="w-6 h-6" />,
    title: 'No results found',
    description: 'No items match your current filters. Try adjusting your search criteria.',
  },
  'no-filters': {
    icon: <Filter className="w-6 h-6" />,
    title: 'No filters selected',
    description: 'Select at least one filter to view data.',
  },
  'error': {
    icon: <FileX className="w-6 h-6" />,
    title: 'Unable to load data',
    description: 'Something went wrong while loading the data. Please try again.',
  },
  'empty': {
    icon: <Inbox className="w-6 h-6" />,
    title: 'Nothing here yet',
    description: 'This section is empty. Get started by adding your first item.',
  },
}

/** Mono status micro-label per variant — teaches the state at a glance. */
const statusLabels: Record<EmptyStateVariant, string> = {
  'no-data': 'No data',
  'no-results': 'No results',
  'no-filters': 'No filters',
  error: 'Error',
  empty: 'Empty',
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
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-border bg-card text-muted-foreground">
        {icon || defaults.icon}
      </div>

      <span className="mb-2 font-mono text-[0.6875rem] uppercase tracking-[0.16em] text-muted-foreground">
        {statusLabels[variant]}
      </span>

      <h3 className="text-lg font-semibold text-foreground mb-1.5">
        {title || defaults.title}
      </h3>

      <p className="text-sm text-muted-foreground max-w-sm mb-6 leading-relaxed">
        {description || defaults.description}
      </p>

      <div className="flex items-center gap-3">
        {action && (
          <button
            onClick={action.onClick}
            className={cn(
              'inline-flex items-center px-5 py-2 rounded-full text-sm font-medium transition-colors duration-200',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
              'active:scale-[0.98]',
              action.variant === 'secondary'
                ? 'border border-border bg-background hover:bg-muted'
                : 'bg-primary text-primary-foreground hover:bg-secondary'
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
      className="min-h-[12.5rem]"
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
