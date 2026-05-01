// =============================================================================
// Stratum AI — Developer Portal (Gap #8)
// =============================================================================

import { useState } from 'react';
import { cn } from '@/lib/utils';
import {
  CodeBracketIcon,
  KeyIcon,
  ChartBarIcon,
  GlobeAltIcon,
  DocumentDuplicateIcon,
  TrashIcon,
  PlusIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

const API_URL = import.meta.env.VITE_API_URL || 'https://api.stratumai.app/api/v1';
const getToken = () => sessionStorage.getItem('access_token') || '';

const SDK_EXAMPLES = [
  {
    language: 'Python',
    install: 'pip install requests',
    code: `import requests

API_URL = "https://api.stratumai.app/api/v1"
API_KEY = "your-api-key"

headers = {"Authorization": f"Bearer {API_KEY}"}

# List campaigns
campaigns = requests.get(f"{API_URL}/campaigns", headers=headers).json()
print(campaigns["data"]["items"])

# Get signal health
health = requests.get(f"{API_URL}/analytics/signal-health", headers=headers).json()
print(f"Trust Score: {health['data']['composite_score']}%")
`,
  },
  {
    language: 'JavaScript',
    install: 'npm install # native fetch',
    code: `const API_URL = 'https://api.stratumai.app/api/v1';
const API_KEY = 'your-api-key';

// Fetch campaigns
const campaigns = await fetch(\`\${API_URL}/campaigns\`, {
  headers: { 'Authorization': \`Bearer \${API_KEY}\` }
}).then(r => r.json());

// Real-time WebSocket
const ws = new WebSocket(\`wss://api.stratumai.app/ws?token=\${API_KEY}\`);
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log('Live update:', msg);
};
`,
  },
  {
    language: 'PHP',
    install: 'composer require guzzlehttp/guzzle',
    code: `<?php
$apiKey = 'your-api-key';
$headers = ['Authorization: Bearer ' . $apiKey];

$ch = curl_init('https://api.stratumai.app/api/v1/campaigns');
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$response = json_decode(curl_exec($ch), true);
print_r($response['data']['items']);
?>
`,
  },
  {
    language: 'Go',
    install: 'go get net/http',
    code: `package main

import (
    "bytes"
    "encoding/json"
    "net/http"
)

func main() {
    apiKey := "your-api-key"
    payload := map[string]interface{}{
        "events": []map[string]interface{}{
            {"event": "purchase", "user_id": "123"},
        },
    }
    body, _ := json.Marshal(payload)
    req, _ := http.NewRequest("POST", "https://api.stratumai.app/api/v1/cdp/events", bytes.NewBuffer(body))
    req.Header.Set("Authorization", "Bearer "+apiKey)
    client := &http.Client{}
    resp, _ := client.Do(req)
    defer resp.Body.Close()
}
`,
  },
];

export default function DeveloperPortal() {
  const [activeTab, setActiveTab] = useState<'keys' | 'usage' | 'webhooks' | 'sdk'>('keys');

  return (
    <div className="min-h-screen bg-[#050B18] text-white p-6">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <CodeBracketIcon className="w-8 h-8 text-[#00F5FF]" />
            Developer Portal
          </h1>
          <p className="text-gray-400 mt-2">API keys, usage analytics, webhook management, and SDK quickstart</p>
        </header>

        <div className="flex gap-2 mb-6">
          {[
            { id: 'keys' as const, label: 'API Keys', icon: KeyIcon },
            { id: 'usage' as const, label: 'Usage', icon: ChartBarIcon },
            { id: 'webhooks' as const, label: 'Webhooks', icon: GlobeAltIcon },
            { id: 'sdk' as const, label: 'SDK Quickstart', icon: CodeBracketIcon },
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

        {activeTab === 'keys' && <KeysPanel />}
        {activeTab === 'usage' && <UsagePanel />}
        {activeTab === 'webhooks' && <WebhooksPanel />}
        {activeTab === 'sdk' && <SDKPanel />}
      </div>
    </div>
  );
}

// ── API Keys Panel ──────────────────────────────────────────────────────────

function KeysPanel() {
  const [keys] = useState([
    { id: 'key_001', name: 'Production', prefix: 'sk_live_abc123...', created_at: '2026-04-01', last_used: '2026-04-27' },
    { id: 'key_002', name: 'Staging', prefix: 'sk_test_def456...', created_at: '2026-04-15', last_used: '2026-04-26' },
  ]);

  return (
    <div className="space-y-4">
      <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">API Keys</h3>
          <button className="bg-primary hover:bg-primary/90 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
            <PlusIcon className="w-4 h-4" /> Create Key
          </button>
        </div>
        <div className="space-y-3">
          {keys.map((k) => (
            <div key={k.id} className="flex items-center justify-between bg-white/[0.03] border border-foreground/5 rounded-lg p-4">
              <div>
                <div className="font-medium">{k.name}</div>
                <div className="text-xs text-gray-500">{k.prefix}</div>
                <div className="text-xs text-gray-600 mt-1">Created {k.created_at} · Last used {k.last_used}</div>
              </div>
              <button className="text-red-400 hover:text-red-300 p-2">
                <TrashIcon className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Usage Panel ─────────────────────────────────────────────────────────────

function UsagePanel() {
  const [usage] = useState({
    total_requests_24h: 3421,
    total_requests_30d: 89345,
    rate_limit_per_minute: 500,
    endpoint_breakdown: [
      { endpoint: 'GET /campaigns', requests: 12400, avg_latency_ms: 45 },
      { endpoint: 'GET /analytics/signal-health', requests: 8200, avg_latency_ms: 23 },
      { endpoint: 'POST /cdp/events', requests: 5600, avg_latency_ms: 67 },
      { endpoint: 'GET /dashboard', requests: 4300, avg_latency_ms: 34 },
      { endpoint: 'POST /autopilot/actions', requests: 2100, avg_latency_ms: 89 },
    ],
    daily_trend: [
      { date: '2026-04-20', requests: 2800, errors: 12 },
      { date: '2026-04-21', requests: 3100, errors: 8 },
      { date: '2026-04-22', requests: 2950, errors: 15 },
      { date: '2026-04-23', requests: 3400, errors: 5 },
      { date: '2026-04-24', requests: 3600, errors: 9 },
      { date: '2026-04-25', requests: 3300, errors: 7 },
      { date: '2026-04-26', requests: 3100, errors: 6 },
    ],
  });

  const maxReq = Math.max(...usage.daily_trend.map((d) => d.requests));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: '24h Requests', value: usage.total_requests_24h.toLocaleString(), color: 'text-white' },
          { label: '30d Requests', value: usage.total_requests_30d.toLocaleString(), color: 'text-[#00F5FF]' },
          { label: 'Rate Limit', value: `${usage.rate_limit_per_minute}/min`, color: 'text-green-400' },
          { label: 'Error Rate', value: `${(usage.daily_trend.reduce((a, d) => a + d.errors, 0) / usage.daily_trend.reduce((a, d) => a + d.requests, 0) * 100).toFixed(2)}%`, color: 'text-yellow-400' },
        ].map((m) => (
          <div key={m.label} className="bg-white/[0.02] border border-foreground/10 rounded-xl p-4 text-center">
            <div className={`text-2xl font-bold ${m.color}`}>{m.value}</div>
            <div className="text-xs text-gray-500 mt-1">{m.label}</div>
          </div>
        ))}
      </div>

      <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4">Daily Requests</h3>
        <div className="flex items-end gap-2 h-40">
          {usage.daily_trend.map((d, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-1">
              <div className="w-full bg-foreground/10 rounded-t relative" style={{ height: `${(d.requests / maxReq) * 100}%` }}>
                <div className="absolute bottom-0 left-0 right-0 bg-primary/40 rounded-t" style={{ height: '100%' }} />
                {d.errors > 0 && (
                  <div className="absolute bottom-0 left-0 right-0 bg-red-500/60 rounded-t" style={{ height: `${(d.errors / d.requests) * 100}%` }} />
                )}
              </div>
              <span className="text-xs text-gray-500">{d.date.slice(5)}</span>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
          <div className="flex items-center gap-1"><span className="w-3 h-3 bg-primary/40 rounded" /> Requests</div>
          <div className="flex items-center gap-1"><span className="w-3 h-3 bg-red-500/60 rounded" /> Errors</div>
        </div>
      </div>

      <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4">Endpoint Breakdown</h3>
        <div className="space-y-3">
          {usage.endpoint_breakdown.map((ep, i) => (
            <div key={i} className="flex items-center gap-4">
              <div className="w-48 text-sm text-gray-300 truncate">{ep.endpoint}</div>
              <div className="flex-1 bg-foreground/10 rounded-full h-2 overflow-hidden">
                <div className="h-full bg-[#00F5FF]/50 rounded-full" style={{ width: `${(ep.requests / usage.endpoint_breakdown[0].requests) * 100}%` }} />
              </div>
              <div className="w-20 text-right text-sm text-gray-400">{ep.requests.toLocaleString()}</div>
              <div className="w-20 text-right text-xs text-gray-500">{ep.avg_latency_ms}ms</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Webhooks Panel ──────────────────────────────────────────────────────────

function WebhooksPanel() {
  
  const [webhooks, setWebhooks] = useState([
    { id: 'wh_001', name: 'Campaign Events → Internal CRM', url: 'https://api.company.com/stratum/webhook', events: ['campaign.created', 'campaign.updated'], secret: 'whsec_...', is_active: true, health_status: 'healthy', delivery_count: 1523, failure_count: 12 },
    { id: 'wh_002', name: 'Trust Gate → PagerDuty', url: 'https://events.pagerduty.com/...', events: ['trust_gate.blocked'], secret: 'whsec_...', is_active: true, health_status: 'healthy', delivery_count: 89, failure_count: 0 },
  ]);
  const [newWebhook, setNewWebhook] = useState({ name: '', url: '', events: [] as string[] });

  const healthColor = (h: string) => {
    if (h === 'healthy') return 'text-green-400';
    if (h === 'degraded') return 'text-yellow-400';
    return 'text-red-400';
  };

  const testWebhook = async (id: string) => {
    const token = getToken();
    if (!token) return;
    try {
      await fetch(`${API_URL}/developer/webhooks/${id}/test`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      alert('Test event sent! Check webhook logs.');
    } catch (e) { /* ignore */ }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4">Create Webhook</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <input value={newWebhook.name} onChange={(e) => setNewWebhook({ ...newWebhook, name: e.target.value })} placeholder="Webhook name" className="bg-white/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-white text-sm" />
          <input value={newWebhook.url} onChange={(e) => setNewWebhook({ ...newWebhook, url: e.target.value })} placeholder="https://..." className="bg-white/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-white text-sm" />
        </div>
        <div className="flex gap-2 mb-4">
          {['campaign.created', 'campaign.updated', 'trust_gate.blocked', 'anomaly.critical', 'daily.digest'].map((e) => (
            <button
              key={e}
              onClick={() => {
                const set = new Set(newWebhook.events);
                if (set.has(e)) set.delete(e); else set.add(e);
                setNewWebhook({ ...newWebhook, events: Array.from(set) });
              }}
              className={cn(
                'text-xs px-3 py-1.5 rounded-full border transition-colors',
                newWebhook.events.includes(e) ? 'bg-primary/20 border-primary text-primary' : 'bg-white/[0.03] border-foreground/10 text-gray-400'
              )}
            >
              {e}
            </button>
          ))}
        </div>
        <button
          onClick={() => {
            if (newWebhook.name && newWebhook.url) {
              setWebhooks([...webhooks, { ...newWebhook, id: `wh_${Date.now()}`, secret: `whsec_${Math.random().toString(36).slice(2)}`, is_active: true, health_status: 'healthy', delivery_count: 0, failure_count: 0 }]);
              setNewWebhook({ name: '', url: '', events: [] });
            }
          }}
          className="bg-primary hover:bg-primary/90 text-white px-5 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
        >
          <PlusIcon className="w-4 h-4" /> Register Webhook
        </button>
      </div>

      {webhooks.map((wh) => (
        <div key={wh.id} className="bg-white/[0.02] border border-foreground/10 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h4 className="font-medium">{wh.name}</h4>
              <p className="text-xs text-gray-500">{wh.url}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={cn('text-xs px-2 py-0.5 rounded-full', wh.is_active ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400')}>{wh.is_active ? 'Active' : 'Inactive'}</span>
              <span className={cn('text-xs px-2 py-0.5 rounded-full', healthColor(wh.health_status))}>{wh.health_status}</span>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4 mb-3">
            <div className="bg-white/[0.03] rounded-lg p-3 text-center">
              <div className="text-lg font-bold">{wh.delivery_count.toLocaleString()}</div>
              <div className="text-xs text-gray-500">Deliveries</div>
            </div>
            <div className="bg-white/[0.03] rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-red-400">{wh.failure_count}</div>
              <div className="text-xs text-gray-500">Failures</div>
            </div>
            <div className="bg-white/[0.03] rounded-lg p-3 text-center">
              <div className="text-lg font-bold">{wh.failure_count > 0 ? ((wh.failure_count / wh.delivery_count) * 100).toFixed(2) : '0.00'}%</div>
              <div className="text-xs text-gray-500">Error Rate</div>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => testWebhook(wh.id)} className="text-xs bg-white/[0.03] hover:bg-white/[0.06] text-[#00F5FF] px-3 py-1.5 rounded-lg transition-colors">Test</button>
            <button onClick={() => setWebhooks(webhooks.filter((w) => w.id !== wh.id))} className="text-xs bg-white/[0.03] hover:bg-white/[0.06] text-red-400 px-3 py-1.5 rounded-lg transition-colors">Delete</button>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── SDK Quickstart Panel ────────────────────────────────────────────────────

function SDKPanel() {
  const [activeLang, setActiveLang] = useState(0);
  const [copied, setCopied] = useState(false);

  const copy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const example = SDK_EXAMPLES[activeLang];

  return (
    <div className="space-y-6">
      <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
        <div className="flex gap-2 mb-4">
          {SDK_EXAMPLES.map((ex, i) => (
            <button
              key={ex.language}
              onClick={() => setActiveLang(i)}
              className={cn(
                'px-4 py-2 rounded-lg text-sm font-medium transition-all',
                activeLang === i ? 'bg-primary text-white' : 'bg-white/[0.03] text-gray-400 hover:bg-white/[0.06]'
              )}
            >
              {ex.language}
            </button>
          ))}
        </div>

        <div className="bg-black/40 border border-foreground/10 rounded-lg p-4 relative">
          <button
            onClick={() => copy(example.code)}
            className="absolute top-3 right-3 text-xs bg-white/[0.05] hover:bg-white/[0.1] text-gray-400 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1"
          >
            {copied ? <CheckCircleIcon className="w-3 h-3 text-green-400" /> : <DocumentDuplicateIcon className="w-3 h-3" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
          <div className="text-xs text-gray-500 mb-2">{example.install}</div>
          <pre className="text-sm font-mono text-gray-300 overflow-x-auto">{example.code}</pre>
        </div>
      </div>

      <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4">API Reference</h3>
        <p className="text-sm text-gray-400 mb-4">Interactive documentation is available at:</p>
        <a href="https://api.stratumai.app/docs" target="_blank" rel="noopener noreferrer" className="text-[#00F5FF] hover:underline text-sm">
          https://api.stratumai.app/docs
        </a>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          {['Campaigns', 'Analytics', 'CDP', 'Autopilot', 'Trust Engine', 'Reporting', 'Integrations', 'Compliance'].map((ep) => (
            <div key={ep} className="bg-white/[0.03] border border-foreground/5 rounded-lg p-3 text-center text-sm text-gray-300">{ep}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
