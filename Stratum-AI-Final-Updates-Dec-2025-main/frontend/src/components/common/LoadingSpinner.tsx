import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  label?: string;
}

const sizeClasses = {
  sm: 'w-4 h-4 border-2',
  md: 'w-8 h-8 border-2',
  lg: 'w-12 h-12 border-3',
  xl: 'w-16 h-16 border-4',
};

export function LoadingSpinner({
  size = 'md',
  className,
  label = 'Loading...',
}: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div
        className={cn(
          'animate-spin rounded-full border-primary border-t-transparent',
          sizeClasses[size],
          className
        )}
        role="status"
        aria-label={label}
      />
      {label && <span className="text-sm text-muted-foreground animate-pulse">{label}</span>}
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <LoadingSpinner size="lg" label="Loading page..." />
    </div>
  );
}

export function InlineLoader({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <LoadingSpinner size="sm" label="" />
      <span className="text-sm text-muted-foreground">Loading...</span>
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div
      className="rounded-xl border bg-card p-6 animate-pulse"
      role="status"
      aria-label="Loading content"
    >
      <span className="sr-only">Loading...</span>
      <div className="h-4 w-24 bg-muted rounded mb-4" aria-hidden="true" />
      <div className="h-8 w-32 bg-muted rounded mb-2" aria-hidden="true" />
      <div className="h-3 w-20 bg-muted rounded" aria-hidden="true" />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div
      className="rounded-xl border bg-card overflow-hidden animate-pulse"
      role="status"
      aria-label="Loading table data"
    >
      <span className="sr-only">Loading table...</span>
      <div className="bg-muted/50 p-4 border-b" aria-hidden="true">
        <div className="flex gap-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-4 flex-1 bg-muted rounded" />
          ))}
        </div>
      </div>
      <div className="divide-y" aria-hidden="true">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="p-4 flex gap-4">
            {[1, 2, 3, 4, 5].map((j) => (
              <div key={j} className="h-4 flex-1 bg-muted rounded" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export default LoadingSpinner;
