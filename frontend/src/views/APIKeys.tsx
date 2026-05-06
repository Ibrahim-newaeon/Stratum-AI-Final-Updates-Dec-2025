/**
 * API Keys — workspace credential management at /dashboard/api-keys.
 *
 * Lets agency admins mint scoped API keys for the Stratum public API
 * (server-to-server access to /v1/* endpoints). Backed by hooks in
 * `@/api/apiKeys`:
 *
 *   useApiKeys       — list active keys (only prefix + masked tail)
 *   useCreateApiKey  — mint new key, secret returned ONCE
 *   useDeleteApiKey  — revoke
 *
 * Security: the full secret is shown exactly once in the create flow,
 * then we display only `key_prefix...mask`. Treat this like Stripe or
 * AWS — keys never round-trip after creation.
 */

import { useState } from 'react';
import {
  useApiKeys,
  useCreateApiKey,
  useDeleteApiKey,
  type ApiKey,
  type ApiKeyCreated,
} from '@/api/apiKeys';
import { Card } from '@/components/primitives/Card';
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable';
import { ConfirmDrawer } from '@/components/primitives/ConfirmDrawer';
import { StatusPill } from '@/components/primitives/StatusPill';
import { cn } from '@/lib/utils';
import { Copy, KeyRound, Plus, Trash2 } from 'lucide-react';

const SCOPE_PRESETS: { value: string; label: string; description: string }[] = [
  { value: 'read', label: 'Read', description: 'GET endpoints across the platform' },
  {
    value: 'write',
    label: 'Write',
    description: 'POST/PUT/DELETE — campaigns, audiences, automations',
  },
  { value: 'webhooks', label: 'Webhooks', description: 'Receive event notifications' },
];

export default function APIKeys() {
  const keysQuery = useApiKeys();
  const createMutation = useCreateApiKey();
  const deleteMutation = useDeleteApiKey();

  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState('');
  const [scopes, setScopes] = useState<Set<string>>(new Set(['read']));
  const [expiresInDays, setExpiresInDays] = useState<number | ''>('');

  const [showSecret, setShowSecret] = useState<ApiKeyCreated | null>(null);
  const [copied, setCopied] = useState(false);

  const [revokeTarget, setRevokeTarget] = useState<ApiKey | null>(null);

  const resetForm = () => {
    setName('');
    setScopes(new Set(['read']));
    setExpiresInDays('');
  };

  const handleCreate = async () => {
    const payload = {
      name: name.trim(),
      scopes: Array.from(scopes),
      ...(expiresInDays !== '' ? { expires_in_days: Number(expiresInDays) } : {}),
    };
    const created = await createMutation.mutateAsync(payload);
    setShowSecret(created);
    setCreateOpen(false);
    resetForm();
  };

  const handleRevoke = async () => {
    if (!revokeTarget) return;
    await deleteMutation.mutateAsync(revokeTarget.id);
    setRevokeTarget(null);
  };

  const copySecret = async () => {
    if (!showSecret) return;
    try {
      await navigator.clipboard.writeText(showSecret.key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore — user can still copy manually
    }
  };

  const toggleScope = (scope: string) => {
    setScopes((prev) => {
      const next = new Set(prev);
      if (next.has(scope)) next.delete(scope);
      else next.add(scope);
      return next;
    });
  };

  const columns: DataTableColumn<ApiKey>[] = [
    {
      id: 'name',
      header: 'Name',
      cell: (k) => (
        <div className="min-w-0">
          <div className="font-medium text-foreground truncate">{k.name}</div>
          <div className="text-xs text-muted-foreground font-mono mt-0.5">{k.masked_key}</div>
        </div>
      ),
      sortable: true,
      sortAccessor: (k) => k.name,
    },
    {
      id: 'scopes',
      header: 'Scopes',
      cell: (k) => (
        <div className="flex flex-wrap gap-1">
          {k.scopes.map((s) => (
            <span
              key={s}
              className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted text-muted-foreground"
            >
              {s}
            </span>
          ))}
        </div>
      ),
      hideOnMobile: true,
    },
    {
      id: 'last_used',
      header: 'Last used',
      cell: (k) => (
        <span className="text-xs font-mono tabular-nums text-muted-foreground">
          {k.last_used_at ? formatDate(k.last_used_at) : 'Never'}
        </span>
      ),
      sortable: true,
      sortAccessor: (k) => (k.last_used_at ? new Date(k.last_used_at).getTime() : 0),
      hideOnMobile: true,
    },
    {
      id: 'expires',
      header: 'Expires',
      cell: (k) => (
        <span className="text-xs text-muted-foreground">
          {k.expires_at ? formatDate(k.expires_at) : 'No expiry'}
        </span>
      ),
      hideOnMobile: true,
    },
    {
      id: 'status',
      header: 'Status',
      cell: (k) => (
        <StatusPill variant={k.is_active ? 'healthy' : 'unhealthy'}>
          {k.is_active ? 'active' : 'revoked'}
        </StatusPill>
      ),
    },
    {
      id: 'actions',
      header: '',
      cell: (k) =>
        k.is_active ? (
          <button
            type="button"
            onClick={() => setRevokeTarget(k)}
            aria-label={`Revoke ${k.name}`}
            className={cn(
              'p-2 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/5',
              'transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
            )}
          >
            <Trash2 className="w-4 h-4" />
          </button>
        ) : null,
      cellClassName: 'text-right',
      headerClassName: 'text-right',
    },
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-primary" />
            API Keys
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Server-to-server credentials for the Stratum public API. Keys are scoped and
            audit-logged on every call.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          className={cn(
            'h-10 inline-flex items-center gap-2 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-medium',
            'transition-opacity hover:brightness-110',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
          )}
        >
          <Plus className="w-4 h-4" />
          New API key
        </button>
      </div>

      {/* Keys table */}
      <Card>
        <DataTable<ApiKey>
          data={keysQuery.data ?? []}
          columns={columns}
          loading={keysQuery.isPending}
          error={keysQuery.error?.message}
          emptyMessage="No API keys yet. Click 'New API key' to mint your first one."
          rowKey={(k) => k.id}
          ariaLabel="API keys"
        />
      </Card>

      {/* Create dialog */}
      <ConfirmDrawer
        open={createOpen}
        onOpenChange={(open) => {
          setCreateOpen(open);
          if (!open) resetForm();
        }}
        title="Create API key"
        description="Give it a name and pick the scopes. The secret will be shown once."
        confirmLabel="Create key"
        onConfirm={handleCreate}
        loading={createMutation.isPending}
        disabled={!name.trim() || scopes.size === 0}
      >
        <div className="space-y-4 mt-3">
          <div>
            <label
              htmlFor="key-name"
              className="text-xs font-mono uppercase tracking-wider text-muted-foreground"
            >
              Name
            </label>
            <input
              id="key-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Reporting integration"
              autoComplete="off"
              className={cn(
                'mt-1.5 h-10 w-full px-3 rounded-lg bg-card border border-border text-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            />
          </div>

          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-2">
              Scopes
            </div>
            <div className="space-y-2">
              {SCOPE_PRESETS.map((s) => (
                <label
                  key={s.value}
                  className={cn(
                    'flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                    scopes.has(s.value)
                      ? 'border-primary/40 bg-primary/[0.04]'
                      : 'border-border hover:border-border'
                  )}
                >
                  <input
                    type="checkbox"
                    checked={scopes.has(s.value)}
                    onChange={() => toggleScope(s.value)}
                    className="mt-0.5"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-foreground">{s.label}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{s.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label
              htmlFor="key-expires"
              className="text-xs font-mono uppercase tracking-wider text-muted-foreground"
            >
              Expires after (days, optional)
            </label>
            <input
              id="key-expires"
              type="number"
              min={1}
              max={3650}
              value={expiresInDays}
              onChange={(e) =>
                setExpiresInDays(e.target.value === '' ? '' : Number(e.target.value))
              }
              placeholder="No expiry"
              autoComplete="off"
              className={cn(
                'mt-1.5 h-10 w-full px-3 rounded-lg bg-card border border-border text-foreground font-mono',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            />
          </div>
        </div>
      </ConfirmDrawer>

      {/* Secret display dialog (one-time) */}
      <ConfirmDrawer
        open={!!showSecret}
        onOpenChange={(open) => {
          if (!open) {
            setShowSecret(null);
            setCopied(false);
          }
        }}
        title="Save your API key now"
        description="This is the only time we will show the full secret. Store it in your password manager or secrets vault before closing."
        variant="warning"
        confirmLabel="I've saved it"
        cancelLabel=""
        onConfirm={() => {
          setShowSecret(null);
          setCopied(false);
        }}
      >
        {showSecret && (
          <div className="space-y-3 mt-3">
            <div className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
              Secret
            </div>
            <div className="flex items-stretch gap-2">
              <code className="flex-1 px-3 py-2 rounded-lg bg-muted/60 border border-border text-foreground font-mono text-sm break-all">
                {showSecret.key}
              </code>
              <button
                type="button"
                onClick={copySecret}
                aria-label="Copy secret"
                className={cn(
                  'flex-shrink-0 px-3 rounded-lg border border-border text-sm transition-colors',
                  'hover:text-foreground',
                  copied ? 'text-success border-success/40' : 'text-muted-foreground'
                )}
              >
                <Copy className="w-4 h-4 inline mr-1.5" />
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <div className="text-xs text-muted-foreground">
              Use it as{' '}
              <code className="font-mono">Authorization: Bearer {showSecret.key_prefix}...</code> on
              every request.
            </div>
          </div>
        )}
      </ConfirmDrawer>

      {/* Revoke confirmation */}
      <ConfirmDrawer
        open={!!revokeTarget}
        onOpenChange={(open) => {
          if (!open) setRevokeTarget(null);
        }}
        title={`Revoke ${revokeTarget?.name ?? 'API key'}?`}
        description="Any service using this key will start receiving 401 immediately. This cannot be undone."
        variant="destructive"
        confirmLabel="Revoke key"
        onConfirm={handleRevoke}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}

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
