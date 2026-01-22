/**
 * Onboarding Checklist - Guide new users through setup
 *
 * Shows progress through essential setup steps with
 * contextual actions and celebratory completion.
 */

import * as React from 'react'
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  CheckCircle2,
  Circle,
  ChevronDown,
  ChevronUp,
  Rocket,
  Link2,
  Users,
  Target,
  BarChart3,
  Bell,
  Zap,
  X,
  PartyPopper,
  ArrowRight,
  Sparkles,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChecklistItem {
  id: string
  title: string
  description: string
  icon: React.ElementType
  actionLabel: string
  actionUrl: string
  completed: boolean
  required: boolean
}

const DEFAULT_CHECKLIST: ChecklistItem[] = [
  {
    id: 'connect_platform',
    title: 'Connect an Ad Platform',
    description: 'Link your Meta, Google, TikTok, or Snapchat account',
    icon: Link2,
    actionLabel: 'Connect',
    actionUrl: '/dashboard/capi-setup',
    completed: false,
    required: true,
  },
  {
    id: 'create_segment',
    title: 'Create a CDP Segment',
    description: 'Build your first audience segment for targeting',
    icon: Users,
    actionLabel: 'Create Segment',
    actionUrl: '/dashboard/cdp/segments?action=create',
    completed: false,
    required: true,
  },
  {
    id: 'setup_rule',
    title: 'Configure an Automation Rule',
    description: 'Set up trust-gated automation for your campaigns',
    icon: Zap,
    actionLabel: 'Create Rule',
    actionUrl: '/dashboard/rules',
    completed: false,
    required: true,
  },
  {
    id: 'review_signals',
    title: 'Review Signal Health',
    description: 'Check your data quality and signal scores',
    icon: BarChart3,
    actionLabel: 'View Signals',
    actionUrl: '/dashboard/emq-dashboard',
    completed: false,
    required: false,
  },
  {
    id: 'enable_notifications',
    title: 'Enable Notifications',
    description: 'Get alerts for Trust Gate decisions and anomalies',
    icon: Bell,
    actionLabel: 'Configure',
    actionUrl: '/dashboard/settings',
    completed: false,
    required: false,
  },
  {
    id: 'launch_campaign',
    title: 'Launch a Campaign',
    description: 'Create and publish your first campaign',
    icon: Target,
    actionLabel: 'Create Campaign',
    actionUrl: '/dashboard/campaigns',
    completed: false,
    required: false,
  },
]

interface OnboardingChecklistProps {
  tenantId?: string
  variant?: 'sidebar' | 'modal' | 'inline' | 'horizontal'
  onComplete?: () => void
}

export function OnboardingChecklist({ tenantId, variant = 'sidebar', onComplete }: OnboardingChecklistProps) {
  const navigate = useNavigate()
  const [checklist, setChecklist] = useState<ChecklistItem[]>(DEFAULT_CHECKLIST)
  const [isExpanded, setIsExpanded] = useState(true)
  const [showCelebration, setShowCelebration] = useState(false)
  const [isDismissed, setIsDismissed] = useState(false)

  // Load progress from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('stratum_onboarding_progress')
    if (stored) {
      try {
        const progress = JSON.parse(stored) as Record<string, boolean>
        setChecklist(prev => prev.map(item => ({
          ...item,
          completed: progress[item.id] || false,
        })))
      } catch (e) {
        // Invalid stored data, use defaults
      }
    }

    const dismissed = localStorage.getItem('stratum_onboarding_dismissed')
    if (dismissed === 'true') {
      setIsDismissed(true)
    }
  }, [])

  // Save progress
  const saveProgress = (items: ChecklistItem[]) => {
    const progress = items.reduce((acc, item) => ({
      ...acc,
      [item.id]: item.completed,
    }), {})
    localStorage.setItem('stratum_onboarding_progress', JSON.stringify(progress))
  }

  const completedCount = checklist.filter(item => item.completed).length
  const totalCount = checklist.length
  const requiredCompleted = checklist.filter(item => item.required && item.completed).length
  const requiredTotal = checklist.filter(item => item.required).length
  const progress = Math.round((completedCount / totalCount) * 100)

  const markComplete = (id: string) => {
    const updated = checklist.map(item =>
      item.id === id ? { ...item, completed: true } : item
    )
    setChecklist(updated)
    saveProgress(updated)

    // Check if all required items are complete
    const allRequiredComplete = updated.filter(i => i.required).every(i => i.completed)
    if (allRequiredComplete && !showCelebration) {
      setShowCelebration(true)
      onComplete?.()
    }
  }

  const handleAction = (item: ChecklistItem) => {
    // Navigate and mark as in-progress
    navigate(item.actionUrl)
    // Could mark complete after navigation or via callback
    // For demo, we'll mark it complete on click
    setTimeout(() => markComplete(item.id), 500)
  }

  const dismiss = () => {
    setIsDismissed(true)
    localStorage.setItem('stratum_onboarding_dismissed', 'true')
  }

  const reset = () => {
    setChecklist(DEFAULT_CHECKLIST)
    localStorage.removeItem('stratum_onboarding_progress')
    localStorage.removeItem('stratum_onboarding_dismissed')
    setIsDismissed(false)
    setShowCelebration(false)
  }

  if (isDismissed && progress < 100) {
    // Show minimal re-open button
    return (
      <button
        onClick={() => setIsDismissed(false)}
        className="fixed bottom-4 left-4 z-40 flex items-center gap-2 px-4 py-2 rounded-full bg-primary text-primary-foreground text-sm font-medium shadow-lg hover:shadow-xl transition-all"
      >
        <Rocket className="h-4 w-4" />
        Setup ({progress}%)
      </button>
    )
  }

  if (progress === 100 && !showCelebration) {
    return null // Fully complete and dismissed
  }

  // Celebration Modal
  if (showCelebration) {
    return (
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setShowCelebration(false)}
        >
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md bg-card rounded-2xl border shadow-2xl overflow-hidden"
          >
            <div className="relative p-8 text-center">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-600/20 via-cyan-600/10 to-transparent" />
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, type: 'spring' }}
                className="relative w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center"
              >
                <PartyPopper className="h-10 w-10 text-white" />
              </motion.div>
              <h2 className="text-2xl font-bold mb-2">You're All Set!</h2>
              <p className="text-muted-foreground mb-6">
                You've completed the essential setup. Stratum AI is now ready to optimize your campaigns with trust-gated automation.
              </p>
              <div className="flex gap-3 justify-center">
                <button
                  onClick={() => {
                    setShowCelebration(false)
                    dismiss()
                  }}
                  className="px-6 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90"
                >
                  Let's Go!
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </AnimatePresence>
    )
  }

  // Horizontal variant - shows as a bar at the top
  if (variant === 'horizontal') {
    return (
      <div className="bg-card/50 backdrop-blur-sm border-b px-6 py-3">
        <div className="flex items-center gap-6">
          {/* Progress indicator */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center">
              <Rocket className="h-4 w-4 text-white" />
            </div>
            <div>
              <span className="text-sm font-medium">Getting Started</span>
              <span className="text-xs text-muted-foreground ml-2">{completedCount}/{totalCount}</span>
            </div>
          </div>

          {/* Horizontal steps */}
          <div className="flex-1 flex items-center gap-2 overflow-x-auto">
            {checklist.slice(0, 4).map((item, index) => {
              const Icon = item.icon
              return (
                <button
                  key={item.id}
                  onClick={() => !item.completed && handleAction(item)}
                  className={cn(
                    "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all",
                    item.completed
                      ? "bg-green-500/10 text-green-600"
                      : "bg-white/5 hover:bg-white/10 text-muted-foreground hover:text-foreground"
                  )}
                >
                  {item.completed ? (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  ) : (
                    <Icon className="h-3.5 w-3.5" />
                  )}
                  {item.title}
                </button>
              )
            })}
          </div>

          {/* Progress bar */}
          <div className="flex items-center gap-3">
            <div className="w-24 h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-cyan-500 transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground">{progress}%</span>
          </div>

          {/* Dismiss button */}
          <button
            onClick={dismiss}
            className="p-1 rounded hover:bg-accent transition-colors"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>
      </div>
    )
  }

  // Sidebar/Inline variant
  return (
    <div className={cn(
      "bg-card border rounded-2xl overflow-hidden",
      variant === 'sidebar' && "fixed bottom-4 left-4 z-40 w-80 shadow-2xl"
    )}>
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-accent/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center">
            <Rocket className="h-5 w-5 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-sm">Getting Started</h3>
            <p className="text-xs text-muted-foreground">
              {completedCount}/{totalCount} completed
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-12 h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-500 to-cyan-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </div>

      {/* Checklist Items */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="px-4 pb-4 space-y-2">
              {checklist.map((item) => (
                <div
                  key={item.id}
                  className={cn(
                    "group flex items-start gap-3 p-3 rounded-xl transition-colors",
                    item.completed ? "bg-green-500/5" : "hover:bg-accent/50"
                  )}
                >
                  <div className="mt-0.5">
                    {item.completed ? (
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                    ) : (
                      <Circle className="h-5 w-5 text-muted-foreground" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        "text-sm font-medium",
                        item.completed && "text-muted-foreground line-through"
                      )}>
                        {item.title}
                      </span>
                      {item.required && !item.completed && (
                        <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-primary/10 text-primary">
                          Required
                        </span>
                      )}
                    </div>
                    {!item.completed && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {item.description}
                      </p>
                    )}
                    {!item.completed && (
                      <button
                        onClick={() => handleAction(item)}
                        className="mt-2 inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-xs font-medium hover:bg-primary/20 transition-colors"
                      >
                        {item.actionLabel}
                        <ArrowRight className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="px-4 py-3 border-t bg-muted/30 flex items-center justify-between">
              <button
                onClick={dismiss}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Dismiss
              </button>
              {progress === 100 && (
                <button
                  onClick={reset}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  Reset
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default OnboardingChecklist
