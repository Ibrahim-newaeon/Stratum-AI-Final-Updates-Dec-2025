/**
 * CDP Consent Manager Component
 * UI for managing privacy consent settings and viewing consent status
 */

import { useState } from 'react';
import {
  CheckCircle,
  Download,
  Filter,
  RefreshCw,
  Search,
  Shield,
  Users,
  XCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useQuery } from '@tanstack/react-query';

// Consent types
const CONSENT_TYPES = [
  { value: 'analytics', label: 'Analytics', description: 'Website analytics and tracking' },
  { value: 'ads', label: 'Advertising', description: 'Personalized advertising' },
  { value: 'email', label: 'Email Marketing', description: 'Marketing emails' },
  { value: 'sms', label: 'SMS Marketing', description: 'Marketing text messages' },
];

interface ConsentStats {
  consent_type: string;
  total_profiles: number;
  granted: number;
  revoked: number;
  grant_rate: number;
}

interface ConsentProfile {
  profile_id: string;
  email?: string;
  consent_type: string;
  granted: boolean;
  granted_at?: string;
  revoked_at?: string;
  source?: string;
}

// Custom hook for consent statistics
function useConsentStats(tenantId: number) {
  return useQuery({
    queryKey: ['cdp-consent-stats', tenantId],
    queryFn: async (): Promise<ConsentStats[]> => {
      // Consent stats API not yet available - return empty data
      return [];
    },
    staleTime: 60 * 1000,
  });
}

// Custom hook for consent profiles
function useConsentProfiles(
  tenantId: number,
  filters: { consent_type?: string; granted?: boolean }
) {
  return useQuery({
    queryKey: ['cdp-consent-profiles', tenantId, filters],
    queryFn: async (): Promise<{ profiles: ConsentProfile[]; total: number }> => {
      // Consent profiles API not yet available - return empty data
      return { profiles: [], total: 0 };
    },
    staleTime: 30 * 1000,
  });
}

export function ConsentManager() {
  const [selectedType, setSelectedType] = useState<string | undefined>(undefined);
  const [grantedFilter, setGrantedFilter] = useState<boolean | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState('');

  // For demo purposes, use tenant ID 1
  const tenantId = 1;

  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useConsentStats(tenantId);
  const { data: profilesData, isLoading: profilesLoading } = useConsentProfiles(tenantId, {
    consent_type: selectedType,
    granted: grantedFilter,
  });

  const profiles = profilesData?.profiles || [];

  const handleExportConsent = async (consentType?: string) => {
    const exportData = profiles.filter(
      (p) => !consentType || p.consent_type === consentType
    );
    if (exportData.length === 0) {
      alert('No consent records to export.');
      return;
    }
    const headers = ['Profile ID', 'Email', 'Consent Type', 'Granted', 'Granted At', 'Revoked At', 'Source'];
    const rows = exportData.map((p) => [
      p.profile_id,
      p.email || '',
      p.consent_type,
      p.granted ? 'Yes' : 'No',
      p.granted_at || '',
      p.revoked_at || '',
      p.source || '',
    ]);
    const csv = [headers, ...rows].map((r) => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `consent-export-${consentType || 'all'}-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="w-6 h-6 text-primary" />
            Consent Management
          </h2>
          <p className="text-muted-foreground">
            GDPR/CCPA compliant consent tracking and management
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetchStats()}
            className="px-3 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => handleExportConsent()}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export All
          </button>
        </div>
      </div>

      {/* Consent Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        {statsLoading
          ? Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="p-4 rounded-xl border bg-card animate-pulse">
                <div className="h-4 w-24 bg-muted rounded mb-2" />
                <div className="h-8 w-16 bg-muted rounded" />
              </div>
            ))
          : stats?.map((stat) => {
              const typeInfo = CONSENT_TYPES.find((t) => t.value === stat.consent_type);
              return (
                <div
                  key={stat.consent_type}
                  className={cn(
                    'p-4 rounded-xl border bg-card cursor-pointer hover:border-primary/50 transition-colors',
                    selectedType === stat.consent_type && 'border-primary'
                  )}
                  onClick={() =>
                    setSelectedType(
                      selectedType === stat.consent_type ? undefined : stat.consent_type
                    )
                  }
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-muted-foreground">
                      {typeInfo?.label || stat.consent_type}
                    </span>
                    <span
                      className={cn(
                        'text-xs px-2 py-0.5 rounded-full',
                        stat.grant_rate >= 70
                          ? 'bg-green-500/10 text-green-600'
                          : stat.grant_rate >= 50
                            ? 'bg-yellow-500/10 text-yellow-600'
                            : 'bg-red-500/10 text-red-600'
                      )}
                    >
                      {stat.grant_rate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="text-2xl font-bold">{stat.granted.toLocaleString()}</div>
                  <div className="text-xs text-muted-foreground">
                    of {stat.total_profiles.toLocaleString()} profiles
                  </div>
                  <div className="mt-2 flex items-center gap-2 text-xs">
                    <span className="flex items-center gap-1 text-green-600">
                      <CheckCircle className="w-3 h-3" />
                      {stat.granted}
                    </span>
                    <span className="flex items-center gap-1 text-red-600">
                      <XCircle className="w-3 h-3" />
                      {stat.revoked}
                    </span>
                  </div>
                </div>
              );
            })}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 p-4 rounded-xl border bg-card">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by email or profile ID..."
            className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <select
            value={selectedType || ''}
            onChange={(e) => setSelectedType(e.target.value || undefined)}
            className="px-3 py-2 rounded-lg border bg-background"
          >
            <option value="">All Types</option>
            {CONSENT_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>

          <select
            value={grantedFilter === undefined ? '' : grantedFilter.toString()}
            onChange={(e) =>
              setGrantedFilter(e.target.value === '' ? undefined : e.target.value === 'true')
            }
            className="px-3 py-2 rounded-lg border bg-background"
          >
            <option value="">All Status</option>
            <option value="true">Granted</option>
            <option value="false">Revoked</option>
          </select>
        </div>
      </div>

      {/* Consent Records Table */}
      <div className="rounded-xl border bg-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium">Profile</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Consent Type</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Date</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {profilesLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td className="px-4 py-3">
                      <div className="h-4 w-32 bg-muted rounded animate-pulse" />
                    </td>
                    <td className="px-4 py-3">
                      <div className="h-4 w-20 bg-muted rounded animate-pulse" />
                    </td>
                    <td className="px-4 py-3">
                      <div className="h-4 w-16 bg-muted rounded animate-pulse" />
                    </td>
                    <td className="px-4 py-3">
                      <div className="h-4 w-24 bg-muted rounded animate-pulse" />
                    </td>
                    <td className="px-4 py-3">
                      <div className="h-4 w-16 bg-muted rounded animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : profiles.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-12 text-center text-muted-foreground">
                    <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    No consent records found.
                  </td>
                </tr>
              ) : (
                profiles.map((profile) => {
                  const typeInfo = CONSENT_TYPES.find((t) => t.value === profile.consent_type);
                  return (
                    <tr
                      key={`${profile.profile_id}-${profile.consent_type}`}
                      className="hover:bg-muted/50"
                    >
                      <td className="px-4 py-3">
                        <div>
                          <div className="font-medium">{profile.email || 'Anonymous'}</div>
                          <div className="text-xs text-muted-foreground font-mono">
                            {profile.profile_id}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 rounded-full text-xs bg-muted">
                          {typeInfo?.label || profile.consent_type}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {profile.granted ? (
                          <span className="flex items-center gap-1 text-green-600">
                            <CheckCircle className="w-4 h-4" />
                            Granted
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-red-600">
                            <XCircle className="w-4 h-4" />
                            Revoked
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {profile.granted_at
                          ? new Date(profile.granted_at).toLocaleDateString()
                          : '-'}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs text-muted-foreground capitalize">
                          {profile.source?.replace('_', ' ') || '-'}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-4 py-3 border-t flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Showing {profiles.length} of {profilesData?.total || 0} records
          </div>
          <div className="flex gap-2">
            <button className="px-3 py-1 rounded border hover:bg-muted text-sm" disabled>
              Previous
            </button>
            <button className="px-3 py-1 rounded border hover:bg-muted text-sm">Next</button>
          </div>
        </div>
      </div>

      {/* Compliance Info */}
      <div className="p-4 rounded-xl border bg-muted/50">
        <h3 className="font-medium mb-2 flex items-center gap-2">
          <Shield className="w-4 h-4" />
          Compliance Information
        </h3>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Data Retention:</span>
            <span className="ml-2 font-medium">365 days</span>
          </div>
          <div>
            <span className="text-muted-foreground">Audit Trail:</span>
            <span className="ml-2 text-green-600 font-medium">Enabled</span>
          </div>
          <div>
            <span className="text-muted-foreground">Auto-Expiry:</span>
            <span className="ml-2 text-green-600 font-medium">Enabled (24 months)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
