// =============================================================================
// Stratum AI — Integration Hub (Gap #6)
// =============================================================================

import { useState } from 'react';
import { cn } from '@/lib/utils';
import {
  BoltIcon,
  CloudArrowUpIcon,
  ChatBubbleLeftRightIcon,
  PlusIcon,
  TrashIcon,
  ArrowPathIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

const API_URL = import.meta.env.VITE_API_URL || 'https://api.stratumai.app/api/v1';
const getToken = () => sessionStorage.getItem('access_token') || '';

export default function IntegrationHub() {
  const [activeTab, setActiveTab] = useState<'zapier' | 'warehouse' | 'teams'>('zapier');

  return (
    <div className="min-h-screen bg-[#050B18] text-white p-6">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <BoltIcon className="w-8 h-8 text-[#00F5FF]" />
            Integration Hub
          </h1>
          <p className="text-gray-400 mt-2">Connect Stratum AI to your external tools and data warehouses</p>
        </header>

        <div className="flex gap-2 mb-6">
          {[
            { id: 'zapier' as const, label: 'Zapier / Make', icon: BoltIcon },
            { id: 'warehouse' as const, label: 'Data Warehouse', icon: CloudArrowUpIcon },
            { id: 'teams' as const, label: 'Microsoft Teams', icon: ChatBubbleLeftRightIcon },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all',
                activeTab === tab.id ? 'bg-[#FF1F6D] text-white' : 'bg-white/[0.03] text-gray-400 hover:bg-white/[0.06]'
              )}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'zapier' && <ZapierPanel />}
        {activeTab === 'warehouse' && <WarehousePanel />}
        {activeTab === 'teams' && <TeamsPanel />}
      </div>
    </div>
  );
}

// ── Zapier Panel ────────────────────────────────────────────────────────────

function ZapierPanel() {
  
  const [webhooks, setWebhooks] = useState<any[]>([
    { id: 'zap_001', name: 'Campaign Alert → CRM', webhook_url: 'https://hooks.zapier.com/hooks/catch/123/abc', event_types: ['campaign_created', 'roas_alert'], is_active: true },
  ]);
  const [newWebhook, setNewWebhook] = useState({ name: '', webhook_url: '', event_types: [] as string[] });
  const [testResult, setTestResult] = useState<any>(null);

  const eventOptions = ['campaign_created', 'campaign_updated', 'campaign_deleted', 'roas_alert', 'trust_gate_blocked', 'daily_summary', 'anomaly_detected'];

  const addWebhook = async () => {
    const token = getToken();
    if (!token || !newWebhook.name || !newWebhook.webhook_url) return;
    try {
      const res = await fetch(`${API_URL}/integrations/outbound/zapier`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify(newWebhook),
      });
      const data = await res.json();
      if (data.success) {
        setWebhooks([...webhooks, data.data]);
        setNewWebhook({ name: '', webhook_url: '', event_types: [] });
      }
    } catch (e) { /* ignore */ }
  };

  const testWebhook = async (id: string) => {
    const token = getToken();
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/integrations/outbound/zapier/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ webhook_id: id, event_type: 'campaign_created', payload: { test: true } }),
      });
      const data = await res.json();
      setTestResult(data.data);
    } catch (e) { /* ignore */ }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white/[0.02] border border-white/10 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4">Zapier / Make.com Webhooks</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-xs text-gray-400">Name</label>
            <input value={newWebhook.name} onChange={(e) => setNewWebhook({ ...newWebhook, name: e.target.value })} className="w-full bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-white text-sm" placeholder="My Zapier Hook" />
          </div>
          <div>
            <label className="text-xs text-gray-400">Webhook URL (https://)</label>
            <input value={newWebhook.webhook_url} onChange={(e) => setNewWebhook({ ...newWebhook, webhook_url: e.target.value })} className="w-full bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-white text-sm" placeholder="https://hooks.zapier.com/..." />
          </div>
        </div>
        <div className="mb-4">
          <label className="text-xs text-gray-400 block mb-2">Event Types</label>
          <div className="flex flex-wrap gap-2">
            {eventOptions.map((e) => (
              <button
                key={e}
                onClick={() => {
                  const set = new Set(newWebhook.event_types);
                  if (set.has(e)) set.delete(e); else set.add(e);
                  setNewWebhook({ ...newWebhook, event_types: Array.from(set) });
                }}
                className={cn(
                  'text-xs px-3 py-1.5 rounded-full border transition-colors',
                  newWebhook.event_types.includes(e)
                    ? 'bg-[#FF1F6D]/20 border-[#FF1F6D] text-[#FF1F6D]'
                    : 'bg-white/[0.03] border-white/10 text-gray-400 hover:bg-white/[0.06]'
                )}
              >
                {e}
              </button>
            ))}
          </div>
        </div>
        <button onClick={addWebhook} className="bg-[#FF1F6D] hover:bg-[#ff4d85] text-white px-5 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
          <PlusIcon className="w-4 h-4" /> Add Webhook
        </button>
      </div>

      {webhooks.map((wh) => (
        <div key={wh.id} className="bg-white/[0.02] border border-white/10 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h4 className="font-medium">{wh.name}</h4>
              <p className="text-xs text-gray-500">{wh.webhook_url}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={cn('text-xs px-2 py-0.5 rounded-full', wh.is_active ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400')}>
                {wh.is_active ? 'Active' : 'Inactive'}
              </span>
              <button onClick={() => testWebhook(wh.id)} className="text-xs bg-white/[0.03] hover:bg-white/[0.06] text-[#00F5FF] px-3 py-1.5 rounded-lg transition-colors">
                Test
              </button>
              <button onClick={() => setWebhooks(webhooks.filter((w) => w.id !== wh.id))} className="text-red-400 hover:text-red-300 p-1">
                <TrashIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div className="flex flex-wrap gap-1">
            {wh.event_types.map((e: string) => (
              <span key={e} className="text-xs bg-white/[0.03] text-gray-400 px-2 py-0.5 rounded-full">{e}</span>
            ))}
          </div>
        </div>
      ))}

      {testResult && (
        <div className="bg-white/[0.02] border border-white/10 rounded-xl p-4">
          <h4 className="text-sm font-medium mb-2">Test Result</h4>
          <div className="text-xs text-gray-400 space-y-1">
            <div>Status: <span className={testResult.status === 'success' ? 'text-green-400' : 'text-red-400'}>{testResult.status}</span></div>
            <div>HTTP: {testResult.response_status || 'N/A'}</div>
            <div>Latency: {testResult.latency_ms}ms</div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Warehouse Panel ─────────────────────────────────────────────────────────

function WarehousePanel() {
  
  const [exports] = useState<any[]>([
    { id: 'wh_001', name: 'BigQuery Production', provider: 'bigquery', dataset: 'stratum_analytics', tables: ['campaigns', 'campaign_metrics'], sync_frequency: 'hourly', is_active: true },
  ]);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<any>(null);

  const syncNow = async (id: string) => {
    const token = getToken();
    if (!token) return;
    setSyncing(true);
    try {
      const res = await fetch(`${API_URL}/integrations/outbound/warehouse/sync?export_id=${id}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      const data = await res.json();
      if (data.success) setSyncResult(data.data);
    } catch (e) { /* ignore */ }
    setSyncing(false);
  };

  const providers = [
    { id: 'bigquery', name: 'Google BigQuery', color: 'text-blue-400' },
    { id: 'snowflake', name: 'Snowflake', color: 'text-cyan-400' },
    { id: 'databricks', name: 'Databricks', color: 'text-red-400' },
    { id: 'redshift', name: 'Amazon Redshift', color: 'text-orange-400' },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {providers.map((p) => (
          <div key={p.id} className="bg-white/[0.02] border border-white/10 rounded-xl p-4 text-center">
            <div className={`text-lg font-bold ${p.color}`}>{p.name}</div>
            <div className="text-xs text-gray-500 mt-1">Available</div>
          </div>
        ))}
      </div>

      {exports.map((ex) => (
        <div key={ex.id} className="bg-white/[0.02] border border-white/10 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h4 className="font-medium">{ex.name}</h4>
              <p className="text-xs text-gray-500">{ex.provider} · {ex.dataset}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={cn('text-xs px-2 py-0.5 rounded-full', ex.is_active ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400')}>
                {ex.is_active ? 'Active' : 'Inactive'}
              </span>
              <button onClick={() => syncNow(ex.id)} disabled={syncing} className="text-xs bg-[#FF1F6D] hover:bg-[#ff4d85] text-white px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50">
                {syncing ? <ArrowPathIcon className="w-3 h-3 animate-spin" /> : 'Sync Now'}
              </button>
            </div>
          </div>
          <div className="text-xs text-gray-400">Tables: {ex.tables.join(', ')} · Frequency: {ex.sync_frequency}</div>
        </div>
      ))}

      {syncResult && (
        <div className="bg-green-500/5 border border-green-500/20 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircleIcon className="w-5 h-5 text-green-400" />
            <span className="text-sm font-medium text-green-400">Sync Complete</span>
          </div>
          <div className="text-xs text-gray-400 space-y-1">
            <div>Rows exported: {syncResult.rows_exported.toLocaleString()}</div>
            <div>Duration: {syncResult.duration_seconds}s</div>
            <div>Status: {syncResult.status}</div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Teams Panel ─────────────────────────────────────────────────────────────

function TeamsPanel() {
  
  const [webhooks, setWebhooks] = useState<any[]>([
    { id: 'teams_001', name: 'Marketing Alerts', webhook_url: 'https://company.webhook.office.com/...', channel_name: 'Marketing Ops', alert_types: ['roas_drop', 'trust_gate_blocked'], is_active: true },
  ]);
  const [testMessage, setTestMessage] = useState<any>(null);

  const sendTest = async (id: string) => {
    const token = getToken();
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/integrations/outbound/teams/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({
          webhook_id: id,
          title: 'Test Alert from Stratum AI',
          text: 'This is a test message to verify your Microsoft Teams integration is working.',
          theme_color: 'FF1F6D',
          facts: [{ name: 'Campaign', value: 'Test Campaign' }, { name: 'ROAS', value: '2.4x' }],
          actions: [{ name: 'Open Dashboard', url: 'https://stratumai.app/dashboard' }],
        }),
      });
      const data = await res.json();
      setTestMessage(data);
    } catch (e) { /* ignore */ }
  };

  return (
    <div className="space-y-6">
      {webhooks.map((wh) => (
        <div key={wh.id} className="bg-white/[0.02] border border-white/10 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h4 className="font-medium">{wh.name}</h4>
              <p className="text-xs text-gray-500">Channel: {wh.channel_name}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={cn('text-xs px-2 py-0.5 rounded-full', wh.is_active ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400')}>
                {wh.is_active ? 'Active' : 'Inactive'}
              </span>
              <button onClick={() => sendTest(wh.id)} className="text-xs bg-white/[0.03] hover:bg-white/[0.06] text-[#00F5FF] px-3 py-1.5 rounded-lg transition-colors">
                Send Test
              </button>
              <button onClick={() => setWebhooks(webhooks.filter((w) => w.id !== wh.id))} className="text-red-400 hover:text-red-300 p-1">
                <TrashIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div className="flex flex-wrap gap-1">
            {wh.alert_types.map((e: string) => (
              <span key={e} className="text-xs bg-white/[0.03] text-gray-400 px-2 py-0.5 rounded-full">{e}</span>
            ))}
          </div>
        </div>
      ))}

      {testMessage && (
        <div className={cn('rounded-xl p-4 border', testMessage.success ? 'bg-green-500/5 border-green-500/20' : 'bg-red-500/5 border-red-500/20')}>
          <div className="text-sm font-medium mb-1">{testMessage.success ? 'Message Sent' : 'Failed'}</div>
          <div className="text-xs text-gray-400">{JSON.stringify(testMessage.data)}</div>
        </div>
      )}
    </div>
  );
}
