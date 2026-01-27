/**
 * CDP Profile Search & Export Component
 * Advanced profile search with filtering and export capabilities
 */

import { useState } from 'react';
import {
  Activity,
  Calendar,
  DollarSign,
  Download,
  Eye,
  FileJson,
  FileText,
  Filter,
  Loader2,
  Mail,
  Phone,
  RefreshCw,
  Search,
  Tag,
  Target,
  User,
  Users,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  CDPProfile,
  LifecycleStage,
  ProfileSearchParams,
  RFMSegment,
  useExportAudience,
  useProfileStatistics,
  useSearchProfiles,
  useSegments,
} from '@/api/cdp';

// Lifecycle stages
const LIFECYCLE_STAGES: { value: LifecycleStage; label: string; color: string }[] = [
  { value: 'anonymous', label: 'Anonymous', color: 'bg-gray-500' },
  { value: 'known', label: 'Known', color: 'bg-blue-500' },
  { value: 'customer', label: 'Customer', color: 'bg-green-500' },
  { value: 'churned', label: 'Churned', color: 'bg-red-500' },
];

// RFM segments for filtering
const RFM_SEGMENTS: { value: RFMSegment; label: string }[] = [
  { value: 'champions', label: 'Champions' },
  { value: 'loyal_customers', label: 'Loyal Customers' },
  { value: 'potential_loyalists', label: 'Potential Loyalists' },
  { value: 'new_customers', label: 'New Customers' },
  { value: 'promising', label: 'Promising' },
  { value: 'need_attention', label: 'Need Attention' },
  { value: 'about_to_sleep', label: 'About to Sleep' },
  { value: 'at_risk', label: 'At Risk' },
  { value: 'cannot_lose', label: "Can't Lose" },
  { value: 'hibernating', label: 'Hibernating' },
  { value: 'lost', label: 'Lost' },
];

// Sort options
const SORT_OPTIONS = [
  { value: 'last_seen_at', label: 'Last Seen' },
  { value: 'first_seen_at', label: 'First Seen' },
  { value: 'total_events', label: 'Total Events' },
  { value: 'total_revenue', label: 'Total Revenue' },
  { value: 'created_at', label: 'Created Date' },
];

interface FilterPanelProps {
  filters: ProfileSearchParams;
  onFilterChange: (filters: ProfileSearchParams) => void;
  onClear: () => void;
}

function FilterPanel({ filters, onFilterChange, onClear }: FilterPanelProps) {
  const { data: segmentsData } = useSegments();
  const segments = segmentsData?.segments || [];

  const updateFilter = (key: keyof ProfileSearchParams, value: unknown) => {
    onFilterChange({ ...filters, [key]: value });
  };

  const activeFilterCount = Object.values(filters).filter(
    (v) => v !== undefined && v !== '' && (!Array.isArray(v) || v.length > 0)
  ).length;

  return (
    <div className="p-4 rounded-xl border bg-card space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium flex items-center gap-2">
          <Filter className="w-4 h-4" />
          Filters
          {activeFilterCount > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-medium">
              {activeFilterCount} active
            </span>
          )}
        </h3>
        {activeFilterCount > 0 && (
          <button
            onClick={onClear}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Lifecycle Stage */}
      <div>
        <label className="block text-sm font-medium mb-2">Lifecycle Stage</label>
        <div className="flex flex-wrap gap-2">
          {LIFECYCLE_STAGES.map((stage) => (
            <button
              key={stage.value}
              onClick={() => {
                const current = filters.lifecycle_stages || [];
                const updated = current.includes(stage.value)
                  ? current.filter((s) => s !== stage.value)
                  : [...current, stage.value];
                updateFilter('lifecycle_stages', updated);
              }}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors',
                filters.lifecycle_stages?.includes(stage.value)
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'hover:border-primary/50'
              )}
            >
              {stage.label}
            </button>
          ))}
        </div>
      </div>

      {/* Segment filter */}
      {segments.length > 0 && (
        <div>
          <label className="block text-sm font-medium mb-2">Segment</label>
          <select
            value={filters.segment_ids?.[0] || ''}
            onChange={(e) => updateFilter('segment_ids', e.target.value ? [e.target.value] : [])}
            className="w-full px-3 py-2 rounded-lg border bg-background"
          >
            <option value="">All segments</option>
            {segments.map((segment) => (
              <option key={segment.id} value={segment.id}>
                {segment.name} ({segment.profile_count.toLocaleString()})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* RFM Segment */}
      <div>
        <label className="block text-sm font-medium mb-2">RFM Segment</label>
        <select
          value={filters.rfm_segments?.[0] || ''}
          onChange={(e) =>
            updateFilter('rfm_segments', e.target.value ? [e.target.value as RFMSegment] : [])
          }
          className="w-full px-3 py-2 rounded-lg border bg-background"
        >
          <option value="">All RFM segments</option>
          {RFM_SEGMENTS.map((segment) => (
            <option key={segment.value} value={segment.value}>
              {segment.label}
            </option>
          ))}
        </select>
      </div>

      {/* Identifier filters */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="flex items-center gap-2 text-sm font-medium mb-2">
            <Mail className="w-4 h-4" />
            Has Email
          </label>
          <select
            value={filters.has_email === undefined ? '' : String(filters.has_email)}
            onChange={(e) =>
              updateFilter(
                'has_email',
                e.target.value === '' ? undefined : e.target.value === 'true'
              )
            }
            className="w-full px-3 py-2 rounded-lg border bg-background"
          >
            <option value="">Any</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </div>
        <div>
          <label className="flex items-center gap-2 text-sm font-medium mb-2">
            <Phone className="w-4 h-4" />
            Has Phone
          </label>
          <select
            value={filters.has_phone === undefined ? '' : String(filters.has_phone)}
            onChange={(e) =>
              updateFilter(
                'has_phone',
                e.target.value === '' ? undefined : e.target.value === 'true'
              )
            }
            className="w-full px-3 py-2 rounded-lg border bg-background"
          >
            <option value="">Any</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </div>
      </div>

      {/* Event count range */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="flex items-center gap-2 text-sm font-medium mb-2">
            <Activity className="w-4 h-4" />
            Min Events
          </label>
          <input
            type="number"
            value={filters.min_events || ''}
            onChange={(e) =>
              updateFilter('min_events', e.target.value ? Number(e.target.value) : undefined)
            }
            placeholder="0"
            min={0}
            className="w-full px-3 py-2 rounded-lg border bg-background"
          />
        </div>
        <div>
          <label className="flex items-center gap-2 text-sm font-medium mb-2">
            <Activity className="w-4 h-4" />
            Max Events
          </label>
          <input
            type="number"
            value={filters.max_events || ''}
            onChange={(e) =>
              updateFilter('max_events', e.target.value ? Number(e.target.value) : undefined)
            }
            placeholder="No limit"
            min={0}
            className="w-full px-3 py-2 rounded-lg border bg-background"
          />
        </div>
      </div>

      {/* Revenue range */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="flex items-center gap-2 text-sm font-medium mb-2">
            <DollarSign className="w-4 h-4" />
            Min Revenue
          </label>
          <input
            type="number"
            value={filters.min_revenue || ''}
            onChange={(e) =>
              updateFilter('min_revenue', e.target.value ? Number(e.target.value) : undefined)
            }
            placeholder="$0"
            min={0}
            className="w-full px-3 py-2 rounded-lg border bg-background"
          />
        </div>
        <div>
          <label className="flex items-center gap-2 text-sm font-medium mb-2">
            <DollarSign className="w-4 h-4" />
            Max Revenue
          </label>
          <input
            type="number"
            value={filters.max_revenue || ''}
            onChange={(e) =>
              updateFilter('max_revenue', e.target.value ? Number(e.target.value) : undefined)
            }
            placeholder="No limit"
            min={0}
            className="w-full px-3 py-2 rounded-lg border bg-background"
          />
        </div>
      </div>

      {/* Date range */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="flex items-center gap-2 text-sm font-medium mb-2">
            <Calendar className="w-4 h-4" />
            Last Seen After
          </label>
          <input
            type="date"
            value={filters.last_seen_after || ''}
            onChange={(e) => updateFilter('last_seen_after', e.target.value || undefined)}
            className="w-full px-3 py-2 rounded-lg border bg-background"
          />
        </div>
        <div>
          <label className="flex items-center gap-2 text-sm font-medium mb-2">
            <Calendar className="w-4 h-4" />
            Last Seen Before
          </label>
          <input
            type="date"
            value={filters.last_seen_before || ''}
            onChange={(e) => updateFilter('last_seen_before', e.target.value || undefined)}
            className="w-full px-3 py-2 rounded-lg border bg-background"
          />
        </div>
      </div>

      {/* Customer filter */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium mb-2">
          <Target className="w-4 h-4" />
          Customer Status
        </label>
        <select
          value={filters.is_customer === undefined ? '' : String(filters.is_customer)}
          onChange={(e) =>
            updateFilter(
              'is_customer',
              e.target.value === '' ? undefined : e.target.value === 'true'
            )
          }
          className="w-full px-3 py-2 rounded-lg border bg-background"
        >
          <option value="">All profiles</option>
          <option value="true">Customers only</option>
          <option value="false">Non-customers only</option>
        </select>
      </div>
    </div>
  );
}

// Profile card component
interface ProfileCardProps {
  profile: CDPProfile;
  onView: () => void;
}

function ProfileCard({ profile, onView }: ProfileCardProps) {
  const lifecycleConfig = LIFECYCLE_STAGES.find((s) => s.value === profile.lifecycle_stage);

  return (
    <div className="p-4 rounded-xl border bg-card hover:shadow-md transition-all">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
            <User className="w-5 h-5 text-primary" />
          </div>
          <div>
            <div className="font-medium">
              {profile.external_id || profile.id.slice(0, 12) + '...'}
            </div>
            <div className="flex items-center gap-2">
              <span
                className={cn('w-2 h-2 rounded-full', lifecycleConfig?.color || 'bg-gray-500')}
              />
              <span className="text-xs text-muted-foreground capitalize">
                {profile.lifecycle_stage}
              </span>
            </div>
          </div>
        </div>
        <button onClick={onView} className="p-2 rounded-lg hover:bg-muted transition-colors">
          <Eye className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-muted-foreground">Events</span>
          <span className="ml-2 font-medium">{profile.total_events.toLocaleString()}</span>
        </div>
        <div>
          <span className="text-muted-foreground">Revenue</span>
          <span className="ml-2 font-medium">${profile.total_revenue.toLocaleString()}</span>
        </div>
        <div>
          <span className="text-muted-foreground">First Seen</span>
          <span className="ml-2 font-medium text-xs">
            {new Date(profile.first_seen_at).toLocaleDateString()}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground">Last Seen</span>
          <span className="ml-2 font-medium text-xs">
            {new Date(profile.last_seen_at).toLocaleDateString()}
          </span>
        </div>
      </div>

      {/* Identifiers */}
      <div className="mt-3 pt-3 border-t flex flex-wrap gap-2">
        {profile.identifiers?.map((id, index) => (
          <span
            key={index}
            className="px-2 py-0.5 rounded-full bg-muted text-xs"
            title={id.identifier_hash}
          >
            {id.identifier_type}
          </span>
        ))}
      </div>
    </div>
  );
}

export function ProfileSearch() {
  const [showFilters, setShowFilters] = useState(true);
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<ProfileSearchParams>({
    limit: 20,
    sort_by: 'last_seen_at',
    sort_order: 'desc',
    include_identifiers: true,
  });
  const [selectedProfile, setSelectedProfile] = useState<CDPProfile | null>(null);

  const searchParams: ProfileSearchParams = {
    ...filters,
    query: query || undefined,
  };

  const { data: searchResult, isLoading, refetch } = useSearchProfiles(searchParams);
  const { data: statistics } = useProfileStatistics();
  const exportMutation = useExportAudience();

  const handleClearFilters = () => {
    setFilters({
      limit: 20,
      sort_by: 'last_seen_at',
      sort_order: 'desc',
      include_identifiers: true,
    });
    setQuery('');
  };

  const handleExport = async (format: 'json' | 'csv') => {
    const exportParams = {
      ...filters,
      format,
      limit: 50000, // Max export limit
    };

    try {
      const result = await exportMutation.mutateAsync(exportParams);

      if (format === 'csv' && result instanceof Blob) {
        // Download CSV
        const url = URL.createObjectURL(result);
        const a = document.createElement('a');
        a.href = url;
        a.download = `profiles_export_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else if (format === 'json') {
        // Download JSON
        const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `profiles_export_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  const profiles = searchResult?.profiles || [];
  const total = searchResult?.total || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Search className="w-6 h-6 text-primary" />
            Profile Search
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Search and export profiles with advanced filtering
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors',
              showFilters ? 'bg-primary/10 border-primary' : 'hover:bg-muted'
            )}
          >
            <Filter className="w-4 h-4" />
            Filters
          </button>
          <div className="relative">
            <button
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              onClick={() => handleExport('json')}
              disabled={exportMutation.isPending}
            >
              {exportMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              Export
            </button>
          </div>
        </div>
      </div>

      {/* Stats */}
      {statistics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl border bg-card">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Users className="w-4 h-4" />
              Total Profiles
            </div>
            <div className="text-2xl font-bold">{statistics.total_profiles.toLocaleString()}</div>
          </div>
          <div className="p-4 rounded-xl border bg-card">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Mail className="w-4 h-4" />
              Email Coverage
            </div>
            <div className="text-2xl font-bold">{statistics.email_coverage_pct.toFixed(1)}%</div>
          </div>
          <div className="p-4 rounded-xl border bg-card">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Target className="w-4 h-4" />
              Customers
            </div>
            <div className="text-2xl font-bold">{statistics.total_customers.toLocaleString()}</div>
          </div>
          <div className="p-4 rounded-xl border bg-card">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Activity className="w-4 h-4" />
              Active (30d)
            </div>
            <div className="text-2xl font-bold">
              {statistics.active_profiles_30d.toLocaleString()}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Filters panel */}
        {showFilters && (
          <div className="lg:col-span-1">
            <FilterPanel
              filters={filters}
              onFilterChange={setFilters}
              onClear={handleClearFilters}
            />
          </div>
        )}

        {/* Results */}
        <div className={cn(showFilters ? 'lg:col-span-3' : 'lg:col-span-4')}>
          {/* Search bar and sort */}
          <div className="flex flex-col sm:flex-row gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by external ID or profile data..."
                className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <select
              value={filters.sort_by}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  sort_by: e.target.value as ProfileSearchParams['sort_by'],
                })
              }
              className="px-3 py-2 rounded-lg border bg-background"
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              value={filters.sort_order}
              onChange={(e) =>
                setFilters({ ...filters, sort_order: e.target.value as 'asc' | 'desc' })
              }
              className="px-3 py-2 rounded-lg border bg-background"
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
            <button
              onClick={() => refetch()}
              disabled={isLoading}
              className="px-3 py-2 rounded-lg border hover:bg-muted transition-colors"
            >
              <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
            </button>
          </div>

          {/* Results count */}
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-muted-foreground">
              {isLoading ? 'Searching...' : `${total.toLocaleString()} profiles found`}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleExport('json')}
                disabled={exportMutation.isPending || total === 0}
                className="flex items-center gap-1 px-3 py-1.5 rounded-md border hover:bg-muted text-sm transition-colors disabled:opacity-50"
              >
                <FileJson className="w-4 h-4" />
                JSON
              </button>
              <button
                onClick={() => handleExport('csv')}
                disabled={exportMutation.isPending || total === 0}
                className="flex items-center gap-1 px-3 py-1.5 rounded-md border hover:bg-muted text-sm transition-colors disabled:opacity-50"
              >
                <FileText className="w-4 h-4" />
                CSV
              </button>
            </div>
          </div>

          {/* Profile grid */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : profiles.length === 0 ? (
            <div className="text-center py-12 bg-card border rounded-xl">
              <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="font-semibold mb-2">No profiles found</h3>
              <p className="text-sm text-muted-foreground">
                Try adjusting your filters or search query
              </p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {profiles.map((profile) => (
                  <ProfileCard
                    key={profile.id}
                    profile={profile}
                    onView={() => setSelectedProfile(profile)}
                  />
                ))}
              </div>

              {/* Pagination info */}
              <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
                <span>
                  Showing {profiles.length} of {total.toLocaleString()} profiles
                </span>
                <div className="flex items-center gap-2">
                  <span>Results per page:</span>
                  <select
                    value={filters.limit}
                    onChange={(e) => setFilters({ ...filters, limit: Number(e.target.value) })}
                    className="px-2 py-1 rounded border bg-background"
                  >
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Profile detail modal */}
      {selectedProfile && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-background rounded-xl border max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="p-4 border-b flex items-center justify-between sticky top-0 bg-background">
              <h3 className="font-semibold">Profile Details</h3>
              <button
                onClick={() => setSelectedProfile(null)}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-6 space-y-6">
              {/* Profile header */}
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="w-8 h-8 text-primary" />
                </div>
                <div>
                  <div className="text-lg font-semibold">
                    {selectedProfile.external_id || 'Anonymous Profile'}
                  </div>
                  <div className="text-sm text-muted-foreground">ID: {selectedProfile.id}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className={cn(
                        'px-2 py-0.5 rounded-full text-xs font-medium',
                        LIFECYCLE_STAGES.find((s) => s.value === selectedProfile.lifecycle_stage)
                          ?.color || 'bg-gray-500',
                        'text-white'
                      )}
                    >
                      {selectedProfile.lifecycle_stage}
                    </span>
                  </div>
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-3 rounded-lg bg-muted/50">
                  <div className="text-xs text-muted-foreground">Events</div>
                  <div className="font-semibold">
                    {selectedProfile.total_events.toLocaleString()}
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-muted/50">
                  <div className="text-xs text-muted-foreground">Sessions</div>
                  <div className="font-semibold">
                    {selectedProfile.total_sessions.toLocaleString()}
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-muted/50">
                  <div className="text-xs text-muted-foreground">Purchases</div>
                  <div className="font-semibold">
                    {selectedProfile.total_purchases.toLocaleString()}
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-muted/50">
                  <div className="text-xs text-muted-foreground">Revenue</div>
                  <div className="font-semibold">
                    ${selectedProfile.total_revenue.toLocaleString()}
                  </div>
                </div>
              </div>

              {/* Identifiers */}
              <div>
                <h4 className="font-medium mb-2">Identifiers</h4>
                <div className="space-y-2">
                  {selectedProfile.identifiers?.map((id, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-2 rounded-lg bg-muted/50"
                    >
                      <div className="flex items-center gap-2">
                        <Tag className="w-4 h-4 text-muted-foreground" />
                        <span className="font-medium capitalize">{id.identifier_type}</span>
                        {id.is_primary && (
                          <span className="px-1.5 py-0.5 rounded text-xs bg-primary/10 text-primary">
                            Primary
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>Confidence: {(id.confidence_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Profile data */}
              {Object.keys(selectedProfile.profile_data || {}).length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Profile Data</h4>
                  <pre className="p-3 rounded-lg bg-muted/50 text-sm overflow-x-auto">
                    {JSON.stringify(selectedProfile.profile_data, null, 2)}
                  </pre>
                </div>
              )}

              {/* Computed traits */}
              {Object.keys(selectedProfile.computed_traits || {}).length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Computed Traits</h4>
                  <pre className="p-3 rounded-lg bg-muted/50 text-sm overflow-x-auto">
                    {JSON.stringify(selectedProfile.computed_traits, null, 2)}
                  </pre>
                </div>
              )}

              {/* Timestamps */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">First Seen:</span>
                  <span className="ml-2">
                    {new Date(selectedProfile.first_seen_at).toLocaleString()}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Last Seen:</span>
                  <span className="ml-2">
                    {new Date(selectedProfile.last_seen_at).toLocaleString()}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Created:</span>
                  <span className="ml-2">
                    {new Date(selectedProfile.created_at).toLocaleString()}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Updated:</span>
                  <span className="ml-2">
                    {new Date(selectedProfile.updated_at).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProfileSearch;
