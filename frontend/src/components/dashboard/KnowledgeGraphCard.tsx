/**
 * Feature #18 — Knowledge Graph Auto-Insights Card
 *
 * Shows cross-metric relationships, patterns, and performance clusters.
 */

import { useState } from 'react';
import {
  Brain,
  GitBranch,
  Lightbulb,
  Layers,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Zap,
  BarChart3,
} from 'lucide-react';
import {
  useKnowledgeGraph,
  type KnowledgeEdge,
  type KnowledgePattern,
  type KnowledgeCluster,
} from '@/api/dashboard';

const severityConfig: Record<string, { color: string; bg: string; icon: typeof CheckCircle2 }> = {
  positive: { color: 'text-emerald-600', bg: 'bg-emerald-50', icon: CheckCircle2 },
  info: { color: 'text-blue-600', bg: 'bg-blue-50', icon: Lightbulb },
  warning: { color: 'text-amber-600', bg: 'bg-amber-50', icon: AlertTriangle },
  critical: { color: 'text-red-600', bg: 'bg-red-50', icon: AlertTriangle },
};

const relConfig: Record<string, { color: string; label: string }> = {
  drives: { color: 'text-emerald-600', label: 'Drives' },
  correlates_with: { color: 'text-blue-600', label: 'Correlates' },
  inhibits: { color: 'text-red-600', label: 'Inhibits' },
  depends_on: { color: 'text-amber-600', label: 'Depends' },
};

const perfConfig: Record<string, { color: string; bg: string }> = {
  top: { color: 'text-emerald-600', bg: 'bg-emerald-50' },
  above_average: { color: 'text-blue-600', bg: 'bg-blue-50' },
  average: { color: 'text-muted-foreground', bg: 'bg-muted/30' },
  below_average: { color: 'text-amber-600', bg: 'bg-amber-50' },
  poor: { color: 'text-red-600', bg: 'bg-red-50' },
};

function RelationshipRow({ edge }: { edge: KnowledgeEdge }) {
  const rcfg = relConfig[edge.relationship] || relConfig.correlates_with;
  return (
    <div className="flex items-center gap-2 p-3 rounded-xl border hover:bg-muted/30 transition-colors">
      <div className="flex items-center gap-1.5 flex-1 min-w-0">
        <span className="text-xs font-semibold text-foreground truncate">{edge.source.replace('n_', '').replace('_', ' ').toUpperCase()}</span>
        <ArrowRight className={`w-3.5 h-3.5 shrink-0 ${rcfg.color}`} />
        <span className="text-xs font-semibold text-foreground truncate">{edge.target.replace('n_', '').replace('_', ' ').toUpperCase()}</span>
      </div>
      <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${rcfg.color}`}>
        {rcfg.label}
      </span>
      <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden shrink-0">
        <div className="h-full rounded-full bg-blue-500 transition-all" style={{ width: `${Math.min(edge.strength, 100)}%` }} />
      </div>
      <span className="text-[10px] font-bold text-muted-foreground shrink-0">{edge.strength.toFixed(0)}%</span>
    </div>
  );
}

function PatternRow({ pattern }: { pattern: KnowledgePattern }) {
  const cfg = severityConfig[pattern.severity] || severityConfig.info;
  const Icon = cfg.icon;
  return (
    <div className="flex items-start gap-3 p-3 rounded-xl border">
      <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${cfg.bg}`}>
        <Icon className={`w-4 h-4 ${cfg.color}`} />
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground">{pattern.title}</span>
          <span className="text-[10px] font-bold text-muted-foreground/50">{pattern.confidence.toFixed(0)}% conf</span>
        </div>
        <div className="text-xs text-muted-foreground mt-0.5">{pattern.description}</div>
        <div className="text-xs text-blue-600 font-semibold mt-1">{pattern.recommendation}</div>
      </div>
    </div>
  );
}

function ClusterRow({ cluster }: { cluster: KnowledgeCluster }) {
  const pcfg = perfConfig[cluster.performance_level] || perfConfig.average;
  return (
    <div className="flex items-center gap-3 p-3 rounded-xl border">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${pcfg.bg}`}>
        <Layers className={`w-4 h-4 ${pcfg.color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm text-foreground">{cluster.label}</span>
          <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${pcfg.bg} ${pcfg.color}`}>
            {cluster.performance_level.replace('_', ' ')}
          </span>
        </div>
        <div className="flex gap-3 text-xs text-muted-foreground mt-0.5">
          <span>{cluster.campaign_count} campaigns</span>
          <span>{cluster.avg_roas.toFixed(1)}x ROAS</span>
          <span>${cluster.avg_cpa.toFixed(0)} CPA</span>
        </div>
      </div>
      <div className="flex gap-1 shrink-0">
        {cluster.platforms.slice(0, 3).map((p, i) => (
          <span key={i} className="text-[10px] font-bold px-1.5 py-0.5 bg-muted/30 text-muted-foreground rounded">
            {p.slice(0, 3).toUpperCase()}
          </span>
        ))}
      </div>
    </div>
  );
}

type TabKey = 'patterns' | 'relationships' | 'clusters';

export function KnowledgeGraphCard() {
  const { data, isLoading, error } = useKnowledgeGraph();
  const [tab, setTab] = useState<TabKey>('patterns');

  if (isLoading) {
    return (
      <div className="rounded-xl border bg-card p-6 animate-pulse">
        <div className="h-6 bg-muted rounded w-48 mb-4" />
        <div className="h-20 bg-muted/30 rounded-xl" />
      </div>
    );
  }

  if (error || !data) return null;

  const tabs: { key: TabKey; label: string; count?: number }[] = [
    { key: 'patterns', label: 'Patterns', count: data.patterns_discovered },
    { key: 'relationships', label: 'Relationships', count: data.total_relationships },
    { key: 'clusters', label: 'Clusters', count: data.clusters.length },
  ];

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4 border-b border">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-violet-50 flex items-center justify-center">
              <Brain className="w-5 h-5 text-violet-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-foreground">Knowledge Graph</h3>
                {data.key_insight && (
                  <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-violet-50 text-violet-600">
                    Auto-Insights
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">{data.summary}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 mt-4">
          <div className="bg-muted/30 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Entities</div>
            <div className="text-lg font-bold text-foreground">{data.nodes.length}</div>
          </div>
          <div className="bg-muted/30 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Relationships</div>
            <div className="text-lg font-bold text-foreground">{data.total_relationships}</div>
          </div>
          <div className="bg-muted/30 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Patterns</div>
            <div className="text-lg font-bold text-violet-600">{data.patterns_discovered}</div>
          </div>
        </div>
      </div>

      <div className="flex border-b border px-6">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
              tab === t.key ? 'border-violet-600 text-violet-600' : 'border-transparent text-muted-foreground/50 hover:text-muted-foreground'
            }`}
          >
            {t.label}
            {t.count !== undefined && <span className="ml-1 text-[10px] text-muted-foreground/50">({t.count})</span>}
          </button>
        ))}
      </div>

      <div className="p-4 space-y-2 max-h-[480px] overflow-y-auto">
        {tab === 'patterns' && data.patterns.map((p, i) => <PatternRow key={i} pattern={p} />)}
        {tab === 'relationships' && data.edges.map((e, i) => <RelationshipRow key={i} edge={e} />)}
        {tab === 'clusters' && data.clusters.map((c, i) => <ClusterRow key={i} cluster={c} />)}
      </div>
    </div>
  );
}
