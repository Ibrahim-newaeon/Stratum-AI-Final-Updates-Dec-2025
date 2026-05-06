/**
 * Trust Gate Indicator Component
 * Fixed position status indicator showing signal health score
 * Part of Stratum AI Dashboard Theme (NN/g Glassmorphism Compliant)
 *
 * Now powered by the live simulation engine for realistic
 * platform-aware signal health with weighted components.
 */

import { memo, useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getSignalHealth } from '@/lib/liveSimulation';
import type { SignalHealthDetail } from '@/lib/liveSimulation';

interface TrustGateIndicatorProps {
  className?: string;
}

// Trust gate thresholds from CLAUDE.md
const HEALTHY_THRESHOLD = 70;
const DEGRADED_THRESHOLD = 40;

type TrustStatus = 'PASS' | 'HOLD' | 'BLOCK';

interface TrustState {
  score: number;
  status: TrustStatus;
  color: string;
  bgColor: string;
}

function getTrustState(score: number): TrustState {
  const root = document.documentElement;
  const style = getComputedStyle(root);

  if (score >= HEALTHY_THRESHOLD) {
    return {
      score,
      status: 'PASS',
      color: style.getPropertyValue('--teal').trim() || 'var(--landing-accent-cyan)',
      bgColor: style.getPropertyValue('--teal-light').trim() || 'rgba(0, 199, 190, 0.15)',
    };
  } else if (score >= DEGRADED_THRESHOLD) {
    return {
      score,
      status: 'HOLD',
      color: style.getPropertyValue('--status-warning').trim() || '#f59e0b',
      bgColor: style.getPropertyValue('--status-warning-bg').trim() || 'rgba(245, 158, 11, 0.15)',
    };
  } else {
    return {
      score,
      status: 'BLOCK',
      color: style.getPropertyValue('--coral').trim() || '#ff6b6b',
      bgColor: 'rgba(255, 107, 107, 0.15)',
    };
  }
}

const DISMISS_STORAGE_KEY = 'stratum-trust-gate-dismissed';

export const TrustGateIndicator = memo(function TrustGateIndicator({
  className,
}: TrustGateIndicatorProps) {
  const [signalHealth, setSignalHealth] = useState(85);
  const [healthDetail, setHealthDetail] = useState<SignalHealthDetail | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [dismissed, setDismissed] = useState(() => {
    try {
      return sessionStorage.getItem(DISMISS_STORAGE_KEY) === '1';
    } catch {
      return false;
    }
  });

  // Use the simulation engine for realistic health updates
  useEffect(() => {
    const updateHealth = () => {
      const detail = getSignalHealth();
      setSignalHealth(detail.overall);
      setHealthDetail(detail);
    };

    updateHealth();

    // Update every 5 seconds for live feel
    const interval = setInterval(updateHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDismissed(true);
    try {
      sessionStorage.setItem(DISMISS_STORAGE_KEY, '1');
    } catch {
      // ignore
    }
  };

  if (dismissed) return null;

  const state = getTrustState(signalHealth);
  const isHealthy = state.status === 'PASS';

  return (
    <div
      className={cn(
        // Bottom-right corner, top of the floating-widget stack:
        //   bottom-4   OnboardingChatButton  (56×56)
        //   bottom-20  CopilotChat button    (56×56)
        //   bottom-36  FeedbackWidget button (48×48)
        //   bottom-52  TrustGateIndicator    ← here
        // Each row leaves a ~16-24px gap above the row below.
        'fixed bottom-52 right-6 z-50',
        'flex flex-col gap-0 rounded-2xl',
        'transition-colors duration-300',
        // Solid card surface — semantic token, themed correctly in
        // dark + light. The previous `var(--bg-primary)` resolved to
        // the page background which read as transparent over the
        // dashboard surface.
        'bg-card',
        className
      )}
      style={{
        border: `2px solid ${state.color}`,
        boxShadow: `0 0 20px ${state.color}40, 0 8px 32px rgba(0, 0, 0, 0.3)`,
      }}
    >
      {/* Close button — dismisses for the rest of the session */}
      <button
        type="button"
        onClick={handleDismiss}
        aria-label="Dismiss trust gate indicator"
        className={cn(
          'absolute -top-2 -right-2 z-10',
          'w-6 h-6 rounded-full bg-card border-2 flex items-center justify-center',
          'text-muted-foreground hover:text-foreground transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
        )}
        style={{ borderColor: state.color }}
      >
        <X className="w-3 h-3" />
      </button>

      {/* Expanded Detail Panel */}
      {expanded && healthDetail && (
        <div className="px-4 pt-3 pb-2 space-y-2 min-w-56">
          <div
            className="text-xs font-semibold uppercase tracking-wider"
            style={{ color: 'rgba(255,255,255,0.4)' }}
          >
            Signal Components
          </div>
          {[
            { label: 'EMQ Score', value: healthDetail.emq, weight: '35%' },
            { label: 'API Health', value: healthDetail.apiHealth, weight: '25%' },
            { label: 'Event Loss', value: healthDetail.eventLoss, weight: '20%' },
            { label: 'Platform Stability', value: healthDetail.platformStability, weight: '10%' },
            { label: 'Data Quality', value: healthDetail.dataQuality, weight: '10%' },
          ].map((comp) => (
            <div key={comp.label} className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 min-w-0">
                <div
                  className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                  style={{
                    backgroundColor:
                      comp.value >= 70
                        ? 'var(--landing-accent-cyan)'
                        : comp.value >= 40
                          ? '#f59e0b'
                          : '#ff6b6b',
                  }}
                />
                <span className="text-xs truncate" style={{ color: 'rgba(255,255,255,0.6)' }}>
                  {comp.label}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span
                  className="text-xs font-mono font-medium"
                  style={{
                    color:
                      comp.value >= 70
                        ? 'var(--landing-accent-cyan)'
                        : comp.value >= 40
                          ? '#f59e0b'
                          : '#ff6b6b',
                  }}
                >
                  {comp.value}
                </span>
                <span className="text-[10px]" style={{ color: 'rgba(255,255,255,0.25)' }}>
                  ({comp.weight})
                </span>
              </div>
            </div>
          ))}
          <div
            className="pt-2 mt-1 text-xs"
            style={{
              borderTop: '1px solid rgba(255,255,255,0.08)',
              color: 'rgba(255,255,255,0.35)',
            }}
          >
            Autopilot:{' '}
            {state.status === 'PASS'
              ? 'Enabled'
              : state.status === 'HOLD'
                ? 'Alert Only'
                : 'Manual Required'}
          </div>
        </div>
      )}

      {/* Main indicator (always visible) */}
      <button
        className={cn('flex items-center gap-3 px-4 py-3', expanded && 'border-t')}
        style={{
          borderColor: expanded ? 'rgba(255,255,255,0.08)' : 'transparent',
        }}
        onClick={() => setExpanded(!expanded)}
        role="status"
        aria-label={`Trust Gate: ${state.status}, Signal Health: ${state.score}%`}
      >
        {/* Pulsing status dot */}
        <div className="relative flex items-center justify-center">
          <div
            className={cn('h-3 w-3 rounded-full', isHealthy && 'animate-status-pulse')}
            style={{
              backgroundColor: state.color,
              boxShadow: `0 0 12px ${state.color}`,
            }}
          />
          {/* Outer ring for emphasis when healthy */}
          {isHealthy && (
            <div
              className="absolute inset-0 h-3 w-3 rounded-full animate-ping"
              style={{
                backgroundColor: state.color,
                opacity: 0.4,
                animationDuration: '2s',
              }}
            />
          )}
        </div>

        {/* Status info */}
        <div className="flex flex-col items-start">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold font-mono" style={{ color: state.color }}>
              {state.score}
            </span>
            <span
              className="text-xs font-bold px-2 py-0.5 rounded"
              style={{
                backgroundColor: state.color,
                color: '#000',
              }}
            >
              {state.status}
            </span>
          </div>
          <span className="text-xs" style={{ color: 'var(--landing-text-white-soft)' }}>
            Signal Health
          </span>
        </div>
      </button>
    </div>
  );
});

export default TrustGateIndicator;
