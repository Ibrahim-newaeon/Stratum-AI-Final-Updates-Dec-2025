/**
 * Integrations Hub — unified credential management at /dashboard/integrations.
 *
 * Replaces the old CRM-only page with a single surface that covers
 * every supported integration, grouped by category:
 *
 *   Ad Platforms   — Meta / Google / TikTok / Snapchat (OAuth)
 *   Server-Side    — CAPI / Conversions API tokens
 *   CRM            — HubSpot (via existing CRM hooks)
 *   Outbound       — Zapier webhooks, Slack notifications
 *
 * Each integration card surfaces its connection status and offers
 * the appropriate action: an OAuth handshake (button → redirect),
 * a credential form (slide-over with secret-typed inputs), or a
 * link out to the dedicated setup page when the flow needs more
 * than a couple of fields.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CheckCircle2,
  Cable,
  ExternalLink,
  Plug,
  RefreshCw,
  Sparkles,
  Trash2,
  Webhook,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import { Card } from '@/components/primitives/Card';
import { StatusPill } from '@/components/primitives/StatusPill';
import { ConfirmDrawer } from '@/components/primitives/ConfirmDrawer';
import { apiClient } from '@/api/client';
import { useCRMConnections, useTriggerCRMSync } from '@/api/hooks';
import { cn } from '@/lib/utils';

// =============================================================================
// Types & catalog
// =============================================================================

type AdPlatform = 'meta' | 'google' | 'tiktok' | 'snapchat';

interface PlatformStatusRow {
  platform: AdPlatform;
  status: 'connected' | 'expired' | 'error' | 'disconnected';
  connected_at?: string;
  expires_at?: string;
  account_count?: number;
  error?: string;
}

interface AdPlatformDef {
  id: AdPlatform;
  name: string;
  description: string;
}

const AD_PLATFORMS: AdPlatformDef[] = [
  {
    id: 'meta',
    name: 'Meta Ads',
    description: 'Facebook + Instagram ad accounts via Meta Marketing API.',
  },
  {
    id: 'google',
    name: 'Google Ads',
    description: 'Search, Display, YouTube, Performance Max — Google Ads API.',
  },
  {
    id: 'tiktok',
    name: 'TikTok Ads',
    description: 'TikTok for Business ad accounts via Marketing API.',
  },
  {
    id: 'snapchat',
    name: 'Snapchat Ads',
    description: 'Snap Ads Manager via Marketing API.',
  },
];

// =============================================================================
// Page
// =============================================================================

export default function IntegrationsHub() {
  const [statuses, setStatuses] = useState<Record<AdPlatform, PlatformStatusRow | null>>({
    meta: null,
    google: null,
    tiktok: null,
    snapchat: null,
  });
  const [loading, setLoading] = useState(true);
  const [actionPlatform, setActionPlatform] = useState<AdPlatform | null>(null);
  const [confirmDisconnect, setConfirmDisconnect] = useState<AdPlatformDef | null>(null);

  const crmConnections = useCRMConnections();
  const triggerSync = useTriggerCRMSync();

  const fetchStatuses = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<{ data: PlatformStatusRow[] }>('/oauth/status');
      const map: Record<AdPlatform, PlatformStatusRow | null> = {
        meta: null,
        google: null,
        tiktok: null,
        snapchat: null,
      };
      for (const row of res.data.data ?? []) {
        if (row.platform in map) map[row.platform] = row;
      }
      setStatuses(map);
    } catch {
      // Endpoint may 403 for non-owner roles — treat all as disconnected.
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatuses();
  }, []);

  const handleConnect = async (platform: AdPlatform) => {
    setActionPlatform(platform);
    try {
      const res = await apiClient.post<{ data: { auth_url?: string; redirect_url?: string } }>(
        `/oauth/${platform}/authorize`,
        {}
      );
      const url = res.data.data?.auth_url || res.data.data?.redirect_url;
      if (url) {
        window.location.href = url;
        return;
      }
    } catch {
      // surface in UI via status refresh
      await fetchStatuses();
    } finally {
      setActionPlatform(null);
    }
  };

  const handleDisconnect = async () => {
    if (!confirmDisconnect) return;
    setActionPlatform(confirmDisconnect.id);
    try {
      await apiClient.delete(`/oauth/${confirmDisconnect.id}/disconnect`);
    } catch {
      // ignore — status refresh will surface state
    } finally {
      await fetchStatuses();
      setConfirmDisconnect(null);
      setActionPlatform(null);
    }
  };

  const handleRefresh = async (platform: AdPlatform) => {
    setActionPlatform(platform);
    try {
      await apiClient.post(`/oauth/${platform}/refresh`, {});
    } catch {
      // ignore
    } finally {
      await fetchStatuses();
      setActionPlatform(null);
    }
  };

  const hubspot = crmConnections.data?.find((c) => c.provider === 'hubspot');

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight flex items-center gap-2">
            <Plug className="w-5 h-5 text-primary" />
            Integrations
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Connect Stratum to the platforms you run ads on, your CRM, and your downstream tools.
            Credentials are encrypted at rest and never returned to the dashboard.
          </p>
        </div>
        <button
          type="button"
          onClick={fetchStatuses}
          disabled={loading}
          className={cn(
            'h-9 inline-flex items-center gap-2 px-4 rounded-lg border border-border text-muted-foreground text-sm',
            'transition-colors hover:text-foreground',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            'disabled:opacity-50'
          )}
        >
          <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Section: Ad Platforms */}
      <Section
        title="Ad Platforms"
        subtitle="OAuth into the platforms running your media. Each connection grants Stratum scoped read + write access."
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {AD_PLATFORMS.map((p) => (
            <PlatformCard
              key={p.id}
              platform={p}
              status={statuses[p.id]}
              loading={loading || actionPlatform === p.id}
              onConnect={() => handleConnect(p.id)}
              onRefresh={() => handleRefresh(p.id)}
              onDisconnect={() => setConfirmDisconnect(p)}
            />
          ))}
        </div>
      </Section>

      {/* Section: Server-Side Tracking */}
      <Section
        title="Server-Side Tracking"
        subtitle="CAPI / Conversions API tokens. Server-to-server event delivery — bypasses ad-blockers and improves match quality."
      >
        <Card>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 min-w-0">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                <Webhook className="w-5 h-5 text-primary" />
              </div>
              <div className="min-w-0">
                <div className="font-medium text-foreground">Conversions API</div>
                <div className="text-sm text-muted-foreground mt-0.5">
                  Configure pixel/dataset IDs and access tokens for Meta CAPI, Google server-side,
                  TikTok Events, and Snapchat CAPI on the dedicated setup page.
                </div>
              </div>
            </div>
            <Link
              to="/dashboard/capi-setup"
              className={cn(
                'flex-shrink-0 inline-flex items-center gap-2 h-9 px-4 rounded-lg',
                'bg-primary text-primary-foreground text-sm font-medium',
                'transition-opacity hover:brightness-110',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            >
              Open setup
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>
        </Card>
      </Section>

      {/* Section: CRM */}
      <Section
        title="CRM"
        subtitle="Sync contacts, deals, and pipeline stages for closed-loop attribution."
      >
        <Card>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 min-w-0">
              <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center flex-shrink-0 text-warning font-bold">
                H
              </div>
              <div className="min-w-0">
                <div className="font-medium text-foreground flex items-center gap-2">
                  HubSpot
                  {hubspot && (
                    <StatusPill
                      variant={
                        hubspot.status === 'connected'
                          ? 'healthy'
                          : hubspot.status === 'error'
                            ? 'unhealthy'
                            : 'degraded'
                      }
                    >
                      {hubspot.status}
                    </StatusPill>
                  )}
                </div>
                <div className="text-sm text-muted-foreground mt-0.5">
                  {hubspot
                    ? `Connected · ${hubspot.lastSyncAt ? `last sync ${formatRelative(hubspot.lastSyncAt)}` : 'never synced'}`
                    : 'Not connected. Use the campaigns connection wizard to OAuth into your HubSpot portal.'}
                </div>
              </div>
            </div>
            <div className="flex-shrink-0 flex items-center gap-2">
              {hubspot ? (
                <button
                  type="button"
                  onClick={() => triggerSync.mutate(hubspot.id)}
                  disabled={triggerSync.isPending}
                  className={cn(
                    'inline-flex items-center gap-2 h-9 px-4 rounded-lg',
                    'border border-border text-muted-foreground text-sm hover:text-foreground',
                    'transition-colors disabled:opacity-50',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                  )}
                >
                  <RefreshCw className={cn('w-4 h-4', triggerSync.isPending && 'animate-spin')} />
                  Sync now
                </button>
              ) : (
                <Link
                  to="/dashboard/campaigns/connect"
                  className={cn(
                    'inline-flex items-center gap-2 h-9 px-4 rounded-lg',
                    'bg-primary text-primary-foreground text-sm font-medium',
                    'transition-opacity hover:brightness-110',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                  )}
                >
                  Connect
                  <ExternalLink className="w-3.5 h-3.5" />
                </Link>
              )}
            </div>
          </div>
        </Card>
      </Section>

      {/* Section: Outbound */}
      <Section
        title="Outbound"
        subtitle="Push Stratum events to Zapier, Make, Slack, or any HTTPS endpoint."
      >
        <Card>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 min-w-0">
              <div className="w-10 h-10 rounded-lg bg-secondary/10 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-5 h-5 text-secondary" />
              </div>
              <div className="min-w-0">
                <div className="font-medium text-foreground">Zapier · Make · Slack · Teams</div>
                <div className="text-sm text-muted-foreground mt-0.5">
                  Wire Stratum's events (campaign created, ROAS alert, trust gate blocked, daily
                  summary, anomaly detected) into your team's tools.
                </div>
              </div>
            </div>
            <Link
              to="/dashboard/integration-hub"
              className={cn(
                'flex-shrink-0 inline-flex items-center gap-2 h-9 px-4 rounded-lg',
                'border border-border text-muted-foreground text-sm hover:text-foreground',
                'transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            >
              Open hub
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>
        </Card>
      </Section>

      {/* Disconnect confirmation */}
      <ConfirmDrawer
        open={!!confirmDisconnect}
        onOpenChange={(open) => {
          if (!open) setConfirmDisconnect(null);
        }}
        title={`Disconnect ${confirmDisconnect?.name}?`}
        description="Stratum will stop pulling data and any active automations on this platform will halt at the next trust-gate evaluation. You can reconnect any time."
        variant="destructive"
        confirmLabel="Disconnect"
        onConfirm={handleDisconnect}
        loading={actionPlatform === confirmDisconnect?.id}
      />
    </div>
  );
}

// =============================================================================
// Helpers
// =============================================================================

interface SectionProps {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}

function Section({ title, subtitle, children }: SectionProps) {
  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold text-foreground">{title}</h2>
        <p className="text-sm text-muted-foreground mt-0.5">{subtitle}</p>
      </div>
      {children}
    </section>
  );
}

interface PlatformCardProps {
  platform: AdPlatformDef;
  status: PlatformStatusRow | null;
  loading: boolean;
  onConnect: () => void;
  onRefresh: () => void;
  onDisconnect: () => void;
}

function PlatformCard({
  platform,
  status,
  loading,
  onConnect,
  onRefresh,
  onDisconnect,
}: PlatformCardProps) {
  const isConnected = status?.status === 'connected';
  const isExpired = status?.status === 'expired';
  const isError = status?.status === 'error';

  return (
    <Card>
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 font-bold text-sm uppercase',
            isConnected ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground'
          )}
        >
          {platform.name.slice(0, 2)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-foreground truncate">{platform.name}</span>
            {isConnected && (
              <CheckCircle2 className="w-4 h-4 text-success flex-shrink-0" aria-label="Connected" />
            )}
            {isExpired && (
              <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0" aria-label="Expired" />
            )}
            {isError && (
              <XCircle className="w-4 h-4 text-destructive flex-shrink-0" aria-label="Error" />
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">{platform.description}</p>
          {isConnected && (
            <div className="text-xs text-muted-foreground font-mono mt-2">
              {status?.account_count ?? 0} account{status?.account_count === 1 ? '' : 's'} ·{' '}
              {status?.expires_at ? `expires ${formatRelative(status.expires_at)}` : 'no expiry'}
            </div>
          )}
          {(isExpired || isError) && status?.error && (
            <div className="text-xs text-destructive mt-2">{status.error}</div>
          )}
        </div>
      </div>

      <div className="mt-4 flex items-center justify-end gap-2">
        {!isConnected && (
          <button
            type="button"
            onClick={onConnect}
            disabled={loading}
            className={cn(
              'inline-flex items-center gap-2 h-9 px-4 rounded-lg',
              'bg-primary text-primary-foreground text-sm font-medium',
              'transition-opacity hover:brightness-110 disabled:opacity-50',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
            )}
          >
            <Cable className="w-4 h-4" />
            Connect
          </button>
        )}
        {isConnected && (
          <>
            <button
              type="button"
              onClick={onRefresh}
              disabled={loading}
              className={cn(
                'inline-flex items-center gap-2 h-9 px-3 rounded-lg',
                'border border-border text-muted-foreground text-sm hover:text-foreground',
                'transition-colors disabled:opacity-50',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            >
              <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
              Refresh token
            </button>
            <button
              type="button"
              onClick={onDisconnect}
              disabled={loading}
              className={cn(
                'inline-flex items-center gap-2 h-9 px-3 rounded-lg',
                'border border-border text-muted-foreground text-sm hover:text-destructive hover:border-destructive/40',
                'transition-colors disabled:opacity-50',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            >
              <Trash2 className="w-4 h-4" />
              Disconnect
            </button>
          </>
        )}
        {(isExpired || isError) && (
          <button
            type="button"
            onClick={onConnect}
            disabled={loading}
            className={cn(
              'inline-flex items-center gap-2 h-9 px-4 rounded-lg',
              'bg-warning text-ink text-sm font-medium',
              'transition-opacity hover:brightness-110 disabled:opacity-50',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
            )}
          >
            Reconnect
          </button>
        )}
      </div>
    </Card>
  );
}

function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    const diffMs = d.getTime() - Date.now();
    const absHours = Math.abs(diffMs) / 3_600_000;
    if (absHours < 1) return 'less than 1h ago';
    if (absHours < 24) return `${Math.round(absHours)}h ${diffMs > 0 ? 'from now' : 'ago'}`;
    const absDays = Math.round(absHours / 24);
    return `${absDays}d ${diffMs > 0 ? 'from now' : 'ago'}`;
  } catch {
    return iso;
  }
}
