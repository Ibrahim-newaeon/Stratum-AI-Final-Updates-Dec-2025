/**
 * useDemoMode Hook - First-time user onboarding demo data
 *
 * On the user's very first visit after signing up, dashboard pages show
 * mock/demo data along with a banner explaining:
 *   "This is sample data — integrate your platforms to start seeing your data in action."
 *
 * Once the banner is dismissed (or on next login), pages switch to real
 * API data (which may be empty if no platforms are connected yet).
 *
 * localStorage key: "stratum_onboarding_demo_dismissed"
 *   - absent  → show demo data + banner
 *   - "true"  → show real data only
 */

import { useCallback, useState } from 'react';

const STORAGE_KEY = 'stratum_onboarding_demo_dismissed';

/**
 * Returns whether the onboarding demo should be shown, plus a dismiss action.
 *
 * @param hasRealData  Pass `true` when the API returned at least 1 real item
 *                     (e.g. campaigns.length > 0). When real data exists,
 *                     demo mode is automatically off regardless of localStorage.
 */
export function useDemoMode(hasRealData = false) {
  const [dismissed, setDismissed] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) === 'true';
  });

  // Demo data should show when:
  //   1. User has NOT dismissed the banner AND
  //   2. There is NO real data from the API
  const showDemoData = !dismissed && !hasRealData;

  // Whether to show the onboarding banner (only if demo data is visible)
  const showDemoBanner = showDemoData;

  const dismissDemo = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, 'true');
    setDismissed(true);
  }, []);

  return {
    /** Whether to display mock/demo data */
    showDemoData,
    /** Whether to render the onboarding demo banner */
    showDemoBanner,
    /** Call to permanently hide demo data */
    dismissDemo,
  };
}

export default useDemoMode;
