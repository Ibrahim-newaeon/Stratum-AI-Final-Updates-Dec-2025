/**
 * 403 Unauthorized / Access Denied Page
 * Shown when an authenticated user lacks the role or permission for a route.
 * ProtectedRoute redirects here on role/portal violations, so this page must
 * NOT be auth-gated (that would loop). It is intentionally a sibling route.
 */

import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeftIcon, HomeIcon, LockClosedIcon } from '@heroicons/react/24/outline';
import { SEO } from '@/components/common/SEO';

export default function Unauthorized() {
  const navigate = useNavigate();

  return (
    <div className="dark min-h-screen flex items-center justify-center p-6 bg-background">
      <SEO
        title="Access Denied"
        description="You don't have permission to view this page."
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
        {/* Lock badge */}
        <div
          className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-2xl"
          style={{
            background: 'hsl(var(--primary) / 0.12)',
            border: '1px solid hsl(var(--primary) / 0.25)',
          }}
          aria-hidden="true"
        >
          <LockClosedIcon className="h-9 w-9" style={{ color: 'hsl(var(--primary))' }} />
        </div>

        {/* 403 number */}
        <div
          className="text-[150px] font-bold leading-none mb-6"
          style={{
            background: 'linear-gradient(135deg, hsl(var(--primary)) 0%, hsl(var(--accent)) 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
          aria-hidden="true"
        >
          403
        </div>

        <h1 className="text-3xl font-bold text-white mb-4">Access Denied</h1>

        <p className="text-lg mb-8" style={{ color: 'hsl(var(--foreground) / 0.6)' }}>
          You don't have permission to view this page. If you think this is a mistake, contact your
          workspace administrator.
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
            to="/dashboard"
            className="flex items-center gap-2 px-6 py-3 rounded-xl font-medium text-white transition-colors"
            style={{
              background: 'hsl(var(--primary))',
              boxShadow: '0 4px 20px hsl(var(--primary) / 0.4)',
            }}
          >
            <HomeIcon className="w-5 h-5" aria-hidden="true" />
            Back to Dashboard
          </Link>
        </div>

        {/* Helpful links */}
        <div className="mt-12 pt-8" style={{ borderTop: '1px solid hsl(var(--foreground) / 0.1)' }}>
          <p className="text-sm mb-4" style={{ color: 'hsl(var(--foreground) / 0.5)' }}>
            Need access?
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/dashboard/settings/profile"
              className="text-sm font-medium transition-colors hover:text-white"
              style={{ color: 'hsl(var(--primary))' }}
            >
              Account Settings
            </Link>
            <span style={{ color: 'hsl(var(--foreground) / 0.2)' }}>|</span>
            <Link
              to="/contact"
              className="text-sm font-medium transition-colors hover:text-white"
              style={{ color: 'hsl(var(--primary))' }}
            >
              Contact Support
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
