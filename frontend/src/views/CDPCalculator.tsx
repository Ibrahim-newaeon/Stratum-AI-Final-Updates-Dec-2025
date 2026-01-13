/**
 * CDP ROI Calculator Page
 * Interactive calculator to estimate the impact of improved identity resolution
 */

import { Link } from 'react-router-dom'
import { ArrowLeft, Database, Users, TrendingUp, Shield } from 'lucide-react'
import { CDPROICalculator } from '@/components/widgets/CDPROICalculator'
import { ErrorBoundary, WidgetErrorFallback } from '@/components/ui/ErrorBoundary'

export default function CDPCalculator() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      {/* Header */}
      <header className="border-b border-border bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link
              to="/"
              className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Back to Home</span>
            </Link>
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-primary" />
              <span className="font-semibold">Stratum CDP</span>
            </div>
            <Link
              to="/signup"
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Page Title */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight mb-4">
            CDP ROI Calculator
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Estimate the business impact of improving your customer identity resolution
            with Stratum CDP's first-party data platform.
          </p>
        </div>

        {/* Value Props */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="flex items-start gap-4 p-6 rounded-xl bg-card border border-border">
            <div className="p-2 rounded-lg bg-primary/10">
              <Users className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold mb-1">Identity Resolution</h3>
              <p className="text-sm text-muted-foreground">
                Unify customer profiles across devices and touchpoints
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4 p-6 rounded-xl bg-card border border-border">
            <div className="p-2 rounded-lg bg-green-500/10">
              <TrendingUp className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <h3 className="font-semibold mb-1">Improved Attribution</h3>
              <p className="text-sm text-muted-foreground">
                Recover conversions lost to tracking limitations
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4 p-6 rounded-xl bg-card border border-border">
            <div className="p-2 rounded-lg bg-amber-500/10">
              <Shield className="w-5 h-5 text-amber-500" />
            </div>
            <div>
              <h3 className="font-semibold mb-1">Privacy-First</h3>
              <p className="text-sm text-muted-foreground">
                GDPR/PDPL compliant with built-in consent management
              </p>
            </div>
          </div>
        </div>

        {/* Calculator Widget */}
        <ErrorBoundary
          fallback={
            <WidgetErrorFallback
              title="CDP ROI Calculator"
              onRetry={() => window.location.reload()}
            />
          }
        >
          <CDPROICalculator className="mb-12" />
        </ErrorBoundary>

        {/* CTA Section */}
        <div className="text-center p-8 rounded-xl bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/20">
          <h2 className="text-2xl font-bold mb-4">
            Ready to See These Results?
          </h2>
          <p className="text-muted-foreground mb-6 max-w-xl mx-auto">
            Start your 30-day pilot program and measure the real impact on your business.
            Free setup consultation included.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              to="/signup"
              className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
            >
              Start Free Pilot
            </Link>
            <a
              href="mailto:sales@stratum.ai"
              className="px-6 py-3 border border-border rounded-lg font-medium hover:bg-muted transition-colors"
            >
              Contact Sales
            </a>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <p>&copy; 2026 Stratum AI. All rights reserved.</p>
            <div className="flex items-center gap-6">
              <a href="#" className="hover:text-foreground transition-colors">Privacy</a>
              <a href="#" className="hover:text-foreground transition-colors">Terms</a>
              <a href="#" className="hover:text-foreground transition-colors">Documentation</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
