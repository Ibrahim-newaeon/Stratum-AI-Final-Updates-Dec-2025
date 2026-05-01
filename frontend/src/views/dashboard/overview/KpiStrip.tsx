/**
 * KpiStrip — 4 compact KPI cards across the top of the Overview.
 *
 * Real Stratum metrics, not LLM-playground placeholders:
 *   1. Trust Gate (gate decision + holds count)
 *   2. Signal Health (composite 0-100)
 *   3. ROAS (today)
 *   4. Pacing (today)
 *
 * The most-attention-needing card uses Card variant=glow for emphasis.
 */

import { Activity, TrendingUp, Target } from 'lucide-react';
import { KPI } from '@/components/primitives/KPI';
import { mockKpis } from './mockData';

interface KpiStripProps {
  loading?: boolean;
  error?: string;
}

export function KpiStrip({ loading, error }: KpiStripProps) {
  const k = mockKpis;

  // Decide which card gets the "glow" emphasis treatment — typically the
  // most-attention-needing surface. If trust gate is degraded or has holds,
  // it leads. Else signal health if degraded. Else ROAS.
  const trustNeedsAttention = k.trustGate.status !== 'pass' || k.trustGate.holds > 0;
  const signalNeedsAttention = k.signalHealth.score < 70;
  const trustEmphasis = trustNeedsAttention ? 'glow' : 'default';
  const signalEmphasis = !trustNeedsAttention && signalNeedsAttention ? 'glow' : 'default';

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <KPI
        label="Trust Gate"
        value={loading ? undefined : k.trustGate.status === 'pass' ? 'Pass' : 'Hold'}
        delta={
          k.trustGate.holds > 0
            ? { value: k.trustGate.holds, format: 'absolute', invert: true }
            : undefined
        }
        footnote={
          k.trustGate.holds > 0
            ? `${k.trustGate.holds} hold${k.trustGate.holds === 1 ? '' : 's'} active`
            : 'All automations clear'
        }
        status={{
          label: trustNeedsAttention ? 'Action needed' : 'Operational',
          variant: trustNeedsAttention ? 'degraded' : 'healthy',
          pulse: !trustNeedsAttention,
        }}
        emphasis={trustEmphasis}
        loading={loading}
        error={error}
      />

      <KPI
        label="Signal Health"
        value={loading ? undefined : k.signalHealth.score.toString()}
        delta={{ value: k.signalHealth.delta }}
        footnote="Composite EMQ + API + event-loss"
        icon={<Activity className="w-4 h-4" />}
        emphasis={signalEmphasis}
        loading={loading}
        error={error}
      />

      <KPI
        label="ROAS · today"
        value={loading ? undefined : `${k.roas.value.toFixed(1)}×`}
        delta={{ value: k.roas.delta, format: 'absolute' }}
        footnote="Spend-weighted across active accounts"
        icon={<TrendingUp className="w-4 h-4" />}
        loading={loading}
        error={error}
      />

      <KPI
        label="Pacing · today"
        value={loading ? undefined : `${k.pacing.onTrack}/${k.pacing.onTrack + k.pacing.breaches}`}
        delta={{ value: k.pacing.deltaPercent }}
        footnote={
          k.pacing.breaches > 0
            ? `${k.pacing.breaches} breach${k.pacing.breaches === 1 ? '' : 'es'} active`
            : 'On track across all targets'
        }
        icon={<Target className="w-4 h-4" />}
        loading={loading}
        error={error}
      />
    </div>
  );
}

export default KpiStrip;
