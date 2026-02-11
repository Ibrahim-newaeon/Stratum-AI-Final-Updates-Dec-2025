// =============================================================================
// Stratum AI - Predictive Churn Model (Enterprise Feature)
// =============================================================================

import { useMemo, useState } from 'react';
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  ArrowTrendingDownIcon,
  ArrowTrendingUpIcon,
  BellAlertIcon,
  BoltIcon,
  CheckCircleIcon,
  CpuChipIcon,
  CurrencyDollarIcon,
  DocumentChartBarIcon,
  ExclamationTriangleIcon,
  PauseIcon,
  PlayIcon,
  SparklesIcon,
  UserGroupIcon,
  UserMinusIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

interface ChurnPrediction {
  profileId: string;
  profileName: string;
  email: string;
  churnProbability: number;
  riskLevel: 'high' | 'medium' | 'low';
  predictedChurnDate: string;
  topFactors: ChurnFactor[];
  revenueAtRisk: number;
  lifetimeValue: number;
  lastActivityDate: string;
  segment: string;
  lifecycle: string;
  recommendedActions: string[];
}

interface ChurnFactor {
  name: string;
  impact: number; // -100 to 100
  direction: 'increases' | 'decreases';
  value: string;
}

interface ModelMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  auc: number;
  lastTrained: string;
  samplesUsed: number;
  featuresUsed: number;
  status: 'trained' | 'training' | 'needs_retrain';
}

interface ChurnStats {
  totalAtRisk: number;
  highRisk: number;
  mediumRisk: number;
  lowRisk: number;
  revenueAtRisk: number;
  predictedChurnRate: number;
  avgChurnProbability: number;
  interventionsActive: number;
}

interface InterventionCampaign {
  id: string;
  name: string;
  status: 'active' | 'paused' | 'completed';
  targetSegment: 'high' | 'medium' | 'low' | 'all';
  channel: 'email' | 'sms' | 'push' | 'in_app';
  profilesTargeted: number;
  conversions: number;
  startDate: string;
}

// =============================================================================
// Mock Data
// =============================================================================

const MOCK_MODEL_METRICS: ModelMetrics = {
  accuracy: 0.89,
  precision: 0.85,
  recall: 0.92,
  f1Score: 0.88,
  auc: 0.94,
  lastTrained: '2024-01-15T08:00:00Z',
  samplesUsed: 125840,
  featuresUsed: 47,
  status: 'trained',
};

const MOCK_STATS: ChurnStats = {
  totalAtRisk: 3247,
  highRisk: 847,
  mediumRisk: 1523,
  lowRisk: 877,
  revenueAtRisk: 892450,
  predictedChurnRate: 12.4,
  avgChurnProbability: 0.38,
  interventionsActive: 4,
};

const MOCK_PREDICTIONS: ChurnPrediction[] = [
  {
    profileId: '1',
    profileName: 'Sarah Johnson',
    email: 'sarah.johnson@example.com',
    churnProbability: 0.89,
    riskLevel: 'high',
    predictedChurnDate: '2024-02-15',
    topFactors: [
      { name: 'Days Since Last Purchase', impact: 85, direction: 'increases', value: '45 days' },
      { name: 'Support Tickets', impact: 72, direction: 'increases', value: '4 open' },
      { name: 'Email Open Rate', impact: -65, direction: 'decreases', value: '12%' },
    ],
    revenueAtRisk: 4500,
    lifetimeValue: 12350,
    lastActivityDate: '2023-12-15',
    segment: 'Enterprise',
    lifecycle: 'At Risk',
    recommendedActions: [
      'Personal outreach call',
      'Offer renewal discount',
      'Schedule product training',
    ],
  },
  {
    profileId: '2',
    profileName: 'Michael Chen',
    email: 'michael.chen@example.com',
    churnProbability: 0.76,
    riskLevel: 'high',
    predictedChurnDate: '2024-02-28',
    topFactors: [
      { name: 'Feature Usage Decline', impact: 78, direction: 'increases', value: '-60%' },
      { name: 'Login Frequency', impact: 70, direction: 'increases', value: '2x/month' },
      { name: 'Contract End Date', impact: 55, direction: 'increases', value: '30 days' },
    ],
    revenueAtRisk: 8900,
    lifetimeValue: 34200,
    lastActivityDate: '2024-01-08',
    segment: 'Mid-Market',
    lifecycle: 'At Risk',
    recommendedActions: [
      'Feature adoption webinar',
      'Success manager check-in',
      'Early renewal offer',
    ],
  },
  {
    profileId: '3',
    profileName: 'Emily Davis',
    email: 'emily.davis@example.com',
    churnProbability: 0.52,
    riskLevel: 'medium',
    predictedChurnDate: '2024-03-15',
    topFactors: [
      { name: 'NPS Score Decline', impact: 55, direction: 'increases', value: '6 → 4' },
      { name: 'API Calls', impact: 45, direction: 'increases', value: '-40%' },
      { name: 'Team Size', impact: -30, direction: 'decreases', value: '-2 users' },
    ],
    revenueAtRisk: 2400,
    lifetimeValue: 8750,
    lastActivityDate: '2024-01-12',
    segment: 'SMB',
    lifecycle: 'Active',
    recommendedActions: [
      'Send NPS follow-up survey',
      'Share new feature guide',
      'Invite to community',
    ],
  },
  {
    profileId: '4',
    profileName: 'James Wilson',
    email: 'james.wilson@example.com',
    churnProbability: 0.45,
    riskLevel: 'medium',
    predictedChurnDate: '2024-03-30',
    topFactors: [
      { name: 'Billing Issues', impact: 50, direction: 'increases', value: '2 failed' },
      { name: 'Response Time', impact: 40, direction: 'increases', value: '>48hrs' },
      { name: 'Feature Requests', impact: 35, direction: 'increases', value: '5 pending' },
    ],
    revenueAtRisk: 1800,
    lifetimeValue: 5400,
    lastActivityDate: '2024-01-14',
    segment: 'SMB',
    lifecycle: 'Active',
    recommendedActions: [
      'Resolve billing immediately',
      'Prioritize feature request',
      'Send product roadmap',
    ],
  },
  {
    profileId: '5',
    profileName: 'Lisa Anderson',
    email: 'lisa.anderson@example.com',
    churnProbability: 0.28,
    riskLevel: 'low',
    predictedChurnDate: '2024-05-01',
    topFactors: [
      { name: 'Industry Downturn', impact: 30, direction: 'increases', value: 'Retail' },
      { name: 'Usage Stability', impact: -25, direction: 'decreases', value: 'Consistent' },
      { name: 'Multi-Product', impact: -40, direction: 'decreases', value: '3 products' },
    ],
    revenueAtRisk: 900,
    lifetimeValue: 15800,
    lastActivityDate: '2024-01-16',
    segment: 'Enterprise',
    lifecycle: 'Loyal',
    recommendedActions: ['Monitor industry news', 'Share ROI report', 'Upsell opportunity'],
  },
];

const MOCK_INTERVENTIONS: InterventionCampaign[] = [
  {
    id: '1',
    name: 'High Risk Win-Back',
    status: 'active',
    targetSegment: 'high',
    channel: 'email',
    profilesTargeted: 847,
    conversions: 124,
    startDate: '2024-01-01',
  },
  {
    id: '2',
    name: 'Renewal Reminder',
    status: 'active',
    targetSegment: 'medium',
    channel: 'email',
    profilesTargeted: 1523,
    conversions: 312,
    startDate: '2024-01-05',
  },
  {
    id: '3',
    name: 'Feature Adoption Push',
    status: 'active',
    targetSegment: 'all',
    channel: 'in_app',
    profilesTargeted: 3247,
    conversions: 567,
    startDate: '2024-01-10',
  },
  {
    id: '4',
    name: 'Personal Outreach',
    status: 'active',
    targetSegment: 'high',
    channel: 'sms',
    profilesTargeted: 200,
    conversions: 45,
    startDate: '2024-01-12',
  },
];

const CHURN_TREND_DATA = [
  { month: 'Aug', rate: 14.2, predicted: 15.1 },
  { month: 'Sep', rate: 13.8, predicted: 14.5 },
  { month: 'Oct', rate: 13.2, predicted: 13.8 },
  { month: 'Nov', rate: 12.9, predicted: 13.2 },
  { month: 'Dec', rate: 12.6, predicted: 12.8 },
  { month: 'Jan', rate: 12.4, predicted: 12.4 },
];

// =============================================================================
// Sub-Components
// =============================================================================

function ModelHealthCard({ metrics }: { metrics: ModelMetrics }) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'trained':
        return 'text-green-500 bg-green-500/10';
      case 'training':
        return 'text-blue-500 bg-blue-500/10';
      case 'needs_retrain':
        return 'text-yellow-500 bg-yellow-500/10';
      default:
        return 'text-muted-foreground bg-muted';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'trained':
        return 'Model Trained';
      case 'training':
        return 'Training...';
      case 'needs_retrain':
        return 'Needs Retrain';
      default:
        return status;
    }
  };

  return (
    <div className="bg-card rounded-xl border p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <CpuChipIcon className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold">Churn Prediction Model</h3>
            <p className="text-sm text-muted-foreground">ML-powered risk scoring</p>
          </div>
        </div>
        <span
          className={cn(
            'px-3 py-1 rounded-full text-xs font-medium',
            getStatusColor(metrics.status)
          )}
        >
          {getStatusLabel(metrics.status)}
        </span>
      </div>

      <div className="grid grid-cols-5 gap-4 mb-4">
        <div className="text-center">
          <div className="text-2xl font-bold">{(metrics.accuracy * 100).toFixed(0)}%</div>
          <div className="text-xs text-muted-foreground">Accuracy</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold">{(metrics.precision * 100).toFixed(0)}%</div>
          <div className="text-xs text-muted-foreground">Precision</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold">{(metrics.recall * 100).toFixed(0)}%</div>
          <div className="text-xs text-muted-foreground">Recall</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold">{(metrics.f1Score * 100).toFixed(0)}%</div>
          <div className="text-xs text-muted-foreground">F1 Score</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold">{(metrics.auc * 100).toFixed(0)}%</div>
          <div className="text-xs text-muted-foreground">AUC-ROC</div>
        </div>
      </div>

      <div className="flex items-center justify-between text-sm text-muted-foreground pt-3 border-t">
        <span>Last trained: {new Date(metrics.lastTrained).toLocaleDateString()}</span>
        <span>
          {metrics.samplesUsed.toLocaleString()} samples, {metrics.featuresUsed} features
        </span>
        <button className="flex items-center gap-1 px-3 py-1 rounded-lg bg-primary text-primary-foreground text-xs hover:bg-primary/90">
          <ArrowPathIcon className="w-3 h-3" />
          Retrain Model
        </button>
      </div>
    </div>
  );
}

function ChurnFactorBar({ factor }: { factor: ChurnFactor }) {
  const isPositive = factor.direction === 'increases';
  const barWidth = Math.abs(factor.impact);

  return (
    <div className="flex items-center gap-3 text-sm">
      <div className="w-40 truncate" title={factor.name}>
        {factor.name}
      </div>
      <div className="flex-1 flex items-center gap-2">
        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all',
              isPositive ? 'bg-red-500' : 'bg-green-500'
            )}
            style={{ width: `${barWidth}%` }}
          />
        </div>
        <div
          className={cn('w-16 text-xs font-medium', isPositive ? 'text-red-500' : 'text-green-500')}
        >
          {isPositive ? '+' : '-'}
          {Math.abs(factor.impact)}%
        </div>
      </div>
      <div className="w-24 text-xs text-muted-foreground truncate" title={factor.value}>
        {factor.value}
      </div>
    </div>
  );
}

function PredictionCard({
  prediction,
  onViewDetails,
}: {
  prediction: ChurnPrediction;
  onViewDetails: () => void;
}) {
  const getRiskColor = (level: string) => {
    switch (level) {
      case 'high':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'medium':
        return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'low':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <div className="bg-card rounded-xl border p-5 hover:border-primary/50 transition-colors">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center text-primary-foreground font-semibold">
            {prediction.profileName.charAt(0)}
          </div>
          <div>
            <h4 className="font-semibold">{prediction.profileName}</h4>
            <p className="text-sm text-muted-foreground">{prediction.email}</p>
          </div>
        </div>
        <div
          className={cn(
            'px-3 py-1 rounded-full text-xs font-medium border',
            getRiskColor(prediction.riskLevel)
          )}
        >
          {prediction.riskLevel.toUpperCase()} RISK
        </div>
      </div>

      <div className="flex items-center gap-6 mb-4 text-sm">
        <div>
          <span className="text-muted-foreground">Churn Probability</span>
          <div className="font-semibold text-lg">
            {(prediction.churnProbability * 100).toFixed(0)}%
          </div>
        </div>
        <div>
          <span className="text-muted-foreground">Revenue at Risk</span>
          <div className="font-semibold text-lg text-red-500">
            ${prediction.revenueAtRisk.toLocaleString()}
          </div>
        </div>
        <div>
          <span className="text-muted-foreground">Predicted Churn</span>
          <div className="font-semibold">
            {new Date(prediction.predictedChurnDate).toLocaleDateString()}
          </div>
        </div>
      </div>

      <div className="mb-4">
        <div className="text-sm font-medium mb-2">Top Churn Factors</div>
        <div className="space-y-2">
          {prediction.topFactors.slice(0, 2).map((factor, i) => (
            <ChurnFactorBar key={i} factor={factor} />
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between pt-3 border-t">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="px-2 py-0.5 rounded bg-muted">{prediction.segment}</span>
          <span className="px-2 py-0.5 rounded bg-muted">{prediction.lifecycle}</span>
        </div>
        <button onClick={onViewDetails} className="text-sm text-primary hover:text-primary/80">
          View Details →
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export default function CDPPredictiveChurn() {
  const [riskFilter, setRiskFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');
  const [sortBy, setSortBy] = useState<'probability' | 'revenue' | 'date'>('probability');
  const [selectedPrediction, setSelectedPrediction] = useState<ChurnPrediction | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  const filteredPredictions = useMemo(() => {
    let filtered = [...MOCK_PREDICTIONS];

    if (riskFilter !== 'all') {
      filtered = filtered.filter((p) => p.riskLevel === riskFilter);
    }

    switch (sortBy) {
      case 'probability':
        filtered.sort((a, b) => b.churnProbability - a.churnProbability);
        break;
      case 'revenue':
        filtered.sort((a, b) => b.revenueAtRisk - a.revenueAtRisk);
        break;
      case 'date':
        filtered.sort(
          (a, b) =>
            new Date(a.predictedChurnDate).getTime() - new Date(b.predictedChurnDate).getTime()
        );
        break;
    }

    return filtered;
  }, [riskFilter, sortBy]);

  const handleViewDetails = (prediction: ChurnPrediction) => {
    setSelectedPrediction(prediction);
    setIsDetailModalOpen(true);
  };

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
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors">
            <ArrowDownTrayIcon className="w-4 h-4" />
            Export Report
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90">
            <BellAlertIcon className="w-4 h-4" />
            Configure Alerts
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-card rounded-xl border p-4">
          <div className="flex items-center justify-between">
            <div className="p-2 rounded-lg bg-red-500/10">
              <ExclamationTriangleIcon className="w-5 h-5 text-red-500" />
            </div>
            <span className="text-xs text-red-500 font-medium">
              {MOCK_STATS.highRisk} high risk
            </span>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold">{MOCK_STATS.totalAtRisk.toLocaleString()}</div>
            <div className="text-sm text-muted-foreground">Profiles at Risk</div>
          </div>
        </div>

        <div className="bg-card rounded-xl border p-4">
          <div className="flex items-center justify-between">
            <div className="p-2 rounded-lg bg-red-500/10">
              <CurrencyDollarIcon className="w-5 h-5 text-red-500" />
            </div>
            <span className="text-xs text-muted-foreground">Monthly</span>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold">
              ${(MOCK_STATS.revenueAtRisk / 1000).toFixed(0)}K
            </div>
            <div className="text-sm text-muted-foreground">Revenue at Risk</div>
          </div>
        </div>

        <div className="bg-card rounded-xl border p-4">
          <div className="flex items-center justify-between">
            <div className="p-2 rounded-lg bg-yellow-500/10">
              <ArrowTrendingDownIcon className="w-5 h-5 text-yellow-500" />
            </div>
            <span className="text-xs text-green-500 font-medium flex items-center gap-1">
              <ArrowTrendingUpIcon className="w-3 h-3" />
              -1.8%
            </span>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold">{MOCK_STATS.predictedChurnRate}%</div>
            <div className="text-sm text-muted-foreground">Predicted Churn Rate</div>
          </div>
        </div>

        <div className="bg-card rounded-xl border p-4">
          <div className="flex items-center justify-between">
            <div className="p-2 rounded-lg bg-green-500/10">
              <BoltIcon className="w-5 h-5 text-green-500" />
            </div>
            <span className="text-xs text-muted-foreground">Running</span>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold">{MOCK_STATS.interventionsActive}</div>
            <div className="text-sm text-muted-foreground">Active Interventions</div>
          </div>
        </div>
      </div>

      {/* Model Health */}
      <ModelHealthCard metrics={MOCK_MODEL_METRICS} />

      {/* Churn Trend Chart (Simplified) */}
      <div className="bg-card rounded-xl border p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Churn Rate Trend</h3>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-primary" />
              <span className="text-muted-foreground">Actual</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-primary/40 border-2 border-dashed border-primary" />
              <span className="text-muted-foreground">Predicted</span>
            </div>
          </div>
        </div>
        <div className="h-32 flex items-end gap-4">
          {CHURN_TREND_DATA.map((data, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-1">
              <div className="w-full flex items-end justify-center gap-1 h-24">
                <div
                  className="w-6 bg-primary rounded-t"
                  style={{ height: `${(data.rate / 16) * 100}%` }}
                  title={`Actual: ${data.rate}%`}
                />
                <div
                  className="w-6 bg-primary/40 rounded-t border-2 border-dashed border-primary"
                  style={{ height: `${(data.predicted / 16) * 100}%` }}
                  title={`Predicted: ${data.predicted}%`}
                />
              </div>
              <span className="text-xs text-muted-foreground">{data.month}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Active Interventions */}
      <div className="bg-card rounded-xl border p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Active Retention Campaigns</h3>
          <button className="text-sm text-primary hover:text-primary/80">+ New Campaign</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-sm text-muted-foreground border-b">
                <th className="text-left py-2 font-medium">Campaign</th>
                <th className="text-left py-2 font-medium">Target</th>
                <th className="text-left py-2 font-medium">Channel</th>
                <th className="text-right py-2 font-medium">Targeted</th>
                <th className="text-right py-2 font-medium">Conversions</th>
                <th className="text-right py-2 font-medium">Rate</th>
                <th className="text-center py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_INTERVENTIONS.map((campaign) => (
                <tr key={campaign.id} className="border-b last:border-0">
                  <td className="py-3 font-medium">{campaign.name}</td>
                  <td className="py-3">
                    <span
                      className={cn(
                        'px-2 py-0.5 rounded text-xs capitalize',
                        campaign.targetSegment === 'high'
                          ? 'bg-red-500/10 text-red-500'
                          : campaign.targetSegment === 'medium'
                            ? 'bg-yellow-500/10 text-yellow-500'
                            : campaign.targetSegment === 'low'
                              ? 'bg-green-500/10 text-green-500'
                              : 'bg-blue-500/10 text-blue-500'
                      )}
                    >
                      {campaign.targetSegment} risk
                    </span>
                  </td>
                  <td className="py-3 capitalize">{campaign.channel.replace('_', ' ')}</td>
                  <td className="py-3 text-right">{campaign.profilesTargeted.toLocaleString()}</td>
                  <td className="py-3 text-right text-green-500">
                    {campaign.conversions.toLocaleString()}
                  </td>
                  <td className="py-3 text-right font-medium">
                    {((campaign.conversions / campaign.profilesTargeted) * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 text-center">
                    <button
                      className={cn(
                        'p-1.5 rounded-lg',
                        campaign.status === 'active'
                          ? 'bg-green-500/10 text-green-500'
                          : 'bg-muted text-muted-foreground'
                      )}
                    >
                      {campaign.status === 'active' ? (
                        <PauseIcon className="w-4 h-4" />
                      ) : (
                        <PlayIcon className="w-4 h-4" />
                      )}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Risk Filters & Sort */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Risk Level:</span>
          {['all', 'high', 'medium', 'low'].map((level) => (
            <button
              key={level}
              onClick={() => setRiskFilter(level as typeof riskFilter)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm capitalize transition-colors',
                riskFilter === level
                  ? level === 'high'
                    ? 'bg-red-500 text-white'
                    : level === 'medium'
                      ? 'bg-yellow-500 text-white'
                      : level === 'low'
                        ? 'bg-green-500 text-white'
                        : 'bg-primary text-primary-foreground'
                  : 'bg-muted hover:bg-muted/80'
              )}
            >
              {level}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Sort by:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="px-3 py-1.5 rounded-lg border bg-background text-sm"
          >
            <option value="probability">Churn Probability</option>
            <option value="revenue">Revenue at Risk</option>
            <option value="date">Predicted Date</option>
          </select>
        </div>
      </div>

      {/* Predictions Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filteredPredictions.map((prediction) => (
          <PredictionCard
            key={prediction.profileId}
            prediction={prediction}
            onViewDetails={() => handleViewDetails(prediction)}
          />
        ))}
      </div>

      {filteredPredictions.length === 0 && (
        <div className="text-center py-12 bg-card rounded-xl border">
          <UserGroupIcon className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">No predictions match your filters</h3>
          <p className="text-muted-foreground">Try adjusting your risk level filter</p>
        </div>
      )}

      {/* Detail Modal */}
      {isDetailModalOpen && selectedPrediction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-card rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center text-primary-foreground font-semibold text-lg">
                    {selectedPrediction.profileName.charAt(0)}
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold">{selectedPrediction.profileName}</h2>
                    <p className="text-muted-foreground">{selectedPrediction.email}</p>
                  </div>
                </div>
                <button
                  onClick={() => setIsDetailModalOpen(false)}
                  className="p-2 hover:bg-muted rounded-lg"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Key Metrics */}
              <div className="grid grid-cols-4 gap-4">
                <div className="text-center p-3 rounded-lg bg-red-500/10">
                  <div className="text-2xl font-bold text-red-500">
                    {(selectedPrediction.churnProbability * 100).toFixed(0)}%
                  </div>
                  <div className="text-xs text-muted-foreground">Churn Probability</div>
                </div>
                <div className="text-center p-3 rounded-lg bg-muted">
                  <div className="text-2xl font-bold">
                    ${selectedPrediction.revenueAtRisk.toLocaleString()}
                  </div>
                  <div className="text-xs text-muted-foreground">Revenue at Risk</div>
                </div>
                <div className="text-center p-3 rounded-lg bg-muted">
                  <div className="text-2xl font-bold">
                    ${selectedPrediction.lifetimeValue.toLocaleString()}
                  </div>
                  <div className="text-xs text-muted-foreground">Lifetime Value</div>
                </div>
                <div className="text-center p-3 rounded-lg bg-muted">
                  <div className="text-2xl font-bold">
                    {new Date(selectedPrediction.predictedChurnDate).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </div>
                  <div className="text-xs text-muted-foreground">Predicted Churn</div>
                </div>
              </div>

              {/* Churn Factors */}
              <div>
                <h3 className="font-semibold mb-3">Churn Risk Factors</h3>
                <div className="space-y-3">
                  {selectedPrediction.topFactors.map((factor, i) => (
                    <ChurnFactorBar key={i} factor={factor} />
                  ))}
                </div>
              </div>

              {/* Recommended Actions */}
              <div>
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <SparklesIcon className="w-5 h-5 text-primary" />
                  Recommended Actions
                </h3>
                <div className="space-y-2">
                  {selectedPrediction.recommendedActions.map((action, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 p-3 rounded-lg bg-primary/5 border border-primary/20"
                    >
                      <CheckCircleIcon className="w-5 h-5 text-primary" />
                      <span>{action}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-3 pt-4 border-t">
                <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90">
                  <BellAlertIcon className="w-4 h-4" />
                  Add to Intervention
                </button>
                <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted">
                  <DocumentChartBarIcon className="w-4 h-4" />
                  View Full Profile
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
