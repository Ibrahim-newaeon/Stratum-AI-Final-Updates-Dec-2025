/**
 * Feature #17 — Collaborative Annotations Card
 *
 * Shows team annotations, notes, and discussions on dashboard metrics.
 */

import { useState } from 'react';
import {
  MessageSquareText,
  Pin,
  Tag,
  MessageCircle,
  AlertTriangle,
  Target,
  BarChart3,
  HelpCircle,
  CheckCircle2,
} from 'lucide-react';
import {
  useCollaborativeAnnotations,
  type Annotation,
  type AnnotationInsight,
} from '@/api/dashboard';

const tagConfig: Record<string, { color: string; bg: string; icon: typeof Tag }> = {
  performance: { color: 'text-blue-600', bg: 'bg-blue-50', icon: BarChart3 },
  strategy: { color: 'text-purple-600', bg: 'bg-purple-50', icon: Target },
  alert: { color: 'text-amber-600', bg: 'bg-amber-50', icon: AlertTriangle },
  question: { color: 'text-cyan-600', bg: 'bg-cyan-50', icon: HelpCircle },
  general: { color: 'text-slate-600', bg: 'bg-slate-50', icon: Tag },
};

function AnnotationRow({ annotation }: { annotation: Annotation }) {
  const [showReplies, setShowReplies] = useState(false);
  const tcfg = tagConfig[annotation.tag] || tagConfig.general;
  const TagIcon = tcfg.icon;

  return (
    <div className="border border-slate-100 rounded-xl p-3 hover:bg-slate-50/30 transition-colors">
      <div className="flex items-start gap-3">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold ${annotation.author.initials === 'AI' ? 'bg-violet-100 text-violet-600' : 'bg-slate-100 text-slate-600'}`}>
          {annotation.author.initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-slate-900">{annotation.author.name}</span>
            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded flex items-center gap-1 ${tcfg.bg} ${tcfg.color}`}>
              <TagIcon className="w-2.5 h-2.5" />{annotation.tag}
            </span>
            {annotation.pinned && (
              <Pin className="w-3 h-3 text-amber-500" />
            )}
            <span className="text-[10px] text-slate-400">{annotation.target_label}</span>
          </div>
          <p className="text-xs text-slate-600 mt-1 leading-relaxed">{annotation.content}</p>
          {annotation.reply_count > 0 && (
            <button
              onClick={() => setShowReplies(!showReplies)}
              className="flex items-center gap-1.5 mt-2 text-xs text-blue-600 hover:text-blue-700 transition-colors"
            >
              <MessageCircle className="w-3 h-3" />
              {annotation.reply_count} repl{annotation.reply_count === 1 ? 'y' : 'ies'}
            </button>
          )}
          {showReplies && annotation.replies.map((r) => (
            <div key={r.reply_id} className="mt-2 ml-4 pl-3 border-l-2 border-slate-100">
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${r.author.initials === 'AI' ? 'bg-violet-50 text-violet-600' : 'bg-slate-50 text-slate-500'}`}>
                  {r.author.initials}
                </span>
                <span className="text-xs font-medium text-slate-700">{r.author.name}</span>
              </div>
              <p className="text-xs text-slate-500 mt-1">{r.content}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function InsightRow({ insight }: { insight: AnnotationInsight }) {
  const isWarn = insight.severity === 'warning';
  return (
    <div className="flex items-start gap-3 p-3 rounded-xl border border-slate-100">
      <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${isWarn ? 'bg-amber-50' : 'bg-blue-50'}`}>
        {isWarn ? <AlertTriangle className="w-4 h-4 text-amber-600" /> : <CheckCircle2 className="w-4 h-4 text-blue-600" />}
      </div>
      <div className="flex-1">
        <div className="text-sm font-semibold text-slate-900">{insight.title}</div>
        <div className="text-xs text-slate-500 mt-0.5">{insight.description}</div>
      </div>
    </div>
  );
}

type TabKey = 'all' | 'pinned' | 'insights';

export function CollaborativeAnnotationsCard() {
  const { data, isLoading, error } = useCollaborativeAnnotations();
  const [tab, setTab] = useState<TabKey>('all');

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 animate-pulse">
        <div className="h-6 bg-slate-100 rounded w-48 mb-4" />
        <div className="h-20 bg-slate-50 rounded-xl" />
      </div>
    );
  }

  if (error || !data) return null;

  const pinned = data.annotations.filter((a) => a.pinned);
  const tabs: { key: TabKey; label: string; count?: number }[] = [
    { key: 'all', label: 'All Notes', count: data.stats.total },
    { key: 'pinned', label: 'Pinned', count: pinned.length },
    { key: 'insights', label: 'Activity', count: data.insights.length },
  ];

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4 border-b border-slate-100">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-50 flex items-center justify-center">
              <MessageSquareText className="w-5 h-5 text-sky-600" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-900">Team Annotations</h3>
              <p className="text-xs text-slate-500 mt-0.5">{data.summary}</p>
            </div>
          </div>
        </div>

        <div className="flex gap-3 mt-4 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-50 rounded-lg text-slate-600">
            <MessageCircle className="w-3.5 h-3.5" />
            <span>{data.active_discussions} discussion{data.active_discussions !== 1 ? 's' : ''}</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-amber-50 rounded-lg text-amber-600">
            <Pin className="w-3.5 h-3.5" />
            <span>{data.stats.pinned} pinned</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-50 rounded-lg text-slate-500">
            <span>{data.team_members_active} contributor{data.team_members_active !== 1 ? 's' : ''}</span>
          </div>
        </div>
      </div>

      <div className="flex border-b border-slate-100 px-6">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
              tab === t.key ? 'border-sky-600 text-sky-600' : 'border-transparent text-slate-400 hover:text-slate-600'
            }`}
          >
            {t.label}
            {t.count !== undefined && <span className="ml-1 text-[10px] text-slate-400">({t.count})</span>}
          </button>
        ))}
      </div>

      <div className="p-4 space-y-2 max-h-[480px] overflow-y-auto">
        {tab === 'all' && data.annotations.map((a, i) => <AnnotationRow key={i} annotation={a} />)}
        {tab === 'pinned' && pinned.map((a, i) => <AnnotationRow key={i} annotation={a} />)}
        {tab === 'insights' && data.insights.map((ins, i) => <InsightRow key={i} insight={ins} />)}
      </div>
    </div>
  );
}
