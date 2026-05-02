/**
 * RecentAutopilot — last 24h of autopilot decisions, always present.
 *
 * Anchors the bottom of the Overview. Even when alerts = 0 it gives the
 * user proof the system is doing something. Click a row to drill into
 * the autopilot detail (handler provided by parent).
 */

import { useMemo } from 'react';
import { Card } from '@/components/primitives/Card';
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable';
import { StatusPill } from '@/components/primitives/StatusPill';
import { cn } from '@/lib/utils';
import type { AutopilotDecisionRow } from './types';

interface RecentAutopilotProps {
  rows: AutopilotDecisionRow[];
  loading?: boolean;
  error?: string;
  onRowClick?: (row: AutopilotDecisionRow) => void;
}

const ACTION_LABEL: Record<AutopilotDecisionRow['action'], string> = {
  budget_increase: 'Budget +',
  budget_decrease: 'Budget −',
  pause: 'Pause',
  enable: 'Enable',
  bid_adjust: 'Bid adjust',
};

const RESULT_VARIANT: Record<
  AutopilotDecisionRow['result'],
  'healthy' | 'degraded' | 'unhealthy' | 'neutral'
> = {
  executed: 'healthy',
  pending: 'neutral',
  held: 'degraded',
  blocked: 'unhealthy',
};

export function RecentAutopilot({ rows, loading, error, onRowClick }: RecentAutopilotProps) {
  const columns: DataTableColumn<AutopilotDecisionRow>[] = useMemo(
    () => [
      {
        id: 'time',
        header: 'Time',
        cell: (r) => (
          <span className="text-meta text-muted-foreground font-mono tabular-nums">{r.time}</span>
        ),
        className: 'w-20',
      },
      {
        id: 'campaign',
        header: 'Campaign',
        cell: (r) => <span className="text-foreground">{r.campaign}</span>,
      },
      {
        id: 'action',
        header: 'Action',
        cell: (r) => (
          <span className="text-meta text-muted-foreground font-mono uppercase tracking-[0.06em]">
            {ACTION_LABEL[r.action]}
          </span>
        ),
        hideOnMobile: true,
      },
      {
        id: 'result',
        header: 'Result',
        cell: (r) => (
          <StatusPill variant={RESULT_VARIANT[r.result]} size="sm">
            {r.result}
          </StatusPill>
        ),
        className: 'w-32',
      },
      {
        id: 'trust',
        header: 'Trust',
        cell: (r) => (
          <span
            className={cn(
              'tabular-nums font-mono',
              r.trust >= 70 ? 'text-success' : r.trust >= 40 ? 'text-warning' : 'text-danger'
            )}
          >
            {r.trust}
          </span>
        ),
        sortable: true,
        sortAccessor: (r) => r.trust,
        className: 'w-20',
      },
    ],
    []
  );

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-h3 font-medium tracking-tight text-foreground">
          Recent autopilot decisions
        </h3>
        <span className="text-meta uppercase tracking-[0.06em] font-mono text-muted-foreground">
          Last 24h
        </span>
      </div>
      <DataTable
        data={rows}
        columns={columns}
        rowKey={(r) => r.id}
        loading={loading}
        loadingRows={5}
        emptyMessage="No autopilot decisions in the last 24 hours."
        error={error}
        ariaLabel="Recent autopilot decisions"
        onRowClick={onRowClick}
      />
    </Card>
  );
}

export default RecentAutopilot;
