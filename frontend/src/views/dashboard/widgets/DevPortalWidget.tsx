/**
 * Stratum AI — Gap #8: Developer Portal Widget
 * Embedded in dashboard: API usage + webhook health + SDK quickstart
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Code2, ArrowRight, Webhook, Key, TrendingUp, CheckCircle2, AlertTriangle, Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

const WEBHOOKS = [
  { id: 'wh_001', name: 'CRM Events', status: 'healthy', deliveries: 1523, failures: 12 },
  { id: 'wh_002', name: 'PagerDuty', status: 'healthy', deliveries: 89, failures: 0 },
  { id: 'wh_003', name: 'Backup', status: 'failing', deliveries: 45, failures: 23 },
];

const SNIPPETS = [
  { lang: 'Python', code: 'requests.get(url, headers={"Authorization": f"Bearer {token}"})' },
  { lang: 'JavaScript', code: 'fetch(url, { headers: { Authorization: `Bearer ${token}` } })' },
];

export function DevPortalWidget() {
  const navigate = useNavigate();
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const copyCode = (code: string, idx: number) => {
    navigator.clipboard.writeText(code);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const totalDeliveries = WEBHOOKS.reduce((a, w) => a + w.deliveries, 0);
  const totalFailures = WEBHOOKS.reduce((a, w) => a + w.failures, 0);
  const errorRate = totalDeliveries > 0 ? ((totalFailures / totalDeliveries) * 100).toFixed(2) : '0.00';

  return (
    <div className="dashboard-card h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center">
            <Code2 className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">Developer</h3>
            <p className="text-xs text-muted-foreground">API · Webhooks · SDKs</p>
          </div>
        </div>
        <button
          onClick={() => navigate('/developer')}
          className="text-xs text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
        >
          Portal <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      {/* API Usage Mini */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="bg-white/[0.02] rounded-lg p-2 text-center">
          <div className="text-sm font-bold text-foreground">3.4k</div>
          <div className="text-[10px] text-muted-foreground">24h calls</div>
        </div>
        <div className="bg-white/[0.02] rounded-lg p-2 text-center">
          <div className="text-sm font-bold text-emerald-400">{errorRate}%</div>
          <div className="text-[10px] text-muted-foreground">Error rate</div>
        </div>
        <div className="bg-white/[0.02] rounded-lg p-2 text-center">
          <div className="text-sm font-bold text-sky-400">500</div>
          <div className="text-[10px] text-muted-foreground">/min limit</div>
        </div>
      </div>

      {/* Webhook Health */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Webhook className="w-3 h-3" /> Webhook Health
          </span>
          <span className="text-[10px] text-muted-foreground">{totalDeliveries.toLocaleString()} deliveries</span>
        </div>
        <div className="space-y-1.5">
          {WEBHOOKS.map((wh) => (
            <div key={wh.id} className="flex items-center gap-2 bg-white/[0.02] rounded-md px-2 py-1.5">
              {wh.status === 'healthy' ? (
                <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
              ) : (
                <AlertTriangle className="w-3 h-3 text-red-400 shrink-0" />
              )}
              <span className="text-xs text-foreground flex-1 truncate">{wh.name}</span>
              <span className={cn(
                'text-[10px] px-1.5 py-0.5 rounded-full',
                wh.status === 'healthy' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
              )}>
                {wh.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* SDK Quick Snippets */}
      <div className="flex-1">
        <div className="text-xs text-muted-foreground mb-1.5 flex items-center gap-1">
          <Key className="w-3 h-3" /> Quick Snippets
        </div>
        <div className="space-y-1.5">
          {SNIPPETS.map((s, i) => (
            <div key={s.lang} className="bg-black/30 rounded-md p-2 relative group">
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-[10px] text-muted-foreground">{s.lang}</span>
                <button
                  onClick={() => copyCode(s.code, i)}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  {copiedIdx === i ? (
                    <Check className="w-3 h-3 text-emerald-400" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </button>
              </div>
              <code className="text-[10px] font-mono text-foreground/80 block truncate">{s.code}</code>
            </div>
          ))}
        </div>
      </div>

      <button
        onClick={() => navigate('/developer')}
        className="mt-3 w-full text-xs text-center py-1.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] text-muted-foreground hover:text-foreground transition-colors flex items-center justify-center gap-1"
      >
        <TrendingUp className="w-3 h-3" /> Full Developer Portal →
      </button>
    </div>
  );
}
