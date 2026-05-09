/**
 * LTV Batch Predict — paste a JSON array of customer behavior records,
 * get back per-customer 365d LTV, churn probability, recommended max
 * CAC, and segment label. Plus the segment definition reference table.
 *
 * Surfaces POST /audit-services/ltv/batch-predict and
 * GET /audit-services/ltv/segments.
 *
 * Mounted at /console/ltv-batch under Operations.
 */

import { useMemo, useState } from 'react';
import { ArrowPathIcon, CalculatorIcon } from '@heroicons/react/24/outline';
import {
  useBatchPredictLTV,
  useLTVSegments,
  type CustomerBehaviorInput,
  type BatchLTVPrediction,
} from '@/api/auditServicesPages';
import { Card } from '@/components/primitives/Card';
import { KPI } from '@/components/primitives/KPI';
import { StatusPill, type StatusPillVariant } from '@/components/primitives/StatusPill';
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable';

const SAMPLE_CUSTOMERS = `[
  {"customer_id":"c1","acquisition_date":"2026-01-15","acquisition_channel":"meta","first_order_value":85,"total_orders":3,"total_revenue":240,"avg_order_value":80,"days_since_last_order":4,"sessions_first_week":7,"email_opens_first_week":5},
  {"customer_id":"c2","acquisition_date":"2026-02-02","acquisition_channel":"google","first_order_value":350,"total_orders":1,"total_revenue":350,"avg_order_value":350,"days_since_last_order":62,"sessions_first_week":2,"email_opens_first_week":1},
  {"customer_id":"c3","acquisition_date":"2026-03-08","acquisition_channel":"organic","first_order_value":50,"total_orders":8,"total_revenue":620,"avg_order_value":77,"days_since_last_order":2,"sessions_first_week":12,"email_opens_first_week":9}
]`;

function segmentVariant(segment: string): StatusPillVariant {
  const lc = segment.toLowerCase();
  if (lc === 'vip' || lc === 'high_value') return 'healthy';
  if (lc === 'medium_value') return 'neutral';
  if (lc === 'at_risk') return 'unhealthy';
  return 'degraded';
}

const predictionColumns: DataTableColumn<BatchLTVPrediction>[] = [
  {
    id: 'customer_id',
    header: 'Customer',
    cell: (p) => <span className="font-mono text-xs">{p.customer_id}</span>,
    sortable: true,
    sortAccessor: (p) => p.customer_id,
  },
  {
    id: 'segment',
    header: 'Segment',
    cell: (p) => (
      <StatusPill variant={segmentVariant(p.segment)} size="sm">
        {p.segment.replace(/_/g, ' ')}
      </StatusPill>
    ),
  },
  {
    id: 'ltv',
    header: '365d LTV',
    cell: (p) => (
      <span className="font-mono text-sm font-medium tabular-nums">
        ${p.predicted_ltv_365d.toLocaleString(undefined, { maximumFractionDigits: 2 })}
      </span>
    ),
    sortable: true,
    sortAccessor: (p) => p.predicted_ltv_365d,
    cellClassName: 'text-right',
    headerClassName: 'text-right',
  },
  {
    id: 'churn',
    header: 'Churn p',
    cell: (p) => (
      <span
        className={`font-mono text-xs tabular-nums ${
          p.churn_probability > 0.6
            ? 'text-danger'
            : p.churn_probability > 0.3
              ? 'text-warning'
              : 'text-success'
        }`}
      >
        {(p.churn_probability * 100).toFixed(1)}%
      </span>
    ),
    sortable: true,
    sortAccessor: (p) => p.churn_probability,
    cellClassName: 'text-right',
    headerClassName: 'text-right',
  },
  {
    id: 'max_cac',
    header: 'Max CAC',
    cell: (p) => (
      <span className="font-mono text-xs tabular-nums">
        ${p.max_cac.toLocaleString(undefined, { maximumFractionDigits: 2 })}
      </span>
    ),
    sortable: true,
    sortAccessor: (p) => p.max_cac,
    cellClassName: 'text-right',
    headerClassName: 'text-right',
  },
];

export default function LTVBatchPredict() {
  const [input, setInput] = useState(SAMPLE_CUSTOMERS);
  const [parseError, setParseError] = useState<string | null>(null);
  const [predictions, setPredictions] = useState<BatchLTVPrediction[]>([]);

  const predict = useBatchPredictLTV();
  const segmentsQuery = useLTVSegments();

  const runPredict = async () => {
    setParseError(null);
    setPredictions([]);
    let parsed: CustomerBehaviorInput[];
    try {
      parsed = JSON.parse(input) as CustomerBehaviorInput[];
      if (!Array.isArray(parsed)) {
        setParseError('Input must be a JSON array of customer records.');
        return;
      }
    } catch (e) {
      setParseError('Invalid JSON.');
      return;
    }
    if (parsed.length === 0) {
      setParseError('Add at least one customer record.');
      return;
    }
    try {
      const result = await predict.mutateAsync(parsed);
      setPredictions(result.predictions ?? []);
    } catch {
      // surfaced via predict.isError
    }
  };

  const summary = useMemo(() => {
    if (predictions.length === 0) return null;
    const avgLtv =
      predictions.reduce((acc, p) => acc + p.predicted_ltv_365d, 0) / predictions.length;
    const atRisk = predictions.filter((p) => p.churn_probability > 0.5).length;
    const vips = predictions.filter(
      (p) => p.segment.toLowerCase() === 'vip' || p.segment.toLowerCase() === 'high_value'
    ).length;
    return { avgLtv, atRisk, vips };
  }, [predictions]);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">LTV Batch Predict</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Paste a JSON array of customer behavior records — the predictor returns 365d LTV, churn
          probability, recommended max CAC, and a segment label per customer.
        </p>
      </header>

      <Card className="p-6 space-y-4">
        <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">Input</h2>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={10}
          className="w-full bg-muted/60 border border-border rounded-lg p-4 font-mono text-xs text-foreground focus:outline-none focus:border-primary resize-y"
          spellCheck={false}
        />
        {parseError && <p className="text-sm text-danger">{parseError}</p>}
        <button
          onClick={runPredict}
          disabled={predict.isPending}
          className="bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
        >
          {predict.isPending ? (
            <ArrowPathIcon className="w-5 h-5 animate-spin" />
          ) : (
            <CalculatorIcon className="w-5 h-5" />
          )}
          Predict
        </button>
        {predict.isError && (
          <p className="text-sm text-danger">Could not reach the LTV predictor.</p>
        )}
      </Card>

      {summary && (
        <section className="grid gap-4 md:grid-cols-3">
          <KPI label="Customers" value={predictions.length.toString()} />
          <KPI
            label="Avg 365d LTV"
            value={`$${summary.avgLtv.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
          />
          <KPI
            label="At-risk customers"
            value={summary.atRisk.toString()}
            status={
              summary.atRisk > 0
                ? { label: 'review', variant: 'degraded' }
                : { label: 'clean', variant: 'healthy' }
            }
          />
        </section>
      )}

      {predictions.length > 0 && (
        <Card className="p-6">
          <h2 className="mb-4 font-mono text-sm uppercase tracking-wider text-muted-foreground">
            Predictions
          </h2>
          <DataTable<BatchLTVPrediction>
            data={predictions}
            columns={predictionColumns}
            rowKey={(p) => p.customer_id}
            ariaLabel="Per-customer LTV predictions"
          />
        </Card>
      )}

      <Card className="p-6">
        <h2 className="mb-4 font-mono text-sm uppercase tracking-wider text-muted-foreground">
          Segment definitions
        </h2>
        {segmentsQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : segmentsQuery.isError ? (
          <p className="text-sm text-danger">Could not load segment definitions.</p>
        ) : (
          <ul className="space-y-2">
            {(segmentsQuery.data ?? []).map((s) => (
              <li
                key={s.value}
                className="flex items-start justify-between gap-3 rounded-xl border border-border bg-muted/40 p-3"
              >
                <div className="min-w-0 space-y-0.5">
                  <div className="flex items-center gap-2">
                    <StatusPill variant={segmentVariant(s.value)} size="sm">
                      {s.name}
                    </StatusPill>
                    <span className="font-mono text-xs text-muted-foreground">{s.value}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">{s.description}</p>
                </div>
                {s.ltv_threshold != null && (
                  <span className="font-mono text-xs text-foreground tabular-nums shrink-0">
                    ≥ ${s.ltv_threshold.toLocaleString()}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
