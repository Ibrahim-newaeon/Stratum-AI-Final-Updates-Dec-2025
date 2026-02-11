/**
 * CDP Events - Event timeline and analytics
 */

import { useMemo, useState } from 'react';
import {
  ArrowDownTrayIcon,
  ChartBarIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import {
  type AnomalySeverity,
  type DailyVolume,
  type EventByName,
  useAnomalySummary,
  useEventAnomalies,
  useEventStatistics,
  useEventTrends,
  useExportAudience,
} from '@/api/cdp';

// Severity Badge
function SeverityBadge({ severity }: { severity: AnomalySeverity }) {
  const config = {
    low: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
    high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
    critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  };

  return (
    <span className={cn('px-2 py-1 rounded-full text-xs font-medium capitalize', config[severity])}>
      {severity}
    </span>
  );
}

// Daily Volume Chart
function VolumeChart({ data, height = 200 }: { data: DailyVolume[]; height?: number }) {
  const maxCount = Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="relative" style={{ height }}>
      <div className="absolute inset-0 flex items-end gap-1">
        {data.map((day, i) => {
          const heightPercent = (day.count / maxCount) * 100;
          return (
            <div key={i} className="flex-1 flex flex-col items-center justify-end h-full group">
              <div
                className="w-full bg-primary/80 rounded-t hover:bg-primary transition-colors cursor-pointer relative"
                style={{ height: `${heightPercent}%`, minHeight: '4px' }}
              >
                {/* Tooltip */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-popover border rounded shadow-lg text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                  <p className="font-medium">{day.count.toLocaleString()} events</p>
                  <p className="text-muted-foreground">{new Date(day.date).toLocaleDateString()}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      {/* X-axis labels */}
      <div className="absolute -bottom-6 inset-x-0 flex justify-between text-xs text-muted-foreground">
        <span>
          {data.length > 0
            ? new Date(data[0].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
            : ''}
        </span>
        <span>
          {data.length > 0
            ? new Date(data[data.length - 1].date).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
              })
            : ''}
        </span>
      </div>
    </div>
  );
}

// Events by Name Chart (Horizontal Bar)
function EventsBarChart({ data }: { data: EventByName[] }) {
  const maxCount = Math.max(...data.map((d) => d.count), 1);
  const topEvents = data.slice(0, 10);

  return (
    <div className="space-y-3">
      {topEvents.map((event, i) => {
        const widthPercent = (event.count / maxCount) * 100;
        return (
          <div key={event.event_name}>
            <div className="flex justify-between text-sm mb-1">
              <span className="font-medium truncate">{event.event_name}</span>
              <span className="text-muted-foreground ml-2">{event.count.toLocaleString()}</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all duration-500',
                  i === 0 ? 'bg-primary' : i < 3 ? 'bg-primary/70' : 'bg-primary/50'
                )}
                style={{ width: `${widthPercent}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Trend Indicator
function TrendIndicator({ trend, change }: { trend: string; change: number }) {
  const isUp = trend === 'up' || change > 0;
  const isDown = trend === 'down' || change < 0;

  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          'text-2xl font-bold',
          isUp ? 'text-green-500' : isDown ? 'text-red-500' : 'text-muted-foreground'
        )}
      >
        {isUp ? '+' : ''}
        {change.toFixed(1)}%
      </span>
      <span className="text-sm text-muted-foreground">vs last period</span>
    </div>
  );
}

// EMQ Distribution Chart
function EMQDistributionChart({ data }: { data: Array<{ score_range: string; count: number }> }) {
  const total = data.reduce((sum, d) => sum + d.count, 0);

  const getColor = (range: string) => {
    if (range.includes('90') || range.includes('80-')) return 'bg-green-400';
    if (range.includes('70') || range.includes('60-')) return 'bg-yellow-400';
    if (range.includes('50') || range.includes('40-')) return 'bg-orange-400';
    return 'bg-red-400';
  };

  return (
    <div className="space-y-2">
      {data.map((bucket) => {
        const percent = total > 0 ? (bucket.count / total) * 100 : 0;
        return (
          <div key={bucket.score_range} className="flex items-center gap-3">
            <span className="text-xs w-16 text-muted-foreground">{bucket.score_range}</span>
            <div className="flex-1 h-4 bg-muted rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all', getColor(bucket.score_range))}
                style={{ width: `${percent}%` }}
              />
            </div>
            <span className="text-xs w-12 text-right">{percent.toFixed(1)}%</span>
          </div>
        );
      })}
    </div>
  );
}

export default function CDPEvents() {
  const [periodDays, setPeriodDays] = useState(30);
  const [eventFilter, setEventFilter] = useState('');
  const [showAnomalies, setShowAnomalies] = useState(false);

  const { data: stats, isLoading: statsLoading } = useEventStatistics(periodDays);
  const { data: trends, isLoading: trendsLoading } = useEventTrends(periodDays);
  const { data: summary } = useAnomalySummary();
  const { data: anomalies, isLoading: anomaliesLoading } = useEventAnomalies({
    window_days: 7,
    zscore_threshold: 2.0,
  });
  const exportMutation = useExportAudience();

  const filteredEvents = useMemo(() => {
    if (!stats?.events_by_name) return [];
    if (!eventFilter) return stats.events_by_name;
    return stats.events_by_name.filter((e) =>
      e.event_name.toLowerCase().includes(eventFilter.toLowerCase())
    );
  }, [stats, eventFilter]);

  const handleExport = async () => {
    try {
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - periodDays);
      await exportMutation.mutateAsync({
        format: 'csv',
        first_seen_after: startDate.toISOString().split('T')[0],
        limit: 10000,
      });
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Events Timeline</h1>
          <p className="text-muted-foreground mt-1">
            {stats?.total_events?.toLocaleString() || 0} events in the last {periodDays} days
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={periodDays}
            onChange={(e) => setPeriodDays(Number(e.target.value))}
            className="px-3 py-2 border rounded-lg bg-background text-sm"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <button
            onClick={handleExport}
            disabled={exportMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 border rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
          >
            <ArrowDownTrayIcon className="h-4 w-4" />
            Export
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-card rounded-xl border p-4">
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <ClockIcon className="h-4 w-4" />
            <span className="text-sm">Total Events</span>
          </div>
          {statsLoading ? (
            <div className="h-8 w-24 bg-muted animate-pulse rounded" />
          ) : (
            <p className="text-2xl font-bold">{stats?.total_events?.toLocaleString() || 0}</p>
          )}
        </div>

        <div className="bg-card rounded-xl border p-4">
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <ChartBarIcon className="h-4 w-4" />
            <span className="text-sm">Unique Profiles</span>
          </div>
          {statsLoading ? (
            <div className="h-8 w-24 bg-muted animate-pulse rounded" />
          ) : (
            <p className="text-2xl font-bold">{stats?.unique_profiles?.toLocaleString() || 0}</p>
          )}
        </div>

        <div className="bg-card rounded-xl border p-4">
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <CheckCircleIcon className="h-4 w-4" />
            <span className="text-sm">Avg EMQ Score</span>
          </div>
          {statsLoading ? (
            <div className="h-8 w-24 bg-muted animate-pulse rounded" />
          ) : (
            <p className="text-2xl font-bold">{stats?.avg_emq_score?.toFixed(1) || 'N/A'}</p>
          )}
        </div>

        <div className="bg-card rounded-xl border p-4">
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <ExclamationTriangleIcon className="h-4 w-4" />
            <span className="text-sm">Week over Week</span>
          </div>
          {trendsLoading ? (
            <div className="h-8 w-24 bg-muted animate-pulse rounded" />
          ) : trends ? (
            <TrendIndicator trend={trends.overall_trend} change={trends.overall_change_pct} />
          ) : (
            <p className="text-2xl font-bold">N/A</p>
          )}
        </div>
      </div>

      {/* Main Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Volume Timeline */}
        <div className="lg:col-span-2 bg-card rounded-xl border p-6">
          <h3 className="text-lg font-semibold mb-4">Event Volume</h3>
          {statsLoading ? (
            <div className="h-48 bg-muted animate-pulse rounded" />
          ) : stats?.daily_volume && stats.daily_volume.length > 0 ? (
            <div className="pb-8">
              <VolumeChart data={stats.daily_volume} />
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-muted-foreground">
              No event data available
            </div>
          )}
        </div>

        {/* EMQ Distribution */}
        <div className="bg-card rounded-xl border p-6">
          <h3 className="text-lg font-semibold mb-4">EMQ Score Distribution</h3>
          {statsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-4 bg-muted animate-pulse rounded" />
              ))}
            </div>
          ) : stats?.emq_distribution && stats.emq_distribution.length > 0 ? (
            <EMQDistributionChart data={stats.emq_distribution} />
          ) : (
            <p className="text-muted-foreground text-sm">No EMQ data available</p>
          )}
        </div>
      </div>

      {/* Events by Name */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card rounded-xl border p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Top Events</h3>
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                value={eventFilter}
                onChange={(e) => setEventFilter(e.target.value)}
                placeholder="Filter events..."
                className="pl-9 pr-3 py-1.5 text-sm border rounded-lg bg-background w-40"
              />
            </div>
          </div>
          {statsLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-6 bg-muted animate-pulse rounded" />
              ))}
            </div>
          ) : filteredEvents.length > 0 ? (
            <EventsBarChart data={filteredEvents} />
          ) : (
            <p className="text-muted-foreground text-sm">No events found</p>
          )}
        </div>

        {/* Events by Source */}
        <div className="bg-card rounded-xl border p-6">
          <h3 className="text-lg font-semibold mb-4">Events by Source</h3>
          {statsLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-6 bg-muted animate-pulse rounded" />
              ))}
            </div>
          ) : stats?.events_by_source && stats.events_by_source.length > 0 ? (
            <div className="space-y-3">
              {stats.events_by_source.map((source) => (
                <div
                  key={source.source_name}
                  className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                >
                  <span className="font-medium">{source.source_name}</span>
                  <span className="text-muted-foreground">{source.count.toLocaleString()}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-sm">No source data available</p>
          )}
        </div>
      </div>

      {/* Anomalies Section */}
      <div className="bg-card rounded-xl border p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold">Anomaly Detection</h3>
            {anomalies && anomalies.anomaly_count > 0 && (
              <span className="px-2 py-1 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400 rounded-full text-xs font-medium">
                {anomalies.anomaly_count} detected
              </span>
            )}
          </div>
          <button
            onClick={() => setShowAnomalies(!showAnomalies)}
            className="text-sm text-primary hover:underline"
          >
            {showAnomalies ? 'Hide Details' : 'View Details'}
          </button>
        </div>

        {/* Health Status */}
        <div className="flex items-center gap-4 mb-4">
          <div className="flex items-center gap-2">
            {summary?.health_status === 'healthy' ? (
              <CheckCircleIcon className="h-5 w-5 text-green-500" />
            ) : (
              <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
            )}
            <span className="font-medium capitalize">{summary?.health_status || 'Unknown'}</span>
          </div>
          <span className="text-muted-foreground">|</span>
          <span className="text-sm text-muted-foreground">
            Trend: <span className="capitalize">{summary?.volume_trend || 'N/A'}</span>
          </span>
        </div>

        {/* Anomaly List */}
        {showAnomalies && (
          <div className="space-y-3 mt-4 pt-4 border-t">
            {anomaliesLoading ? (
              <div className="space-y-2">
                {[1, 2].map((i) => (
                  <div key={i} className="h-16 bg-muted animate-pulse rounded" />
                ))}
              </div>
            ) : anomalies?.anomalies && anomalies.anomalies.length > 0 ? (
              anomalies.anomalies.map((anomaly, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-4 bg-muted/50 rounded-lg"
                >
                  <div>
                    <p className="font-medium">{anomaly.source_name}</p>
                    <p className="text-sm text-muted-foreground">
                      {anomaly.metric}: {anomaly.current_value.toLocaleString()} (
                      {anomaly.pct_change >= 0 ? '+' : ''}
                      {anomaly.pct_change.toFixed(1)}% from baseline)
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <SeverityBadge severity={anomaly.severity} />
                    <span
                      className={cn(
                        'text-sm font-medium',
                        anomaly.direction === 'high' ? 'text-red-500' : 'text-blue-500'
                      )}
                    >
                      {anomaly.direction === 'high' ? 'Spike' : 'Drop'}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <CheckCircleIcon className="h-12 w-12 mx-auto mb-3 text-green-500" />
                <p>No anomalies detected in the last 7 days</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
