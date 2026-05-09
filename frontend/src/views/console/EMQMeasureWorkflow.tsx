/**
 * EMQ Measure Workflow — operator-triggered EMQ measurement for a
 * (platform, pixel_id) pair, plus the rolling history of prior runs.
 *
 * Surfaces POST /audit-services/emq/measure + GET /audit-services/emq/history.
 * Mounted at /console/emq-measure under the platform-owner Operations
 * group.
 */

import { useState } from 'react';
import { ArrowPathIcon, BeakerIcon, PlayIcon } from '@heroicons/react/24/outline';
import {
  useMeasureEMQ,
  useEMQHistory,
  type EMQPlatform,
  type EMQMeasurementResult,
} from '@/api/emqMeasure';
import { Card } from '@/components/primitives/Card';
import { KPI } from '@/components/primitives/KPI';
import { StatusPill, type StatusPillVariant } from '@/components/primitives/StatusPill';
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable';
import { cn } from '@/lib/utils';

const PLATFORMS: { value: EMQPlatform; label: string }[] = [
  { value: 'meta', label: 'Meta (Facebook/Instagram)' },
  { value: 'google', label: 'Google Ads' },
  { value: 'tiktok', label: 'TikTok Ads' },
  { value: 'snapchat', label: 'Snapchat Ads' },
];

const FIELD_SURFACE =
  'w-full bg-muted/40 border border-border rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary';

function scoreVariant(score: number | null): StatusPillVariant {
  if (score == null) return 'neutral';
  if (score >= 70) return 'healthy';
  if (score >= 40) return 'degraded';
  return 'unhealthy';
}

function formatScore(score: number | null): string {
  if (score == null) return '—';
  return score.toFixed(1);
}

interface HistoryRow {
  measured_at: string;
  overall_score: number | null;
  parameter_quality: number | null;
  event_coverage: number | null;
  match_rate: number | null;
}

const historyColumns: DataTableColumn<HistoryRow>[] = [
  {
    id: 'measured_at',
    header: 'Measured',
    cell: (r) => (
      <span className="font-mono text-xs text-muted-foreground">
        {r.measured_at ? new Date(r.measured_at).toLocaleString() : '—'}
      </span>
    ),
    sortable: true,
    sortAccessor: (r) => new Date(r.measured_at).getTime(),
  },
  {
    id: 'overall_score',
    header: 'Overall',
    cell: (r) => (
      <StatusPill variant={scoreVariant(r.overall_score)} size="sm">
        {formatScore(r.overall_score)}
      </StatusPill>
    ),
    sortable: true,
    sortAccessor: (r) => r.overall_score ?? -1,
  },
  {
    id: 'parameter_quality',
    header: 'Param quality',
    cell: (r) => (
      <span className="font-mono tabular-nums text-xs">{formatScore(r.parameter_quality)}</span>
    ),
    cellClassName: 'text-right',
    headerClassName: 'text-right',
  },
  {
    id: 'event_coverage',
    header: 'Coverage',
    cell: (r) => (
      <span className="font-mono tabular-nums text-xs">{formatScore(r.event_coverage)}</span>
    ),
    cellClassName: 'text-right',
    headerClassName: 'text-right',
  },
  {
    id: 'match_rate',
    header: 'Match rate',
    cell: (r) => (
      <span className="font-mono tabular-nums text-xs">{formatScore(r.match_rate)}</span>
    ),
    cellClassName: 'text-right',
    headerClassName: 'text-right',
  },
];

export default function EMQMeasureWorkflow() {
  const [platform, setPlatform] = useState<EMQPlatform>('meta');
  const [pixelId, setPixelId] = useState('');
  const [days, setDays] = useState(30);
  const [latest, setLatest] = useState<EMQMeasurementResult | null>(null);

  const measure = useMeasureEMQ();
  const historyQuery = useEMQHistory(platform, pixelId, days);

  const canMeasure = pixelId.trim().length > 0 && !measure.isPending;

  const runMeasurement = async () => {
    if (!canMeasure) return;
    setLatest(null);
    try {
      const result = await measure.mutateAsync({
        platform,
        pixel_id: pixelId.trim(),
      });
      setLatest(result);
    } catch (e) {
      // Network errors handled by surfacing measure.isError below.
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">EMQ Measurement</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Trigger a manual Event Match Quality measurement for a pixel/dataset and inspect the
          rolling history. Server-side computation; results publish to the pixel's quality timeline.
        </p>
      </header>

      <Card className="p-6">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="block text-sm text-muted-foreground mb-1">Platform</label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value as EMQPlatform)}
              className={FIELD_SURFACE}
            >
              {PLATFORMS.map((p) => (
                <option key={p.value} value={p.value} className="bg-card">
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-muted-foreground mb-1">Pixel / dataset ID</label>
            <input
              value={pixelId}
              onChange={(e) => setPixelId(e.target.value)}
              placeholder="e.g. 1234567890"
              className={FIELD_SURFACE}
            />
          </div>
          <div>
            <label className="block text-sm text-muted-foreground mb-1">History window</label>
            <select
              value={days}
              onChange={(e) => setDays(parseInt(e.target.value))}
              className={FIELD_SURFACE}
            >
              {[7, 14, 30, 60, 90].map((d) => (
                <option key={d} value={d} className="bg-card">
                  Last {d} days
                </option>
              ))}
            </select>
          </div>
        </div>
        <button
          onClick={runMeasurement}
          disabled={!canMeasure}
          className="mt-4 bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
        >
          {measure.isPending ? (
            <ArrowPathIcon className="w-5 h-5 animate-spin" />
          ) : (
            <PlayIcon className="w-5 h-5" />
          )}
          Run measurement
        </button>
      </Card>

      {measure.isError && (
        <Card className="p-4 bg-danger/10 border border-danger/30 text-danger text-sm">
          Could not reach the EMQ measurement service.
        </Card>
      )}

      {latest && !latest.success && latest.error && (
        <Card className="p-4 bg-danger/10 border border-danger/30 text-danger text-sm">
          {latest.error}
        </Card>
      )}

      {latest?.success && (
        <>
          <section className="grid gap-4 md:grid-cols-4">
            <KPI
              label="Overall EMQ"
              value={formatScore(latest.overall_score)}
              status={{
                label:
                  scoreVariant(latest.overall_score) === 'healthy'
                    ? 'reliable'
                    : scoreVariant(latest.overall_score) === 'degraded'
                      ? 'directional'
                      : 'unsafe',
                variant: scoreVariant(latest.overall_score),
                pulse: scoreVariant(latest.overall_score) === 'healthy',
              }}
            />
            <KPI label="Parameter quality" value={formatScore(latest.parameter_quality)} />
            <KPI label="Event coverage" value={formatScore(latest.event_coverage)} />
            <KPI label="Match rate" value={formatScore(latest.match_rate)} />
          </section>

          {latest.recommendations && latest.recommendations.length > 0 && (
            <Card className="p-6">
              <h2 className="mb-4 font-mono text-sm uppercase tracking-wider text-muted-foreground">
                Recommendations
              </h2>
              <ul className="space-y-2">
                {latest.recommendations.map((rec, idx) => (
                  <li
                    key={idx}
                    className="flex gap-2 text-sm rounded-xl border border-border bg-muted/40 p-3"
                  >
                    <span className="font-mono text-xs text-muted-foreground tabular-nums shrink-0">
                      {idx + 1}.
                    </span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </>
      )}

      <Card className="p-6">
        <header className="mb-4 flex items-center justify-between">
          <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
            Measurement history
          </h2>
          <span className="text-xs text-muted-foreground">last {days}d</span>
        </header>
        {!pixelId.trim() ? (
          <div
            className={cn(
              'flex flex-col items-center gap-2 py-10 text-center text-sm text-muted-foreground'
            )}
          >
            <BeakerIcon className="w-10 h-10 opacity-40" />
            <p>Enter a pixel ID to load the history.</p>
          </div>
        ) : historyQuery.isError ? (
          <p className="text-sm text-danger">Could not load measurement history.</p>
        ) : !historyQuery.isLoading && (historyQuery.data ?? []).length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No prior measurements for this pixel in the window.
          </p>
        ) : (
          <DataTable<HistoryRow>
            data={(historyQuery.data ?? []) as HistoryRow[]}
            columns={historyColumns}
            loading={historyQuery.isLoading}
            rowKey={(r) => r.measured_at}
            ariaLabel="EMQ measurement history"
          />
        )}
      </Card>
    </div>
  );
}
