import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Calculator,
  DollarSign,
  Info,
  RefreshCw,
  Target,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { cn, formatCompactNumber, formatCurrency, formatPercent } from '@/lib/utils';
import { SmartTooltip } from '../guide/SmartTooltip';

interface SimulationInput {
  budgetChange: number; // -50 to +100 percent
  bidChange: number; // -30 to +50 percent
  targetAudienceChange: number; // -50 to +100 percent
}

interface SimulationResult {
  estimatedSpend: number;
  estimatedRevenue: number;
  estimatedROAS: number;
  estimatedImpressions: number;
  estimatedClicks: number;
  estimatedConversions: number;
  confidence: number;
}

interface CampaignBaseline {
  name: string;
  currentSpend: number;
  currentRevenue: number;
  currentROAS: number;
  currentImpressions: number;
  currentClicks: number;
  currentConversions: number;
}

interface SimulateSliderProps {
  campaign?: CampaignBaseline;
  onSimulate?: (input: SimulationInput, result: SimulationResult) => void;
  className?: string;
}

const DEFAULT_CAMPAIGN: CampaignBaseline = {
  name: 'All Campaigns',
  currentSpend: 15000,
  currentRevenue: 52500,
  currentROAS: 3.5,
  currentImpressions: 2500000,
  currentClicks: 75000,
  currentConversions: 1875,
};

export function SimulateSlider({
  campaign = DEFAULT_CAMPAIGN,
  onSimulate,
  className,
}: SimulateSliderProps) {
  const { t } = useTranslation();
  const [inputs, setInputs] = useState<SimulationInput>({
    budgetChange: 0,
    bidChange: 0,
    targetAudienceChange: 0,
  });
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);

  // Simulate effect of changes using a simplified model
  const runSimulation = useCallback(() => {
    setIsSimulating(true);

    // Simulated delay for realism
    setTimeout(() => {
      const { budgetChange, bidChange, targetAudienceChange } = inputs;

      // Calculate multipliers
      const budgetMultiplier = 1 + budgetChange / 100;
      const bidMultiplier = 1 + bidChange / 100;
      const audienceMultiplier = 1 + targetAudienceChange / 100;

      // Budget increases spend linearly
      const newSpend = campaign.currentSpend * budgetMultiplier;

      // Impressions scale with budget and audience, diminishing returns
      const impressionGrowth = Math.pow(budgetMultiplier, 0.7) * Math.pow(audienceMultiplier, 0.5);
      const newImpressions = campaign.currentImpressions * impressionGrowth;

      // Higher bids improve position but have diminishing returns
      const bidEfficiency = bidMultiplier > 1 ? Math.pow(bidMultiplier, 0.6) : bidMultiplier;
      const ctrImprovement = bidEfficiency;

      // Clicks depend on impressions and CTR (influenced by bid)
      const newClicks =
        newImpressions * (campaign.currentClicks / campaign.currentImpressions) * ctrImprovement;

      // Conversions scale with clicks and slight efficiency loss at higher volumes
      const conversionEfficiency = Math.pow(budgetMultiplier, -0.1); // diminishing returns
      const newConversions =
        newClicks * (campaign.currentConversions / campaign.currentClicks) * conversionEfficiency;

      // Revenue scales with conversions
      const newRevenue = newConversions * (campaign.currentRevenue / campaign.currentConversions);

      // Calculate new ROAS
      const newROAS = newSpend > 0 ? newRevenue / newSpend : 0;

      // Confidence decreases with larger changes
      const changesMagnitude =
        Math.abs(budgetChange) + Math.abs(bidChange) + Math.abs(targetAudienceChange);
      const confidence = Math.max(60, 95 - changesMagnitude * 0.3);

      const simulationResult: SimulationResult = {
        estimatedSpend: newSpend,
        estimatedRevenue: newRevenue,
        estimatedROAS: newROAS,
        estimatedImpressions: Math.round(newImpressions),
        estimatedClicks: Math.round(newClicks),
        estimatedConversions: Math.round(newConversions),
        confidence: Math.round(confidence),
      };

      setResult(simulationResult);
      onSimulate?.(inputs, simulationResult);
      setIsSimulating(false);
    }, 500);
  }, [inputs, campaign, onSimulate]);

  // Run simulation when inputs change
  useEffect(() => {
    const hasChanges =
      inputs.budgetChange !== 0 || inputs.bidChange !== 0 || inputs.targetAudienceChange !== 0;
    if (hasChanges) {
      const timer = setTimeout(runSimulation, 300);
      return () => clearTimeout(timer);
    } else {
      setResult(null);
    }
  }, [inputs, runSimulation]);

  const resetInputs = () => {
    setInputs({
      budgetChange: 0,
      bidChange: 0,
      targetAudienceChange: 0,
    });
    setResult(null);
  };

  const renderSlider = (
    label: string,
    value: number,
    min: number,
    max: number,
    onChange: (value: number) => void,
    tooltip: string
  ) => (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <SmartTooltip content={tooltip} position="right">
          <span className="text-sm font-medium flex items-center gap-1">
            {label}
            <Info className="w-3.5 h-3.5 text-muted-foreground" />
          </span>
        </SmartTooltip>
        <span
          className={cn(
            'text-sm font-semibold',
            value > 0 && 'text-green-500',
            value < 0 && 'text-red-500'
          )}
        >
          {value > 0 ? '+' : ''}
          {value}%
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
      />
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{min}%</span>
        <span>{max}%</span>
      </div>
    </div>
  );

  const getChangeIndicator = (current: number, estimated: number) => {
    const change = ((estimated - current) / current) * 100;
    if (Math.abs(change) < 0.5) return null;

    return (
      <span
        className={cn(
          'flex items-center gap-0.5 text-xs',
          change > 0 ? 'text-green-500' : 'text-red-500'
        )}
      >
        {change > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
        {change > 0 ? '+' : ''}
        {formatPercent(change)}
      </span>
    );
  };

  return (
    <div id="simulator-widget" className={cn('rounded-xl border bg-card p-5', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-primary/10">
            <Calculator className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold">{t('simulator.title')}</h3>
            <p className="text-xs text-muted-foreground">{campaign.name}</p>
          </div>
        </div>
        <button
          onClick={resetInputs}
          className="p-2 rounded-lg hover:bg-muted transition-colors"
          title="Reset"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Sliders */}
      <div className="space-y-5 mb-6">
        {renderSlider(
          t('simulator.budget'),
          inputs.budgetChange,
          -50,
          100,
          (value) => setInputs((prev) => ({ ...prev, budgetChange: value })),
          t('simulator.budgetTooltip')
        )}
        {renderSlider(
          t('simulator.bid'),
          inputs.bidChange,
          -30,
          50,
          (value) => setInputs((prev) => ({ ...prev, bidChange: value })),
          t('simulator.bidTooltip')
        )}
        {renderSlider(
          t('simulator.audience'),
          inputs.targetAudienceChange,
          -50,
          100,
          (value) => setInputs((prev) => ({ ...prev, targetAudienceChange: value })),
          t('simulator.audienceTooltip')
        )}
      </div>

      {/* Results */}
      {(result || isSimulating) && (
        <div className="border-t pt-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium">{t('simulator.projectedResults')}</span>
            {result && (
              <span className="text-xs text-muted-foreground">
                {result.confidence}% {t('simulator.confidence')}
              </span>
            )}
          </div>

          {isSimulating ? (
            <div className="grid grid-cols-3 gap-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="p-3 rounded-lg bg-muted/50 animate-pulse">
                  <div className="h-3 w-12 bg-muted rounded mb-2" />
                  <div className="h-5 w-16 bg-muted rounded" />
                </div>
              ))}
            </div>
          ) : result ? (
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                  <DollarSign className="w-3 h-3" />
                  {t('simulator.spend')}
                </div>
                <div className="font-semibold">{formatCurrency(result.estimatedSpend)}</div>
                {getChangeIndicator(campaign.currentSpend, result.estimatedSpend)}
              </div>

              <div className="p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                  <TrendingUp className="w-3 h-3" />
                  {t('simulator.revenue')}
                </div>
                <div className="font-semibold">{formatCurrency(result.estimatedRevenue)}</div>
                {getChangeIndicator(campaign.currentRevenue, result.estimatedRevenue)}
              </div>

              <div className="p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                  <Target className="w-3 h-3" />
                  ROAS
                </div>
                <div className="font-semibold">{result.estimatedROAS.toFixed(2)}x</div>
                {getChangeIndicator(campaign.currentROAS, result.estimatedROAS)}
              </div>
            </div>
          ) : null}

          {result && (
            <div className="mt-3 grid grid-cols-3 gap-3 text-center">
              <div>
                <div className="text-xs text-muted-foreground">{t('simulator.impressions')}</div>
                <div className="text-sm font-medium">
                  {formatCompactNumber(result.estimatedImpressions)}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">{t('simulator.clicks')}</div>
                <div className="text-sm font-medium">
                  {formatCompactNumber(result.estimatedClicks)}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">{t('simulator.conversions')}</div>
                <div className="text-sm font-medium">
                  {formatCompactNumber(result.estimatedConversions)}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* No changes message */}
      {!result && !isSimulating && (
        <div className="border-t pt-4 text-center text-sm text-muted-foreground">
          <p>{t('simulator.adjustSliders')}</p>
        </div>
      )}
    </div>
  );
}

export default SimulateSlider;
