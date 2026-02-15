/**
 * Onboarding Demo Banner
 *
 * Shown to first-time users when dashboard pages display mock/demo data.
 * Tells the user that the data is sample data and invites them to
 * connect their platforms to see real metrics.
 *
 * Once dismissed, the banner never appears again (localStorage persistence).
 */

import { useNavigate } from 'react-router-dom';
import { ArrowRight, Info, Link2, Sparkles, X } from 'lucide-react';
import { motion } from 'framer-motion';

interface OnboardingDemoBannerProps {
  /** Called when the user dismisses the banner */
  onDismiss: () => void;
  /** Optional: override the CTA destination (default: /dashboard/integrations) */
  ctaRoute?: string;
}

export function OnboardingDemoBanner({
  onDismiss,
  ctaRoute = '/dashboard/integrations',
}: OnboardingDemoBannerProps) {
  const navigate = useNavigate();

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="relative overflow-hidden rounded-2xl border border-amber-500/30 bg-gradient-to-br from-amber-500/5 via-card to-card p-5 lg:p-6"
    >
      {/* Background glow */}
      <div className="absolute -top-16 -right-16 w-48 h-48 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Dismiss button */}
      <button
        onClick={onDismiss}
        className="absolute top-3 right-3 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors z-10"
        title="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>

      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        {/* Icon + message */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 rounded-lg bg-amber-500/15 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-amber-500" />
            </div>
            <span className="text-xs font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider">
              Sample Data
            </span>
          </div>

          <p className="text-sm text-muted-foreground leading-relaxed max-w-2xl">
            You're viewing <strong className="text-foreground">demo data</strong> to preview the
            dashboard experience. Connect your ad platforms to start seeing{' '}
            <strong className="text-foreground">your real metrics</strong> in action.
          </p>
        </div>

        {/* CTA */}
        <button
          onClick={() => navigate(ctaRoute)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-all group whitespace-nowrap"
        >
          <Link2 className="w-4 h-4" />
          Connect Platforms
          <ArrowRight className="w-4 h-4 opacity-0 -ml-2 group-hover:opacity-100 group-hover:ml-0 transition-all" />
        </button>
      </div>

      {/* Subtle hint */}
      <div className="mt-3 pt-3 border-t border-border/40 flex items-center gap-2">
        <Info className="w-3 h-3 text-muted-foreground flex-shrink-0" />
        <p className="text-xs text-muted-foreground">
          This banner will not appear again once dismissed or after you connect a platform.
        </p>
      </div>
    </motion.div>
  );
}

export default OnboardingDemoBanner;
