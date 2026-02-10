/**
 * Trust Gate Indicator Component
 * Fixed position status indicator showing signal health score
 * Part of Stratum AI Dashboard Theme (NN/g Glassmorphism Compliant)
 */

import { memo, useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

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
      color: style.getPropertyValue('--teal').trim() || '#00c7be',
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

export const TrustGateIndicator = memo(function TrustGateIndicator({
  className,
}: TrustGateIndicatorProps) {
  // Simulated signal health - in production this would come from the trust engine API
  const [signalHealth, setSignalHealth] = useState(85);

  // Simulate periodic health updates
  useEffect(() => {
    const interval = setInterval(() => {
      // Slight variation to show the indicator is live
      setSignalHealth((prev) => {
        const variation = Math.random() * 6 - 3; // -3 to +3
        const newValue = Math.round(prev + variation);
        return Math.max(0, Math.min(100, newValue));
      });
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const state = getTrustState(signalHealth);
  const isHealthy = state.status === 'PASS';

  return (
    <div
      className={cn(
        'fixed bottom-6 left-6 z-50',
        'flex items-center gap-3 px-4 py-3 rounded-2xl',
        'transition-all duration-300',
        className
      )}
      style={{
        background: 'var(--bg-primary)',
        border: '2px solid var(--teal)',
        boxShadow: '0 0 20px var(--teal-glow), 0 8px 32px rgba(0, 0, 0, 0.3)',
      }}
      role="status"
      aria-label={`Trust Gate: ${state.status}, Signal Health: ${state.score}%`}
    >
      {/* Pulsing status dot */}
      <div className="relative flex items-center justify-center">
        <div
          className={cn(
            'h-3 w-3 rounded-full',
            isHealthy && 'animate-status-pulse'
          )}
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
      <div className="flex flex-col">
        <div className="flex items-center gap-2">
          <span
            className="text-sm font-semibold font-mono"
            style={{ color: state.color }}
          >
            {state.score}
          </span>
          <span
            className="text-xs font-medium px-1.5 py-0.5 rounded"
            style={{
              backgroundColor: state.bgColor,
              color: state.color,
            }}
          >
            {state.status}
          </span>
        </div>
        <span
          className="text-xs"
          style={{ color: 'rgba(255, 255, 255, 0.5)' }}
        >
          Signal Health
        </span>
      </div>
    </div>
  );
});

export default TrustGateIndicator;
