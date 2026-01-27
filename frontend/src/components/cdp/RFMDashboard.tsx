/**
 * CDP RFM Dashboard Component
 * Visualize RFM (Recency, Frequency, Monetary) analysis and customer segmentation
 */

import { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Calendar,
  ChevronRight,
  Clock,
  Crown,
  DollarSign,
  Frown,
  Heart,
  Loader2,
  Moon,
  PieChart,
  RefreshCw,
  Search,
  Star,
  Target,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  RFMSegment,
  useCDPProfile,
  useComputeRFMBatch,
  useProfileRFM,
  useRFMSummary,
} from '@/api/cdp';

// RFM Segment configuration
const RFM_SEGMENTS: Record<
  RFMSegment,
  {
    label: string;
    description: string;
    icon: React.ReactNode;
    color: string;
    bgColor: string;
    actionTip: string;
  }
> = {
  champions: {
    label: 'Champions',
    description: 'Best customers who bought recently, buy often and spend the most',
    icon: <Crown className="w-5 h-5" />,
    color: 'text-amber-500',
    bgColor: 'bg-amber-500/10',
    actionTip: 'Reward them, make them brand ambassadors',
  },
  loyal_customers: {
    label: 'Loyal Customers',
    description: 'Customers who buy often and spend good money',
    icon: <Heart className="w-5 h-5" />,
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    actionTip: 'Upsell higher value products, ask for reviews',
  },
  potential_loyalists: {
    label: 'Potential Loyalists',
    description: 'Recent customers with average frequency',
    icon: <Star className="w-5 h-5" />,
    color: 'text-purple-500',
    bgColor: 'bg-purple-500/10',
    actionTip: 'Offer membership/loyalty program, recommend products',
  },
  new_customers: {
    label: 'New Customers',
    description: 'Bought recently but not often',
    icon: <Zap className="w-5 h-5" />,
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    actionTip: 'Provide onboarding support, special offers',
  },
  promising: {
    label: 'Promising',
    description: 'Recent shoppers but not much spent',
    icon: <TrendingUp className="w-5 h-5" />,
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    actionTip: 'Create brand awareness, offer free trials',
  },
  need_attention: {
    label: 'Need Attention',
    description: 'Above average recency, frequency and monetary',
    icon: <AlertTriangle className="w-5 h-5" />,
    color: 'text-orange-500',
    bgColor: 'bg-orange-500/10',
    actionTip: 'Make limited-time offers, recommend based on past',
  },
  about_to_sleep: {
    label: 'About to Sleep',
    description: 'Below average recency, frequency and monetary',
    icon: <Moon className="w-5 h-5" />,
    color: 'text-indigo-500',
    bgColor: 'bg-indigo-500/10',
    actionTip: 'Share valuable resources, recommend popular products',
  },
  at_risk: {
    label: 'At Risk',
    description: 'Spent big money, purchased often but long time ago',
    icon: <AlertTriangle className="w-5 h-5" />,
    color: 'text-red-600',
    bgColor: 'bg-red-600/10',
    actionTip: 'Send personalized emails, offer renewals',
  },
  cannot_lose: {
    label: "Can't Lose",
    description: 'Made biggest purchases and often, but long time ago',
    icon: <Heart className="w-5 h-5" />,
    color: 'text-pink-500',
    bgColor: 'bg-pink-500/10',
    actionTip: 'Win them back via renewals, newer products',
  },
  hibernating: {
    label: 'Hibernating',
    description: 'Last purchase was long ago, low spenders',
    icon: <Moon className="w-5 h-5" />,
    color: 'text-gray-500',
    bgColor: 'bg-gray-500/10',
    actionTip: 'Offer relevant products, special discounts',
  },
  lost: {
    label: 'Lost',
    description: 'Lowest recency, frequency and monetary',
    icon: <Frown className="w-5 h-5" />,
    color: 'text-gray-400',
    bgColor: 'bg-gray-400/10',
    actionTip: 'Revive interest with reach out, ignore otherwise',
  },
  other: {
    label: 'Other',
    description: 'Customers that do not fit other segments',
    icon: <Users className="w-5 h-5" />,
    color: 'text-slate-500',
    bgColor: 'bg-slate-500/10',
    actionTip: 'Analyze individually for better targeting',
  },
};

// RFM Score visualization
interface RFMScoreBarProps {
  label: string;
  score: number;
  rawValue: string;
}

function RFMScoreBar({ label, score, rawValue }: RFMScoreBarProps) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">{rawValue}</span>
      </div>
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <div
            key={n}
            className={cn(
              'flex-1 h-2 rounded-full transition-colors',
              n <= score ? 'bg-primary' : 'bg-muted'
            )}
          />
        ))}
      </div>
      <div className="text-xs text-muted-foreground text-right">Score: {score}/5</div>
    </div>
  );
}

// Segment card component
interface SegmentCardProps {
  segment: RFMSegment;
  count: number;
  totalProfiles: number;
  isSelected: boolean;
  onClick: () => void;
}

function SegmentCard({ segment, count, totalProfiles, isSelected, onClick }: SegmentCardProps) {
  const config = RFM_SEGMENTS[segment];
  const percentage = totalProfiles > 0 ? (count / totalProfiles) * 100 : 0;

  return (
    <div
      className={cn(
        'p-4 rounded-xl border cursor-pointer transition-all hover:shadow-md',
        isSelected ? 'border-primary ring-2 ring-primary/20' : 'hover:border-primary/50'
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className={cn('p-2 rounded-lg', config.bgColor, config.color)}>{config.icon}</div>
        <span className="text-2xl font-bold">{count.toLocaleString()}</span>
      </div>
      <h4 className="font-semibold mb-1">{config.label}</h4>
      <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{config.description}</p>
      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
        <div
          className={cn('h-full transition-all', config.bgColor.replace('/10', ''))}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="text-xs text-muted-foreground mt-1">{percentage.toFixed(1)}% of profiles</div>
    </div>
  );
}

// Profile RFM details view
interface ProfileRFMViewProps {
  profileId: string;
  onBack: () => void;
}

function ProfileRFMView({ profileId, onBack }: ProfileRFMViewProps) {
  const { data: profile, isLoading: profileLoading } = useCDPProfile(profileId);
  const { data: rfm, isLoading: rfmLoading } = useProfileRFM(profileId);

  const isLoading = profileLoading || rfmLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!rfm || !profile) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
        <h3 className="font-semibold mb-2">RFM Data Not Available</h3>
        <p className="text-sm text-muted-foreground mb-4">
          This profile doesn't have RFM scores yet
        </p>
        <button onClick={onBack} className="text-primary hover:underline">
          Back to Dashboard
        </button>
      </div>
    );
  }

  const segmentConfig = RFM_SEGMENTS[rfm.rfm_segment];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="p-2 rounded-lg hover:bg-muted transition-colors">
          <ChevronRight className="w-5 h-5 rotate-180" />
        </button>
        <div>
          <h2 className="text-xl font-semibold">Profile RFM Analysis</h2>
          <p className="text-sm text-muted-foreground">
            {profile.external_id || profile.id.slice(0, 12) + '...'}
          </p>
        </div>
      </div>

      {/* Segment badge */}
      <div className={cn('p-6 rounded-xl border', segmentConfig.bgColor)}>
        <div className="flex items-center gap-4">
          <div className={cn('p-3 rounded-xl bg-background', segmentConfig.color)}>
            {segmentConfig.icon}
          </div>
          <div>
            <div className="text-sm text-muted-foreground">RFM Segment</div>
            <div className="text-2xl font-bold">{segmentConfig.label}</div>
            <p className="text-sm text-muted-foreground mt-1">{segmentConfig.description}</p>
          </div>
        </div>
        <div className="mt-4 p-3 rounded-lg bg-background/80">
          <div className="text-xs font-medium text-muted-foreground mb-1">Recommended Action</div>
          <p className="text-sm">{segmentConfig.actionTip}</p>
        </div>
      </div>

      {/* RFM Scores */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border bg-card">
          <RFMScoreBar
            label="Recency"
            score={rfm.recency_score}
            rawValue={`${rfm.recency_days} days ago`}
          />
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <RFMScoreBar
            label="Frequency"
            score={rfm.frequency_score}
            rawValue={`${rfm.frequency} purchases`}
          />
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <RFMScoreBar
            label="Monetary"
            score={rfm.monetary_score}
            rawValue={`$${rfm.monetary.toLocaleString()}`}
          />
        </div>
      </div>

      {/* Combined RFM Score */}
      <div className="p-6 rounded-xl border bg-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Combined RFM Score</h3>
          <span className="text-3xl font-bold text-primary">{rfm.rfm_score}</span>
        </div>
        <div className="h-3 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-primary transition-all"
            style={{ width: `${(rfm.rfm_score / 15) * 100}%` }}
          />
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground mt-2">
          <span>3 (Low)</span>
          <span>9 (Average)</span>
          <span>15 (High)</span>
        </div>
      </div>

      {/* Profile stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground">Lifecycle</div>
          <div className="text-lg font-semibold capitalize">{profile.lifecycle_stage}</div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground">Total Events</div>
          <div className="text-lg font-semibold">{profile.total_events.toLocaleString()}</div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground">Purchases</div>
          <div className="text-lg font-semibold">{profile.total_purchases.toLocaleString()}</div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground">Total Revenue</div>
          <div className="text-lg font-semibold">${profile.total_revenue.toLocaleString()}</div>
        </div>
      </div>

      <div className="text-xs text-muted-foreground flex items-center gap-2">
        <Clock className="w-3 h-3" />
        Analysis window: {rfm.analysis_window_days} days · Calculated:{' '}
        {new Date(rfm.calculated_at).toLocaleString()}
      </div>
    </div>
  );
}

export function RFMDashboard() {
  const [selectedSegment, setSelectedSegment] = useState<RFMSegment | null>(null);
  const [searchProfileId, setSearchProfileId] = useState('');
  const [viewingProfileId, setViewingProfileId] = useState<string | null>(null);

  const { data: summary, isLoading, refetch } = useRFMSummary();
  const computeMutation = useComputeRFMBatch();

  const handleCompute = async () => {
    await computeMutation.mutateAsync(undefined);
    refetch();
  };

  if (viewingProfileId) {
    return <ProfileRFMView profileId={viewingProfileId} onBack={() => setViewingProfileId(null)} />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Target className="w-6 h-6 text-primary" />
            RFM Analysis
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Customer segmentation based on Recency, Frequency, and Monetary value
          </p>
        </div>
        <button
          onClick={handleCompute}
          disabled={computeMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {computeMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Recalculate RFM
        </button>
      </div>

      {/* Profile lookup */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          value={searchProfileId}
          onChange={(e) => setSearchProfileId(e.target.value)}
          placeholder="Enter Profile ID to view individual RFM analysis..."
          className="w-full pl-10 pr-24 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && searchProfileId) {
              setViewingProfileId(searchProfileId);
            }
          }}
        />
        {searchProfileId && (
          <button
            onClick={() => setViewingProfileId(searchProfileId)}
            className="absolute right-3 top-1/2 -translate-y-1/2 px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-sm hover:bg-primary/90 transition-colors"
          >
            View RFM
          </button>
        )}
      </div>

      {/* Summary stats */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : summary ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border bg-card">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <Users className="w-4 h-4" />
                Total Profiles
              </div>
              <div className="text-2xl font-bold">{summary.total_profiles.toLocaleString()}</div>
            </div>
            <div className="p-4 rounded-xl border bg-card">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <Activity className="w-4 h-4" />
                With RFM Data
              </div>
              <div className="text-2xl font-bold">{summary.profiles_with_rfm.toLocaleString()}</div>
            </div>
            <div className="p-4 rounded-xl border bg-card">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <PieChart className="w-4 h-4" />
                Coverage
              </div>
              <div className="text-2xl font-bold text-green-500">
                {summary.coverage_pct.toFixed(1)}%
              </div>
            </div>
            <div className="p-4 rounded-xl border bg-card">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <BarChart3 className="w-4 h-4" />
                Segments
              </div>
              <div className="text-2xl font-bold">
                {Object.values(summary.segment_distribution).filter((v) => v > 0).length}
              </div>
            </div>
          </div>

          {/* Segment distribution */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">Customer Segments</h3>
              {selectedSegment && (
                <button
                  onClick={() => setSelectedSegment(null)}
                  className="text-sm text-primary hover:underline"
                >
                  Clear selection
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {(Object.entries(summary.segment_distribution) as [RFMSegment, number][])
                .sort((a, b) => b[1] - a[1])
                .map(([segment, count]) => (
                  <SegmentCard
                    key={segment}
                    segment={segment}
                    count={count}
                    totalProfiles={summary.profiles_with_rfm}
                    isSelected={selectedSegment === segment}
                    onClick={() => setSelectedSegment(selectedSegment === segment ? null : segment)}
                  />
                ))}
            </div>
          </div>

          {/* Selected segment details */}
          {selectedSegment && (
            <div className="p-6 rounded-xl border bg-card">
              <div className="flex items-start gap-4">
                <div
                  className={cn(
                    'p-3 rounded-xl',
                    RFM_SEGMENTS[selectedSegment].bgColor,
                    RFM_SEGMENTS[selectedSegment].color
                  )}
                >
                  {RFM_SEGMENTS[selectedSegment].icon}
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold">{RFM_SEGMENTS[selectedSegment].label}</h3>
                  <p className="text-muted-foreground mt-1">
                    {RFM_SEGMENTS[selectedSegment].description}
                  </p>
                  <div className="mt-4 p-3 rounded-lg bg-primary/5 border border-primary/20">
                    <div className="text-sm font-medium text-primary mb-1">Recommended Action</div>
                    <p className="text-sm">{RFM_SEGMENTS[selectedSegment].actionTip}</p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold">
                    {summary.segment_distribution[selectedSegment].toLocaleString()}
                  </div>
                  <div className="text-sm text-muted-foreground">profiles</div>
                </div>
              </div>
            </div>
          )}

          {/* RFM Explanation */}
          <div className="p-4 rounded-xl border bg-muted/30">
            <h3 className="font-semibold mb-3">Understanding RFM Scores</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <div className="font-medium flex items-center gap-2 mb-1">
                  <Calendar className="w-4 h-4 text-primary" />
                  Recency (R)
                </div>
                <p className="text-muted-foreground">
                  How recently did the customer make a purchase? Lower is better.
                </p>
              </div>
              <div>
                <div className="font-medium flex items-center gap-2 mb-1">
                  <RefreshCw className="w-4 h-4 text-primary" />
                  Frequency (F)
                </div>
                <p className="text-muted-foreground">
                  How often does the customer make purchases? Higher is better.
                </p>
              </div>
              <div>
                <div className="font-medium flex items-center gap-2 mb-1">
                  <DollarSign className="w-4 h-4 text-primary" />
                  Monetary (M)
                </div>
                <p className="text-muted-foreground">
                  How much does the customer spend? Higher is better.
                </p>
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="text-center py-12 bg-card border rounded-xl">
          <Target className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="font-semibold mb-2">No RFM Data Available</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Calculate RFM scores to segment your customers
          </p>
          <button
            onClick={handleCompute}
            disabled={computeMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            {computeMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Calculate RFM
          </button>
        </div>
      )}
    </div>
  );
}

export default RFMDashboard;
