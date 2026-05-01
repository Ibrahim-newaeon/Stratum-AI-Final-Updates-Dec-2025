// =============================================================================
// Stratum AI — Compliance Dashboard (Gap #5)
// =============================================================================

import { useState } from 'react';
import { cn } from '@/lib/utils';
import {
  ShieldCheckIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  UserGroupIcon,
  DocumentTextIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';

const API_URL = import.meta.env.VITE_API_URL || 'https://api.stratumai.app/api/v1';
const getToken = () => sessionStorage.getItem('access_token') || '';

export default function ComplianceDashboard() {
  const [activeTab, setActiveTab] = useState<'audit' | 'rbac' | 'gdpr'>('audit');

  return (
    <div className="min-h-screen bg-[#050B18] text-white p-6">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <ShieldCheckIcon className="w-8 h-8 text-[#00F5FF]" />
            Compliance & Governance
          </h1>
          <p className="text-gray-400 mt-2">Audit logs, role-based access control, and data retention policies</p>
        </header>

        <div className="flex gap-2 mb-6">
          {[
            { id: 'audit' as const, label: 'Audit Log', icon: DocumentTextIcon },
            { id: 'rbac' as const, label: 'RBAC', icon: UserGroupIcon },
            { id: 'gdpr' as const, label: 'GDPR & Retention', icon: ShieldCheckIcon },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all',
                activeTab === tab.id ? 'bg-primary text-white' : 'bg-white/[0.03] text-gray-400 hover:bg-white/[0.06]'
              )}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'audit' && <AuditLogPanel />}
        {activeTab === 'rbac' && <RBACPanel />}
        {activeTab === 'gdpr' && <GDPRPanel />}
      </div>
    </div>
  );
}

// ── Audit Log Panel ─────────────────────────────────────────────────────────

function AuditLogPanel() {
  
  const [filters, setFilters] = useState({
    dateFrom: '',
    dateTo: '',
    actions: '',
    resourceTypes: '',
    severity: '',
    searchTerm: '',
  });
  const [loading, setLoading] = useState(false);
  const [entries, setEntries] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);

  const search = async () => {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    try {
      const body: Record<string, unknown> = {};
      if (filters.dateFrom) body.date_from = filters.dateFrom;
      if (filters.dateTo) body.date_to = filters.dateTo;
      if (filters.actions) body.actions = filters.actions.split(',').map((s) => s.trim());
      if (filters.resourceTypes) body.resource_types = filters.resourceTypes.split(',').map((s) => s.trim());
      if (filters.severity) body.severity = filters.severity.split(',').map((s) => s.trim());
      if (filters.searchTerm) body.search_term = filters.searchTerm;

      const res = await fetch(`${API_URL}/admin/compliance/audit-log/search?page=${page}&page_size=50`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.success) {
        setEntries(data.data.entries || []);
        setTotal(data.data.total || 0);
      }
    } catch (e) { /* ignore */ }
    setLoading(false);
  };

  const severityBadge = (s: string) => {
    if (s === 'critical') return 'bg-red-500/20 text-red-400';
    if (s === 'warning') return 'bg-yellow-500/20 text-yellow-400';
    return 'bg-green-500/20 text-green-400';
  };

  return (
    <div className="space-y-4">
      <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          <div>
            <label className="text-xs text-gray-400">From</label>
            <input type="date" value={filters.dateFrom} onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })} className="w-full bg-white/[0.03] border border-foreground/10 rounded px-2 py-1.5 text-sm text-white" />
          </div>
          <div>
            <label className="text-xs text-gray-400">To</label>
            <input type="date" value={filters.dateTo} onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })} className="w-full bg-white/[0.03] border border-foreground/10 rounded px-2 py-1.5 text-sm text-white" />
          </div>
          <div>
            <label className="text-xs text-gray-400">Severity</label>
            <input value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })} placeholder="info,warning,critical" className="w-full bg-white/[0.03] border border-foreground/10 rounded px-2 py-1.5 text-sm text-white placeholder-gray-600" />
          </div>
          <div>
            <label className="text-xs text-gray-400">Search</label>
            <div className="flex gap-1">
              <input value={filters.searchTerm} onChange={(e) => setFilters({ ...filters, searchTerm: e.target.value })} placeholder="keyword..." className="flex-1 bg-white/[0.03] border border-foreground/10 rounded px-2 py-1.5 text-sm text-white placeholder-gray-600" />
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={search} disabled={loading} className="bg-primary hover:bg-primary/90 disabled:opacity-50 text-white px-4 py-1.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
            {loading ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <MagnifyingGlassIcon className="w-4 h-4" />}
            Search
          </button>
          <button onClick={() => { setFilters({ dateFrom: '', dateTo: '', actions: '', resourceTypes: '', severity: '', searchTerm: '' }); setEntries([]); setTotal(0); }} className="bg-white/[0.03] hover:bg-white/[0.06] text-gray-400 px-4 py-1.5 rounded-lg text-sm transition-colors">
            Reset
          </button>
        </div>
      </div>

      <div className="bg-white/[0.02] border border-foreground/10 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-foreground/10 bg-white/[0.02]">
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Time</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">User</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Action</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Resource</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Severity</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Details</th>
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-500">No entries found. Apply filters and search.</td>
                </tr>
              )}
              {entries.map((entry, i) => (
                <tr key={i} className="border-b border-foreground/5 hover:bg-white/[0.02]">
                  <td className="py-3 px-4 text-gray-400 whitespace-nowrap">{entry.timestamp?.slice(0, 16).replace('T', ' ')}</td>
                  <td className="py-3 px-4 text-gray-300">{entry.user_email || `User #${entry.user_id}`}</td>
                  <td className="py-3 px-4 text-gray-300">{entry.action}</td>
                  <td className="py-3 px-4 text-gray-300">{entry.resource_type}{entry.resource_id ? ` #${entry.resource_id}` : ''}</td>
                  <td className="py-3 px-4">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${severityBadge(entry.severity)}`}>{entry.severity}</span>
                  </td>
                  <td className="py-3 px-4 text-gray-400 text-xs max-w-xs truncate">{JSON.stringify(entry.details)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {total > 50 && (
          <div className="flex items-center justify-between p-4 border-t border-foreground/10">
            <span className="text-sm text-gray-400">{total} total entries</span>
            <div className="flex gap-2">
              <button onClick={() => { setPage(Math.max(1, page - 1)); search(); }} disabled={page === 1} className="px-3 py-1 bg-white/[0.03] rounded text-sm text-gray-400 hover:bg-white/[0.06] disabled:opacity-30">Previous</button>
              <span className="px-3 py-1 text-sm text-gray-400">Page {page}</span>
              <button onClick={() => { setPage(page + 1); search(); }} disabled={entries.length < 50} className="px-3 py-1 bg-white/[0.03] rounded text-sm text-gray-400 hover:bg-white/[0.06] disabled:opacity-30">Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── RBAC Panel ──────────────────────────────────────────────────────────────

function RBACPanel() {
  
  const [roles, setRoles] = useState<any[]>([]);
  const [, setLoading] = useState(false);

  const fetchRoles = async () => {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/admin/compliance/rbac/roles`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      const data = await res.json();
      if (data.success) setRoles(data.data || []);
    } catch (e) { /* ignore */ }
    setLoading(false);
  };

  useState(() => { fetchRoles(); });

  const builtInRoles = [
    {
      id: 'super_admin',
      name: 'Super Admin',
      description: 'Full platform access — all tenants, all features',
      is_custom: false,
      permissions: [{ resource_type: '*', action: '*' }],
    },
    {
      id: 'tenant_admin',
      name: 'Tenant Admin',
      description: 'Manage tenant settings, users, and billing',
      is_custom: false,
      permissions: [
        { resource_type: 'campaign', action: '*' },
        { resource_type: 'user', action: '*' },
        { resource_type: 'setting', action: '*' },
        { resource_type: 'report', action: '*' },
      ],
    },
    {
      id: 'campaign_manager',
      name: 'Campaign Manager',
      description: 'Create and optimize campaigns, view analytics',
      is_custom: false,
      permissions: [
        { resource_type: 'campaign', action: '*' },
        { resource_type: 'report', action: 'read' },
        { resource_type: 'asset', action: 'read' },
      ],
    },
    {
      id: 'viewer',
      name: 'Viewer',
      description: 'Read-only access to campaigns and dashboards',
      is_custom: false,
      permissions: [
        { resource_type: 'campaign', action: 'read' },
        { resource_type: 'report', action: 'read' },
        { resource_type: 'dashboard', action: 'read' },
      ],
    },
    {
      id: 'approver',
      name: 'Approver',
      description: 'Approve campaign changes and autopilot actions',
      is_custom: false,
      permissions: [
        { resource_type: 'campaign', action: 'approve' },
        { resource_type: 'campaign', action: 'read' },
        { resource_type: 'autopilot', action: 'approve' },
      ],
    },
  ];

  const displayRoles = roles.length > 0 ? roles : builtInRoles;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {displayRoles.map((role) => (
          <div key={role.id} className="bg-white/[0.02] border border-foreground/10 rounded-xl p-5">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold">{role.name}</h3>
              {!role.is_custom && <span className="text-xs bg-white/[0.05] text-gray-500 px-2 py-0.5 rounded-full">Built-in</span>}
            </div>
            <p className="text-sm text-gray-400 mb-3">{role.description}</p>
            <div className="space-y-1">
              <span className="text-xs text-gray-500 font-medium">Permissions:</span>
              {role.permissions.map((p: any, i: number) => (
                <div key={i} className="text-xs text-gray-400 flex items-center gap-1">
                  <span className="w-1 h-1 rounded-full bg-[#00F5FF]" />
                  {p.resource_type} → {p.action}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4">Create Custom Role</h3>
        <p className="text-sm text-gray-400">Custom roles can be defined with resource-level conditions. Contact support to enable.</p>
      </div>
    </div>
  );
}

// ── GDPR Panel ─────────────────────────────────────────────────────────────

function GDPRPanel() {
  
  const [policy, setPolicy] = useState({
    profile_retention_days: 365,
    event_retention_days: 180,
    audit_log_retention_days: 2555,
    campaign_metric_retention_days: 730,
    auto_purge_enabled: true,
  });
  const [preview, setPreview] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const savePolicy = async () => {
    const token = getToken();
    if (!token) return;
    try {
      await fetch(`${API_URL}/admin/compliance/gdpr/retention-policy`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify(policy),
      });
    } catch (e) { /* ignore */ }
  };

  const previewPurge = async () => {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/admin/compliance/gdpr/purge-preview`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      const data = await res.json();
      if (data.success) setPreview(data.data);
    } catch (e) { /* ignore */ }
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4">Data Retention Policy</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[
            { key: 'profile_retention_days', label: 'Profile Retention', min: 30, max: 2555 },
            { key: 'event_retention_days', label: 'Event Retention', min: 7, max: 1095 },
            { key: 'audit_log_retention_days', label: 'Audit Log Retention', min: 365, max: 3650 },
            { key: 'campaign_metric_retention_days', label: 'Campaign Metric Retention', min: 90, max: 1825 },
          ].map((field) => (
            <div key={field.key}>
              <label className="block text-sm text-gray-400 mb-1">{field.label} ({field.min}-{field.max} days)</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={field.min}
                  max={field.max}
                  value={policy[field.key as keyof typeof policy] as number}
                  onChange={(e) => setPolicy({ ...policy, [field.key]: parseInt(e.target.value) })}
                  className="flex-1 accent-primary"
                />
                <span className="text-sm font-mono w-16 text-right">{policy[field.key as keyof typeof policy]}d</span>
              </div>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-3 mt-4">
          <input
            type="checkbox"
            checked={policy.auto_purge_enabled}
            onChange={(e) => setPolicy({ ...policy, auto_purge_enabled: e.target.checked })}
            className="w-4 h-4 accent-primary"
          />
          <label className="text-sm text-gray-300">Enable automated purge</label>
        </div>
        <button onClick={savePolicy} className="mt-4 bg-primary hover:bg-primary/90 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors">
          Save Policy
        </button>
      </div>

      <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Purge Preview</h3>
          <button
            onClick={previewPurge}
            disabled={loading}
            className="bg-white/[0.03] hover:bg-white/[0.06] text-gray-300 px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
          >
            {loading ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <TrashIcon className="w-4 h-4" />}
            Preview Purge
          </button>
        </div>
        <p className="text-sm text-gray-400 mb-4">See what data would be deleted under current policy. No data is actually deleted.</p>

        {preview && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Profiles', count: preview.profiles_to_purge, color: 'text-purple-400' },
              { label: 'Events', count: preview.events_to_purge, color: 'text-blue-400' },
              { label: 'Audit Logs', count: preview.audit_logs_to_purge, color: 'text-yellow-400' },
              { label: 'Campaign Metrics', count: preview.campaign_metrics_to_purge, color: 'text-green-400' },
            ].map((item) => (
              <div key={item.label} className="bg-white/[0.03] border border-foreground/5 rounded-lg p-4 text-center">
                <div className={`text-2xl font-bold ${item.color}`}>{item.count.toLocaleString()}</div>
                <div className="text-xs text-gray-500 mt-1">{item.label}</div>
              </div>
            ))}
            <div className="col-span-2 md:col-span-4 bg-white/[0.03] border border-foreground/5 rounded-lg p-4">
              <div className="text-sm text-gray-400">Estimated space to reclaim: <span className="text-white font-medium">{preview.total_estimated_mb} MB</span></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
