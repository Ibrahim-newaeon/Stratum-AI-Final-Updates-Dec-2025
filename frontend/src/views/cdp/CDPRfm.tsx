/**
 * CDP RFM Analysis View
 * Page for RFM (Recency, Frequency, Monetary) customer segmentation
 */

import { RFMDashboard } from '@/components/cdp/RFMDashboard'

export default function CDPRfm() {
  return (
    <div className="p-6">
      <RFMDashboard />
    </div>
  )
}
