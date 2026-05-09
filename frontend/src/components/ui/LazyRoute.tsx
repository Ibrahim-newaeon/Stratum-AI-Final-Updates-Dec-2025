/**
 * LazyRoute — composes ErrorBoundary + Suspense + LoadingSpinner for the
 * lazy-imported route components in App.tsx. A render error inside one
 * lazy route used to blank-screen the entire dashboard; now it stays
 * scoped to the route, the rest of the app keeps working, and the
 * exception is reported to Sentry with a "lazy-route" tag.
 *
 * Replaces:
 *   <Suspense fallback={<LoadingSpinner />}>
 *     <SomeView />
 *   </Suspense>
 *
 * With:
 *   <LazyRoute>
 *     <SomeView />
 *   </LazyRoute>
 */

import { Suspense, type ReactNode } from 'react';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import { ErrorBoundary } from './ErrorBoundary';

interface LazyRouteProps {
  children: ReactNode;
  /** Override the default loading spinner. */
  fallback?: ReactNode;
  /** Friendlier user-facing copy when the route crashes. */
  errorMessage?: string;
}

export function LazyRoute({ children, fallback, errorMessage }: LazyRouteProps) {
  return (
    <ErrorBoundary boundaryTag="lazy-route" message={errorMessage ?? 'This page failed to load.'}>
      <Suspense fallback={fallback ?? <LoadingSpinner />}>{children}</Suspense>
    </ErrorBoundary>
  );
}

export default LazyRoute;
