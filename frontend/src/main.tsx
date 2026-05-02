import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { init as sentryInit, browserTracingIntegration } from '@sentry/react'
import App from './App'
import { queryClient } from './lib/queryClient'
import './index.css'
import './i18n'

// Re-exported for backward compat with imports from `@/main`. New code
// should import directly from `@/lib/queryClient` so test code can
// load that module without triggering the top-level createRoot below.
export { queryClient }

// Initialize Sentry for production error tracking
const sentryDsn = import.meta.env.VITE_SENTRY_DSN;
if (sentryDsn) {
  sentryInit({
    dsn: sentryDsn,
    environment: import.meta.env.MODE,
    integrations: [
      browserTracingIntegration(),
    ],
    tracesSampleRate: import.meta.env.MODE === 'production' ? 0.1 : 1.0,
    // Strip PII from error reports before sending to Sentry
    beforeSend(event) {
      if (event.user) {
        delete event.user.email;
        delete event.user.ip_address;
        delete event.user.username;
      }
      return event;
    },
  });
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
