/**
 * Shared React Query client.
 *
 * Lives in its own module (not main.tsx) so consumers can import it
 * without triggering main.tsx's top-level createRoot call. The
 * pre-existing AuthContext.test.tsx flake was caused by exactly that:
 * AuthContext → @/main → createRoot(document.getElementById('root')!)
 * blew up under jsdom because there was no #root in the test DOM.
 */

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
