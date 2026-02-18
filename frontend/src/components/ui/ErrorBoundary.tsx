/**
 * Error Boundary Component
 * Catches JavaScript errors in child components and displays fallback UI
 */

import { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
  className?: string
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.props.onError?.(error, errorInfo)
  }

  private handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className={cn(
          'flex flex-col items-center justify-center p-8 rounded-xl border bg-card',
          this.props.className
        )}>
          <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
            <AlertTriangle className="w-6 h-6 text-destructive" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            Something went wrong
          </h3>
          <p className="text-sm text-muted-foreground text-center mb-4 max-w-sm">
            We encountered an error while rendering this component. Please try again.
          </p>
          <button
            onClick={this.handleRetry}
            className="inline-flex items-center px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Try Again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

// Chart-specific error fallback
export function ChartErrorFallback({
  onRetry,
  height = 300
}: {
  onRetry?: () => void
  height?: number
}) {
  return (
    <div
      className="flex flex-col items-center justify-center rounded-xl border bg-card"
      style={{ height }}
    >
      <div className="w-10 h-10 rounded-full bg-amber-500/10 flex items-center justify-center mb-3">
        <AlertTriangle className="w-5 h-5 text-amber-500" />
      </div>
      <p className="text-sm font-medium text-foreground mb-1">
        Chart unavailable
      </p>
      <p className="text-xs text-muted-foreground mb-3">
        Failed to render chart data
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs text-primary hover:underline"
        >
          Retry
        </button>
      )}
    </div>
  )
}

// Widget error fallback
export function WidgetErrorFallback({
  title,
  onRetry
}: {
  title?: string
  onRetry?: () => void
}) {
  return (
    <div className="rounded-xl border bg-card p-6">
      {title && (
        <h3 className="text-lg font-semibold text-foreground mb-4">{title}</h3>
      )}
      <div className="flex flex-col items-center justify-center py-8">
        <div className="w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center mb-3">
          <AlertTriangle className="w-5 h-5 text-destructive" />
        </div>
        <p className="text-sm text-muted-foreground text-center">
          Unable to load this widget
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-3 text-sm text-primary hover:underline inline-flex items-center"
          >
            <RefreshCw className="w-3 h-3 mr-1" />
            Retry
          </button>
        )}
      </div>
    </div>
  )
}

export default ErrorBoundary
