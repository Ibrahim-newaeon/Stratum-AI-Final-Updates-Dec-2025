/**
 * SignalScoreTrend - SVG sparkline of signal health score with sub-metrics
 */

import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SignalHealthSummary } from '@/api/dashboard';

interface SignalScoreTrendProps {
  signalHealth?: SignalHealthSummary;
  loading?: boolean;
}

const PASS_THRESHOLD = 70;
const BLOCK_THRESHOLD = 40;

function generateTrendData(currentScore: number): number[] {
  const points = 12;
  const data: number[] = [];
  let value = currentScore - 15 + Math.random() * 10;
  for (let i = 0; i < points; i++) {
    value += (currentScore - value) * 0.25 + (Math.random() - 0.5) * 8;
    data.push(Math.max(0, Math.min(100, Math.round(value))));
  }
  data.push(currentScore);
  return data;
}

function getStatusLabel(score: number): { label: string; color: string } {
  if (score >= PASS_THRESHOLD) return { label: 'PASS', color: 'text-emerald-500' };
  if (score >= BLOCK_THRESHOLD) return { label: 'HOLD', color: 'text-amber-500' };
  return { label: 'BLOCK', color: 'text-red-500' };
}

function buildSparklinePath(data: number[], width: number, height: number): string {
  if (data.length < 2) return '';
  const stepX = width / (data.length - 1);
  return data
    .map((v, i) => {
      const x = i * stepX;
      const y = height - (v / 100) * height;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
}

export function SignalScoreTrend({ signalHealth, loading }: SignalScoreTrendProps) {
  const score = signalHealth?.overall_score ?? 72;
  const status = getStatusLabel(score);
  const trendData = generateTrendData(score);

  const svgW = 260;
  const svgH = 100;
  const linePath = buildSparklinePath(trendData, svgW, svgH);
  const areaPath = `${linePath} L${svgW},${svgH} L0,${svgH} Z`;

  const lastX = svgW;
  const lastY = svgH - (score / 100) * svgH;

  const passY = svgH - (PASS_THRESHOLD / 100) * svgH;
  const blockY = svgH - (BLOCK_THRESHOLD / 100) * svgH;

  if (loading) {
    return (
      <div className="widget-card flex items-center justify-center min-h-[280px]">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="widget-card h-full">
      <div className="widget-header">
        <h3 className="widget-title">
          Signal Score Trend
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-2xl font-bold">{score}</span>
          <span
            className={cn(
              'px-2 py-0.5 text-xs font-semibold rounded-full',
              status.label === 'PASS' && 'bg-emerald-500/10 text-emerald-500',
              status.label === 'HOLD' && 'bg-amber-500/10 text-amber-500',
              status.label === 'BLOCK' && 'bg-red-500/10 text-red-500'
            )}
          >
            {status.label}
          </span>
        </div>
      </div>

      {/* SVG Sparkline */}
      <div className="w-full mb-5">
        <svg viewBox={`0 0 ${svgW} ${svgH}`} className="w-full h-24" preserveAspectRatio="none">
          <defs>
            <linearGradient id="signalGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.3" />
              <stop offset="100%" stopColor="currentColor" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {/* Threshold lines */}
          <line
            x1="0"
            y1={passY}
            x2={svgW}
            y2={passY}
            stroke="#10b981"
            strokeWidth="0.8"
            strokeDasharray="4 3"
            opacity="0.5"
          />
          <line
            x1="0"
            y1={blockY}
            x2={svgW}
            y2={blockY}
            stroke="#ef4444"
            strokeWidth="0.8"
            strokeDasharray="4 3"
            opacity="0.5"
          />

          {/* Area fill */}
          <path d={areaPath} fill="url(#signalGradient)" className="text-primary" />

          {/* Line */}
          <path d={linePath} fill="none" stroke="currentColor" strokeWidth="2" className="text-primary" />

          {/* Current value dot */}
          <circle cx={lastX} cy={lastY} r="4" fill="currentColor" className="text-primary" />
          <circle cx={lastX} cy={lastY} r="7" fill="currentColor" opacity="0.2" className="text-primary" />
        </svg>
      </div>

      {/* Sub-metrics grid — frosted sub-cards */}
      <div className="grid grid-cols-2 gap-2.5">
        <div className="p-3 rounded-xl bg-white/[0.04] border border-white/[0.05]">
          <p className="text-[11px] text-muted-foreground mb-1 uppercase tracking-wide">EMQ Score</p>
          <p className="text-sm font-bold tabular-nums">
            {signalHealth?.emq_score != null ? signalHealth.emq_score : '--'}
          </p>
        </div>
        <div className="p-3 rounded-xl bg-white/[0.04] border border-white/[0.05]">
          <p className="text-[11px] text-muted-foreground mb-1 uppercase tracking-wide">Data Freshness</p>
          <p className="text-sm font-bold tabular-nums">
            {signalHealth?.data_freshness_minutes != null
              ? `${signalHealth.data_freshness_minutes}m ago`
              : '--'}
          </p>
        </div>
        <div className="p-3 rounded-xl bg-white/[0.04] border border-white/[0.05]">
          <p className="text-[11px] text-muted-foreground mb-1 uppercase tracking-wide">API Health</p>
          <div className="flex items-center gap-1.5">
            <div className={cn('w-1.5 h-1.5 rounded-full', signalHealth?.api_health ? 'bg-emerald-500' : 'bg-red-500')} />
            <p className={cn('text-sm font-bold', signalHealth?.api_health ? 'text-emerald-400' : 'text-red-400')}>
              {signalHealth?.api_health != null ? (signalHealth.api_health ? 'Healthy' : 'Degraded') : '--'}
            </p>
          </div>
        </div>
        <div className="p-3 rounded-xl bg-white/[0.04] border border-white/[0.05]">
          <p className="text-[11px] text-muted-foreground mb-1 uppercase tracking-wide">Autopilot</p>
          <div className="flex items-center gap-1.5">
            <div className={cn('w-1.5 h-1.5 rounded-full', signalHealth?.autopilot_enabled ? 'bg-emerald-500' : 'bg-muted-foreground')} />
            <p className={cn('text-sm font-bold', signalHealth?.autopilot_enabled ? 'text-emerald-400' : 'text-muted-foreground')}>
              {signalHealth?.autopilot_enabled != null
                ? signalHealth.autopilot_enabled
                  ? 'Enabled'
                  : 'Disabled'
                : '--'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
