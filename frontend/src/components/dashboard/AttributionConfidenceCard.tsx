/**
 * Feature #12 — Attribution Confidence Dashboard Card
 *
 * Displays attribution confidence across channels, model comparisons,
 * data quality metrics, and recommendations.
 */

import { useState } from 'react';
import {
  Shield,
  BarChart3,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Layers,
  Target,
  Zap,
  Info,
} from 'lucide-react';
import {
  useAttributionConfidence,
  type ChannelAttribution,
  type ModelComparison,
  type DataQualityMetric,
  type AttributionRecommendation,
} from '@/api/dashboard';

// ── Config ──────────────────────────────────────────────────────────────────

const confidenceConfig = {
  high: { color: 'text-emerald-600', bg: 'bg-emerald-50', bar: 'bg-emerald-500', border: 'border-emerald-200', label: 'High' },
  medium: { color: 'text-amber-600', bg: 'bg-amber-50', bar: 'bg-amber-500', border: 'border-amber-200', label: 'Medium' },
  low: { color: 'text-orange-600', bg: 'bg-orange-50', bar: 'bg-orange-500', border: 'border-orange-200', label: 'Low' },
  insufficient: { color: 'text-red-600', bg: 'bg-red-50', bar: 'bg-red-500', border: 'border-red-200', label: 'Insufficient' },
};

const qualityStatusConfig = {
  good: { color: 'text-emerald-600', bg: 'bg-emerald-50', icon: CheckCircle2 },
  warning: { color: 'text-amber-600', bg: 'bg-amber-50', icon: AlertTriangle },
  poor: { color: 'text-red-600', bg: 'bg-red-50', icon: AlertTriangle },
};

const priorityConfig = {
  high: { color: 'text-red-600', bg: 'bg-red-50' },
  medium: { color: 'text-amber-600', bg: 'bg-amber-50' },
  low: { color: 'text-blue-600', bg: 'bg-blue-50' },
};

// ── Sub-components ──────────────────────────────────────────────────────────

function ConfidenceRing({ score, size = 64 }: { score: number; size?: number }) {
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - score / 100);
  const cfg = confidenceConfig[score >= 75 ? 'high' : score >= 50 ? 'medium' : score >= 25 ? 'low' : 'insufficient'];

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="w-full h-full -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="transparent" stroke="currentColor" strokeWidth="4" className="text-muted" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="transparent" stroke="currentColor" strokeWidth="6" strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round" className={cfg.color} style={{ transition: 'stroke-dashoffset 1s ease' }} />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className={`text-sm font-bold ${cfg.color}`}>{score.toFixed(0)}%</span>
      </div>
    </div>
  );
}

function ChannelRow({ channel }: { channel: ChannelAttribution }) {
  const [open, setOpen] = useState(false);
  const cfg = confidenceConfig[channel.confidence_label] || confidenceConfig.insufficient;

  return (
    <div className={`border rounded-xl transition-all ${open ? cfg.border : 'border'}`}>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-3 p-3 text-left hover:bg-muted/30 rounded-xl transition-colors">
        <ConfidenceRing score={channel.confidence_score} size={44} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-foreground truncate">{channel.channel}</span>
            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${cfg.bg} ${cfg.color}`}>{cfg.label}</span>
          </div>
          <div className="flex gap-3 mt-0.5 text-xs text-muted-foreground">
            <span>${channel.attributed_revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })} rev</span>
            <span>{channel.attributed_conversions.toLocaleString()} conv</span>
            <span>{channel.revenue_share_pct.toFixed(1)}% share</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="hidden sm:block w-24 h-1.5 bg-muted rounded-full overflow-hidden">
            <div className={`h-full rounded-full ${cfg.bar}`} style={{ width: `${Math.min(channel.confidence_score, 100)}%` }} />
          </div>
          {open ? <ChevronDown className="w-4 h-4 text-muted-foreground/50" /> : <ChevronRight className="w-4 h-4 text-muted-foreground/50" />}
        </div>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 space-y-3 border-t border">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="text-center p-2 bg-muted/30 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Last-Touch</div>
              <div className="text-sm font-bold text-foreground">{channel.last_touch_pct.toFixed(1)}%</div>
            </div>
            <div className="text-center p-2 bg-muted/30 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-muted-foreground/50">First-Touch</div>
              <div className="text-sm font-bold text-foreground">{channel.first_touch_pct.toFixed(1)}%</div>
            </div>
            <div className="text-center p-2 bg-muted/30 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Linear</div>
              <div className="text-sm font-bold text-foreground">{channel.linear_pct.toFixed(1)}%</div>
            </div>
            <div className="text-center p-2 bg-muted/30 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Data-Driven</div>
              <div className="text-sm font-bold text-foreground">{channel.data_driven_pct.toFixed(1)}%</div>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Layers className="w-3.5 h-3.5" />
            <span>Model agreement: <strong className="text-foreground">{channel.model_agreement.toFixed(0)}%</strong></span>
            <span className="text-muted-foreground/30">|</span>
            <span>Sample size: <strong className="text-foreground">{channel.sample_size.toLocaleString()}</strong></span>
          </div>
        </div>
      )}
    </div>
  );
}

function ModelCard({ model, isRecommended }: { model: ModelComparison; isRecommended: boolean }) {
  return (
    <div className={`border rounded-xl p-4 ${isRecommended ? 'border-blue-200 bg-blue-50/30 ring-1 ring-blue-100' : 'border'}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-sm text-foreground">{model.display_name}</span>
        {isRecommended && (
          <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">Recommended</span>
        )}
      </div>
      <div className="text-xs text-muted-foreground mb-3">{model.best_for}</div>
      <div className="flex gap-4 text-xs mb-3">
        <div>
          <div className="text-[10px] text-muted-foreground/50 uppercase font-bold">Revenue</div>
          <div className="font-bold text-foreground">${model.total_attributed_revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground/50 uppercase font-bold">Confidence</div>
          <div className="font-bold text-foreground">{model.confidence.toFixed(0)}%</div>
        </div>
      </div>
      <div className="space-y-1">
        {model.strengths.slice(0, 2).map((s, i) => (
          <div key={i} className="flex items-start gap-1.5 text-[11px] text-emerald-600">
            <CheckCircle2 className="w-3 h-3 mt-0.5 shrink-0" />
            <span>{s}</span>
          </div>
        ))}
        {model.weaknesses.slice(0, 1).map((w, i) => (
          <div key={i} className="flex items-start gap-1.5 text-[11px] text-amber-600">
            <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
            <span>{w}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function QualityRow({ metric }: { metric: DataQualityMetric }) {
  const cfg = qualityStatusConfig[metric.status] || qualityStatusConfig.poor;
  const Icon = cfg.icon;

  return (
    <div className="flex items-center gap-3 p-3 rounded-xl border hover:bg-muted/30 transition-colors">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${cfg.bg}`}>
        <Icon className={`w-4 h-4 ${cfg.color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-foreground">{metric.label}</div>
        <div className="text-xs text-muted-foreground">{metric.description}</div>
      </div>
      <div className="text-right">
        <div className={`text-sm font-bold ${cfg.color}`}>{metric.score.toFixed(0)}%</div>
        <div className="text-[10px] text-muted-foreground/50 uppercase font-bold">{metric.impact} impact</div>
      </div>
    </div>
  );
}

function RecommendationRow({ rec }: { rec: AttributionRecommendation }) {
  const cfg = priorityConfig[rec.priority] || priorityConfig.medium;
  return (
    <div className="flex items-start gap-3 p-3 rounded-xl border">
      <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${cfg.bg}`}>
        <Zap className={`w-3.5 h-3.5 ${cfg.color}`} />
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground">{rec.title}</span>
          <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${cfg.bg} ${cfg.color}`}>{rec.priority}</span>
        </div>
        <div className="text-xs text-muted-foreground mt-0.5">{rec.description}</div>
      </div>
    </div>
  );
}

// ── Main Card ───────────────────────────────────────────────────────────────

type TabKey = 'channels' | 'models' | 'quality' | 'recommendations';

export function AttributionConfidenceCard() {
  const { data, isLoading, error } = useAttributionConfidence();
  const [tab, setTab] = useState<TabKey>('channels');

  if (isLoading) {
    return (
      <div className="rounded-xl border bg-card p-6 animate-pulse">
        <div className="h-6 bg-muted rounded w-48 mb-4" />
        <div className="h-20 bg-muted/30 rounded-xl" />
      </div>
    );
  }

  if (error || !data) return null;

  const cfg = confidenceConfig[data.confidence_label] || confidenceConfig.insufficient;

  const tabs: { key: TabKey; label: string; count?: number }[] = [
    { key: 'channels', label: 'Channels', count: data.channels.length },
    { key: 'models', label: 'Models', count: data.model_comparisons.length },
    { key: 'quality', label: 'Data Quality', count: data.data_quality_metrics.length },
    { key: 'recommendations', label: 'Actions', count: data.recommendations.length },
  ];

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 pt-5 pb-4 border-b border">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
              <Shield className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-foreground">Attribution Confidence</h3>
                <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${cfg.bg} ${cfg.color}`}>
                  {cfg.label}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">{data.summary}</p>
            </div>
          </div>
          <ConfidenceRing score={data.overall_confidence} size={56} />
        </div>

        {/* Stats bar */}
        <div className="flex gap-4 mt-4 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-muted/30 rounded-lg">
            <BarChart3 className="w-3.5 h-3.5 text-muted-foreground/50" />
            <span className="text-muted-foreground">{data.channels_tracked} channels</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-muted/30 rounded-lg">
            <Target className="w-3.5 h-3.5 text-muted-foreground/50" />
            <span className="text-muted-foreground">{data.total_conversions.toLocaleString()} conversions</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-muted/30 rounded-lg">
            <Info className="w-3.5 h-3.5 text-muted-foreground/50" />
            <span className="text-muted-foreground">Model: {data.model_used.replace('_', '-')}</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border px-6">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
              tab === t.key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-muted-foreground/50 hover:text-muted-foreground'
            }`}
          >
            {t.label}
            {t.count !== undefined && (
              <span className="ml-1 text-[10px] text-muted-foreground/50">({t.count})</span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4 space-y-2 max-h-[480px] overflow-y-auto">
        {tab === 'channels' && data.channels.map((ch, i) => <ChannelRow key={i} channel={ch} />)}
        {tab === 'models' && (
          <div className="grid sm:grid-cols-2 gap-3">
            {data.model_comparisons.map((m, i) => (
              <ModelCard key={i} model={m} isRecommended={m.model_name === data.recommended_model} />
            ))}
          </div>
        )}
        {tab === 'quality' && data.data_quality_metrics.map((m, i) => <QualityRow key={i} metric={m} />)}
        {tab === 'recommendations' && data.recommendations.map((r, i) => <RecommendationRow key={i} rec={r} />)}
        {tab === 'recommendations' && data.recommendations.length === 0 && (
          <div className="text-center py-8 text-sm text-muted-foreground/50">
            <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-400" />
            Attribution data quality is excellent. No actions needed.
          </div>
        )}
      </div>
    </div>
  );
}
