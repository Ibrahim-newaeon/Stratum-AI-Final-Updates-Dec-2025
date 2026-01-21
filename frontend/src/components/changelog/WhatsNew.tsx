/**
 * What's New / Changelog Modal
 *
 * Shows product updates, new features, and improvements
 * to keep users informed about platform changes.
 */

import * as React from 'react'
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Sparkles,
  Zap,
  Bug,
  Wrench,
  ArrowRight,
  ExternalLink,
  Gift,
  Star,
  Rocket,
} from 'lucide-react'
import { cn } from '@/lib/utils'

type ChangeType = 'feature' | 'improvement' | 'fix' | 'breaking'

interface Change {
  type: ChangeType
  title: string
  description?: string
}

interface Release {
  version: string
  date: string
  title: string
  highlights?: string[]
  changes: Change[]
}

const RELEASES: Release[] = [
  {
    version: '2.5.0',
    date: 'January 2026',
    title: 'Premium Experience Update',
    highlights: [
      'Command Palette (Cmd+K) for instant navigation',
      'Interactive Demo Mode - no signup required',
      'Slack Integration for Trust Gate alerts',
    ],
    changes: [
      { type: 'feature', title: 'Command Palette', description: 'Search and navigate anywhere with Cmd+K' },
      { type: 'feature', title: 'Interactive Demo Mode', description: 'Experience Stratum AI with sample data' },
      { type: 'feature', title: 'Slack Integration', description: 'Receive Trust Gate alerts in Slack' },
      { type: 'feature', title: 'PDF Report Export', description: 'One-click professional dashboard exports' },
      { type: 'feature', title: 'Notification Center', description: 'Real-time alerts and activity hub' },
      { type: 'improvement', title: 'Enhanced Glossary', description: 'Industry benchmarks for all metrics' },
    ],
  },
  {
    version: '2.4.0',
    date: 'January 2026',
    title: 'Security & Payments',
    changes: [
      { type: 'feature', title: 'Stripe Integration', description: 'Subscription payments and billing portal' },
      { type: 'feature', title: 'MFA Authentication', description: 'Two-factor authentication with TOTP' },
      { type: 'feature', title: 'Subscription Enforcement', description: 'Tier-based feature gating' },
      { type: 'improvement', title: 'RLS Security', description: 'Row-level security for tenant isolation' },
      { type: 'fix', title: 'OAuth Token Refresh', description: 'Fixed token expiration handling' },
    ],
  },
  {
    version: '2.3.0',
    date: 'December 2025',
    title: 'AI Landing & Marketing Kit',
    changes: [
      { type: 'feature', title: 'AI Landing Page', description: 'Modern landing with trust engine showcase' },
      { type: 'feature', title: 'SaaS Glossary', description: '120+ terms with industry benchmarks' },
      { type: 'feature', title: 'Tier Landing Pages', description: 'Dedicated pages for each pricing tier' },
      { type: 'improvement', title: 'Battle Cards', description: 'Competitive comparison components' },
    ],
  },
  {
    version: '2.2.0',
    date: 'December 2025',
    title: 'CDP Audience Sync',
    changes: [
      { type: 'feature', title: 'Multi-Platform Sync', description: 'Push segments to Meta, Google, TikTok, Snapchat' },
      { type: 'feature', title: 'Auto-Sync Scheduling', description: 'Configurable sync intervals' },
      { type: 'feature', title: 'Match Rate Tracking', description: 'Monitor audience match performance' },
      { type: 'improvement', title: 'Identity Resolution', description: 'Enhanced cross-device tracking' },
    ],
  },
  {
    version: '2.1.0',
    date: 'November 2025',
    title: 'AI & ML Features',
    changes: [
      { type: 'feature', title: 'LTV Prediction', description: 'ML-powered customer lifetime value forecasting' },
      { type: 'feature', title: 'SHAP Explainability', description: 'Understand why predictions were made' },
      { type: 'feature', title: 'Bayesian A/B Testing', description: 'Probabilistic experiment analysis' },
      { type: 'feature', title: 'Churn Prediction', description: 'Identify at-risk customers early' },
    ],
  },
]

const getChangeIcon = (type: ChangeType) => {
  switch (type) {
    case 'feature':
      return { icon: Sparkles, color: 'text-purple-500', bg: 'bg-purple-500/10' }
    case 'improvement':
      return { icon: Zap, color: 'text-cyan-500', bg: 'bg-cyan-500/10' }
    case 'fix':
      return { icon: Bug, color: 'text-green-500', bg: 'bg-green-500/10' }
    case 'breaking':
      return { icon: Wrench, color: 'text-orange-500', bg: 'bg-orange-500/10' }
    default:
      return { icon: Star, color: 'text-gray-500', bg: 'bg-gray-500/10' }
  }
}

const getChangeLabel = (type: ChangeType) => {
  switch (type) {
    case 'feature': return 'New'
    case 'improvement': return 'Improved'
    case 'fix': return 'Fixed'
    case 'breaking': return 'Breaking'
    default: return 'Update'
  }
}

interface WhatsNewModalProps {
  isOpen: boolean
  onClose: () => void
}

export function WhatsNewModal({ isOpen, onClose }: WhatsNewModalProps) {
  const [selectedRelease, setSelectedRelease] = useState(0)
  const currentRelease = RELEASES[selectedRelease]

  // Mark as seen in localStorage
  useEffect(() => {
    if (isOpen) {
      localStorage.setItem('stratum_last_seen_version', RELEASES[0].version)
    }
  }, [isOpen])

  // Close on escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      return () => document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen, onClose])

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-2xl max-h-[85vh] bg-card rounded-2xl border shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-600/20 via-cyan-600/10 to-transparent" />
              <div className="relative px-6 py-5 flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center shadow-lg">
                    <Gift className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold">What's New</h2>
                    <p className="text-sm text-muted-foreground">Latest updates and features</p>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 rounded-lg hover:bg-accent transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex h-[calc(85vh-140px)]">
              {/* Version Sidebar */}
              <div className="w-48 border-r bg-muted/30 p-3 overflow-y-auto shrink-0">
                <div className="space-y-1">
                  {RELEASES.map((release, index) => (
                    <button
                      key={release.version}
                      onClick={() => setSelectedRelease(index)}
                      className={cn(
                        "w-full text-left px-3 py-2.5 rounded-lg transition-colors",
                        selectedRelease === index
                          ? "bg-primary text-primary-foreground"
                          : "hover:bg-accent"
                      )}
                    >
                      <div className="flex items-center gap-2">
                        {index === 0 && (
                          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        )}
                        <span className="font-semibold text-sm">v{release.version}</span>
                      </div>
                      <span className={cn(
                        "text-xs",
                        selectedRelease === index ? "text-primary-foreground/70" : "text-muted-foreground"
                      )}>
                        {release.date}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Release Details */}
              <div className="flex-1 overflow-y-auto p-6">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={currentRelease.version}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    transition={{ duration: 0.2 }}
                  >
                    {/* Release Header */}
                    <div className="mb-6">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-bold">{currentRelease.title}</h3>
                        {selectedRelease === 0 && (
                          <span className="px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 text-xs font-medium">
                            Latest
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Version {currentRelease.version} - {currentRelease.date}
                      </p>
                    </div>

                    {/* Highlights */}
                    {currentRelease.highlights && currentRelease.highlights.length > 0 && (
                      <div className="mb-6 p-4 rounded-xl bg-gradient-to-br from-purple-500/10 to-cyan-500/10 border border-purple-500/20">
                        <div className="flex items-center gap-2 mb-3">
                          <Rocket className="h-4 w-4 text-purple-500" />
                          <span className="text-sm font-semibold">Highlights</span>
                        </div>
                        <ul className="space-y-2">
                          {currentRelease.highlights.map((highlight, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm">
                              <ArrowRight className="h-4 w-4 text-purple-500 shrink-0 mt-0.5" />
                              <span>{highlight}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Changes List */}
                    <div className="space-y-3">
                      {currentRelease.changes.map((change, index) => {
                        const { icon: Icon, color, bg } = getChangeIcon(change.type)
                        return (
                          <div
                            key={index}
                            className="flex items-start gap-3 p-3 rounded-xl hover:bg-accent/50 transition-colors"
                          >
                            <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center shrink-0", bg)}>
                              <Icon className={cn("h-4 w-4", color)} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-sm">{change.title}</span>
                                <span className={cn(
                                  "px-1.5 py-0.5 rounded text-[10px] font-medium uppercase",
                                  change.type === 'feature' && "bg-purple-500/10 text-purple-500",
                                  change.type === 'improvement' && "bg-cyan-500/10 text-cyan-500",
                                  change.type === 'fix' && "bg-green-500/10 text-green-500",
                                  change.type === 'breaking' && "bg-orange-500/10 text-orange-500",
                                )}>
                                  {getChangeLabel(change.type)}
                                </span>
                              </div>
                              {change.description && (
                                <p className="text-sm text-muted-foreground mt-0.5">
                                  {change.description}
                                </p>
                              )}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </motion.div>
                </AnimatePresence>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t bg-muted/30 flex items-center justify-between">
              <a
                href="/changelog"
                className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
              >
                View full changelog
                <ExternalLink className="h-3 w-3" />
              </a>
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90"
              >
                Got it!
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

/**
 * Hook to check if user has new updates
 */
export function useWhatsNew() {
  const [hasNewUpdates, setHasNewUpdates] = useState(false)

  useEffect(() => {
    const lastSeen = localStorage.getItem('stratum_last_seen_version')
    const latestVersion = RELEASES[0].version
    setHasNewUpdates(lastSeen !== latestVersion)
  }, [])

  return { hasNewUpdates, latestVersion: RELEASES[0].version }
}

export default WhatsNewModal
