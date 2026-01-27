/**
 * Error Boundary Component
 * Catches JavaScript errors in child components and displays fallback UI
 * Integrates with Sentry for error reporting when available
 */

import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, ChevronDown, ChevronUp, Copy, RefreshCw } from 'lucide-react';
import * as Sentry from '@sentry/react';
import { cn } from '@/lib/utils';

// Generate a unique error ID for tracking
function generateErrorId(): string {
  return `ERR-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 7)}`.toUpperCase();
}

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  className?: string;
  /** Show detailed error info (auto-enabled in development) */
  showDetails?: boolean;
  /** Custom error message */
  message?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId: string | null;
  showStack: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    errorId: null,
    showStack: false,
  };

  public static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error, errorId: generateErrorId() };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // Update state with error info
    this.setState({ errorInfo });

    // Report to Sentry if available
    if (typeof Sentry !== 'undefined' && Sentry.captureException) {
      Sentry.captureException(error, {
        extra: {
          componentStack: errorInfo.componentStack,
          errorId: this.state.errorId,
        },
      });
    }

    // Call custom error handler
    this.props.onError?.(error, errorInfo);
  }

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
      showStack: false,
    });
  };

  private toggleStack = () => {
    this.setState((prev) => ({ showStack: !prev.showStack }));
  };

  private copyErrorInfo = () => {
    const { error, errorInfo, errorId } = this.state;
    const errorText = `Error ID: ${errorId}\nMessage: ${error?.message}\nStack: ${error?.stack}\nComponent Stack: ${errorInfo?.componentStack}`;
    navigator.clipboard.writeText(errorText);
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { error, errorId, showStack, errorInfo } = this.state;
      const showDetails = this.props.showDetails ?? import.meta.env.DEV;

      return (
        <div
          className={cn(
            'flex flex-col items-center justify-center p-8 rounded-xl border bg-card',
            this.props.className
          )}
          role="alert"
          aria-live="assertive"
        >
          <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
            <AlertTriangle className="w-6 h-6 text-destructive" aria-hidden="true" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            {this.props.message || 'Something went wrong'}
          </h3>
          <p className="text-sm text-muted-foreground text-center mb-2 max-w-sm">
            We encountered an error while rendering this component. Please try again.
          </p>

          {/* Error ID for support */}
          {errorId && (
            <p className="text-xs text-muted-foreground mb-4">
              Error ID: <code className="bg-muted px-1 py-0.5 rounded">{errorId}</code>
            </p>
          )}

          <div className="flex items-center gap-2 mb-4">
            <button
              onClick={this.handleRetry}
              className="inline-flex items-center px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <RefreshCw className="w-4 h-4 mr-2" aria-hidden="true" />
              Try Again
            </button>

            {showDetails && (
              <button
                onClick={this.copyErrorInfo}
                className="inline-flex items-center px-3 py-2 rounded-lg border bg-background hover:bg-muted transition-colors text-sm"
                title="Copy error details"
              >
                <Copy className="w-4 h-4" aria-hidden="true" />
                <span className="sr-only">Copy error details</span>
              </button>
            )}
          </div>

          {/* Expandable error details (dev mode) */}
          {showDetails && error && (
            <div className="w-full max-w-lg">
              <button
                onClick={this.toggleStack}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors mb-2"
              >
                {showStack ? (
                  <ChevronUp className="w-3 h-3" />
                ) : (
                  <ChevronDown className="w-3 h-3" />
                )}
                {showStack ? 'Hide' : 'Show'} error details
              </button>

              {showStack && (
                <div className="bg-muted/50 rounded-lg p-3 text-xs font-mono overflow-auto max-h-48">
                  <p className="text-destructive mb-2">{error.message}</p>
                  {error.stack && (
                    <pre className="text-muted-foreground whitespace-pre-wrap">{error.stack}</pre>
                  )}
                  {errorInfo?.componentStack && (
                    <>
                      <p className="text-foreground mt-2 mb-1">Component Stack:</p>
                      <pre className="text-muted-foreground whitespace-pre-wrap">
                        {errorInfo.componentStack}
                      </pre>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

// Chart-specific error fallback
export function ChartErrorFallback({
  onRetry,
  height = 300,
}: {
  onRetry?: () => void;
  height?: number;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center rounded-xl border bg-card"
      style={{ height }}
      role="alert"
      aria-label="Chart failed to load"
    >
      <div className="w-10 h-10 rounded-full bg-amber-500/10 flex items-center justify-center mb-3">
        <AlertTriangle className="w-5 h-5 text-amber-500" aria-hidden="true" />
      </div>
      <p className="text-sm font-medium text-foreground mb-1">Chart unavailable</p>
      <p className="text-xs text-muted-foreground mb-3">Failed to render chart data</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs text-primary hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 rounded"
        >
          Retry
        </button>
      )}
    </div>
  );
}

// Widget error fallback
export function WidgetErrorFallback({ title, onRetry }: { title?: string; onRetry?: () => void }) {
  return (
    <div className="rounded-xl border bg-card p-6" role="alert">
      {title && <h3 className="text-lg font-semibold text-foreground mb-4">{title}</h3>}
      <div className="flex flex-col items-center justify-center py-8">
        <div className="w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center mb-3">
          <AlertTriangle className="w-5 h-5 text-destructive" aria-hidden="true" />
        </div>
        <p className="text-sm text-muted-foreground text-center">Unable to load this widget</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-3 text-sm text-primary hover:underline inline-flex items-center focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 rounded"
          >
            <RefreshCw className="w-3 h-3 mr-1" aria-hidden="true" />
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

export default ErrorBoundary;
