/**
 * Skeleton Loading Components
 * Provides visual placeholders during data loading
 */

import { cn } from '@/lib/utils'

interface SkeletonProps {
  className?: string
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'skeleton rounded-lg',
        className
      )}
    />
  )
}

// KPI Card Skeleton
export function KPICardSkeleton({ size = 'normal' }: { size?: 'small' | 'normal' }) {
  return (
    <div className={cn(
      'relative overflow-hidden rounded-xl border bg-card',
      size === 'small' ? 'p-4' : 'p-6'
    )}>
      <div className="absolute left-0 top-0 h-full w-1 bg-muted" />
      <div className="relative space-y-3">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-5 w-5 rounded" />
        </div>
        <Skeleton className={cn('h-8', size === 'small' ? 'w-20' : 'w-28')} />
        {size === 'normal' && (
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4" />
            <Skeleton className="h-4 w-16" />
          </div>
        )}
      </div>
    </div>
  )
}

// Chart Skeleton
export function ChartSkeleton({ height = 300 }: { height?: number }) {
  return (
    <div className="rounded-xl border bg-card p-6">
      <Skeleton className="h-5 w-48 mb-4" />
      <div
        className="relative overflow-hidden rounded-lg bg-muted/50"
        style={{ height }}
      >
        {/* Animated shimmer effect */}
        <div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent" />

        {/* Chart bars placeholder */}
        <div className="absolute bottom-4 left-4 right-4 flex items-end justify-around gap-2">
          {[65, 80, 45, 90, 55, 70, 85].map((height, i) => (
            <div
              key={i}
              className="flex-1 rounded-t bg-muted"
              style={{ height: `${height}%` }}
            />
          ))}
        </div>

        {/* Axis lines */}
        <div className="absolute bottom-4 left-4 right-4 border-b border-muted-foreground/20" />
        <div className="absolute top-4 bottom-4 left-4 border-l border-muted-foreground/20" />
      </div>
    </div>
  )
}

// Area Chart Skeleton
export function AreaChartSkeleton({ height = 300 }: { height?: number }) {
  return (
    <div className="rounded-xl border bg-card p-6">
      <Skeleton className="h-5 w-48 mb-4" />
      <div
        className="relative overflow-hidden rounded-lg bg-muted/50"
        style={{ height }}
      >
        <div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent" />

        {/* Area wave placeholder */}
        <svg className="absolute inset-4" viewBox="0 0 100 50" preserveAspectRatio="none">
          <path
            d="M0 40 Q 10 30, 20 35 T 40 25 T 60 30 T 80 20 T 100 25 L 100 50 L 0 50 Z"
            className="fill-muted"
          />
          <path
            d="M0 45 Q 10 40, 20 42 T 40 38 T 60 40 T 80 35 T 100 38 L 100 50 L 0 50 Z"
            className="fill-muted/50"
          />
        </svg>
      </div>
    </div>
  )
}

// Pie Chart Skeleton
export function PieChartSkeleton({ height = 300 }: { height?: number }) {
  return (
    <div className="rounded-xl border bg-card p-6">
      <Skeleton className="h-5 w-40 mb-4" />
      <div
        className="relative flex items-center justify-center overflow-hidden rounded-lg bg-muted/50"
        style={{ height }}
      >
        <div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent" />

        {/* Donut placeholder */}
        <div className="relative w-40 h-40">
          <div className="absolute inset-0 rounded-full border-[20px] border-muted" />
          <div className="absolute inset-6 rounded-full bg-card" />
        </div>

        {/* Legend placeholders */}
        <div className="absolute right-4 top-1/2 -translate-y-1/2 space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex items-center gap-2">
              <Skeleton className="h-3 w-3 rounded-full" />
              <Skeleton className="h-3 w-16" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Table Row Skeleton
export function TableRowSkeleton({ columns = 7 }: { columns?: number }) {
  return (
    <tr className="border-b">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton className={cn('h-4', i === 0 ? 'w-32' : 'w-16')} />
        </td>
      ))}
    </tr>
  )
}

// Table Skeleton
export function TableSkeleton({ rows = 5, columns = 7 }: { rows?: number; columns?: number }) {
  return (
    <div className="rounded-xl border bg-card overflow-hidden">
      <div className="px-6 py-4 border-b">
        <Skeleton className="h-5 w-48" />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50">
              {Array.from({ length: columns }).map((_, i) => (
                <th key={i} className="px-4 py-3 text-left">
                  <Skeleton className="h-4 w-20" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: rows }).map((_, i) => (
              <TableRowSkeleton key={i} columns={columns} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Alert Card Skeleton
export function AlertSkeleton() {
  return (
    <div className="p-4 rounded-lg bg-muted/30 border-l-4 border-muted">
      <div className="flex items-start gap-3">
        <Skeleton className="h-5 w-5 rounded mt-0.5" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-48" />
          <Skeleton className="h-3 w-20" />
        </div>
      </div>
    </div>
  )
}

// Full Dashboard Skeleton
export function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <div className="flex gap-3">
          <Skeleton className="h-10 w-24 rounded-lg" />
          <Skeleton className="h-10 w-24 rounded-lg" />
        </div>
      </div>

      {/* Filter Bar */}
      <Skeleton className="h-24 w-full rounded-lg" />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <KPICardSkeleton key={i} />
        ))}
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {[1, 2, 3, 4, 5].map((i) => (
          <KPICardSkeleton key={i} size="small" />
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
    </div>
  )
}

export default Skeleton
