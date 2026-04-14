/**
 * Feature #19 — Cross-Channel Journey Mapping Card
 *
 * Shows customer journey paths, channel contributions, and drop-off points.
 */

import { useState } from 'react';
import {
  Route,
  ArrowRight,
  MapPin,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Eye,
  MousePointerClick,
  ShoppingCart,
  Zap,
} from 'lucide-react';
import {
  useJourneyMap,
  type JourneyPath,
  type ChannelContribution,
  type JourneyInsight,
} from '@/api/dashboard';

const interactionIcon: Record<string, typeof Eye> = {
  impression: Eye,
  click: MousePointerClick,
  visit: MapPin,
  conversion: ShoppingCart,
};

const severityConfig: Record<string, { color: string; bg: string; icon: typeof CheckCircle2 }> = {
  positive: { color: 'text-emerald-600', bg: 'bg-emerald-50', icon: CheckCircle2 },
  info: { color: 'text-blue-600', bg: 'bg-blue-50', icon: Zap },
  warning: { color: 'text-amber-600', bg: 'bg-amber-50', icon: AlertTriangle },
  critical: { color: 'text-red-600', bg: 'bg-red-50', icon: AlertTriangle },
};

function PathRow({ path }: { path: JourneyPath }) {
  const [open, setOpen] = useState(false);

  return (
    <div className={`border rounded-xl transition-all ${open ? 'border-slate-200' : 'border-slate-100'}`}>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-3 p-3 text-left hover:bg-slate-50/50 rounded-xl transition-colors">
        <div className="w-9 h-9 rounded-lg bg-teal-50 flex items-center justify-center shrink-0">
          <Route className="w-4.5 h-4.5 text-teal-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-slate-900 truncate">{path.path_name}</span>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-teal-50 text-teal-600">
              {path.frequency.toFixed(0)}% of journeys
            </span>
          </div>
          <div className="flex gap-3 mt-0.5 text-xs text-slate-500">
            <span>{path.touchpoints.length} touchpoints</span>
            <span>{path.avg_days_to_convert.toFixed(1)}d avg</span>
            <span>{path.conversion_rate.toFixed(1)}% CVR</span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-sm font-bold text-slate-700">{path.avg_conversions.toLocaleString()}</span>
          <span className="text-[10px] text-slate-400">conv</span>
          {open ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
        </div>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-slate-50">
          <div className="flex items-center gap-1 py-3 overflow-x-auto">
            {path.touchpoints.map((tp, i) => {
              const TpIcon = interactionIcon[tp.interaction_type] || Eye;
              const isLast = i === path.touchpoints.length - 1;
              return (
                <div key={i} className="flex items-center gap-1 shrink-0">
                  <div className="flex flex-col items-center gap-1">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${tp.interaction_type === 'conversion' ? 'bg-emerald-50' : 'bg-slate-50'}`}>
                      <TpIcon className={`w-4.5 h-4.5 ${tp.interaction_type === 'conversion' ? 'text-emerald-600' : 'text-slate-400'}`} />
                    </div>
                    <span className="text-[10px] font-bold text-slate-500">{tp.platform.slice(0, 6)}</span>
                    <span className="text-[9px] text-slate-400 capitalize">{tp.interaction_type}</span>
                    {tp.drop_off_rate > 0 && (
                      <span className="text-[9px] text-red-400">-{tp.drop_off_rate.toFixed(0)}%</span>
                    )}
                  </div>
                  {!isLast && (
                    <div className="flex flex-col items-center mx-1">
                      <ArrowRight className="w-3.5 h-3.5 text-slate-300" />
                      {tp.avg_time_to_next && (
                        <span className="text-[9px] text-slate-400 mt-0.5">{tp.avg_time_to_next}</span>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          <div className="flex gap-4 text-xs text-slate-500 mt-2 pt-2 border-t border-slate-50">
            <span>${path.avg_revenue_per_journey.toFixed(0)} avg rev</span>
            <span>{path.avg_days_to_convert.toFixed(1)} days avg</span>
            <span>{path.conversion_rate.toFixed(1)}% CVR</span>
          </div>
        </div>
      )}
    </div>
  );
}

function ContributionRow({ cc }: { cc: ChannelContribution }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-xl border border-slate-100">
      <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center shrink-0">
        <MapPin className="w-4 h-4 text-slate-400" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-semibold text-sm text-slate-900">{cc.platform}</div>
        <div className="flex gap-2 mt-1">
          <div className="flex-1">
            <div className="text-[10px] text-slate-400 mb-0.5">First Touch</div>
            <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-blue-500" style={{ width: `${cc.first_touch_pct}%` }} />
            </div>
          </div>
          <div className="flex-1">
            <div className="text-[10px] text-slate-400 mb-0.5">Assist</div>
            <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-amber-500" style={{ width: `${cc.assist_pct}%` }} />
            </div>
          </div>
          <div className="flex-1">
            <div className="text-[10px] text-slate-400 mb-0.5">Last Touch</div>
            <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-emerald-500" style={{ width: `${cc.last_touch_pct}%` }} />
            </div>
          </div>
        </div>
      </div>
      <div className="text-right shrink-0">
        <div className="text-xs text-slate-400">Avg Position</div>
        <div className="text-sm font-bold text-slate-700">{cc.avg_position.toFixed(1)}</div>
      </div>
    </div>
  );
}

function InsightRow({ insight }: { insight: JourneyInsight }) {
  const cfg = severityConfig[insight.severity] || severityConfig.info;
  const Icon = cfg.icon;
  return (
    <div className="flex items-start gap-3 p-3 rounded-xl border border-slate-100">
      <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${cfg.bg}`}>
        <Icon className={`w-4 h-4 ${cfg.color}`} />
      </div>
      <div className="flex-1">
        <div className="text-sm font-semibold text-slate-900">{insight.title}</div>
        <div className="text-xs text-slate-500 mt-0.5">{insight.description}</div>
      </div>
      {insight.action_label && (
        <span className={`text-[10px] font-bold uppercase px-2 py-1 rounded-lg shrink-0 ${cfg.bg} ${cfg.color}`}>
          {insight.action_label}
        </span>
      )}
    </div>
  );
}

type TabKey = 'paths' | 'channels' | 'insights';

export function JourneyMapCard() {
  const { data, isLoading, error } = useJourneyMap();
  const [tab, setTab] = useState<TabKey>('paths');

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 animate-pulse">
        <div className="h-6 bg-slate-100 rounded w-48 mb-4" />
        <div className="h-20 bg-slate-50 rounded-xl" />
      </div>
    );
  }

  if (error || !data) return null;

  const tabs: { key: TabKey; label: string; count?: number }[] = [
    { key: 'paths', label: 'Journeys', count: data.top_paths.length },
    { key: 'channels', label: 'Channel Mix', count: data.channel_contributions.length },
    { key: 'insights', label: 'Insights', count: data.insights.length },
  ];

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4 border-b border-slate-100">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center">
              <Route className="w-5 h-5 text-teal-600" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-900">Journey Mapping</h3>
              <p className="text-xs text-slate-500 mt-0.5">{data.summary}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
          <div className="bg-slate-50 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-400">Avg Touchpoints</div>
            <div className="text-lg font-bold text-slate-900">{data.avg_touchpoints.toFixed(1)}</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-400">Days to Convert</div>
            <div className="text-lg font-bold text-slate-900">{data.avg_days_to_convert.toFixed(1)}</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-400">Entry Channel</div>
            <div className="text-sm font-bold text-blue-600 truncate">{data.top_entry_channel}</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-400">Closing Channel</div>
            <div className="text-sm font-bold text-emerald-600 truncate">{data.top_closing_channel}</div>
          </div>
        </div>
      </div>

      <div className="flex border-b border-slate-100 px-6">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
              tab === t.key ? 'border-teal-600 text-teal-600' : 'border-transparent text-slate-400 hover:text-slate-600'
            }`}
          >
            {t.label}
            {t.count !== undefined && <span className="ml-1 text-[10px] text-slate-400">({t.count})</span>}
          </button>
        ))}
      </div>

      <div className="p-4 space-y-2 max-h-[480px] overflow-y-auto">
        {tab === 'paths' && data.top_paths.map((p, i) => <PathRow key={i} path={p} />)}
        {tab === 'channels' && data.channel_contributions.map((c, i) => <ContributionRow key={i} cc={c} />)}
        {tab === 'insights' && data.insights.map((ins, i) => <InsightRow key={i} insight={ins} />)}
      </div>
    </div>
  );
}
