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
  general: { color: 'text-muted-foreground', bg: 'bg-muted/30', icon: Tag },
};

function AnnotationRow({ annotation }: { annotation: Annotation }) {
  const [showReplies, setShowReplies] = useState(false);
  const tcfg = tagConfig[annotation.tag] || tagConfig.general;
  const TagIcon = tcfg.icon;

  return (
    <div className="border rounded-xl p-3 hover:bg-muted/30 transition-colors">
      <div className="flex items-start gap-3">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold ${annotation.author.initials === 'AI' ? 'bg-violet-100 text-violet-600' : 'bg-muted text-muted-foreground'}`}>
          {annotation.author.initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-foreground">{annotation.author.name}</span>
            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded flex items-center gap-1 ${tcfg.bg} ${tcfg.color}`}>
              <TagIcon className="w-2.5 h-2.5" />{annotation.tag}
            </span>
            {annotation.pinned && (
              <Pin className="w-3 h-3 text-amber-500" />
            )}
            <span className="text-[10px] text-muted-foreground/50">{annotation.target_label}</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{annotation.content}</p>
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
            <div key={r.reply_id} className="mt-2 ml-4 pl-3 border">
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${r.author.initials === 'AI' ? 'bg-violet-50 text-violet-600' : 'bg-muted/30 text-muted-foreground'}`}>
                  {r.author.initials}
                </span>
                <span className="text-xs font-medium text-foreground">{r.author.name}</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">{r.content}</p>
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
    <div className="flex items-start gap-3 p-3 rounded-xl border">
      <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${isWarn ? 'bg-amber-50' : 'bg-blue-50'}`}>
        {isWarn ? <AlertTriangle className="w-4 h-4 text-amber-600" /> : <CheckCircle2 className="w-4 h-4 text-blue-600" />}
      </div>
      <div className="flex-1">
        <div className="text-sm font-semibold text-foreground">{insight.title}</div>
        <div className="text-xs text-muted-foreground mt-0.5">{insight.description}</div>
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
      <div className="rounded-xl border bg-card p-6 animate-pulse">
        <div className="h-6 bg-muted rounded w-48 mb-4" />
        <div className="h-20 bg-muted/30 rounded-xl" />
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
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4 border-b border">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-sky-50 flex items-center justify-center">
              <MessageSquareText className="w-5 h-5 text-sky-600" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Team Annotations</h3>
              <p className="text-xs text-muted-foreground mt-0.5">{data.summary}</p>
            </div>
          </div>
        </div>

        <div className="flex gap-3 mt-4 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-muted/30 rounded-lg text-muted-foreground">
            <MessageCircle className="w-3.5 h-3.5" />
            <span>{data.active_discussions} discussion{data.active_discussions !== 1 ? 's' : ''}</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-amber-50 rounded-lg text-amber-600">
            <Pin className="w-3.5 h-3.5" />
            <span>{data.stats.pinned} pinned</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-muted/30 rounded-lg text-muted-foreground">
            <span>{data.team_members_active} contributor{data.team_members_active !== 1 ? 's' : ''}</span>
          </div>
        </div>
      </div>

      <div className="flex border-b border px-6">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
              tab === t.key ? 'border-sky-600 text-sky-600' : 'border-transparent text-muted-foreground/50 hover:text-muted-foreground'
            }`}
          >
            {t.label}
            {t.count !== undefined && <span className="ml-1 text-[10px] text-muted-foreground/50">({t.count})</span>}
          </button>
        ))}
      </div>

      <div className="p-4 space-y-2 max-h-[30rem] overflow-y-auto">
        {tab === 'all' && data.annotations.map((a, i) => <AnnotationRow key={a.annotation_id || i} annotation={a} />)}
        {tab === 'pinned' && pinned.map((a, i) => <AnnotationRow key={a.annotation_id || i} annotation={a} />)}
        {tab === 'insights' && data.insights.map((ins, i) => <InsightRow key={`${ins.title}-${i}`} insight={ins} />)}
      </div>
    </div>
  );
}
