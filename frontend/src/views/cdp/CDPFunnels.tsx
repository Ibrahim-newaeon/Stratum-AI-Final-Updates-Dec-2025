/**
 * CDP Funnel Builder View
 * Page for creating and analyzing conversion funnels
 */

import { FunnelBuilder } from '@/components/cdp/FunnelBuilder';

export default function CDPFunnels() {
  return (
    <div className="p-6">
      <FunnelBuilder />
    </div>
  );
}
