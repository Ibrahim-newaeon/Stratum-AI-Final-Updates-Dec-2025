/**
 * Trial Banner Component
 * Shows trial status and days remaining for trial accounts
 */

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { X, Clock, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

interface TrialBannerProps {
  planExpiresAt?: string | null
  plan?: string
}

export default function TrialBanner({ planExpiresAt, plan }: TrialBannerProps) {
  const [dismissed, setDismissed] = useState(false)
  const [daysRemaining, setDaysRemaining] = useState<number | null>(null)

  useEffect(() => {
    if (plan !== 'trial' || !planExpiresAt) {
      setDaysRemaining(null)
      return
    }

    const expiryDate = new Date(planExpiresAt)
    const now = new Date()
    const diffTime = expiryDate.getTime() - now.getTime()
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

    setDaysRemaining(diffDays)
  }, [planExpiresAt, plan])

  // Don't show if not on trial or dismissed
  if (plan !== 'trial' || dismissed || daysRemaining === null) {
    return null
  }

  // Determine banner color based on days remaining
  const isExpired = daysRemaining <= 0
  const isUrgent = daysRemaining <= 3
  const isWarning = daysRemaining <= 7

  const bannerClass = cn(
    'relative flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white',
    isExpired
      ? 'bg-red-600'
      : isUrgent
      ? 'bg-orange-500'
      : isWarning
      ? 'bg-yellow-500 text-yellow-900'
      : 'bg-gradient-to-r from-purple-600 to-indigo-600'
  )

  return (
    <div className={bannerClass}>
      <Clock className="h-4 w-4" />
      {isExpired ? (
        <span>
          Your trial has expired.{' '}
          <Link to="/app/settings" className="underline font-bold hover:no-underline">
            Upgrade now
          </Link>{' '}
          to continue using Stratum AI.
        </span>
      ) : (
        <span>
          {daysRemaining === 1 ? '1 day' : `${daysRemaining} days`} left in your trial.{' '}
          <Link to="/app/settings" className="underline font-bold hover:no-underline">
            Upgrade now
          </Link>{' '}
          to unlock all features.
        </span>
      )}
      <Sparkles className="h-4 w-4" />

      {!isExpired && (
        <button
          onClick={() => setDismissed(true)}
          className="absolute right-2 p-1 hover:bg-white/20 rounded"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}
