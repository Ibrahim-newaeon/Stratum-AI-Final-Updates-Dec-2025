/**
 * Demo Banner Component - Shows when in demo mode
 *
 * Displays a prominent banner indicating demo mode is active
 * with CTA to sign up for a real account.
 */

import * as React from 'react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { X, Sparkles, ArrowRight, Play } from 'lucide-react'
import { useDemo } from '@/contexts/DemoContext'
import { cn } from '@/lib/utils'

interface DemoBannerProps {
  variant?: 'top' | 'floating'
}

export function DemoBanner({ variant = 'top' }: DemoBannerProps) {
  const { isDemoMode, exitDemoMode } = useDemo()
  const [isMinimized, setIsMinimized] = useState(false)
  const navigate = useNavigate()

  if (!isDemoMode) return null

  if (variant === 'floating' && isMinimized) {
    return (
      <button
        onClick={() => setIsMinimized(false)}
        className="fixed bottom-4 right-4 z-50 flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-purple-600 to-cyan-500 text-white text-sm font-medium shadow-lg hover:shadow-xl transition-all"
      >
        <Play className="h-4 w-4" />
        Demo Mode
      </button>
    )
  }

  if (variant === 'floating') {
    return (
      <div className="fixed bottom-4 right-4 z-50 w-80 rounded-2xl bg-card border shadow-2xl overflow-hidden animate-in slide-in-from-bottom-5">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-cyan-500 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2 text-white">
            <Sparkles className="h-4 w-4" />
            <span className="font-semibold text-sm">Demo Mode Active</span>
          </div>
          <button
            onClick={() => setIsMinimized(true)}
            className="text-white/70 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-3">
          <p className="text-sm text-muted-foreground">
            You're exploring Stratum AI with sample data. Ready to use your own data?
          </p>

          <div className="flex gap-2">
            <button
              onClick={() => navigate('/signup')}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90"
            >
              Start Free Trial
              <ArrowRight className="h-4 w-4" />
            </button>
            <button
              onClick={exitDemoMode}
              className="px-4 py-2 rounded-lg border text-sm font-medium hover:bg-accent"
            >
              Exit
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Top banner variant
  return (
    <div className="bg-gradient-to-r from-purple-600 via-violet-600 to-cyan-500 text-white">
      <div className="max-w-7xl mx-auto px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-white/20 text-xs font-medium">
            <Play className="h-3 w-3" />
            DEMO MODE
          </div>
          <span className="text-sm">
            Exploring with sample data from <strong>Acme Commerce</strong>
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/signup')}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-white text-purple-600 text-sm font-semibold hover:bg-white/90 transition-colors"
          >
            Start Free Trial
            <ArrowRight className="h-4 w-4" />
          </button>
          <button
            onClick={exitDemoMode}
            className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
            title="Exit demo mode"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * Demo CTA Card - Shown on landing page to enter demo mode
 */
export function DemoCtaCard() {
  const { enterDemoMode } = useDemo()
  const navigate = useNavigate()

  const handleEnterDemo = () => {
    enterDemoMode()
    navigate('/dashboard/overview')
  }

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-purple-900/50 to-cyan-900/50 border border-purple-500/20 p-8">
      {/* Background effects */}
      <div className="absolute inset-0 bg-grid-white/5 [mask-image:radial-gradient(ellipse_at_center,transparent_20%,black)]" />
      <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/20 rounded-full blur-3xl" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-cyan-500/20 rounded-full blur-3xl" />

      <div className="relative">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center">
            <Play className="h-6 w-6 text-white" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-white">Try Interactive Demo</h3>
            <p className="text-sm text-gray-400">No signup required</p>
          </div>
        </div>

        <p className="text-gray-300 mb-6">
          Experience Stratum AI with real sample data. Explore trust gates, CDP profiles,
          audience sync, and AI predictions - all in your browser.
        </p>

        <div className="flex flex-wrap gap-3 mb-6">
          <span className="px-3 py-1 rounded-full bg-purple-500/20 text-purple-300 text-xs font-medium">
            Trust Engine
          </span>
          <span className="px-3 py-1 rounded-full bg-cyan-500/20 text-cyan-300 text-xs font-medium">
            CDP Profiles
          </span>
          <span className="px-3 py-1 rounded-full bg-green-500/20 text-green-300 text-xs font-medium">
            AI Predictions
          </span>
          <span className="px-3 py-1 rounded-full bg-orange-500/20 text-orange-300 text-xs font-medium">
            Audience Sync
          </span>
        </div>

        <button
          onClick={handleEnterDemo}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-cyan-500 text-white font-semibold hover:from-purple-500 hover:to-cyan-400 transition-all shadow-lg shadow-purple-500/25"
        >
          <Sparkles className="h-5 w-5" />
          Launch Interactive Demo
          <ArrowRight className="h-5 w-5" />
        </button>
      </div>
    </div>
  )
}

export default DemoBanner
