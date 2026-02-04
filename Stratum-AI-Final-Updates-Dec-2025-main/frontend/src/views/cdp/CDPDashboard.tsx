/**
 * CDP Dashboard - Main overview page for Customer Data Platform
 */

import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowTrendingDownIcon,
  ArrowTrendingUpIcon,
  ArrowUpOnSquareIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  ShareIcon,
  TagIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import {
  useAnomalySummary,
  useCDPHealth,
  useEventStatistics,
  useProfileStatistics,
  useSegments,
} from '@/api/cdp';

// Stat Card Component
function StatCard({
  title,
  value,
  change,
  changeLabel,
  icon: Icon,
  href,
  loading,
  variant = 'info',
}: {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon: React.ElementType;
  href?: string;
  loading?: boolean;
  variant?: 'success' | 'warning' | 'error' | 'info' | 'premium' | 'active';
}) {
  const content = (
    <div className={cn('metric-card p-6', variant)}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          {loading ? (
            <div className="h-8 w-24 bg-muted animate-pulse rounded mt-2" />
          ) : (
            <p className="text-2xl font-bold mt-2">{value}</p>
          )}
          {change !== undefined && (
            <div className="flex items-center gap-1 mt-2">
              {change >= 0 ? (
                <ArrowTrendingUpIcon className="h-4 w-4 text-green-500" />
              ) : (
                <ArrowTrendingDownIcon className="h-4 w-4 text-red-500" />
              )}
              <span
                className={cn(
                  'text-sm font-medium',
                  change >= 0 ? 'text-green-500' : 'text-red-500'
                )}
              >
                {change >= 0 ? '+' : ''}
                {change.toFixed(1)}%
              </span>
              {changeLabel && <span className="text-sm text-muted-foreground">{changeLabel}</span>}
            </div>
          )}
        </div>
        <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
          <Icon className="h-6 w-6 text-primary" />
        </div>
      </div>
    </div>
  );

  if (href) {
    return <Link to={href}>{content}</Link>;
  }
  return content;
}

// Health Status Badge
function HealthBadge({ status }: { status: string }) {
  const config = {
    healthy: {
      color: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      icon: CheckCircleIcon,
    },
    degraded: {
      color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      icon: ExclamationTriangleIcon,
    },
    unhealthy: {
      color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      icon: ExclamationTriangleIcon,
    },
  }[status] || { color: 'bg-gray-100 text-gray-800', icon: CheckCircleIcon };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium',
        config.color
      )}
    >
      <config.icon className="h-4 w-4" />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

// Lifecycle Distribution Chart
function LifecycleChart({ data }: { data: Record<string, number> }) {
  const stages = [
    { key: 'anonymous', label: 'Anonymous', color: 'bg-gray-400' },
    { key: 'known', label: 'Known', color: 'bg-blue-400' },
    { key: 'customer', label: 'Customer', color: 'bg-green-400' },
    { key: 'churned', label: 'Churned', color: 'bg-red-400' },
  ];

  const total = Object.values(data).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-3">
      {stages.map((stage) => {
        const count = data[stage.key] || 0;
        const percentage = total > 0 ? (count / total) * 100 : 0;
        return (
          <div key={stage.key}>
            <div className="flex justify-between text-sm mb-1">
              <span className="font-medium">{stage.label}</span>
              <span className="text-muted-foreground">
                {count.toLocaleString()} ({percentage.toFixed(1)}%)
              </span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all duration-500', stage.color)}
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Event Volume Chart (Simple Bar Chart)
function EventVolumeChart({ data }: { data: Array<{ date: string; count: number }> }) {
  const maxCount = Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="flex items-end gap-1 h-32">
      {data.slice(-14).map((day, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1">
          <div
            className="w-full bg-primary/80 rounded-t hover:bg-primary transition-colors"
            style={{ height: `${(day.count / maxCount) * 100}%`, minHeight: '4px' }}
            title={`${day.date}: ${day.count.toLocaleString()} events`}
          />
          {i % 2 === 0 && (
            <span className="text-[10px] text-muted-foreground">
              {new Date(day.date).getDate()}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

export default function CDPDashboard() {
  const { data: health, isLoading: healthLoading } = useCDPHealth();
  const { data: profileStats, isLoading: profileLoading } = useProfileStatistics();
  const { data: eventStats, isLoading: eventLoading } = useEventStatistics(30);
  const { data: segments, isLoading: segmentsLoading } = useSegments();
  const { data: anomalySummary } = useAnomalySummary();

  const activeSegments = useMemo(() => {
    return segments?.segments.filter((s) => s.status === 'active').length || 0;
  }, [segments]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Customer Data Platform</h1>
          <p className="text-muted-foreground mt-1">
            Unified customer profiles, segments, and behavioral data
          </p>
        </div>
        <div className="flex items-center gap-3">
          {health && <HealthBadge status={health.status} />}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Profiles"
          value={profileStats?.total_profiles?.toLocaleString() || '0'}
          change={
            profileStats?.new_profiles_7d
              ? (profileStats.new_profiles_7d / (profileStats.total_profiles || 1)) * 100
              : undefined
          }
          changeLabel="new this week"
          icon={UserGroupIcon}
          href="/dashboard/cdp/profiles"
          loading={profileLoading}
          variant="success"
        />
        <StatCard
          title="Active Segments"
          value={activeSegments}
          icon={TagIcon}
          href="/dashboard/cdp/segments"
          loading={segmentsLoading}
          variant="premium"
        />
        <StatCard
          title="Events (30d)"
          value={eventStats?.total_events?.toLocaleString() || '0'}
          change={anomalySummary?.wow_change_pct}
          changeLabel="vs last week"
          icon={ClockIcon}
          href="/dashboard/cdp/events"
          loading={eventLoading}
          variant="active"
        />
        <StatCard
          title="Avg EMQ Score"
          value={eventStats?.avg_emq_score?.toFixed(1) || 'N/A'}
          icon={ShareIcon}
          href="/dashboard/cdp/identity"
          loading={eventLoading}
          variant="info"
        />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Lifecycle Distribution */}
        <div className="metric-card info p-6">
          <h3 className="text-lg font-semibold mb-4">Profile Lifecycle</h3>
          {profileLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-6 bg-muted animate-pulse rounded" />
              ))}
            </div>
          ) : profileStats?.lifecycle_distribution ? (
            <LifecycleChart data={profileStats.lifecycle_distribution} />
          ) : (
            <p className="text-muted-foreground text-sm">No data available</p>
          )}
          <div className="mt-4 pt-4 border-t grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Email Coverage</p>
              <p className="font-semibold">{profileStats?.email_coverage_pct?.toFixed(1) || 0}%</p>
            </div>
            <div>
              <p className="text-muted-foreground">Phone Coverage</p>
              <p className="font-semibold">{profileStats?.phone_coverage_pct?.toFixed(1) || 0}%</p>
            </div>
          </div>
        </div>

        {/* Event Volume */}
        <div className="metric-card active p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Event Volume (Last 14 Days)</h3>
            <Link to="/dashboard/cdp/events" className="text-sm text-primary hover:underline">
              View all events
            </Link>
          </div>
          {eventLoading ? (
            <div className="h-32 bg-muted animate-pulse rounded" />
          ) : eventStats?.daily_volume ? (
            <EventVolumeChart data={eventStats.daily_volume} />
          ) : (
            <p className="text-muted-foreground text-sm">No event data available</p>
          )}
          {eventStats?.events_by_name && eventStats.events_by_name.length > 0 && (
            <div className="mt-4 pt-4 border-t">
              <p className="text-sm font-medium mb-2">Top Events</p>
              <div className="flex flex-wrap gap-2">
                {eventStats.events_by_name.slice(0, 5).map((event) => (
                  <span
                    key={event.event_name}
                    className="px-2 py-1 bg-muted rounded text-xs font-medium"
                  >
                    {event.event_name}: {event.count.toLocaleString()}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <Link
          to="/dashboard/cdp/profiles"
          className="metric-card info p-4 flex items-center gap-4"
        >
          <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
            <UserGroupIcon className="h-5 w-5 text-blue-500" />
          </div>
          <div>
            <p className="font-medium">View Profiles</p>
            <p className="text-sm text-muted-foreground">Browse & manage customers</p>
          </div>
        </Link>
        <Link
          to="/dashboard/cdp/segments"
          className="metric-card premium p-4 flex items-center gap-4"
        >
          <div className="h-10 w-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
            <TagIcon className="h-5 w-5 text-purple-500" />
          </div>
          <div>
            <p className="font-medium">Build Segments</p>
            <p className="text-sm text-muted-foreground">Create audience segments</p>
          </div>
        </Link>
        <Link
          to="/dashboard/cdp/events"
          className="metric-card success p-4 flex items-center gap-4"
        >
          <div className="h-10 w-10 rounded-lg bg-green-500/10 flex items-center justify-center">
            <ClockIcon className="h-5 w-5 text-green-500" />
          </div>
          <div>
            <p className="font-medium">Event Timeline</p>
            <p className="text-sm text-muted-foreground">Track user behavior</p>
          </div>
        </Link>
        <Link
          to="/dashboard/cdp/identity"
          className="metric-card warning p-4 flex items-center gap-4"
        >
          <div className="h-10 w-10 rounded-lg bg-orange-500/10 flex items-center justify-center">
            <ShareIcon className="h-5 w-5 text-orange-500" />
          </div>
          <div>
            <p className="font-medium">Identity Graph</p>
            <p className="text-sm text-muted-foreground">Visualize connections</p>
          </div>
        </Link>
        <Link
          to="/dashboard/cdp/audience-sync"
          className="metric-card active p-4 flex items-center gap-4"
        >
          <div className="h-10 w-10 rounded-lg bg-pink-500/10 flex items-center justify-center">
            <ArrowUpOnSquareIcon className="h-5 w-5 text-pink-500" />
          </div>
          <div>
            <p className="font-medium">Audience Sync</p>
            <p className="text-sm text-muted-foreground">Push to ad platforms</p>
          </div>
        </Link>
      </div>

      {/* Anomaly Alerts */}
      {anomalySummary && anomalySummary.health_status !== 'healthy' && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 dark:text-yellow-400 mt-0.5" />
            <div>
              <p className="font-medium text-yellow-800 dark:text-yellow-200">Data Quality Alert</p>
              <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                Event volume has changed by {anomalySummary.wow_change_pct?.toFixed(1)}% compared to
                last week. Current trend: {anomalySummary.volume_trend}.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
