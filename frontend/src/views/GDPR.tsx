/**
 * GDPR — Data subject rights page at /dashboard/gdpr.
 *
 * Three sections, all backed by existing hooks in `@/api/gdpr`:
 *
 *   1. Export my data       — useExportHistory + useExportData
 *   2. Right to be forgotten — useRequestDeletion (with ConfirmDrawer)
 *   3. Consent records      — useConsentRecords + useUpdateConsent
 *
 * Admin+ in operator dashboard. The B2B compliance angle: agencies
 * with EU clients need to be able to honor data-subject requests on
 * demand without filing a support ticket.
 */

import { useState } from 'react';
import {
  useExportHistory,
  useExportData,
  useRequestDeletion,
  useConsentRecords,
  useUpdateConsent,
  type DataExportRequest,
  type ConsentRecord,
} from '@/api/gdpr';
import { Card } from '@/components/primitives/Card';
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable';
import { ConfirmDrawer } from '@/components/primitives/ConfirmDrawer';
import { StatusPill } from '@/components/primitives/StatusPill';
import { cn } from '@/lib/utils';
import { Download, FileDown, Trash2, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function GDPR() {
  const exportHistory = useExportHistory();
  const exportMutation = useExportData();
  const consentQuery = useConsentRecords();
  const consentMutation = useUpdateConsent();
  const deletionMutation = useRequestDeletion();

  const [format, setFormat] = useState<'json' | 'csv'>('json');
  const [deletionOpen, setDeletionOpen] = useState(false);
  const [deletionConfirm, setDeletionConfirm] = useState('');

  const handleExport = () => {
    exportMutation.mutate(format);
  };

  const handleDeletion = async () => {
    await deletionMutation.mutateAsync(undefined);
    setDeletionOpen(false);
    setDeletionConfirm('');
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">
          Data &amp; Privacy
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          GDPR &amp; CCPA controls — export, delete, or audit the data Stratum holds about you and
          your tenant. Every action is audit-logged.
        </p>
      </div>

      {/* 1. Data export */}
      <Card>
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <FileDown className="w-4 h-4 text-primary" />
              Export my data
            </h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              Request a machine-readable archive of your personal and tenant-scoped data. Honored
              within 30 days per GDPR Article 15.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value as 'json' | 'csv')}
              className={cn(
                'h-9 px-3 rounded-lg bg-card border border-border text-foreground text-sm',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            >
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
            </select>
            <button
              type="button"
              onClick={handleExport}
              disabled={exportMutation.isPending}
              className={cn(
                'h-9 inline-flex items-center gap-2 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-medium',
                'transition-opacity disabled:opacity-50 disabled:cursor-not-allowed hover:brightness-110',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            >
              {exportMutation.isPending ? 'Requesting…' : 'Request export'}
            </button>
          </div>
        </div>

        <DataTable<DataExportRequest>
          data={exportHistory.data ?? []}
          columns={EXPORT_COLUMNS}
          loading={exportHistory.isPending}
          emptyMessage="No data export requests yet."
          rowKey={(r) => r.id}
          ariaLabel="Past data export requests"
        />
      </Card>

      {/* 2. Consent records */}
      <Card>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-primary" />
            Consent records
          </h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            What you've granted, when, and from where. Toggle to revoke or re-grant.
          </p>
        </div>

        {consentQuery.isPending && (
          <div className="text-sm text-muted-foreground">Loading consent records…</div>
        )}
        {consentQuery.data && consentQuery.data.length === 0 && (
          <div className="text-sm text-muted-foreground">
            No consent records on file. Grant consent flows seed records here.
          </div>
        )}
        {consentQuery.data && consentQuery.data.length > 0 && (
          <div className="divide-y divide-border">
            {consentQuery.data.map((c: ConsentRecord) => (
              <div key={c.id} className="py-3 flex items-start gap-4 first:pt-0 last:pb-0">
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-foreground capitalize">
                    {c.consentType.replace(/_/g, ' ')}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    Granted {formatDate(c.grantedAt)}
                    {c.revokedAt && (
                      <span className="text-destructive"> · revoked {formatDate(c.revokedAt)}</span>
                    )}
                    {c.source && (
                      <span className="font-mono text-xs ml-2">· source: {c.source}</span>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    consentMutation.mutate({
                      consentType: c.consentType,
                      granted: !c.granted,
                    })
                  }
                  disabled={consentMutation.isPending}
                  className={cn(
                    'h-9 px-4 rounded-lg text-sm font-medium border transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    c.granted
                      ? 'border-border text-muted-foreground hover:text-destructive hover:border-destructive/40'
                      : 'border-primary/40 text-primary hover:bg-primary/5'
                  )}
                >
                  {c.granted ? 'Revoke' : 'Grant'}
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* 3. Right to be forgotten */}
      <Card className="border-destructive/30 bg-destructive/[0.02]">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <Trash2 className="w-4 h-4 text-destructive" />
            Right to be forgotten
          </h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Request permanent anonymization of your personal data. We will retain only the minimum
            aggregate records required by law (audit logs, financial records). Honored within 30
            days per GDPR Article 17.
          </p>
        </div>
        <div className="flex items-center gap-3 p-4 rounded-lg bg-destructive/5 border border-destructive/20">
          <AlertTriangle className="w-5 h-5 text-destructive flex-shrink-0" />
          <div className="text-sm text-foreground flex-1">
            This action cannot be undone. Your account will be deactivated and your personal
            identifiers replaced with anonymous tokens.
          </div>
          <button
            type="button"
            onClick={() => setDeletionOpen(true)}
            className={cn(
              'h-9 px-4 rounded-lg text-sm font-medium bg-destructive text-white',
              'transition-opacity hover:opacity-90',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
            )}
          >
            Request deletion
          </button>
        </div>
      </Card>

      {/* Deletion confirmation */}
      <ConfirmDrawer
        open={deletionOpen}
        onOpenChange={(open) => {
          setDeletionOpen(open);
          if (!open) setDeletionConfirm('');
        }}
        title="Request data deletion?"
        description="Type DELETE below to confirm. We will process your request within 30 days. Once processed, your account is irreversible."
        variant="destructive"
        confirmLabel="Submit deletion request"
        onConfirm={handleDeletion}
        loading={deletionMutation.isPending}
        disabled={deletionConfirm !== 'DELETE'}
      >
        <div className="mt-4">
          <label
            htmlFor="deletion-confirm"
            className="text-xs font-mono uppercase tracking-wider text-muted-foreground"
          >
            Type DELETE to confirm
          </label>
          <input
            id="deletion-confirm"
            type="text"
            value={deletionConfirm}
            onChange={(e) => setDeletionConfirm(e.target.value)}
            autoComplete="off"
            className={cn(
              'mt-2 h-10 w-full px-3 rounded-lg bg-card border border-border text-foreground font-mono',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
            )}
          />
        </div>
      </ConfirmDrawer>
    </div>
  );
}

const EXPORT_COLUMNS: DataTableColumn<DataExportRequest>[] = [
  {
    id: 'created',
    header: 'Requested',
    cell: (r) => (
      <span className="text-xs font-mono tabular-nums text-muted-foreground">
        {formatDate(r.createdAt)}
      </span>
    ),
    sortable: true,
    sortAccessor: (r) => new Date(r.createdAt).getTime(),
  },
  {
    id: 'format',
    header: 'Format',
    cell: (r) => <span className="font-mono uppercase text-xs">{r.format}</span>,
  },
  {
    id: 'status',
    header: 'Status',
    cell: (r) => {
      const variant: 'healthy' | 'degraded' | 'unhealthy' | 'neutral' =
        r.status === 'completed'
          ? 'healthy'
          : r.status === 'failed'
            ? 'unhealthy'
            : r.status === 'processing'
              ? 'degraded'
              : 'neutral';
      return <StatusPill variant={variant}>{r.status}</StatusPill>;
    },
  },
  {
    id: 'expires',
    header: 'Expires',
    cell: (r) => (
      <span className="text-xs text-muted-foreground">
        {r.expiresAt ? formatDate(r.expiresAt) : '—'}
      </span>
    ),
    hideOnMobile: true,
  },
  {
    id: 'download',
    header: '',
    cell: (r) =>
      r.downloadUrl && r.status === 'completed' ? (
        <a
          href={r.downloadUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
        >
          <Download className="w-3.5 h-3.5" />
          Download
        </a>
      ) : (
        <span className="text-xs text-muted-foreground">—</span>
      ),
    cellClassName: 'text-right',
    headerClassName: 'text-right',
  },
];

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return iso;
  }
}
