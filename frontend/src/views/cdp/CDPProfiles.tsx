/**
 * CDP Profiles - Profile viewer and manager
 */

import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowDownTrayIcon,
  CalendarIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CurrencyDollarIcon,
  DevicePhoneMobileIcon,
  EnvelopeIcon,
  EyeIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  PhoneIcon,
  UserCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import {
  type IdentifierType,
  type LifecycleStage,
  useCDPProfile,
  useExportAudience,
  useSearchProfiles,
} from '@/api/cdp';

// Lifecycle Stage Badge
function LifecycleBadge({ stage }: { stage: LifecycleStage }) {
  const config = {
    anonymous: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
    known: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    customer: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    churned: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  };

  return (
    <span className={cn('px-2 py-1 rounded-full text-xs font-medium capitalize', config[stage])}>
      {stage}
    </span>
  );
}

// Identifier Icon
function IdentifierIcon({ type }: { type: IdentifierType }) {
  const icons = {
    email: EnvelopeIcon,
    phone: PhoneIcon,
    device_id: DevicePhoneMobileIcon,
    anonymous_id: UserCircleIcon,
    external_id: UserCircleIcon,
  };
  const Icon = icons[type] || UserCircleIcon;
  return <Icon className="h-4 w-4 text-muted-foreground" />;
}

// Profile Detail Modal
function ProfileDetailModal({ profileId, onClose }: { profileId: string; onClose: () => void }) {
  const { data: profile, isLoading } = useCDPProfile(profileId);

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div className="bg-card rounded-xl p-8">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
        </div>
      </div>
    );
  }

  if (!profile) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-card rounded-xl border shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-full bg-gradient-stratum flex items-center justify-center">
              <UserCircleIcon className="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 className="font-semibold">Profile Details</h3>
              <p className="text-sm text-muted-foreground font-mono">{profile.id.slice(0, 8)}...</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-muted rounded-lg transition-colors">
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[calc(90vh-120px)] space-y-6">
          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-muted/50 rounded-lg p-3">
              <p className="text-xs text-muted-foreground">Lifecycle</p>
              <div className="mt-1">
                <LifecycleBadge stage={profile.lifecycle_stage} />
              </div>
            </div>
            <div className="bg-muted/50 rounded-lg p-3">
              <p className="text-xs text-muted-foreground">Total Events</p>
              <p className="font-semibold">{profile.total_events.toLocaleString()}</p>
            </div>
            <div className="bg-muted/50 rounded-lg p-3">
              <p className="text-xs text-muted-foreground">Total Revenue</p>
              <p className="font-semibold">${profile.total_revenue.toLocaleString()}</p>
            </div>
            <div className="bg-muted/50 rounded-lg p-3">
              <p className="text-xs text-muted-foreground">Purchases</p>
              <p className="font-semibold">{profile.total_purchases}</p>
            </div>
          </div>

          {/* Identifiers */}
          <div>
            <h4 className="font-medium mb-3">Identifiers ({profile.identifiers?.length || 0})</h4>
            <div className="space-y-2">
              {profile.identifiers?.map((id) => (
                <div
                  key={id.id}
                  className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <IdentifierIcon type={id.identifier_type} />
                    <div>
                      <p className="text-sm font-medium capitalize">
                        {id.identifier_type.replace('_', ' ')}
                      </p>
                      <p className="text-xs text-muted-foreground font-mono">
                        {id.identifier_hash.slice(0, 16)}...
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    {id.is_primary && (
                      <span className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded">
                        Primary
                      </span>
                    )}
                    <p className="text-xs text-muted-foreground mt-1">
                      Score: {(id.confidence_score * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
              ))}
              {(!profile.identifiers || profile.identifiers.length === 0) && (
                <p className="text-sm text-muted-foreground">No identifiers found</p>
              )}
            </div>
          </div>

          {/* Profile Data */}
          {profile.profile_data && Object.keys(profile.profile_data).length > 0 && (
            <div>
              <h4 className="font-medium mb-3">Profile Data</h4>
              <pre className="bg-muted/50 rounded-lg p-3 text-xs overflow-x-auto">
                {JSON.stringify(profile.profile_data, null, 2)}
              </pre>
            </div>
          )}

          {/* Computed Traits */}
          {profile.computed_traits && Object.keys(profile.computed_traits).length > 0 && (
            <div>
              <h4 className="font-medium mb-3">Computed Traits</h4>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(profile.computed_traits).map(([key, value]) => (
                  <div key={key} className="bg-muted/50 rounded-lg p-2">
                    <p className="text-xs text-muted-foreground">{key}</p>
                    <p className="text-sm font-medium">{String(value)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div className="grid grid-cols-2 gap-4 pt-4 border-t">
            <div>
              <p className="text-xs text-muted-foreground">First Seen</p>
              <p className="text-sm">{new Date(profile.first_seen_at).toLocaleString()}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Last Seen</p>
              <p className="text-sm">{new Date(profile.last_seen_at).toLocaleString()}</p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t">
          <Link
            to={`/dashboard/cdp/identity?profile=${profile.id}`}
            className="px-4 py-2 text-sm font-medium hover:bg-muted rounded-lg transition-colors"
          >
            View Identity Graph
          </Link>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// Filter Panel
type ProfileFilters = {
  lifecycle_stages?: LifecycleStage[];
  has_email?: boolean;
  has_phone?: boolean;
  is_customer?: boolean;
};

function FilterPanel({
  filters,
  onFilterChange,
  onClose,
}: {
  filters: ProfileFilters;
  onFilterChange: (filters: ProfileFilters) => void;
  onClose: () => void;
}) {
  const lifecycleOptions: LifecycleStage[] = ['anonymous', 'known', 'customer', 'churned'];

  return (
    <div className="bg-card rounded-xl border p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">Filters</h3>
        <button onClick={onClose} className="p-1 hover:bg-muted rounded">
          <XMarkIcon className="h-4 w-4" />
        </button>
      </div>

      {/* Lifecycle Stage */}
      <div>
        <label className="text-sm font-medium">Lifecycle Stage</label>
        <div className="mt-2 flex flex-wrap gap-2">
          {lifecycleOptions.map((stage) => (
            <button
              key={stage}
              onClick={() => {
                const current = filters.lifecycle_stages || [];
                const updated = current.includes(stage)
                  ? current.filter((s) => s !== stage)
                  : [...current, stage];
                onFilterChange({
                  ...filters,
                  lifecycle_stages: updated.length > 0 ? updated : undefined,
                });
              }}
              className={cn(
                'px-3 py-1 rounded-full text-sm capitalize transition-colors',
                filters.lifecycle_stages?.includes(stage)
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted hover:bg-muted/80'
              )}
            >
              {stage}
            </button>
          ))}
        </div>
      </div>

      {/* Has Email/Phone */}
      <div className="flex gap-4">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={filters.has_email || false}
            onChange={(e) =>
              onFilterChange({ ...filters, has_email: e.target.checked || undefined })
            }
            className="rounded border-gray-300"
          />
          <span className="text-sm">Has Email</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={filters.has_phone || false}
            onChange={(e) =>
              onFilterChange({ ...filters, has_phone: e.target.checked || undefined })
            }
            className="rounded border-gray-300"
          />
          <span className="text-sm">Has Phone</span>
        </label>
      </div>

      {/* Customer Only */}
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={filters.is_customer || false}
          onChange={(e) =>
            onFilterChange({ ...filters, is_customer: e.target.checked || undefined })
          }
          className="rounded border-gray-300"
        />
        <span className="text-sm">Customers Only</span>
      </label>

      {/* Clear Filters */}
      <button
        onClick={() => onFilterChange({})}
        className="w-full py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        Clear All Filters
      </button>
    </div>
  );
}

export default function CDPProfiles() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [filters, setFilters] = useState<{
    lifecycle_stages?: LifecycleStage[];
    has_email?: boolean;
    has_phone?: boolean;
    is_customer?: boolean;
  }>({});

  const pageSize = 20;

  const { data, isLoading } = useSearchProfiles({
    query: search || undefined,
    limit: pageSize,
    offset: (page - 1) * pageSize,
    lifecycle_stages: filters.lifecycle_stages,
    has_email: filters.has_email,
    has_phone: filters.has_phone,
    is_customer: filters.is_customer,
    sort_by: 'last_seen_at',
    sort_order: 'desc',
  });

  const exportMutation = useExportAudience();

  const totalPages = Math.ceil((data?.total || 0) / pageSize);

  const handleExport = async () => {
    try {
      await exportMutation.mutateAsync({ format: 'csv', limit: 1000 });
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.lifecycle_stages?.length) count++;
    if (filters.has_email) count++;
    if (filters.has_phone) count++;
    if (filters.is_customer) count++;
    return count;
  }, [filters]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Profiles</h1>
          <p className="text-muted-foreground mt-1">
            {data?.total?.toLocaleString() || 0} total profiles
          </p>
        </div>
        <div className="flex items-center gap-3">
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

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search by email, phone, or ID..."
            className="w-full pl-10 pr-4 py-2 border rounded-lg bg-background focus:ring-2 focus:ring-primary focus:outline-none"
          />
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={cn(
            'flex items-center gap-2 px-4 py-2 border rounded-lg transition-colors',
            showFilters || activeFilterCount > 0 ? 'bg-primary/10 border-primary' : 'hover:bg-muted'
          )}
        >
          <FunnelIcon className="h-4 w-4" />
          Filters
          {activeFilterCount > 0 && (
            <span className="px-1.5 py-0.5 bg-primary text-primary-foreground text-xs rounded-full">
              {activeFilterCount}
            </span>
          )}
        </button>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <FilterPanel
          filters={filters}
          onFilterChange={(newFilters) => {
            setFilters(newFilters);
            setPage(1);
          }}
          onClose={() => setShowFilters(false)}
        />
      )}

      {/* Profiles Table */}
      <div className="bg-card rounded-xl border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                  Profile
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                  Lifecycle
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                  Identifiers
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                  Events
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                  Revenue
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                  Last Seen
                </th>
                <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b">
                    <td colSpan={7} className="px-4 py-4">
                      <div className="h-6 bg-muted animate-pulse rounded" />
                    </td>
                  </tr>
                ))
              ) : data?.profiles.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-muted-foreground">
                    No profiles found
                  </td>
                </tr>
              ) : (
                data?.profiles.map((profile) => (
                  <tr key={profile.id} className="border-b hover:bg-muted/50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-gradient-stratum flex items-center justify-center">
                          <UserCircleIcon className="h-4 w-4 text-white" />
                        </div>
                        <div>
                          <p className="font-medium font-mono text-sm">
                            {profile.id.slice(0, 8)}...
                          </p>
                          {profile.external_id && (
                            <p className="text-xs text-muted-foreground">{profile.external_id}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <LifecycleBadge stage={profile.lifecycle_stage} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        {profile.identifiers
                          ?.slice(0, 3)
                          .map((id, i) => <IdentifierIcon key={i} type={id.identifier_type} />)}
                        {(profile.identifiers?.length || 0) > 3 && (
                          <span className="text-xs text-muted-foreground">
                            +{(profile.identifiers?.length || 0) - 3}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">{profile.total_events.toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 text-sm">
                        <CurrencyDollarIcon className="h-4 w-4 text-muted-foreground" />
                        {profile.total_revenue.toLocaleString()}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <CalendarIcon className="h-4 w-4" />
                        {new Date(profile.last_seen_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => setSelectedProfileId(profile.id)}
                        className="p-2 hover:bg-muted rounded-lg transition-colors"
                        title="View Details"
                      >
                        <EyeIcon className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t">
            <p className="text-sm text-muted-foreground">
              Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, data?.total || 0)} of{' '}
              {data?.total?.toLocaleString()} profiles
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="p-2 hover:bg-muted rounded-lg transition-colors disabled:opacity-50"
              >
                <ChevronLeftIcon className="h-4 w-4" />
              </button>
              <span className="text-sm">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="p-2 hover:bg-muted rounded-lg transition-colors disabled:opacity-50"
              >
                <ChevronRightIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Profile Detail Modal */}
      {selectedProfileId && (
        <ProfileDetailModal
          profileId={selectedProfileId}
          onClose={() => setSelectedProfileId(null)}
        />
      )}
    </div>
  );
}
