/**
 * CDP Audience Sync Component
 * Manage audience sync to ad platforms (Meta, Google, TikTok, Snapchat)
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  ArrowUpRight,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Download,
  FileJson,
  FileSpreadsheet,
  History,
  Link2,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  Users,
  X,
  XCircle,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  AudienceExportParams,
  CDPSegment,
  PlatformAudience,
  SyncPlatform,
  SyncStatus,
  useConnectedPlatforms,
  useCreatePlatformAudience,
  useDeletePlatformAudience,
  useExportAudience,
  usePlatformAudiences,
  useSegments,
  useSyncHistory,
  useTriggerSync,
} from '@/api/cdp';

// Platform configurations
const PLATFORM_CONFIG: Record<
  SyncPlatform,
  {
    name: string;
    color: string;
    bgColor: string;
    icon: string;
  }
> = {
  meta: {
    name: 'Meta',
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    icon: 'M',
  },
  google: {
    name: 'Google',
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    icon: 'G',
  },
  tiktok: {
    name: 'TikTok',
    color: 'text-gray-900 dark:text-white',
    bgColor: 'bg-gray-900/10 dark:bg-white/10',
    icon: 'T',
  },
  snapchat: {
    name: 'Snapchat',
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-500/10',
    icon: 'S',
  },
};

// Platform icon component
function PlatformIcon({
  platform,
  size = 'md',
}: {
  platform: SyncPlatform;
  size?: 'sm' | 'md' | 'lg';
}) {
  const config = PLATFORM_CONFIG[platform];
  const sizeClasses = {
    sm: 'w-6 h-6 text-xs',
    md: 'w-8 h-8 text-sm',
    lg: 'w-10 h-10 text-base',
  };

  return (
    <div
      className={cn(
        'rounded-lg flex items-center justify-center font-bold',
        config.bgColor,
        config.color,
        sizeClasses[size]
      )}
    >
      {config.icon}
    </div>
  );
}

// Status badge component
function StatusBadge({ status }: { status: SyncStatus | null }) {
  const statusConfig: Record<
    SyncStatus,
    { icon: React.ReactNode; className: string; label: string }
  > = {
    pending: {
      icon: <Clock className="w-3 h-3" />,
      className: 'bg-gray-500/10 text-gray-500',
      label: 'Pending',
    },
    processing: {
      icon: <Loader2 className="w-3 h-3 animate-spin" />,
      className: 'bg-blue-500/10 text-blue-500',
      label: 'Syncing',
    },
    completed: {
      icon: <CheckCircle2 className="w-3 h-3" />,
      className: 'bg-green-500/10 text-green-500',
      label: 'Synced',
    },
    failed: {
      icon: <XCircle className="w-3 h-3" />,
      className: 'bg-red-500/10 text-red-500',
      label: 'Failed',
    },
    partial: {
      icon: <AlertCircle className="w-3 h-3" />,
      className: 'bg-amber-500/10 text-amber-500',
      label: 'Partial',
    },
  };

  if (!status) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-500/10 text-gray-500">
        <Clock className="w-3 h-3" />
        Never synced
      </span>
    );
  }

  const config = statusConfig[status];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
        config.className
      )}
    >
      {config.icon}
      {config.label}
    </span>
  );
}

// Create audience modal
interface CreateAudienceModalProps {
  isOpen: boolean;
  onClose: () => void;
  segments: CDPSegment[];
  connectedPlatforms: Array<{
    platform: SyncPlatform;
    ad_accounts: Array<{ ad_account_id: string; ad_account_name: string | null }>;
  }>;
}

function CreateAudienceModal({
  isOpen,
  onClose,
  segments,
  connectedPlatforms,
}: CreateAudienceModalProps) {
  const [segmentId, setSegmentId] = useState('');
  const [platform, setPlatform] = useState<SyncPlatform | ''>('');
  const [adAccountId, setAdAccountId] = useState('');
  const [audienceName, setAudienceName] = useState('');
  const [description, setDescription] = useState('');
  const [autoSync, setAutoSync] = useState(true);
  const [syncInterval, setSyncInterval] = useState(24);

  const createMutation = useCreatePlatformAudience();

  const selectedPlatform = connectedPlatforms.find((p) => p.platform === platform);
  const adAccounts = selectedPlatform?.ad_accounts || [];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!segmentId || !platform || !adAccountId || !audienceName) return;

    try {
      await createMutation.mutateAsync({
        segment_id: segmentId,
        platform: platform,
        ad_account_id: adAccountId,
        audience_name: audienceName,
        description: description || undefined,
        auto_sync: autoSync,
        sync_interval_hours: syncInterval,
      });
      onClose();
      // Reset form
      setSegmentId('');
      setPlatform('');
      setAdAccountId('');
      setAudienceName('');
      setDescription('');
      setAutoSync(true);
      setSyncInterval(24);
    } catch (error) {
      console.error('Failed to create audience:', error);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-card border rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Create Platform Audience</h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Segment selection */}
          <div>
            <label className="block text-sm font-medium mb-1.5">CDP Segment</label>
            <select
              value={segmentId}
              onChange={(e) => setSegmentId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
              required
            >
              <option value="">Select a segment...</option>
              {segments.map((segment) => (
                <option key={segment.id} value={segment.id}>
                  {segment.name} ({segment.profile_count?.toLocaleString() || 0} profiles)
                </option>
              ))}
            </select>
          </div>

          {/* Platform selection */}
          <div>
            <label className="block text-sm font-medium mb-1.5">Ad Platform</label>
            <div className="grid grid-cols-2 gap-2">
              {connectedPlatforms.map((p) => (
                <button
                  key={p.platform}
                  type="button"
                  onClick={() => {
                    setPlatform(p.platform);
                    setAdAccountId('');
                  }}
                  className={cn(
                    'flex items-center gap-2 p-3 rounded-lg border transition-all',
                    platform === p.platform
                      ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                      : 'hover:border-muted-foreground/20'
                  )}
                >
                  <PlatformIcon platform={p.platform} size="sm" />
                  <span className="font-medium">{PLATFORM_CONFIG[p.platform].name}</span>
                </button>
              ))}
            </div>
            {connectedPlatforms.length === 0 && (
              <p className="mt-2 text-sm text-muted-foreground">
                No platforms connected. Connect platforms in Settings.
              </p>
            )}
          </div>

          {/* Ad Account selection */}
          {platform && adAccounts.length > 0 && (
            <div>
              <label className="block text-sm font-medium mb-1.5">Ad Account</label>
              <select
                value={adAccountId}
                onChange={(e) => setAdAccountId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
                required
              >
                <option value="">Select an ad account...</option>
                {adAccounts.map((account) => (
                  <option key={account.ad_account_id} value={account.ad_account_id}>
                    {account.ad_account_name || account.ad_account_id}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Audience name */}
          <div>
            <label className="block text-sm font-medium mb-1.5">Audience Name</label>
            <input
              type="text"
              value={audienceName}
              onChange={(e) => setAudienceName(e.target.value)}
              placeholder="e.g., High Value Customers"
              className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium mb-1.5">Description (optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe this audience..."
              rows={2}
              className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 resize-none"
            />
          </div>

          {/* Auto-sync settings */}
          <div className="flex items-center gap-4 p-3 rounded-lg bg-muted/30 border">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="autoSync"
                checked={autoSync}
                onChange={(e) => setAutoSync(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300"
              />
              <label htmlFor="autoSync" className="text-sm font-medium">
                Auto-sync audience
              </label>
            </div>
            {autoSync && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">every</span>
                <select
                  value={syncInterval}
                  onChange={(e) => setSyncInterval(Number(e.target.value))}
                  className="px-2 py-1 rounded border bg-background text-sm"
                >
                  <option value={1}>1 hour</option>
                  <option value={6}>6 hours</option>
                  <option value={12}>12 hours</option>
                  <option value={24}>24 hours</option>
                  <option value={48}>48 hours</option>
                  <option value={168}>1 week</option>
                </select>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={
                !segmentId || !platform || !adAccountId || !audienceName || createMutation.isPending
              }
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {createMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Plus className="w-4 h-4" />
              )}
              Create Audience
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Sync history panel
interface SyncHistoryPanelProps {
  audienceId: string;
  audienceName: string;
  onClose: () => void;
}

function SyncHistoryPanel({ audienceId, audienceName, onClose }: SyncHistoryPanelProps) {
  const { data, isLoading } = useSyncHistory(audienceId, 20);
  const jobs = data?.jobs || [];

  const formatDuration = (ms: number | null) => {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const formatDate = (date: string | null) => {
    if (!date) return '-';
    return new Date(date).toLocaleString();
  };

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-lg bg-card border-l shadow-xl z-50 overflow-hidden flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <History className="w-5 h-5" />
            Sync History
          </h2>
          <p className="text-sm text-muted-foreground">{audienceName}</p>
        </div>
        <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted transition-colors">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-12">
            <History className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="font-semibold mb-2">No sync history</h3>
            <p className="text-sm text-muted-foreground">This audience hasn't been synced yet.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => (
              <div key={job.id} className="p-4 rounded-lg border bg-muted/20">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={job.status} />
                    <span className="text-sm text-muted-foreground capitalize">
                      {job.operation}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(job.created_at)}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <div className="text-muted-foreground">Profiles</div>
                    <div className="font-semibold">{job.profiles_sent.toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Added</div>
                    <div className="font-semibold text-green-500">
                      +{job.profiles_added.toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Duration</div>
                    <div className="font-semibold">{formatDuration(job.duration_ms)}</div>
                  </div>
                </div>

                {job.profiles_failed > 0 && (
                  <div className="mt-2 text-sm text-red-500">
                    {job.profiles_failed.toLocaleString()} profiles failed
                  </div>
                )}

                {job.error_message && (
                  <div className="mt-2 p-2 rounded bg-red-500/10 text-red-500 text-sm">
                    {job.error_message}
                  </div>
                )}

                <div className="mt-2 text-xs text-muted-foreground">
                  Triggered by: {job.triggered_by || 'manual'}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Export audience modal
interface ExportAudienceModalProps {
  isOpen: boolean;
  onClose: () => void;
  segments: CDPSegment[];
}

function ExportAudienceModal({ isOpen, onClose, segments }: ExportAudienceModalProps) {
  const [segmentId, setSegmentId] = useState<string>('');
  const [format, setFormat] = useState<'csv' | 'json'>('csv');
  const [includeTraits, setIncludeTraits] = useState(true);
  const [includeEvents, setIncludeEvents] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const exportMutation = useExportAudience();

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const params: AudienceExportParams = {
        format,
        segment_id: segmentId || undefined,
        include_traits: includeTraits,
        include_events: includeEvents,
      };

      const result = await exportMutation.mutateAsync(params);

      // Handle file download
      if (result instanceof Blob) {
        const url = URL.createObjectURL(result);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audience-export-${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else {
        // JSON response - convert to downloadable file
        const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audience-export-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }

      onClose();
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExporting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-card border rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Download className="w-5 h-5" />
            Export Custom Audience
          </h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          {/* Segment selection */}
          <div>
            <label className="block text-sm font-medium mb-1.5">Segment (optional)</label>
            <select
              value={segmentId}
              onChange={(e) => setSegmentId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
            >
              <option value="">All profiles</option>
              {segments.map((segment) => (
                <option key={segment.id} value={segment.id}>
                  {segment.name} ({segment.profile_count?.toLocaleString() || 0} profiles)
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-muted-foreground">Leave empty to export all profiles</p>
          </div>

          {/* Format selection */}
          <div>
            <label className="block text-sm font-medium mb-1.5">Export Format</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setFormat('csv')}
                className={cn(
                  'flex items-center justify-center gap-2 p-3 rounded-lg border transition-all',
                  format === 'csv'
                    ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                    : 'hover:border-muted-foreground/20'
                )}
              >
                <FileSpreadsheet className="w-5 h-5" />
                <span className="font-medium">CSV</span>
              </button>
              <button
                type="button"
                onClick={() => setFormat('json')}
                className={cn(
                  'flex items-center justify-center gap-2 p-3 rounded-lg border transition-all',
                  format === 'json'
                    ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                    : 'hover:border-muted-foreground/20'
                )}
              >
                <FileJson className="w-5 h-5" />
                <span className="font-medium">JSON</span>
              </button>
            </div>
          </div>

          {/* Include options */}
          <div className="space-y-2">
            <label className="block text-sm font-medium">Include Data</label>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={includeTraits}
                  onChange={(e) => setIncludeTraits(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300"
                />
                <span className="text-sm">Profile traits & attributes</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={includeEvents}
                  onChange={(e) => setIncludeEvents(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300"
                />
                <span className="text-sm">Recent events (last 30 days)</span>
              </label>
            </div>
          </div>

          {/* Info box */}
          <div className="p-3 rounded-lg bg-muted/30 border text-sm">
            <p className="text-muted-foreground">
              Export includes: email, phone, identifiers, lifecycle stage
              {includeTraits && ', custom traits'}
              {includeEvents && ', event history'}
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleExport}
              disabled={isExporting}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {isExporting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              Export {format.toUpperCase()}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Audience card component
interface AudienceCardProps {
  audience: PlatformAudience;
  onSync: () => void;
  onDelete: () => void;
  onViewHistory: () => void;
  isSyncing: boolean;
}

function AudienceCard({ audience, onSync, onDelete, onViewHistory, isSyncing }: AudienceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const formatDate = (date: string | null) => {
    if (!date) return 'Never';
    return new Date(date).toLocaleDateString();
  };

  const matchRate = audience.match_rate ? `${audience.match_rate.toFixed(1)}%` : '-';

  return (
    <div className="p-4 rounded-xl border bg-card hover:shadow-md transition-all">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <PlatformIcon platform={audience.platform} />
          <div>
            <h3 className="font-semibold">{audience.platform_audience_name}</h3>
            <p className="text-sm text-muted-foreground">
              {PLATFORM_CONFIG[audience.platform]?.name} • {audience.ad_account_id}
            </p>
          </div>
        </div>
        <StatusBadge status={audience.last_sync_status as SyncStatus} />
      </div>

      {audience.description && (
        <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{audience.description}</p>
      )}

      <div className="grid grid-cols-3 gap-4 text-sm mb-4">
        <div>
          <div className="text-muted-foreground">Platform Size</div>
          <div className="font-semibold">{audience.platform_size?.toLocaleString() || '-'}</div>
        </div>
        <div>
          <div className="text-muted-foreground">Match Rate</div>
          <div className="font-semibold">{matchRate}</div>
        </div>
        <div>
          <div className="text-muted-foreground">Last Sync</div>
          <div className="font-semibold">{formatDate(audience.last_sync_at)}</div>
        </div>
      </div>

      {/* Auto-sync indicator */}
      {audience.auto_sync && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
          <RefreshCw className="w-3 h-3" />
          <span>Auto-sync every {audience.sync_interval_hours}h</span>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-3 border-t">
        <button
          onClick={onSync}
          disabled={isSyncing}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 rounded-md bg-primary/10 text-primary hover:bg-primary/20 text-sm font-medium transition-colors disabled:opacity-50"
        >
          {isSyncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
          Sync Now
        </button>
        <button
          onClick={onViewHistory}
          className="px-3 py-1.5 rounded-md bg-muted hover:bg-muted/80 text-sm font-medium transition-colors"
        >
          <History className="w-4 h-4" />
        </button>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="px-3 py-1.5 rounded-md bg-muted hover:bg-muted/80 text-sm font-medium transition-colors"
        >
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
        <button
          onClick={onDelete}
          className="px-3 py-1.5 rounded-md hover:bg-red-500/10 text-muted-foreground hover:text-red-500 text-sm font-medium transition-colors"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Expanded details */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Segment ID</span>
            <span className="font-mono text-xs">{audience.segment_id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Platform Audience ID</span>
            <span className="font-mono text-xs">
              {audience.platform_audience_id || 'Not created yet'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Created</span>
            <span>{new Date(audience.created_at).toLocaleDateString()}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// Main component
export function AudienceSync() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [platformFilter, setPlatformFilter] = useState<SyncPlatform | ''>('');
  const [historyAudience, setHistoryAudience] = useState<PlatformAudience | null>(null);
  const [syncingIds, setSyncingIds] = useState<Set<string>>(new Set());

  // Queries
  const { data: platformsData, isLoading: platformsLoading } = useConnectedPlatforms();
  const {
    data: audiencesData,
    isLoading: audiencesLoading,
    refetch,
  } = usePlatformAudiences({
    platform: platformFilter || undefined,
  });
  const { data: segmentsData } = useSegments({ status: 'active' });

  // Mutations
  const syncMutation = useTriggerSync();
  const deleteMutation = useDeletePlatformAudience();

  const connectedPlatforms = platformsData || [];
  const audiences = audiencesData?.audiences || [];
  const segments = segmentsData?.segments || [];

  // Filter audiences by search
  const filteredAudiences = audiences.filter(
    (a) =>
      a.platform_audience_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Handle sync
  const handleSync = async (audienceId: string) => {
    setSyncingIds((prev) => new Set(prev).add(audienceId));
    try {
      await syncMutation.mutateAsync({ audienceId, operation: 'update' });
      refetch();
    } catch (error) {
      console.error('Sync failed:', error);
    } finally {
      setSyncingIds((prev) => {
        const next = new Set(prev);
        next.delete(audienceId);
        return next;
      });
    }
  };

  // Handle delete
  const handleDelete = async (audienceId: string) => {
    if (
      !confirm(
        'Are you sure you want to delete this audience? This will also remove it from the ad platform.'
      )
    ) {
      return;
    }
    try {
      await deleteMutation.mutateAsync({ audienceId, deleteFromPlatform: true });
      refetch();
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  const isLoading = platformsLoading || audiencesLoading;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <ArrowUpRight className="w-6 h-6 text-primary" />
            Audience Sync
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Push CDP segments to ad platforms for targeting
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowExportModal(true)}
            disabled={segments.length === 0}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted disabled:opacity-50 transition-colors"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            disabled={connectedPlatforms.length === 0 || segments.length === 0}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Audience
          </button>
        </div>
      </div>

      {/* Connected platforms summary */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm text-muted-foreground">Connected:</span>
        {connectedPlatforms.length === 0 ? (
          <div className="flex items-center gap-2">
            <span className="text-sm text-amber-500">No platforms connected</span>
            <Link
              to="/dashboard/settings"
              className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
            >
              <Link2 className="w-3 h-3" />
              Connect platforms
            </Link>
          </div>
        ) : (
          connectedPlatforms.map((p) => (
            <div
              key={p.platform}
              className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-muted text-sm"
            >
              <PlatformIcon platform={p.platform} size="sm" />
              <span>{PLATFORM_CONFIG[p.platform].name}</span>
              <span className="text-muted-foreground">({p.ad_accounts.length})</span>
            </div>
          ))
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search audiences..."
            className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <select
          value={platformFilter}
          onChange={(e) => setPlatformFilter(e.target.value as SyncPlatform | '')}
          className="px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
        >
          <option value="">All Platforms</option>
          {Object.entries(PLATFORM_CONFIG).map(([key, config]) => (
            <option key={key} value={key}>
              {config.name}
            </option>
          ))}
        </select>
      </div>

      {/* Audiences grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : filteredAudiences.length === 0 ? (
        <div className="text-center py-12 bg-card border rounded-xl">
          <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="font-semibold mb-2">No audiences yet</h3>
          <p className="text-sm text-muted-foreground mb-4 max-w-md mx-auto">
            {connectedPlatforms.length === 0
              ? 'Connect your ad platforms (Meta, Google, TikTok, Snapchat) to start syncing audiences.'
              : segments.length === 0
                ? 'Create a CDP segment first, then sync it to your ad platforms.'
                : 'Create your first platform audience to start syncing.'}
          </p>
          {connectedPlatforms.length === 0 ? (
            <Link
              to="/dashboard/settings"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Link2 className="w-4 h-4" />
              Connect Platforms
            </Link>
          ) : segments.length === 0 ? (
            <Link
              to="/dashboard/cdp/segments"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Create Segment
            </Link>
          ) : (
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Create Audience
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredAudiences.map((audience) => (
            <AudienceCard
              key={audience.id}
              audience={audience}
              onSync={() => handleSync(audience.id)}
              onDelete={() => handleDelete(audience.id)}
              onViewHistory={() => setHistoryAudience(audience)}
              isSyncing={syncingIds.has(audience.id)}
            />
          ))}
        </div>
      )}

      {/* Create modal */}
      <CreateAudienceModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        segments={segments}
        connectedPlatforms={connectedPlatforms}
      />

      {/* Export modal */}
      <ExportAudienceModal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        segments={segments}
      />

      {/* History panel */}
      {historyAudience && (
        <SyncHistoryPanel
          audienceId={historyAudience.id}
          audienceName={historyAudience.platform_audience_name}
          onClose={() => setHistoryAudience(null)}
        />
      )}
    </div>
  );
}

export default AudienceSync;
