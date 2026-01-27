/**
 * CDP Consent Management View
 * Page for managing privacy consent
 */

import { ConsentManager } from '@/components/cdp/ConsentManager';

export default function CDPConsent() {
  return (
    <div className="p-6">
      <ConsentManager />
    </div>
  );
}
