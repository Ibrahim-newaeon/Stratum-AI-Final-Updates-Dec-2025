/**
 * Feature Flags — Platform Owner page at /console/feature-flags.
 *
 * Lets the owner toggle per-tenant feature gates (signal_health,
 * attribution_variance, anomaly_alerts, autopilot_level, max_campaigns,
 * etc.). Composed thinly over existing react-query hooks:
 *
 *   useTenants                       — tenant picker source
 *   useSuperadminFeatureFlags(id)    — load
 *   useSuperadminUpdateFeatureFlags  — save
 *   useSuperadminResetFeatureFlags   — reset to defaults
 *
 * Backend exposes the data already grouped by category — we render
 * those groups as collapsible cards. Boolean flags become toggles,
 * numeric flags become number inputs.
 */

import { useEffect, useMemo, useState } from 'react';
import {
  useSuperadminFeatureFlags,
  useSuperadminUpdateFeatureFlags,
  useSuperadminResetFeatureFlags,
  type FeatureFlagsUpdate,
} from '@/api/featureFlags';
import { useTenants } from '@/api/admin';
import { Card } from '@/components/primitives/Card';
import { ConfirmDrawer } from '@/components/primitives/ConfirmDrawer';
import { cn } from '@/lib/utils';
import { Save, RotateCcw, AlertTriangle } from 'lucide-react';

type FlagValue = boolean | number;

function isBooleanFlag(value: unknown): value is boolean {
  return typeof value === 'boolean';
}

function isNumericFlag(value: unknown): value is number {
  return typeof value === 'number';
}

export default function FeatureFlags() {
  const tenantsQuery = useTenants({ limit: 200 });
  const [tenantId, setTenantId] = useState<number | null>(null);

  // Auto-pick the first tenant once the list loads.
  useEffect(() => {
    if (tenantId !== null) return;
    const first = tenantsQuery.data?.items?.[0];
    if (first) setTenantId(first.id);
  }, [tenantsQuery.data, tenantId]);

  const flagsQuery = useSuperadminFeatureFlags(tenantId ?? 0);
  const updateMutation = useSuperadminUpdateFeatureFlags(tenantId ?? 0);
  const resetMutation = useSuperadminResetFeatureFlags(tenantId ?? 0);

  // Local working copy — diffed against server state on save.
  const [working, setWorking] = useState<Record<string, FlagValue>>({});
  const [resetOpen, setResetOpen] = useState(false);

  useEffect(() => {
    if (flagsQuery.data?.features) {
      setWorking({ ...flagsQuery.data.features } as Record<string, FlagValue>);
    }
  }, [flagsQuery.data]);

  const dirty = useMemo(() => {
    if (!flagsQuery.data?.features) return false;
    const server = flagsQuery.data.features as unknown as Record<string, FlagValue>;
    return Object.keys(working).some((k) => working[k] !== server[k]);
  }, [working, flagsQuery.data]);

  const handleSave = async () => {
    if (!flagsQuery.data?.features) return;
    const server = flagsQuery.data.features as unknown as Record<string, FlagValue>;
    const diff: Record<string, FlagValue> = {};
    for (const k of Object.keys(working)) {
      if (working[k] !== server[k]) diff[k] = working[k];
    }
    if (Object.keys(diff).length === 0) return;
    await updateMutation.mutateAsync(diff as FeatureFlagsUpdate);
  };

  const handleReset = async () => {
    await resetMutation.mutateAsync();
    setResetOpen(false);
  };

  if (tenantsQuery.isPending) {
    return <div className="text-muted-foreground">Loading tenants…</div>;
  }

  const tenants = tenantsQuery.data?.items ?? [];
  const data = flagsQuery.data;
  const selectedTenant = tenants.find((t) => t.id === tenantId);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">Feature Flags</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Per-tenant feature gates. Changes are written immediately on save and audit-logged.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Tenant picker */}
          <label className="sr-only" htmlFor="tenant-picker">
            Tenant
          </label>
          <select
            id="tenant-picker"
            value={tenantId ?? ''}
            onChange={(e) => setTenantId(Number(e.target.value))}
            className={cn(
              'h-10 px-3 rounded-lg bg-card border border-border text-foreground text-sm',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              'min-w-56'
            )}
          >
            {tenants.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} · {t.plan}
              </option>
            ))}
          </select>

          {/* Save */}
          <button
            type="button"
            onClick={handleSave}
            disabled={!dirty || updateMutation.isPending}
            className={cn(
              'h-10 inline-flex items-center gap-2 px-4 rounded-lg',
              'bg-primary text-primary-foreground text-sm font-medium',
              'transition-opacity disabled:opacity-50 disabled:cursor-not-allowed',
              'hover:brightness-110',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
            )}
          >
            <Save className="w-4 h-4" />
            {updateMutation.isPending ? 'Saving…' : 'Save changes'}
          </button>

          {/* Reset */}
          <button
            type="button"
            onClick={() => setResetOpen(true)}
            disabled={!tenantId || resetMutation.isPending}
            className={cn(
              'h-10 inline-flex items-center gap-2 px-4 rounded-lg',
              'border border-border text-muted-foreground text-sm',
              'transition-colors hover:text-foreground hover:border-border',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
            )}
          >
            <RotateCcw className="w-4 h-4" />
            Reset to defaults
          </button>
        </div>
      </div>

      {/* States */}
      {flagsQuery.isPending && tenantId && (
        <Card>
          <div className="text-muted-foreground text-sm">Loading feature flags…</div>
        </Card>
      )}
      {flagsQuery.isError && (
        <Card>
          <div className="flex items-center gap-3 text-destructive text-sm">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            Couldn't load feature flags for this tenant.
          </div>
        </Card>
      )}
      {dirty && (
        <Card className="border-warning/30 bg-warning/5">
          <div className="flex items-center gap-2 text-warning text-sm">
            <AlertTriangle className="w-4 h-4" />
            Unsaved changes for{' '}
            <span className="font-medium text-foreground">{selectedTenant?.name}</span>
          </div>
        </Card>
      )}

      {/* Categories */}
      {data && (
        <div className="space-y-4">
          {Object.entries(data.categories).map(([key, cat]) => (
            <Card key={key}>
              <div className="mb-4">
                <h2 className="text-lg font-semibold text-foreground">{cat.name}</h2>
                <p className="text-sm text-muted-foreground mt-0.5">{cat.description}</p>
              </div>
              <div className="divide-y divide-border">
                {cat.features.map((flag) => {
                  const value = working[flag];
                  const description = data.descriptions[flag] ?? '';
                  return (
                    <div key={flag} className="py-3 flex items-start gap-4 first:pt-0 last:pb-0">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-foreground font-mono">{flag}</div>
                        {description && (
                          <div className="text-xs text-muted-foreground mt-0.5">{description}</div>
                        )}
                      </div>
                      <div className="flex-shrink-0">
                        {isBooleanFlag(value) && (
                          <Toggle
                            checked={value}
                            onChange={(v) => setWorking((prev) => ({ ...prev, [flag]: v }))}
                            label={flag}
                          />
                        )}
                        {isNumericFlag(value) && (
                          <input
                            type="number"
                            value={value}
                            min={0}
                            onChange={(e) =>
                              setWorking((prev) => ({
                                ...prev,
                                [flag]: Number(e.target.value),
                              }))
                            }
                            className={cn(
                              'h-9 w-28 px-3 rounded-md bg-card border border-border text-foreground text-sm font-mono',
                              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                            )}
                          />
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Reset confirmation */}
      <ConfirmDrawer
        open={resetOpen}
        onOpenChange={setResetOpen}
        title={`Reset ${selectedTenant?.name ?? 'tenant'} flags to defaults?`}
        description="This restores every feature flag for this tenant to its plan-default. Cannot be undone."
        variant="destructive"
        confirmLabel="Reset to defaults"
        onConfirm={handleReset}
        loading={resetMutation.isPending}
      />
    </div>
  );
}

/** Inline toggle — no shadcn `Switch` is shipped in this repo, so build
 *  a minimal accessible button-as-checkbox here. */
function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        checked ? 'bg-primary' : 'bg-muted'
      )}
    >
      <span
        className={cn(
          'inline-block h-5 w-5 transform rounded-full bg-card shadow-sm transition-transform',
          checked ? 'translate-x-5' : 'translate-x-0.5'
        )}
      />
    </button>
  );
}
