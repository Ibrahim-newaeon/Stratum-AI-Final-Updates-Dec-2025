import { useState, useRef, useEffect, ReactNode, useId, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { Info, HelpCircle, X, ExternalLink, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

type TooltipPosition = 'top' | 'bottom' | 'left' | 'right'

interface SmartTooltipProps {
  children: ReactNode
  content: ReactNode
  title?: string
  learnMoreUrl?: string
  position?: TooltipPosition
  trigger?: 'hover' | 'click'
  delay?: number
  className?: string
  showIcon?: boolean
  iconType?: 'info' | 'help'
  /** Show a "Got it" button instead of X for acknowledgment-style tooltips */
  showGotIt?: boolean
  /** Callback when user dismisses with "Got it" */
  onGotIt?: () => void
  /** Accessible label for the tooltip (used if content is not a string) */
  ariaLabel?: string
}

interface TooltipCoords {
  top: number
  left: number
}

export function SmartTooltip({
  children,
  content,
  title,
  learnMoreUrl,
  position = 'top',
  trigger = 'hover',
  delay = 200,
  className,
  showIcon = false,
  iconType = 'info',
  showGotIt = false,
  onGotIt,
  ariaLabel,
}: SmartTooltipProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [coords, setCoords] = useState<TooltipCoords>({ top: 0, left: 0 })
  const triggerRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Generate unique ID for accessibility
  const tooltipId = useId()
  const titleId = useId()

  const calculatePosition = () => {
    if (!triggerRef.current || !tooltipRef.current) return

    const triggerRect = triggerRef.current.getBoundingClientRect()
    const tooltipRect = tooltipRef.current.getBoundingClientRect()
    const padding = 8

    let top = 0
    let left = 0

    switch (position) {
      case 'top':
        top = triggerRect.top - tooltipRect.height - padding
        left = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2
        break
      case 'bottom':
        top = triggerRect.bottom + padding
        left = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2
        break
      case 'left':
        top = triggerRect.top + triggerRect.height / 2 - tooltipRect.height / 2
        left = triggerRect.left - tooltipRect.width - padding
        break
      case 'right':
        top = triggerRect.top + triggerRect.height / 2 - tooltipRect.height / 2
        left = triggerRect.right + padding
        break
    }

    // Keep tooltip within viewport
    const viewportWidth = window.innerWidth
    const viewportHeight = window.innerHeight

    if (left < padding) left = padding
    if (left + tooltipRect.width > viewportWidth - padding) {
      left = viewportWidth - tooltipRect.width - padding
    }
    if (top < padding) top = padding
    if (top + tooltipRect.height > viewportHeight - padding) {
      top = viewportHeight - tooltipRect.height - padding
    }

    setCoords({ top, left })
  }

  const showTooltip = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true)
    }, delay)
  }

  const hideTooltip = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    setIsVisible(false)
  }

  const handleTriggerClick = () => {
    if (trigger === 'click') {
      setIsVisible(!isVisible)
    }
  }

  const handleDismiss = useCallback(() => {
    setIsVisible(false)
    onGotIt?.()
  }, [onGotIt])

  // Handle Escape key to close tooltip
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && isVisible) {
      handleDismiss()
      triggerRef.current?.focus()
    }
  }, [isVisible, handleDismiss])

  useEffect(() => {
    if (isVisible) {
      calculatePosition()
      window.addEventListener('scroll', calculatePosition, true)
      window.addEventListener('resize', calculatePosition)
      document.addEventListener('keydown', handleKeyDown)
    }

    return () => {
      window.removeEventListener('scroll', calculatePosition, true)
      window.removeEventListener('resize', calculatePosition)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isVisible, handleKeyDown])

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [])

  // Close on outside click for click trigger
  useEffect(() => {
    if (trigger !== 'click' || !isVisible) return

    const handleClickOutside = (e: MouseEvent) => {
      if (
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node) &&
        tooltipRef.current &&
        !tooltipRef.current.contains(e.target as Node)
      ) {
        setIsVisible(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [trigger, isVisible])

  const Icon = iconType === 'help' ? HelpCircle : Info

  return (
    <>
      <div
        ref={triggerRef}
        className={cn('inline-flex items-center gap-1 cursor-pointer', className)}
        onMouseEnter={trigger === 'hover' ? showTooltip : undefined}
        onMouseLeave={trigger === 'hover' ? hideTooltip : undefined}
        onClick={handleTriggerClick}
        onKeyDown={(e) => {
          if (trigger === 'click' && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault()
            setIsVisible(!isVisible)
          }
        }}
        role="button"
        tabIndex={0}
        aria-describedby={isVisible ? tooltipId : undefined}
        aria-expanded={trigger === 'click' ? isVisible : undefined}
      >
        {children}
        {showIcon && (
          <Icon
            className="w-4 h-4 text-muted-foreground hover:text-foreground transition-colors"
            aria-hidden="true"
          />
        )}
      </div>

      {isVisible &&
        createPortal(
          <div
            ref={tooltipRef}
            id={tooltipId}
            role="tooltip"
            aria-label={ariaLabel}
            aria-labelledby={title ? titleId : undefined}
            className={cn(
              'fixed z-[9999] max-w-xs animate-in fade-in-0 zoom-in-95 duration-200',
              'bg-popover text-popover-foreground rounded-lg shadow-lg border'
            )}
            style={{
              top: coords.top,
              left: coords.left,
            }}
            onMouseEnter={trigger === 'hover' ? showTooltip : undefined}
            onMouseLeave={trigger === 'hover' ? hideTooltip : undefined}
          >
            <div className="p-3">
              {title && (
                <div className="flex items-center justify-between mb-2">
                  <h4 id={titleId} className="font-semibold text-sm">{title}</h4>
                  {trigger === 'click' && !showGotIt && (
                    <button
                      onClick={handleDismiss}
                      className="p-0.5 rounded hover:bg-muted"
                      aria-label="Close tooltip"
                    >
                      <X className="w-3.5 h-3.5" aria-hidden="true" />
                    </button>
                  )}
                </div>
              )}
              <div className="text-sm text-muted-foreground">{content}</div>
              {learnMoreUrl && (
                <a
                  href={learnMoreUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  Learn more
                  <ExternalLink className="w-3 h-3" aria-hidden="true" />
                </a>
              )}
              {showGotIt && (
                <button
                  onClick={handleDismiss}
                  className="mt-3 w-full py-1.5 px-3 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                  Got it
                </button>
              )}
            </div>
          </div>,
          document.body
        )}
    </>
  )
}

// Contextual help variant
interface ContextualHelpProps {
  term: string
  definition: string
  example?: string
  learnMoreUrl?: string
}

export function ContextualHelp({
  term,
  definition,
  example,
  learnMoreUrl,
}: ContextualHelpProps) {
  return (
    <SmartTooltip
      trigger="click"
      title={term}
      learnMoreUrl={learnMoreUrl}
      content={
        <div className="space-y-2">
          <p>{definition}</p>
          {example && (
            <div className="mt-2 p-2 rounded bg-muted text-xs">
              <span className="font-medium">Example:</span> {example}
            </div>
          )}
        </div>
      }
      showIcon
      iconType="help"
    >
      <span className="border-b border-dashed border-muted-foreground cursor-help">
        {term}
      </span>
    </SmartTooltip>
  )
}

// Metric explanation variant
interface MetricTooltipProps {
  metric: string
  value: string | number
  explanation: string
  trend?: 'up' | 'down' | 'neutral'
  benchmark?: string
}

export function MetricTooltip({
  metric,
  value,
  explanation,
  trend,
  benchmark,
}: MetricTooltipProps) {
  return (
    <SmartTooltip
      position="bottom"
      title={metric}
      content={
        <div className="space-y-2">
          <p>{explanation}</p>
          {benchmark && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground">Industry benchmark:</span>
              <span className="font-medium">{benchmark}</span>
            </div>
          )}
          {trend && (
            <div className="flex items-center gap-1 text-xs">
              <span
                className={cn(
                  trend === 'up' && 'text-green-500',
                  trend === 'down' && 'text-red-500',
                  trend === 'neutral' && 'text-muted-foreground'
                )}
              >
                {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
              </span>
              <span className="text-muted-foreground">
                {trend === 'up'
                  ? 'Above average'
                  : trend === 'down'
                  ? 'Below average'
                  : 'On par with average'}
              </span>
            </div>
          )}
        </div>
      }
      showIcon
      iconType="info"
    >
      <span className="font-semibold">{value}</span>
    </SmartTooltip>
  )
}

// Feature discovery tooltip
interface FeatureDiscoveryProps {
  feature: string
  description: string
  steps?: string[]
  onDismiss?: () => void
}

export function FeatureDiscovery({
  feature,
  description,
  steps,
  onDismiss,
}: FeatureDiscoveryProps) {
  const [dismissed, setDismissed] = useState(false)

  if (dismissed) return null

  return (
    <div className="relative p-4 rounded-lg border border-primary/30 bg-primary/5">
      <button
        onClick={() => {
          setDismissed(true)
          onDismiss?.()
        }}
        className="absolute top-2 right-2 p-1 rounded hover:bg-primary/10"
      >
        <X className="w-4 h-4" />
      </button>

      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-primary/20">
          <Sparkles className="w-5 h-5 text-primary" />
        </div>
        <div className="flex-1">
          <h4 className="font-semibold text-sm mb-1">{feature}</h4>
          <p className="text-sm text-muted-foreground">{description}</p>
          {steps && steps.length > 0 && (
            <ul className="mt-2 space-y-1">
              {steps.map((step, i) => (
                <li
                  key={i}
                  className="flex items-center gap-2 text-xs text-muted-foreground"
                >
                  <ChevronRight className="w-3 h-3 text-primary" />
                  {step}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

function Sparkles({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
      <path d="M5 3v4" />
      <path d="M19 17v4" />
      <path d="M3 5h4" />
      <path d="M17 19h4" />
    </svg>
  )
}

export default SmartTooltip
