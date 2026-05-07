/**
 * AI Recommendations — surfaces /analytics/ai/recommendations and /kpis.
 *
 * The backend returns four lists (recommendations, actions, alerts,
 * insights) plus a portfolio KPI summary. Renders each list as a card
 * stack so operators can see prioritized actions without a SQL query.
 *
 * Mounted at /dashboard/ai-recommendations under the Intelligence group.
 */

import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, Lightbulb, Sparkles, Target } from 'lucide-react';

import api from '@/api/client';
import { Card } from '@/components/primitives/Card';
import { KPI } from '@/components/primitives/KPI';
import { StatusPill, type StatusPillVariant } from '@/components/primitives/StatusPill';
import { cn } from '@/lib/utils';

interface RecommendationItem {
  type?: string;
  priority?: string;
  title?: string;
  description?: string;
  expected_impact?: Record<string, unknown>;
}

interface AlertItem {
  type?: string;
  metric?: string;
  severity?: string;
  message?: string;
  zscore?: number;
}

interface RecommendationsResponse {
  recommendations: RecommendationItem[];
  actions: RecommendationItem[];
  alerts: AlertItem[];
  insights: RecommendationItem[];
  message?: string;
}

interface AIKpis {
  total_spend: number;
  total_revenue: number;
  portfolio_roas: number;
  campaign_count: number;
  total_impressions?: number;
  total_clicks?: number;
  total_conversions?: number;
  avg_ctr?: number;
  avg_cpa?: number;
}

const SEVERITY_VARIANT: Record<string, StatusPillVariant> = {
  critical: 'unhealthy',
  high: 'unhealthy',
  medium: 'degraded',
  low: 'neutral',
};

function priorityVariant(p?: string): StatusPillVariant {
  if (!p) return 'neutral';
  return SEVERITY_VARIANT[p.toLowerCase()] ?? 'neutral';
}

function useAIRecommendations() {
  return useQuery({
    queryKey: ['analytics-ai', 'recommendations'],
    queryFn: async () => {
      const res = await api.get<RecommendationsResponse>('/analytics/ai/recommendations');
      return res.data;
    },
    staleTime: 60 * 1000,
  });
}

function useAIKpis() {
  return useQuery({
    queryKey: ['analytics-ai', 'kpis'],
    queryFn: async () => {
      const res = await api.get<AIKpis>('/analytics/ai/kpis');
      return res.data;
    },
    staleTime: 60 * 1000,
  });
}

function ItemList({
  items,
  emptyText,
  emptyIcon: EmptyIcon,
}: {
  items: RecommendationItem[];
  emptyText: string;
  emptyIcon: typeof Lightbulb;
}) {
  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
        <EmptyIcon className="mx-auto mb-2 h-5 w-5" />
        {emptyText}
      </div>
    );
  }
  return (
    <ul className="space-y-3">
      {items.map((it, idx) => (
        <li
          key={`${it.type ?? 'item'}-${idx}`}
          className="rounded-xl border border-border bg-muted/40 p-4 space-y-1"
        >
          <div className="flex items-center gap-2">
            {it.priority && (
              <StatusPill variant={priorityVariant(it.priority)} size="sm">
                {it.priority}
              </StatusPill>
            )}
            {it.type && <span className="font-mono text-xs text-muted-foreground">{it.type}</span>}
          </div>
          {it.title && <p className="text-sm font-medium">{it.title}</p>}
          {it.description && <p className="text-sm text-muted-foreground">{it.description}</p>}
        </li>
      ))}
    </ul>
  );
}

export default function AIRecommendations() {
  const recsQuery = useAIRecommendations();
  const kpisQuery = useAIKpis();

  const data = recsQuery.data;
  const k = kpisQuery.data;

  return (
    <div className="space-y-6 p-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">AI Recommendations</h1>
        <p className="text-sm text-muted-foreground">
          Prioritized actions, anomalies, and insights generated from today's campaign metrics.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-4">
        <KPI
          label="Portfolio ROAS"
          value={k ? `${k.portfolio_roas.toFixed(2)}x` : undefined}
          loading={kpisQuery.isLoading}
        />
        <KPI
          label="Total revenue"
          value={k ? `$${k.total_revenue.toLocaleString()}` : undefined}
          loading={kpisQuery.isLoading}
        />
        <KPI
          label="Total spend"
          value={k ? `$${k.total_spend.toLocaleString()}` : undefined}
          loading={kpisQuery.isLoading}
        />
        <KPI
          label="Campaigns"
          value={k ? k.campaign_count.toString() : undefined}
          loading={kpisQuery.isLoading}
        />
      </section>

      {data?.message && <Card className="p-4 text-sm text-muted-foreground">{data.message}</Card>}

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className={cn('p-6 space-y-4')}>
          <header className="flex items-center gap-2">
            <Target className="h-4 w-4 text-primary" />
            <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
              Recommendations
            </h2>
          </header>
          <ItemList
            items={data?.recommendations ?? []}
            emptyText={recsQuery.isLoading ? 'Loading…' : 'No actions recommended.'}
            emptyIcon={Target}
          />
        </Card>

        <Card className="p-6 space-y-4">
          <header className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-warning" />
            <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
              Alerts
            </h2>
          </header>
          {(data?.alerts ?? []).length === 0 ? (
            <div className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
              <AlertTriangle className="mx-auto mb-2 h-5 w-5" />
              {recsQuery.isLoading ? 'Loading…' : 'No alerts firing.'}
            </div>
          ) : (
            <ul className="space-y-3">
              {(data?.alerts ?? []).map((a, idx) => (
                <li
                  key={`${a.type ?? 'alert'}-${idx}`}
                  className="rounded-xl border border-border bg-muted/40 p-4 space-y-1"
                >
                  <div className="flex items-center gap-2">
                    {a.severity && (
                      <StatusPill variant={priorityVariant(a.severity)} size="sm">
                        {a.severity}
                      </StatusPill>
                    )}
                    {a.metric && (
                      <span className="font-mono text-xs text-muted-foreground">{a.metric}</span>
                    )}
                    {typeof a.zscore === 'number' && (
                      <span className="font-mono text-xs text-muted-foreground">
                        z={a.zscore.toFixed(2)}
                      </span>
                    )}
                  </div>
                  {a.message && <p className="text-sm">{a.message}</p>}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="p-6 space-y-4">
          <header className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
              Budget actions
            </h2>
          </header>
          <ItemList
            items={data?.actions ?? []}
            emptyText={recsQuery.isLoading ? 'Loading…' : 'No budget moves suggested.'}
            emptyIcon={Sparkles}
          />
        </Card>

        <Card className="p-6 space-y-4">
          <header className="flex items-center gap-2">
            <Lightbulb className="h-4 w-4 text-info" />
            <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
              Insights
            </h2>
          </header>
          <ItemList
            items={data?.insights ?? []}
            emptyText={recsQuery.isLoading ? 'Loading…' : 'No insights yet.'}
            emptyIcon={Lightbulb}
          />
        </Card>
      </section>
    </div>
  );
}
