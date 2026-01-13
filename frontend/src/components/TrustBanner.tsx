/**
 * Stratum AI - Trust Banner Component
 *
 * Displays trust status banners at the top of dashboards.
 * Shows signal health, attribution variance, and automation status.
 */

import React from 'react'
import { useTrustStatus, getStatusLabel, TrustBanner as TrustBannerType } from '@/api/trustLayer'
import { useCanFeature } from '@/stores/featureFlagsStore'

// =============================================================================
// Types
// =============================================================================

interface TrustBannerProps {
  tenantId: number
  date?: string
  showDetails?: boolean
  onViewDetails?: () => void
}

interface BannerAlertProps {
  banner: TrustBannerType
  onDismiss?: () => void
}

// =============================================================================
// Sub-components
// =============================================================================

const BannerAlert: React.FC<BannerAlertProps> = ({ banner, onDismiss }) => {
  const bgColors = {
    info: 'bg-blue-500/10 border-blue-500/30 dark:bg-blue-500/10 dark:border-blue-500/20',
    warning: 'bg-amber-500/10 border-amber-500/30 dark:bg-amber-500/10 dark:border-amber-500/20',
    error: 'bg-red-500/10 border-red-500/30 dark:bg-red-500/10 dark:border-red-500/20',
  }

  const iconColors = {
    info: 'text-blue-500 dark:text-blue-400',
    warning: 'text-amber-500 dark:text-amber-400',
    error: 'text-red-500 dark:text-red-400',
  }

  const icons = {
    info: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
      </svg>
    ),
    warning: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
      </svg>
    ),
    error: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
      </svg>
    ),
  }

  return (
    <div className={`rounded-lg border p-4 ${bgColors[banner.type]}`}>
      <div className="flex items-start">
        <div className={`flex-shrink-0 ${iconColors[banner.type]}`}>
          {icons[banner.type]}
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium text-foreground">{banner.title}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{banner.message}</p>
          {banner.actions.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {banner.actions.map((action, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-card border border-border text-foreground"
                >
                  {action}
                </span>
              ))}
            </div>
          )}
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 ml-4 text-muted-foreground hover:text-foreground transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            aria-label="Dismiss alert"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        )}
      </div>
    </div>
  )
}

const StatusIndicator: React.FC<{ status: string; label: string }> = ({ status, label }) => {
  const colorClasses: Record<string, string> = {
    ok: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400',
    healthy: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400',
    risk: 'bg-amber-500/15 text-amber-700 dark:text-amber-400',
    minor_variance: 'bg-amber-500/15 text-amber-700 dark:text-amber-400',
    degraded: 'bg-orange-500/15 text-orange-700 dark:text-orange-400',
    moderate_variance: 'bg-orange-500/15 text-orange-700 dark:text-orange-400',
    critical: 'bg-red-500/15 text-red-700 dark:text-red-400',
    high_variance: 'bg-red-500/15 text-red-700 dark:text-red-400',
    no_data: 'bg-muted text-muted-foreground',
  }

  const dotColors: Record<string, string> = {
    ok: 'bg-emerald-500',
    healthy: 'bg-emerald-500',
    risk: 'bg-amber-500',
    minor_variance: 'bg-amber-500',
    degraded: 'bg-orange-500',
    moderate_variance: 'bg-orange-500',
    critical: 'bg-red-500',
    high_variance: 'bg-red-500',
    no_data: 'bg-muted-foreground',
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClasses[status] || 'bg-muted text-muted-foreground'}`}
      role="status"
      aria-label={`Status: ${label}`}
    >
      <span className={`w-2 h-2 rounded-full mr-1.5 ${dotColors[status] || 'bg-muted-foreground'}`} aria-hidden="true" />
      {label}
    </span>
  )
}

// =============================================================================
// Main Component
// =============================================================================

export const TrustBanner: React.FC<TrustBannerProps> = ({
  tenantId,
  date,
  showDetails = true,
  onViewDetails,
}) => {
  const canSignalHealth = useCanFeature('signal_health')
  const canAttributionVariance = useCanFeature('attribution_variance')

  const { data: trustStatus, isLoading, error } = useTrustStatus(tenantId, date)

  // Don't render if no trust features are enabled
  if (!canSignalHealth && !canAttributionVariance) {
    return null
  }

  if (isLoading) {
    return (
      <div className="bg-card rounded-lg border border-border p-4 animate-pulse">
        <div className="flex items-center space-x-4">
          <div className="h-4 skeleton w-24" />
          <div className="h-4 skeleton w-32" />
          <div className="h-4 skeleton w-20" />
        </div>
      </div>
    )
  }

  if (error || !trustStatus) {
    return null
  }

  const hasBanners = trustStatus.banners.length > 0
  const _showSummary = showDetails && (trustStatus.signal_health || trustStatus.attribution_variance)

  return (
    <div className="space-y-3">
      {/* Summary Bar */}
      <div className="bg-card rounded-lg border border-border p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-foreground">Trust Status:</span>
              <StatusIndicator
                status={trustStatus.overall_status}
                label={getStatusLabel(trustStatus.overall_status)}
              />
            </div>

            {trustStatus.signal_health && canSignalHealth && (
              <div className="flex items-center space-x-2 pl-4 border-l border-border">
                <span className="text-sm text-muted-foreground">Signal Health:</span>
                <StatusIndicator
                  status={trustStatus.signal_health.status}
                  label={getStatusLabel(trustStatus.signal_health.status)}
                />
              </div>
            )}

            {trustStatus.attribution_variance && canAttributionVariance && (
              <div className="flex items-center space-x-2 pl-4 border-l border-border">
                <span className="text-sm text-muted-foreground">Attribution:</span>
                <StatusIndicator
                  status={trustStatus.attribution_variance.status}
                  label={getStatusLabel(trustStatus.attribution_variance.status)}
                />
              </div>
            )}
          </div>

          <div className="flex items-center space-x-4">
            {!trustStatus.automation_allowed && (
              <span
                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-500/15 text-red-700 dark:text-red-400"
                role="alert"
                aria-label="Automation is blocked due to trust status"
              >
                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                </svg>
                Automation Blocked
              </span>
            )}

            {onViewDetails && (
              <button
                onClick={onViewDetails}
                className="text-sm text-primary hover:text-primary/80 font-medium transition-colors focus:outline-none focus-visible:underline"
              >
                View Details
              </button>
            )}
          </div>
        </div>

        {/* Date indicator */}
        <div className="mt-2 text-xs text-muted-foreground">
          Data as of: {new Date(trustStatus.date).toLocaleDateString()}
        </div>
      </div>

      {/* Alert Banners */}
      {hasBanners && (
        <div className="space-y-2">
          {trustStatus.banners.map((banner, index) => (
            <BannerAlert key={index} banner={banner} />
          ))}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Compact Banner Variant
// =============================================================================

export const TrustBannerCompact: React.FC<TrustBannerProps> = ({
  tenantId,
  date,
  onViewDetails,
}) => {
  const canSignalHealth = useCanFeature('signal_health')
  const canAttributionVariance = useCanFeature('attribution_variance')

  const { data: trustStatus, isLoading } = useTrustStatus(tenantId, date)

  if (!canSignalHealth && !canAttributionVariance) {
    return null
  }

  if (isLoading || !trustStatus) {
    return null
  }

  // Only show compact banner if there are issues
  if (trustStatus.overall_status === 'ok' && trustStatus.banners.length === 0) {
    return null
  }

  return (
    <button
      className={`w-full rounded-lg px-4 py-2 flex items-center justify-between cursor-pointer hover:opacity-90 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        trustStatus.overall_status === 'critical'
          ? 'bg-red-500/10 border border-red-500/30 dark:border-red-500/20'
          : trustStatus.overall_status === 'degraded'
          ? 'bg-orange-500/10 border border-orange-500/30 dark:border-orange-500/20'
          : 'bg-amber-500/10 border border-amber-500/30 dark:border-amber-500/20'
      }`}
      onClick={onViewDetails}
      aria-label="View trust status details"
    >
      <div className="flex items-center space-x-2">
        <StatusIndicator
          status={trustStatus.overall_status}
          label={getStatusLabel(trustStatus.overall_status)}
        />
        <span className="text-sm text-foreground">
          {trustStatus.banners.length > 0
            ? trustStatus.banners[0].title
            : 'Trust status requires attention'}
        </span>
      </div>
      <svg className="w-4 h-4 text-muted-foreground" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
        <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
      </svg>
    </button>
  )
}

export default TrustBanner
