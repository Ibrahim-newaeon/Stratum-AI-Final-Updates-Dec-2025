/**
 * Onboarding Guard Component
 * Checks if user needs to complete onboarding before accessing the app.
 *
 * If the backend says onboarding is required BUT the user previously
 * clicked "Skip setup", we honour the skip (localStorage flag) so the
 * user is never stuck in a redirect loop.
 */

import { Navigate, useLocation } from 'react-router-dom';
import { useOnboardingCheck } from '@/api/onboarding';
import LoadingSpinner from '@/components/common/LoadingSpinner';

const SKIP_KEY = 'stratum_onboarding_skipped';

interface OnboardingGuardProps {
  children: React.ReactNode;
}

export default function OnboardingGuard({ children }: OnboardingGuardProps) {
  const location = useLocation();
  const { data, isLoading, error } = useOnboardingCheck();

  // Show loading while checking onboarding status
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <LoadingSpinner />
      </div>
    );
  }

  // If there's an error checking onboarding, allow through (fail open)
  // The dashboard will handle showing appropriate error states
  if (error) {
    return <>{children}</>;
  }

  // If user previously skipped onboarding (client-side), let them through
  if (localStorage.getItem(SKIP_KEY) === 'true') {
    return <>{children}</>;
  }

  // If onboarding is required, redirect to onboarding
  if (data?.required) {
    // Preserve the intended destination so we can redirect after onboarding
    return <Navigate to="/onboarding" state={{ from: location }} replace />;
  }

  // Onboarding complete, render children
  return <>{children}</>;
}
