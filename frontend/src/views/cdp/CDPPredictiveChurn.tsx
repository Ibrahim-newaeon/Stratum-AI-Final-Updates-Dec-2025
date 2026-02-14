// =============================================================================
// Stratum AI - Predictive Churn Model (Enterprise Feature)
// =============================================================================

import {
  CpuChipIcon,
  SparklesIcon,
  UserGroupIcon,
  UserMinusIcon,
} from '@heroicons/react/24/outline';

// =============================================================================
// Main Component
// =============================================================================

export default function CDPPredictiveChurn() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <UserMinusIcon className="w-8 h-8 text-red-500" />
            Predictive Churn Model
          </h1>
          <p className="text-muted-foreground mt-1">
            ML-powered churn prediction to identify at-risk customers before they leave
          </p>
        </div>
      </div>

      {/* Empty State */}
      <div className="bg-card rounded-xl border p-12 text-center">
        <div className="mx-auto w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-6">
          <CpuChipIcon className="w-8 h-8 text-primary" />
        </div>
        <h2 className="text-xl font-semibold mb-3">Churn Prediction Model Not Yet Trained</h2>
        <p className="text-muted-foreground max-w-md mx-auto mb-6">
          This feature requires sufficient CDP profile data and event history to train a churn
          prediction model. Once enough data is collected, the model will automatically begin
          training and predictions will appear here.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl mx-auto mt-8">
          <div className="p-4 rounded-lg bg-muted/50 border text-left">
            <div className="flex items-center gap-2 mb-2">
              <UserGroupIcon className="w-5 h-5 text-primary" />
              <span className="font-medium text-sm">Step 1</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Ingest customer profiles and event data through the CDP
            </p>
          </div>
          <div className="p-4 rounded-lg bg-muted/50 border text-left">
            <div className="flex items-center gap-2 mb-2">
              <CpuChipIcon className="w-5 h-5 text-primary" />
              <span className="font-medium text-sm">Step 2</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Model auto-trains once 1,000+ profiles with activity history exist
            </p>
          </div>
          <div className="p-4 rounded-lg bg-muted/50 border text-left">
            <div className="flex items-center gap-2 mb-2">
              <SparklesIcon className="w-5 h-5 text-primary" />
              <span className="font-medium text-sm">Step 3</span>
            </div>
            <p className="text-sm text-muted-foreground">
              View risk scores, churn factors, and recommended retention actions
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
