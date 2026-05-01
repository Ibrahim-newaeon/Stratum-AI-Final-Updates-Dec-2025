/**
 * Stratum AI — Gap #5: Enterprise Compliance Widget
 * Embedded in dashboard: Audit log summary + RBAC status + GDPR retention
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, ArrowRight, AlertTriangle, FileText, Users, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const MOCK_AUDIT = [
  { action: 'campaign_update', user: 'admin@...', resource: 'Campaign #452', severity: 'info', time: '2m ago' },
  { action: 'trust_gate_blocked', user: 'system', resource: 'Auto-action', severity: 'warning', time: '15m ago' },
  { action: 'login_failed', user: 'user@...', resource: 'Auth', severity: 'critical', time: '1h ago' },
  { action: 'mfa_verify', user: 'admin@...', resource: 'Security', severity: 'info', time: '2h ago' },
];

const ROLES = [
  { id: 'super_admin', name: 'Super Admin', users: 1, color: 'bg-purple-500/20 text-purple-400' },
  { id: 'tenant_admin', name: 'Tenant Admin', users: 2, color: 'bg-blue-500/20 text-blue-400' },
  { id: 'campaign_mgr', name: 'Campaign Mgr', users: 5, color: 'bg-emerald-500/20 text-emerald-400' },
  { id: 'viewer', name: 'Viewer', users: 8, color: 'bg-gray-500/20 text-gray-400' },
];

export function ComplianceWidget() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'audit' | 'rbac' | 'gdpr'>('audit');

  const severityIcon = (s: string) => {
    if (s === 'critical') return <AlertTriangle className="w-3 h-3 text-red-400" />;
    if (s === 'warning') return <AlertTriangle className="w-3 h-3 text-yellow-400" />;
    return <FileText className="w-3 h-3 text-emerald-400" />;
  };

  return (
    <div className="dashboard-card h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
            <ShieldCheck className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">Compliance</h3>
            <p className="text-xs text-muted-foreground">Audit · Roles · GDPR</p>
          </div>
        </div>
        <button
          onClick={() => navigate('/compliance')}
          className="text-xs text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
        >
          Manage <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-3 bg-white/[0.03] rounded-lg p-0.5">
        {[
          { id: 'audit', label: 'Audit', icon: FileText },
          { id: 'rbac', label: 'Roles', icon: Users },
          { id: 'gdpr', label: 'GDPR', icon: Trash2 },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id as any)}
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-medium rounded-md transition-all',
              activeTab === t.id ? 'bg-white/[0.08] text-foreground' : 'text-muted-foreground hover:text-foreground/70'
            )}
          >
            <t.icon className="w-3.5 h-3.5" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Audit Log */}
      {activeTab === 'audit' && (
        <div className="flex-1 overflow-auto">
          <div className="space-y-1.5">
            {MOCK_AUDIT.map((entry, i) => (
              <div key={i} className="flex items-center gap-2 bg-white/[0.02] rounded-lg px-2.5 py-2">
                {severityIcon(entry.severity)}
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-foreground truncate">{entry.action}</div>
                  <div className="text-[10px] text-muted-foreground truncate">{entry.resource}</div>
                </div>
                <span className="text-[10px] text-muted-foreground shrink-0">{entry.time}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center justify-between mt-3 text-[10px] text-muted-foreground">
            <span>4 of 1,247 events</span>
            <button onClick={() => navigate('/compliance')} className="text-primary hover:underline">View all →</button>
          </div>
        </div>
      )}

      {/* RBAC */}
      {activeTab === 'rbac' && (
        <div className="flex-1 overflow-auto">
          <div className="grid grid-cols-2 gap-2">
            {ROLES.map((role) => (
              <div key={role.id} className="bg-white/[0.02] border border-white/[0.04] rounded-lg p-2.5">
                <div className={cn('text-[10px] px-1.5 py-0.5 rounded-full inline-block mb-1', role.color)}>
                  {role.users} users
                </div>
                <div className="text-xs font-medium text-foreground">{role.name}</div>
              </div>
            ))}
          </div>
          <button
            onClick={() => navigate('/compliance')}
            className="mt-3 w-full text-xs text-center text-primary hover:underline py-1.5 rounded-lg bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
          >
            + Create custom role
          </button>
        </div>
      )}

      {/* GDPR */}
      {activeTab === 'gdpr' && (
        <div className="flex-1 flex flex-col justify-center">
          <div className="space-y-3">
            {[
              { label: 'Profile Data', days: 365, used: '62%' },
              { label: 'Events', days: 180, used: '45%' },
              { label: 'Audit Logs', days: 2555, used: '12%' },
              { label: 'Campaign Metrics', days: 730, used: '38%' },
            ].map((item) => (
              <div key={item.label}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-foreground">{item.label}</span>
                  <span className="text-muted-foreground">{item.days}d retention · {item.used} used</span>
                </div>
                <div className="h-1.5 bg-foreground/10 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full" style={{ width: item.used }} />
                </div>
              </div>
            ))}
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={() => navigate('/compliance')}
              className="flex-1 text-xs text-center py-1.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] text-muted-foreground hover:text-foreground transition-colors"
            >
              Purge Preview
            </button>
            <button
              onClick={() => navigate('/compliance')}
              className="flex-1 text-xs text-center py-1.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] text-muted-foreground hover:text-foreground transition-colors"
            >
              Export Data
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
