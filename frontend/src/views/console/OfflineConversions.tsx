/**
 * Offline Conversions — operator workflow for uploading offline events
 * to ad platforms and inspecting prior batches.
 *
 * Surfaces POST /audit-services/offline-conversions/upload +
 * GET /audit-services/offline-conversions/batches.
 *
 * Mounted at /console/offline-conversions under Operations.
 */

import { useMemo, useState } from 'react';
import { ArrowPathIcon, CloudArrowUpIcon } from '@heroicons/react/24/outline';
import {
  useUploadOfflineConversions,
  useOfflineConversionBatches,
  type OfflineConversionRecord,
  type OfflineConversionBatch,
  type OfflineConversionUploadResponse,
} from '@/api/auditServicesPages';
import { Card } from '@/components/primitives/Card';
import { KPI } from '@/components/primitives/KPI';
import { StatusPill, type StatusPillVariant } from '@/components/primitives/StatusPill';
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable';

const PLATFORMS = ['meta', 'google', 'tiktok', 'snapchat'] as const;

const FIELD_SURFACE =
  'w-full bg-muted/40 border border-border rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary';

function statusVariant(status: string): StatusPillVariant {
  switch (status.toLowerCase()) {
    case 'completed':
    case 'success':
      return 'healthy';
    case 'processing':
    case 'pending':
      return 'degraded';
    case 'failed':
    case 'error':
      return 'unhealthy';
    default:
      return 'neutral';
  }
}

const REQUIRED_HEADERS = ['event_name', 'event_time'];

function parseCSV(text: string): { rows: OfflineConversionRecord[]; error: string | null } {
  const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length < 2)
    return { rows: [], error: 'CSV must have a header row + at least one data row.' };
  const headers = lines[0].split(',').map((h) => h.trim());
  for (const required of REQUIRED_HEADERS) {
    if (!headers.includes(required)) {
      return { rows: [], error: `Missing required column: ${required}` };
    }
  }
  const rows: OfflineConversionRecord[] = [];
  for (let i = 1; i < lines.length; i++) {
    const cells = lines[i].split(',').map((c) => c.trim());
    const record: Record<string, unknown> = {};
    headers.forEach((h, idx) => {
      record[h] = cells[idx] ?? '';
    });
    if (record.value) record.value = parseFloat(String(record.value)) || 0;
    rows.push(record as unknown as OfflineConversionRecord);
  }
  return { rows, error: null };
}

const batchColumns: DataTableColumn<OfflineConversionBatch>[] = [
  {
    id: 'created_at',
    header: 'Uploaded',
    cell: (b) => (
      <span className="font-mono text-xs text-muted-foreground">
        {b.created_at ? new Date(b.created_at).toLocaleString() : '—'}
      </span>
    ),
    sortable: true,
    sortAccessor: (b) => new Date(b.created_at ?? 0).getTime(),
  },
  {
    id: 'batch_name',
    header: 'Batch',
    cell: (b) => (
      <span className="font-medium">
        {b.batch_name ?? <span className="font-mono text-muted-foreground">{b.batch_id}</span>}
      </span>
    ),
  },
  {
    id: 'platform',
    header: 'Platform',
    cell: (b) => <span className="font-mono text-xs">{b.platform}</span>,
  },
  {
    id: 'status',
    header: 'Status',
    cell: (b) => (
      <StatusPill variant={statusVariant(b.status)} size="sm">
        {b.status}
      </StatusPill>
    ),
  },
  {
    id: 'totals',
    header: 'Records',
    cell: (b) => (
      <span className="font-mono text-xs">
        <span className="text-success">{b.successful}</span>
        {b.failed > 0 && <span className="text-danger"> / {b.failed} failed</span>}
        <span className="text-muted-foreground"> · {b.total_records} total</span>
      </span>
    ),
  },
];

export default function OfflineConversions() {
  const [platform, setPlatform] = useState<(typeof PLATFORMS)[number]>('meta');
  const [batchName, setBatchName] = useState('');
  const [parsed, setParsed] = useState<OfflineConversionRecord[]>([]);
  const [parseError, setParseError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>('');
  const [latest, setLatest] = useState<OfflineConversionUploadResponse | null>(null);

  const upload = useUploadOfflineConversions();
  const batchesQuery = useOfflineConversionBatches(platform);

  const handleFile = async (file: File) => {
    setFileName(file.name);
    setParseError(null);
    setParsed([]);
    setLatest(null);
    const text = await file.text();
    const { rows, error } = parseCSV(text);
    if (error) {
      setParseError(error);
      return;
    }
    setParsed(rows);
  };

  const runUpload = async () => {
    if (parsed.length === 0) return;
    setLatest(null);
    try {
      const result = await upload.mutateAsync({
        platform,
        conversions: parsed,
        batch_name: batchName.trim() || undefined,
      });
      setLatest(result);
      if (result.success) {
        setParsed([]);
        setFileName('');
      }
    } catch (e) {
      // surfaced via upload.isError
    }
  };

  const totals = useMemo(() => {
    const list = batchesQuery.data ?? [];
    return {
      total: list.length,
      successful: list.reduce((acc, b) => acc + (b.successful ?? 0), 0),
      failed: list.reduce((acc, b) => acc + (b.failed ?? 0), 0),
    };
  }, [batchesQuery.data]);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">
          Offline Conversions
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload CSV-formatted offline conversion events to an ad platform and review prior batches.
          Required columns: <code>event_name, event_time</code>. Optional:
          <code> value, currency, email, phone, external_id, click_id</code>.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <KPI
          label="Recent batches"
          value={batchesQuery.isLoading ? undefined : totals.total.toString()}
          loading={batchesQuery.isLoading}
        />
        <KPI
          label="Records ingested"
          value={batchesQuery.isLoading ? undefined : totals.successful.toLocaleString()}
          loading={batchesQuery.isLoading}
        />
        <KPI
          label="Failed records"
          value={batchesQuery.isLoading ? undefined : totals.failed.toLocaleString()}
          loading={batchesQuery.isLoading}
          status={
            totals.failed > 0
              ? { label: 'review', variant: 'degraded' }
              : { label: 'clean', variant: 'healthy' }
          }
        />
      </section>

      <Card className="p-6 space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm text-muted-foreground mb-1">Platform</label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value as (typeof PLATFORMS)[number])}
              className={FIELD_SURFACE}
            >
              {PLATFORMS.map((p) => (
                <option key={p} value={p} className="bg-card">
                  {p}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-muted-foreground mb-1">
              Batch name (optional)
            </label>
            <input
              value={batchName}
              onChange={(e) => setBatchName(e.target.value)}
              placeholder="e.g. q1-purchases-2026"
              className={FIELD_SURFACE}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm text-muted-foreground mb-1">CSV file</label>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
            className="block w-full text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-muted/60 file:text-foreground hover:file:bg-muted"
          />
          {fileName && (
            <p className="mt-2 text-xs text-muted-foreground font-mono">
              {fileName} — {parsed.length} record{parsed.length === 1 ? '' : 's'} parsed
            </p>
          )}
          {parseError && <p className="mt-2 text-sm text-danger">{parseError}</p>}
        </div>

        <button
          onClick={runUpload}
          disabled={parsed.length === 0 || upload.isPending}
          className="bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
        >
          {upload.isPending ? (
            <ArrowPathIcon className="w-5 h-5 animate-spin" />
          ) : (
            <CloudArrowUpIcon className="w-5 h-5" />
          )}
          Upload {parsed.length > 0 && `(${parsed.length})`}
        </button>
      </Card>

      {upload.isError && (
        <Card className="p-4 bg-danger/10 border border-danger/30 text-danger text-sm">
          Could not reach the offline-conversion service.
        </Card>
      )}

      {latest && (
        <Card className="p-6 space-y-2">
          <header className="flex items-center gap-2">
            <StatusPill variant={latest.success ? 'healthy' : 'unhealthy'} size="sm">
              {latest.success ? 'Uploaded' : 'Failed'}
            </StatusPill>
            <span className="font-mono text-xs text-muted-foreground">{latest.batch_id}</span>
          </header>
          <p className="text-sm">
            <span className="text-success font-medium">{latest.successful}</span> succeeded
            {latest.failed > 0 && (
              <>
                , <span className="text-danger font-medium">{latest.failed}</span> failed
              </>
            )}
            <span className="text-muted-foreground"> · {latest.total_records} total</span>
          </p>
          {latest.errors && latest.errors.length > 0 && (
            <ul className="mt-2 space-y-1 text-sm text-danger">
              {latest.errors.slice(0, 5).map((e, i) => (
                <li key={i} className="font-mono text-xs">
                  {e}
                </li>
              ))}
              {latest.errors.length > 5 && (
                <li className="font-mono text-xs text-muted-foreground">
                  …and {latest.errors.length - 5} more
                </li>
              )}
            </ul>
          )}
        </Card>
      )}

      <Card className="p-6">
        <header className="mb-4 flex items-center justify-between">
          <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
            Recent batches
          </h2>
          <span className="text-xs text-muted-foreground">{platform}</span>
        </header>
        {batchesQuery.isError ? (
          <p className="text-sm text-danger">Could not load batch history.</p>
        ) : !batchesQuery.isLoading && (batchesQuery.data ?? []).length === 0 ? (
          <p className="text-sm text-muted-foreground">No batches yet for {platform}.</p>
        ) : (
          <DataTable<OfflineConversionBatch>
            data={batchesQuery.data ?? []}
            columns={batchColumns}
            loading={batchesQuery.isLoading}
            rowKey={(b) => b.batch_id}
            ariaLabel="Offline conversion upload batches"
          />
        )}
      </Card>
    </div>
  );
}
