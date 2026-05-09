/**
 * Budget Reallocation — 4-step flow: plan → review → approve → execute,
 * with rollback as the destructive escape hatch.
 *
 * Surfaces POST /audit-services/budget/reallocation-plan + the three
 * lifecycle endpoints (/approve, /execute, /rollback). The operator
 * pastes campaign data as JSON (one record per line), generates a
 * plan, reviews the per-campaign deltas + projected impact, then
 * approves + executes (or rolls back if a previously-executed plan
 * needs reverting).
 *
 * Mounted at /console/budget-reallocation under Operations.
 */

import { useState } from 'react';
import {
  ArrowPathIcon,
  CheckCircleIcon,
  PlayIcon,
  ArrowUturnLeftIcon,
  CalculatorIcon,
} from '@heroicons/react/24/outline';
import {
  useCreateReallocationPlan,
  useApproveReallocationPlan,
  useExecuteReallocationPlan,
  useRollbackReallocationPlan,
  type CampaignBudgetInput,
  type ReallocationPlanResponse,
  type ReallocationChange,
} from '@/api/auditServicesPages';
import { Card } from '@/components/primitives/Card';
import { KPI } from '@/components/primitives/KPI';
import { StatusPill } from '@/components/primitives/StatusPill';
import { ConfirmDrawer } from '@/components/primitives/ConfirmDrawer';
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable';

const FIELD_SURFACE =
  'w-full bg-muted/40 border border-border rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary';

const SAMPLE_INPUT = `{"campaign_id":"c1","campaign_name":"Spring Sale","platform":"meta","current_daily_budget":500,"current_spend":487,"performance_metrics":{"roas":3.2,"ctr":1.8}}
{"campaign_id":"c2","campaign_name":"Brand Awareness","platform":"google","current_daily_budget":300,"current_spend":295,"performance_metrics":{"roas":1.4,"ctr":0.9}}
{"campaign_id":"c3","campaign_name":"Retargeting","platform":"meta","current_daily_budget":200,"current_spend":198,"performance_metrics":{"roas":5.6,"ctr":3.1}}`;

const STRATEGIES = [
  { value: 'ROAS_MAXIMIZATION', label: 'ROAS maximization' },
  { value: 'EQUAL_DISTRIBUTION', label: 'Equal distribution' },
  { value: 'BALANCED', label: 'Balanced' },
  { value: 'GROWTH', label: 'Growth' },
];

function parseCampaigns(text: string): {
  rows: CampaignBudgetInput[];
  error: string | null;
} {
  const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length === 0) return { rows: [], error: null };
  const rows: CampaignBudgetInput[] = [];
  for (let i = 0; i < lines.length; i++) {
    try {
      const parsed = JSON.parse(lines[i]) as CampaignBudgetInput;
      if (!parsed.campaign_id || !parsed.campaign_name || !parsed.platform) {
        return { rows: [], error: `Line ${i + 1}: missing required fields.` };
      }
      rows.push(parsed);
    } catch (e) {
      return { rows: [], error: `Line ${i + 1}: invalid JSON.` };
    }
  }
  return { rows, error: null };
}

const changeColumns: DataTableColumn<ReallocationChange>[] = [
  {
    id: 'campaign',
    header: 'Campaign',
    cell: (c) => (
      <div className="space-y-0.5">
        <p className="font-medium text-sm">{c.campaign_name}</p>
        <p className="font-mono text-xs text-muted-foreground">{c.campaign_id}</p>
      </div>
    ),
    sortable: true,
    sortAccessor: (c) => c.campaign_name,
  },
  {
    id: 'current',
    header: 'Current',
    cell: (c) => <span className="font-mono text-xs">${c.current_budget.toFixed(2)}</span>,
    cellClassName: 'text-right',
    headerClassName: 'text-right',
  },
  {
    id: 'new',
    header: 'New',
    cell: (c) => <span className="font-mono text-xs font-medium">${c.new_budget.toFixed(2)}</span>,
    cellClassName: 'text-right',
    headerClassName: 'text-right',
  },
  {
    id: 'change',
    header: 'Δ',
    cell: (c) => (
      <span
        className={`font-mono text-xs tabular-nums ${
          c.change_percent > 0
            ? 'text-success'
            : c.change_percent < 0
              ? 'text-danger'
              : 'text-muted-foreground'
        }`}
      >
        {c.change_percent > 0 ? '+' : ''}
        {c.change_percent.toFixed(1)}%
      </span>
    ),
    sortable: true,
    sortAccessor: (c) => c.change_percent,
    cellClassName: 'text-right',
    headerClassName: 'text-right',
  },
  {
    id: 'reason',
    header: 'Reason',
    cell: (c) => <span className="text-xs text-muted-foreground">{c.reason}</span>,
  },
];

export default function BudgetReallocation() {
  const [input, setInput] = useState(SAMPLE_INPUT);
  const [strategy, setStrategy] = useState('ROAS_MAXIMIZATION');
  const [maxChange, setMaxChange] = useState(50);
  const [minBudget, setMinBudget] = useState(10);
  const [parseError, setParseError] = useState<string | null>(null);
  const [plan, setPlan] = useState<ReallocationPlanResponse | null>(null);
  const [confirmExecute, setConfirmExecute] = useState(false);
  const [confirmRollback, setConfirmRollback] = useState(false);

  const create = useCreateReallocationPlan();
  const approve = useApproveReallocationPlan();
  const execute = useExecuteReallocationPlan();
  const rollback = useRollbackReallocationPlan();

  const generatePlan = async () => {
    setParseError(null);
    setPlan(null);
    const { rows, error } = parseCampaigns(input);
    if (error) {
      setParseError(error);
      return;
    }
    if (rows.length === 0) {
      setParseError('Add at least one campaign.');
      return;
    }
    try {
      const result = await create.mutateAsync({
        campaigns: rows,
        strategy,
        max_change_percent: maxChange,
        min_campaign_budget: minBudget,
      });
      setPlan(result);
    } catch {
      // surfaced via create.isError
    }
  };

  const onApprove = async () => {
    if (!plan) return;
    try {
      await approve.mutateAsync(plan.plan_id);
      setPlan({ ...plan, status: 'approved' });
    } catch {
      // surfaced via approve.isError
    }
  };

  const onExecute = async () => {
    if (!plan) return;
    setConfirmExecute(false);
    try {
      await execute.mutateAsync(plan.plan_id);
      setPlan({ ...plan, status: 'executed' });
    } catch {
      // surfaced via execute.isError
    }
  };

  const onRollback = async () => {
    if (!plan) return;
    setConfirmRollback(false);
    try {
      await rollback.mutateAsync(plan.plan_id);
      setPlan({ ...plan, status: 'rolled_back' });
    } catch {
      // surfaced via rollback.isError
    }
  };

  const status = plan?.status ?? '';
  const isApproved = status === 'approved';
  const isExecuted = status === 'executed';

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">
          Budget Reallocation
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Plan → review → approve → execute. Each step is auditable; rollback reverts a
          previously-executed plan in one operation.
        </p>
      </header>

      <Card className="p-6 space-y-4">
        <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
          1 · Plan
        </h2>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="block text-sm text-muted-foreground mb-1">Strategy</label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className={FIELD_SURFACE}
            >
              {STRATEGIES.map((s) => (
                <option key={s.value} value={s.value} className="bg-card">
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-muted-foreground mb-1">
              Max change: {maxChange}%
            </label>
            <input
              type="range"
              min={5}
              max={100}
              step={5}
              value={maxChange}
              onChange={(e) => setMaxChange(parseInt(e.target.value))}
              className="w-full accent-primary"
            />
          </div>
          <div>
            <label className="block text-sm text-muted-foreground mb-1">
              Min campaign budget ($)
            </label>
            <input
              type="number"
              min={0}
              step={1}
              value={minBudget}
              onChange={(e) => setMinBudget(parseFloat(e.target.value) || 0)}
              className={FIELD_SURFACE}
            />
          </div>
        </div>
        <div>
          <label className="block text-sm text-muted-foreground mb-1">
            Campaigns (one JSON object per line)
          </label>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={6}
            className="w-full bg-muted/60 border border-border rounded-lg p-4 font-mono text-xs text-foreground focus:outline-none focus:border-primary resize-y"
            spellCheck={false}
          />
          {parseError && <p className="mt-2 text-sm text-danger">{parseError}</p>}
        </div>
        <button
          onClick={generatePlan}
          disabled={create.isPending}
          className="bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
        >
          {create.isPending ? (
            <ArrowPathIcon className="w-5 h-5 animate-spin" />
          ) : (
            <CalculatorIcon className="w-5 h-5" />
          )}
          Generate plan
        </button>
        {create.isError && <p className="text-sm text-danger">Could not generate plan.</p>}
      </Card>

      {plan && (
        <>
          <section className="grid gap-4 md:grid-cols-3">
            <KPI
              label="Total budget"
              value={`$${plan.total_budget.toLocaleString()}`}
              status={{ label: plan.status, variant: isExecuted ? 'healthy' : 'neutral' }}
            />
            <KPI label="Campaigns affected" value={plan.campaigns_affected.toString()} />
            <KPI
              label="Projected ROAS Δ"
              value={`${plan.projected_impact.roas_change > 0 ? '+' : ''}${plan.projected_impact.roas_change.toFixed(2)}x`}
              delta={{
                value: plan.projected_impact.roas_change,
                format: 'absolute',
              }}
            />
          </section>

          <Card className="p-6 space-y-4">
            <header className="flex items-center justify-between">
              <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
                2 · Review
              </h2>
              <span className="font-mono text-xs text-muted-foreground">{plan.plan_id}</span>
            </header>
            <DataTable<ReallocationChange>
              data={plan.changes}
              columns={changeColumns}
              rowKey={(c) => c.campaign_id}
              ariaLabel="Reallocation changes"
            />
          </Card>

          <Card className="p-6 space-y-4">
            <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
              3 · Approve and execute
            </h2>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={onApprove}
                disabled={isApproved || isExecuted || approve.isPending}
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-card hover:bg-muted px-4 py-2 text-sm font-medium disabled:opacity-50"
              >
                {approve.isPending ? (
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircleIcon className="w-4 h-4" />
                )}
                {isApproved || isExecuted ? 'Approved' : 'Approve'}
              </button>
              <button
                onClick={() => setConfirmExecute(true)}
                disabled={!isApproved || isExecuted || execute.isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 text-sm font-medium disabled:opacity-50"
              >
                {execute.isPending ? (
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                ) : (
                  <PlayIcon className="w-4 h-4" />
                )}
                Execute
              </button>
              <button
                onClick={() => setConfirmRollback(true)}
                disabled={!isExecuted || rollback.isPending}
                className="inline-flex items-center gap-2 rounded-lg border border-danger/30 text-danger hover:bg-danger/10 px-4 py-2 text-sm font-medium disabled:opacity-50"
              >
                {rollback.isPending ? (
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                ) : (
                  <ArrowUturnLeftIcon className="w-4 h-4" />
                )}
                Rollback
              </button>
              <span className="ml-2 inline-flex items-center">
                <StatusPill
                  variant={
                    status === 'executed'
                      ? 'healthy'
                      : status === 'approved'
                        ? 'degraded'
                        : status === 'rolled_back'
                          ? 'unhealthy'
                          : 'neutral'
                  }
                  size="sm"
                >
                  {status || 'pending'}
                </StatusPill>
              </span>
            </div>
            {(approve.isError || execute.isError || rollback.isError) && (
              <p className="text-sm text-danger">
                One of the lifecycle calls failed — check the server logs.
              </p>
            )}
          </Card>
        </>
      )}

      <ConfirmDrawer
        open={confirmExecute}
        onOpenChange={setConfirmExecute}
        onConfirm={onExecute}
        title="Execute reallocation plan?"
        description={`This will apply the new budgets to ${plan?.campaigns_affected ?? 0} campaign${plan?.campaigns_affected === 1 ? '' : 's'} immediately on the platform. Reversible via Rollback.`}
        confirmLabel="Execute now"
        variant="warning"
        loading={execute.isPending}
      />

      <ConfirmDrawer
        open={confirmRollback}
        onOpenChange={setConfirmRollback}
        onConfirm={onRollback}
        title="Rollback executed plan?"
        description="Restores each campaign's pre-plan budget. Use this only if the executed reallocation produced unexpected results."
        confirmLabel="Rollback"
        variant="destructive"
        loading={rollback.isPending}
      />
    </div>
  );
}
