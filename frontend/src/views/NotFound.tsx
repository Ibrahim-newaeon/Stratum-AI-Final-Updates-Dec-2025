/**
 * 404 Not Found Page
 * Displayed when user navigates to a non-existent route
 */

import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeftIcon, HomeIcon } from '@heroicons/react/24/outline';
import { SEO } from '@/components/common/SEO';

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <div
      className="min-h-screen flex items-center justify-center p-6 bg-background"
    >
      <SEO
        title="Page Not Found"
        description="The page you're looking for doesn't exist or has been moved."
        noIndex
      />

      {/* Background orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute w-[500px] h-[500px] rounded-full blur-[100px] opacity-30"
          style={{ background: 'hsl(var(--primary) / 0.25)', top: '10%', left: '10%' }}
        />
        <div
          className="absolute w-[400px] h-[400px] rounded-full blur-[100px] opacity-30"
          style={{ background: 'hsl(var(--accent) / 0.25)', bottom: '10%', right: '10%' }}
        />
      </div>

      <div className="relative z-10 text-center max-w-lg">
        {/* 404 number */}
        <div
          className="text-[150px] font-bold leading-none mb-6"
          style={{
            background: 'linear-gradient(135deg, hsl(var(--primary)) 0%, hsl(var(--accent)) 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
          aria-hidden="true"
        >
          404
        </div>

        <h1 className="text-3xl font-bold text-white mb-4">Page Not Found</h1>

        <p className="text-lg mb-8" style={{ color: 'hsl(var(--foreground) / 0.6)' }}>
          The page you're looking for doesn't exist or has been moved. Let's get you back on track.
        </p>

        {/* Action buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 px-6 py-3 rounded-xl font-medium text-white transition-colors hover:bg-foreground/10"
            style={{
              background: 'hsl(var(--foreground) / 0.06)',
              border: '1px solid hsl(var(--foreground) / 0.12)',
            }}
          >
            <ArrowLeftIcon className="w-5 h-5" aria-hidden="true" />
            Go Back
          </button>

          <Link
            to="/"
            className="flex items-center gap-2 px-6 py-3 rounded-xl font-medium text-white transition-colors"
            style={{
              background: 'hsl(var(--primary))',
              boxShadow: '0 4px 20px hsl(var(--primary) / 0.4)',
            }}
          >
            <HomeIcon className="w-5 h-5" aria-hidden="true" />
            Back to Home
          </Link>
        </div>

        {/* Helpful links */}
        <div className="mt-12 pt-8" style={{ borderTop: '1px solid hsl(var(--foreground) / 0.1)' }}>
          <p className="text-sm mb-4" style={{ color: 'hsl(var(--foreground) / 0.5)' }}>
            Looking for something specific?
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/dashboard"
              className="text-sm font-medium transition-colors hover:text-white"
              style={{ color: 'hsl(var(--primary))' }}
            >
              Dashboard
            </Link>
            <span style={{ color: 'hsl(var(--foreground) / 0.2)' }}>|</span>
            <Link
              to="/features"
              className="text-sm font-medium transition-colors hover:text-white"
              style={{ color: 'hsl(var(--primary))' }}
            >
              Features
            </Link>
            <span style={{ color: 'hsl(var(--foreground) / 0.2)' }}>|</span>
            <Link
              to="/pricing"
              className="text-sm font-medium transition-colors hover:text-white"
              style={{ color: 'hsl(var(--primary))' }}
            >
              Pricing
            </Link>
            <span style={{ color: 'hsl(var(--foreground) / 0.2)' }}>|</span>
            <Link
              to="/contact"
              className="text-sm font-medium transition-colors hover:text-white"
              style={{ color: 'hsl(var(--primary))' }}
            >
              Contact
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
