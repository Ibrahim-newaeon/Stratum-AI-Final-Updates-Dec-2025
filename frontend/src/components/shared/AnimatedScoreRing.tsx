/**
 * AnimatedScoreRing - SVG circular score indicator
 *
 * Animated ring that fills based on score with color-coded status.
 * Used in KG Revenue Attribution, Signal Quality displays.
 */

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

type RingStatus = 'good' | 'warning' | 'critical';
type RingSize = 'sm' | 'md' | 'lg';

interface AnimatedScoreRingProps {
  score: number;
  maxScore?: number;
  status?: RingStatus;
  label?: string;
  size?: RingSize;
  className?: string;
}

const statusColors: Record<RingStatus, { stroke: string; text: string }> = {
  good: { stroke: '#34c759', text: 'text-green-500' },
  warning: { stroke: '#f59e0b', text: 'text-amber-500' },
  critical: { stroke: '#ef4444', text: 'text-red-500' },
};

const sizeConfig: Record<RingSize, { width: number; strokeWidth: number; fontSize: string }> = {
  sm: { width: 64, strokeWidth: 4, fontSize: 'text-sm' },
  md: { width: 96, strokeWidth: 6, fontSize: 'text-xl' },
  lg: { width: 128, strokeWidth: 8, fontSize: 'text-3xl' },
};

export function AnimatedScoreRing({
  score,
  maxScore = 100,
  status = 'good',
  label,
  size = 'md',
  className,
}: AnimatedScoreRingProps) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const config = sizeConfig[size];
  const colors = statusColors[status];

  const radius = (config.width - config.strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const percentage = Math.min(animatedScore / maxScore, 1);
  const dashOffset = circumference * (1 - percentage);

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedScore(score), 100);
    return () => clearTimeout(timer);
  }, [score]);

  return (
    <div className={cn('flex flex-col items-center gap-1', className)}>
      <div className="relative" style={{ width: config.width, height: config.width }}>
        <svg
          width={config.width}
          height={config.width}
          viewBox={`0 0 ${config.width} ${config.width}`}
          className="-rotate-90"
        >
          {/* Background circle */}
          <circle
            cx={config.width / 2}
            cy={config.width / 2}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth={config.strokeWidth}
          />
          {/* Animated progress circle */}
          <circle
            cx={config.width / 2}
            cy={config.width / 2}
            r={radius}
            fill="none"
            stroke={colors.stroke}
            strokeWidth={config.strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            style={{ transition: 'stroke-dashoffset 1s ease-out' }}
          />
        </svg>
        {/* Score text in center */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={cn('font-bold', config.fontSize, colors.text)}>
            {Math.round(animatedScore)}
          </span>
        </div>
      </div>
      {label && <span className="text-xs text-muted-foreground">{label}</span>}
    </div>
  );
}

export default AnimatedScoreRing;
