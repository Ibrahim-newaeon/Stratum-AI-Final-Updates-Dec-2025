'use client';

import * as React from 'react';
import * as ProgressPrimitive from '@radix-ui/react-progress';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

// Progress variants
const progressVariants = cva('relative w-full overflow-hidden rounded-full', {
  variants: {
    variant: {
      default: 'bg-primary/20',
      secondary: 'bg-secondary',
      success: 'bg-success/20',
      warning: 'bg-warning/20',
      destructive: 'bg-destructive/20',
      info: 'bg-info/20',
      gradient: 'bg-muted',
    },
    size: {
      default: 'h-2',
      sm: 'h-1',
      md: 'h-3',
      lg: 'h-4',
      xl: 'h-6',
    },
  },
  defaultVariants: {
    variant: 'default',
    size: 'default',
  },
});

// Indicator variants
const indicatorVariants = cva('h-full w-full flex-1 transition-all', {
  variants: {
    variant: {
      default: 'bg-primary',
      secondary: 'bg-secondary-foreground',
      success: 'bg-success',
      warning: 'bg-warning',
      destructive: 'bg-destructive',
      info: 'bg-info',
      gradient: 'bg-gradient-to-r from-primary to-cyan-500',
    },
    animated: {
      true: 'animate-pulse',
      false: '',
    },
  },
  defaultVariants: {
    variant: 'default',
    animated: false,
  },
});

export interface ProgressProps
  extends React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root>,
    VariantProps<typeof progressVariants> {
  showValue?: boolean;
  indicatorClassName?: string;
  animated?: boolean;
  striped?: boolean;
  label?: string;
}

const Progress = React.forwardRef<React.ElementRef<typeof ProgressPrimitive.Root>, ProgressProps>(
  (
    {
      className,
      value,
      variant,
      size,
      showValue = false,
      indicatorClassName,
      animated = false,
      striped = false,
      label,
      ...props
    },
    ref
  ) => {
    const percentage = value ?? 0;

    return (
      <div className="w-full">
        {/* Label and value display */}
        {(label || showValue) && (
          <div className="flex items-center justify-between mb-1.5">
            {label && <span className="text-sm font-medium text-foreground">{label}</span>}
            {showValue && (
              <span className="text-sm text-muted-foreground">{Math.round(percentage)}%</span>
            )}
          </div>
        )}

        <ProgressPrimitive.Root
          ref={ref}
          className={cn(progressVariants({ variant, size }), className)}
          value={percentage}
          {...props}
        >
          <ProgressPrimitive.Indicator
            className={cn(
              indicatorVariants({ variant, animated }),
              striped && 'bg-stripes',
              indicatorClassName
            )}
            style={{ transform: `translateX(-${100 - percentage}%)` }}
          />
        </ProgressPrimitive.Root>
      </div>
    );
  }
);
Progress.displayName = ProgressPrimitive.Root.displayName;

// Circular Progress component
export interface CircularProgressProps {
  value?: number;
  size?: number;
  strokeWidth?: number;
  variant?: 'default' | 'success' | 'warning' | 'destructive' | 'info';
  showValue?: boolean;
  className?: string;
  children?: React.ReactNode;
}

const CircularProgress = React.forwardRef<SVGSVGElement, CircularProgressProps>(
  (
    {
      value = 0,
      size = 48,
      strokeWidth = 4,
      variant = 'default',
      showValue = false,
      className,
      children,
    },
    ref
  ) => {
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (value / 100) * circumference;

    const colorMap = {
      default: 'stroke-primary',
      success: 'stroke-success',
      warning: 'stroke-warning',
      destructive: 'stroke-destructive',
      info: 'stroke-info',
    };

    return (
      <div className={cn('relative inline-flex', className)}>
        <svg
          ref={ref}
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="transform -rotate-90"
        >
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            className="stroke-muted"
            strokeWidth={strokeWidth}
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            className={cn(colorMap[variant], 'transition-all duration-300')}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        {/* Center content */}
        {(showValue || children) && (
          <div className="absolute inset-0 flex items-center justify-center">
            {children || <span className="text-xs font-medium">{Math.round(value)}%</span>}
          </div>
        )}
      </div>
    );
  }
);
CircularProgress.displayName = 'CircularProgress';

// Progress steps component
export interface ProgressStep {
  label: string;
  description?: string;
  completed?: boolean;
  current?: boolean;
  error?: boolean;
}

export interface ProgressStepsProps {
  steps: ProgressStep[];
  orientation?: 'horizontal' | 'vertical';
  className?: string;
}

const ProgressSteps = React.forwardRef<HTMLDivElement, ProgressStepsProps>(
  ({ steps, orientation = 'horizontal', className }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          orientation === 'horizontal'
            ? 'flex items-center justify-between'
            : 'flex flex-col space-y-4',
          className
        )}
        role="list"
        aria-label="Progress steps"
      >
        {steps.map((step, index) => {
          const isLast = index === steps.length - 1;
          const status = step.error
            ? 'error'
            : step.completed
              ? 'completed'
              : step.current
                ? 'current'
                : 'pending';

          return (
            <div
              key={index}
              className={cn(
                'flex items-center',
                orientation === 'horizontal' && !isLast && 'flex-1'
              )}
              role="listitem"
            >
              {/* Step indicator */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    'flex h-8 w-8 items-center justify-center rounded-full border-2 text-sm font-medium transition-colors',
                    status === 'completed' && 'border-success bg-success text-white',
                    status === 'current' && 'border-primary bg-primary text-primary-foreground',
                    status === 'error' && 'border-destructive bg-destructive text-white',
                    status === 'pending' &&
                      'border-muted-foreground/30 bg-background text-muted-foreground'
                  )}
                  aria-current={step.current ? 'step' : undefined}
                >
                  {status === 'completed' ? (
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  ) : status === 'error' ? (
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  ) : (
                    index + 1
                  )}
                </div>
                {/* Label */}
                <div className="mt-2 text-center">
                  <p
                    className={cn(
                      'text-sm font-medium',
                      (status === 'completed' || status === 'current') && 'text-foreground',
                      status === 'error' && 'text-destructive',
                      status === 'pending' && 'text-muted-foreground'
                    )}
                  >
                    {step.label}
                  </p>
                  {step.description && (
                    <p className="text-xs text-muted-foreground mt-0.5">{step.description}</p>
                  )}
                </div>
              </div>

              {/* Connector line */}
              {!isLast && orientation === 'horizontal' && (
                <div
                  className={cn(
                    'mx-4 h-0.5 flex-1 rounded',
                    step.completed ? 'bg-success' : 'bg-muted'
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
    );
  }
);
ProgressSteps.displayName = 'ProgressSteps';

export { Progress, CircularProgress, ProgressSteps };
