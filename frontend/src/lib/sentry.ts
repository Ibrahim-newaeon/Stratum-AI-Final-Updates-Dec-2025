/**
 * Sentry Error Tracking Configuration
 *
 * Initializes Sentry for error tracking and performance monitoring.
 * Only active when VITE_SENTRY_DSN environment variable is set.
 */

import * as Sentry from '@sentry/react';

const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN;
const ENVIRONMENT = import.meta.env.MODE || 'development';
const IS_PRODUCTION = ENVIRONMENT === 'production';

export function initSentry() {
  if (!SENTRY_DSN) {
    console.log('[Sentry] DSN not configured, skipping initialization');
    return;
  }

  Sentry.init({
    dsn: SENTRY_DSN,
    environment: ENVIRONMENT,
    release: `stratum-frontend@1.0.0`,

    // Performance Monitoring
    tracesSampleRate: IS_PRODUCTION ? 0.1 : 1.0,

    // Session Replay (captures user sessions for debugging)
    replaysSessionSampleRate: IS_PRODUCTION ? 0.1 : 0,
    replaysOnErrorSampleRate: IS_PRODUCTION ? 1.0 : 0,

    // Integration configuration
    integrations: [
      // React Router integration for better route tracking
      Sentry.browserTracingIntegration(),
      // Replay integration for session recordings
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],

    // Filter out certain errors
    beforeSend(event, hint) {
      const error = hint.originalException;

      // Ignore network errors and cancelled requests
      if (error instanceof Error) {
        if (
          error.message.includes('Network Error') ||
          error.message.includes('cancelled') ||
          error.message.includes('aborted')
        ) {
          return null;
        }
      }

      // Don't send errors in development by default
      if (!IS_PRODUCTION && !import.meta.env.VITE_SENTRY_DEBUG) {
        console.error('[Sentry] Would send error:', error);
        return null;
      }

      return event;
    },

    // Don't capture PII
    sendDefaultPii: false,
  });

  console.log('[Sentry] Initialized', { environment: ENVIRONMENT });
}

/**
 * Set user context for Sentry
 * Call this after user login
 */
export function setSentryUser(user: { id: string; email?: string; role?: string }) {
  if (!SENTRY_DSN) return;

  Sentry.setUser({
    id: user.id,
    email: user.email,
    // Don't include sensitive info
  });

  Sentry.setTag('user_role', user.role || 'unknown');
}

/**
 * Clear user context from Sentry
 * Call this after user logout
 */
export function clearSentryUser() {
  if (!SENTRY_DSN) return;
  Sentry.setUser(null);
}

/**
 * Set tenant context for multi-tenant tracking
 */
export function setSentryTenant(tenantId: number, tenantName?: string) {
  if (!SENTRY_DSN) return;

  Sentry.setTag('tenant_id', tenantId.toString());
  if (tenantName) {
    Sentry.setTag('tenant_name', tenantName);
  }
}

/**
 * Capture a custom error with additional context
 */
export function captureError(error: Error, context?: Record<string, unknown>) {
  if (!SENTRY_DSN) {
    console.error('[Sentry] Error:', error, context);
    return;
  }

  Sentry.withScope((scope) => {
    if (context) {
      scope.setContext('additional', context);
    }
    Sentry.captureException(error);
  });
}

/**
 * Capture a custom message/event
 */
export function captureMessage(message: string, level: 'info' | 'warning' | 'error' = 'info') {
  if (!SENTRY_DSN) {
    console.log(`[Sentry] ${level}: ${message}`);
    return;
  }

  Sentry.captureMessage(message, level);
}

// Re-export Sentry ErrorBoundary for use in React components
export const ErrorBoundary = Sentry.ErrorBoundary;
