/**
 * Experiments — model A/B test lifecycle management.
 *
 * Surfaces POST /audit-services/experiments (create), GET /experiments
 * (list), POST /:id/start, POST /:id/stop. Operator picks champion +
 * challenger model versions, sets traffic split + significance
 * threshold, runs the experiment and watches prediction counts.
 *
 * Mounted at /console/experiments under Operations.
 */

import { useState } from 'react';
import { ArrowPathIcon, PlayIcon, PlusIcon, StopIcon } from '@heroicons/react/24/outline';
import {
  useExperiments,
  useCreateExperiment,
  useStartExperiment,
  useStopExperiment,
  type Experiment,
} from '@/api/auditServicesPages';
import { Card } from '@/components/primitives/Card';
import { KPI } from '@/components/primitives/KPI';
import { StatusPill, type StatusPillVariant } from '@/components/primitives/StatusPill';
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable';

const FIELD_SURFACE =
  'w-full bg-muted/40 border border-border rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary';

function statusVariant(status: string): StatusPillVariant {
  switch (status.toLowerCase()) {
    case 'running':
      return 'healthy';
    case 'completed':
      return 'neutral';
    case 'stopped':
      return 'degraded';
    case 'failed':
      return 'unhealthy';
    case 'draft':
    default:
      return 'neutral';
  }
}

export default function Experiments() {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const experimentsQuery = useExperiments(undefined, statusFilter || undefined);
  const create = useCreateExperiment();
  const start = useStartExperiment();
  const stop = useStopExperiment();

  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [modelName, setModelName] = useState('');
  const [championVersion, setChampionVersion] = useState('');
  const [challengerVersion, setChallengerVersion] = useState('');
  const [trafficSplit, setTrafficSplit] = useState(0.1);
  const [significance, setSignificance] = useState(0.05);

  const experiments = experimentsQuery.data ?? [];
  const running = experiments.filter((e) => e.status === 'running').length;
  const completed = experiments.filter((e) => e.status === 'completed').length;

  const canCreate =
    name.trim().length > 0 &&
    modelName.trim().length > 0 &&
    championVersion.trim().length > 0 &&
    challengerVersion.trim().length > 0;

  const submitCreate = async () => {
    if (!canCreate) return;
    try {
      await create.mutateAsync({
        name: name.trim(),
        model_name: modelName.trim(),
        champion_version: championVersion.trim(),
        challenger_version: challengerVersion.trim(),
        traffic_split: trafficSplit,
        significance_threshold: significance,
      });
      setName('');
      setModelName('');
      setChampionVersion('');
      setChallengerVersion('');
      setShowCreate(false);
    } catch {
      // surfaced via create.isError
    }
  };

  const columns: DataTableColumn<Experiment>[] = [
    {
      id: 'name',
      header: 'Experiment',
      cell: (e) => (
        <div className="space-y-0.5">
          <p className="font-medium">{e.name}</p>
          <p className="font-mono text-xs text-muted-foreground">{e.model_name}</p>
        </div>
      ),
      sortable: true,
      sortAccessor: (e) => e.name,
    },
    {
      id: 'versions',
      header: 'Champion → Challenger',
      cell: (e) => (
        <span className="font-mono text-xs">
          {e.champion_version} → {e.challenger_version}
        </span>
      ),
    },
    {
      id: 'split',
      header: 'Split',
      cell: (e) => (
        <span className="font-mono tabular-nums text-xs">{Math.round(e.traffic_split * 100)}%</span>
      ),
    },
    {
      id: 'predictions',
      header: 'Predictions',
      cell: (e) => (
        <span className="font-mono text-xs">
          <span className="text-foreground">{e.champion_predictions.toLocaleString()}</span>
          <span className="text-muted-foreground"> vs </span>
          <span className="text-foreground">{e.challenger_predictions.toLocaleString()}</span>
        </span>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: (e) => (
        <StatusPill variant={statusVariant(e.status)} size="sm">
          {e.status}
        </StatusPill>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: (e) => {
        if (e.status === 'draft' || e.status === 'stopped') {
          return (
            <button
              onClick={() => start.mutate(e.id)}
              disabled={start.isPending}
              className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1 text-xs font-mono uppercase tracking-wider hover:bg-muted disabled:opacity-50"
            >
              <PlayIcon className="w-3 h-3" /> Start
            </button>
          );
        }
        if (e.status === 'running') {
          return (
            <button
              onClick={() => stop.mutate(e.id)}
              disabled={stop.isPending}
              className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1 text-xs font-mono uppercase tracking-wider text-danger hover:bg-danger/10 disabled:opacity-50"
            >
              <StopIcon className="w-3 h-3" /> Stop
            </button>
          );
        }
        return <span className="text-xs text-muted-foreground">—</span>;
      },
    },
  ];

  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">Experiments</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Champion vs challenger model A/B tests with traffic split, prediction counts, and
            significance threshold.
          </p>
        </div>
        <button
          onClick={() => setShowCreate((v) => !v)}
          className="bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
        >
          <PlusIcon className="w-4 h-4" />
          New experiment
        </button>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <KPI
          label="Total experiments"
          value={experimentsQuery.isLoading ? undefined : experiments.length.toString()}
          loading={experimentsQuery.isLoading}
        />
        <KPI
          label="Running"
          value={experimentsQuery.isLoading ? undefined : running.toString()}
          status={
            running > 0
              ? { label: 'live', variant: 'healthy', pulse: true }
              : { label: 'idle', variant: 'neutral' }
          }
          loading={experimentsQuery.isLoading}
        />
        <KPI
          label="Completed"
          value={experimentsQuery.isLoading ? undefined : completed.toString()}
          loading={experimentsQuery.isLoading}
        />
      </section>

      {showCreate && (
        <Card className="p-6 space-y-4">
          <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
            New experiment
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm text-muted-foreground mb-1">Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. ROAS predictor v2 rollout"
                className={FIELD_SURFACE}
              />
            </div>
            <div>
              <label className="block text-sm text-muted-foreground mb-1">Model name</label>
              <input
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                placeholder="e.g. roas_predictor"
                className={FIELD_SURFACE}
              />
            </div>
            <div>
              <label className="block text-sm text-muted-foreground mb-1">Champion version</label>
              <input
                value={championVersion}
                onChange={(e) => setChampionVersion(e.target.value)}
                placeholder="e.g. 1.4.0"
                className={FIELD_SURFACE}
              />
            </div>
            <div>
              <label className="block text-sm text-muted-foreground mb-1">Challenger version</label>
              <input
                value={challengerVersion}
                onChange={(e) => setChallengerVersion(e.target.value)}
                placeholder="e.g. 1.5.0-beta"
                className={FIELD_SURFACE}
              />
            </div>
            <div>
              <label className="block text-sm text-muted-foreground mb-1">
                Traffic split: {Math.round(trafficSplit * 100)}%
              </label>
              <input
                type="range"
                min={0.01}
                max={0.5}
                step={0.01}
                value={trafficSplit}
                onChange={(e) => setTrafficSplit(parseFloat(e.target.value))}
                className="w-full accent-primary"
              />
            </div>
            <div>
              <label className="block text-sm text-muted-foreground mb-1">
                Significance threshold: {significance.toFixed(3)}
              </label>
              <input
                type="range"
                min={0.01}
                max={0.2}
                step={0.005}
                value={significance}
                onChange={(e) => setSignificance(parseFloat(e.target.value))}
                className="w-full accent-primary"
              />
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={submitCreate}
              disabled={!canCreate || create.isPending}
              className="bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
            >
              {create.isPending ? (
                <ArrowPathIcon className="w-5 h-5 animate-spin" />
              ) : (
                <PlusIcon className="w-5 h-5" />
              )}
              Create
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="text-sm text-muted-foreground hover:text-foreground px-4"
            >
              Cancel
            </button>
          </div>
          {create.isError && <p className="text-sm text-danger">Could not create experiment.</p>}
        </Card>
      )}

      <Card className="p-6">
        <header className="mb-4 flex items-center justify-between">
          <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
            All experiments
          </h2>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-muted/40 border border-border rounded-lg px-2 py-1 text-xs"
          >
            <option value="" className="bg-card">
              All statuses
            </option>
            <option value="draft" className="bg-card">
              Draft
            </option>
            <option value="running" className="bg-card">
              Running
            </option>
            <option value="stopped" className="bg-card">
              Stopped
            </option>
            <option value="completed" className="bg-card">
              Completed
            </option>
          </select>
        </header>
        {experimentsQuery.isError ? (
          <p className="text-sm text-danger">Could not load experiments.</p>
        ) : !experimentsQuery.isLoading && experiments.length === 0 ? (
          <p className="text-sm text-muted-foreground">No experiments yet. Create one above.</p>
        ) : (
          <DataTable<Experiment>
            data={experiments}
            columns={columns}
            loading={experimentsQuery.isLoading}
            rowKey={(e) => e.id}
            ariaLabel="Model A/B testing experiments"
          />
        )}
      </Card>
    </div>
  );
}
