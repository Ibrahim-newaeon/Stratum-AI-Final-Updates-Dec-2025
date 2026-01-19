import { useParams, Navigate, Link } from 'react-router-dom';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import { getTierContent, isValidTier } from '@/config/tierLandingContent';
import {
  TierHero,
  TierFeatureGrid,
  TierPricingCTA,
  TierTestimonials,
  TierFAQ,
} from '@/components/landing/tier';
import { Footer } from '@/components/landing/Footer';
import { Button } from '@/components/ui/button';

export default function TierLandingPage() {
  const { tier } = useParams<{ tier: string }>();

  // Validate tier parameter
  if (!tier || !isValidTier(tier)) {
    return <Navigate to="/" replace />;
  }

  // Get content for this tier
  const content = getTierContent(tier);
  if (!content) {
    return <Navigate to="/" replace />;
  }

  const gradientClass = `${content.visuals.gradientFrom} ${content.visuals.gradientTo}`;

  return (
    <div key={tier} className="min-h-screen bg-surface-primary">
      {/* Navigation Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-surface-primary/80 backdrop-blur-lg border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Logo and Back */}
            <div className="flex items-center gap-6">
              <Link to="/" className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-stratum flex items-center justify-center">
                  <span className="text-white font-bold">S</span>
                </div>
                <span className="text-lg text-white font-semibold hidden sm:inline">Stratum AI</span>
              </Link>
              <Link
                to="/"
                className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                <ArrowLeftIcon className="w-4 h-4" />
                <span className="hidden sm:inline">Back to home</span>
              </Link>
            </div>

            {/* Plan Navigation */}
            <nav className="hidden md:flex items-center gap-1 bg-gray-900/50 rounded-full p-1">
              {['starter', 'professional', 'enterprise'].map((t) => (
                <Link
                  key={t}
                  to={`/plans/${t}`}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                    t === tier
                      ? `bg-gradient-to-r ${gradientClass} text-white`
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </Link>
              ))}
            </nav>

            {/* CTA */}
            <div className="flex items-center gap-3">
              <Link to="/login">
                <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
                  Sign in
                </Button>
              </Link>
              <Link to={content.id === 'enterprise' ? '/contact' : `/signup?tier=${content.id}`}>
                <Button
                  size="sm"
                  className={`bg-gradient-to-r ${gradientClass} text-white hover:opacity-90`}
                >
                  {content.id === 'enterprise' ? 'Contact Sales' : 'Start Trial'}
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="pt-16">
        <TierHero content={content} />
        <TierFeatureGrid content={content} />
        <TierTestimonials content={content} />
        <TierPricingCTA content={content} />
        <TierFAQ content={content} />
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}
