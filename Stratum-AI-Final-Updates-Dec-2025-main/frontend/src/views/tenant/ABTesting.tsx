/**
 * Stratum AI - A/B Testing Page
 *
 * Comprehensive A/B testing framework with power analysis, LTV impact, and statistical results.
 */

import { useState } from 'react';
import {
  ABTest,
  TestStatus,
  TestType,
  useABTest,
  useABTestResults,
  useABTests,
  useLTVImpact,
  usePauseABTest,
  usePowerAnalysis,
  useStartABTest,
  useStopABTest,
} from '@/api/abTesting';
import {
  ArrowTrendingUpIcon,
  BeakerIcon,
  CalculatorIcon,
  ChartBarIcon,
  CheckCircleIcon,
  LightBulbIcon,
  PauseIcon,
  PlayIcon,
  PlusIcon,
  SparklesIcon,
  StopIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

type TabType = 'active' | 'completed' | 'drafts' | 'power-analysis';

const statusColors: Record<TestStatus, string> = {
  draft: 'bg-gray-100 dark:bg-gray-900/20 text-gray-700 dark:text-gray-300',
  running: 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300',
  paused: 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300',
  completed: 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
  stopped: 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300',
};

const testTypeLabels: Record<TestType, string> = {
  campaign: 'Campaign',
  creative: 'Creative',
  audience: 'Audience',
  landing_page: 'Landing Page',
  bid_strategy: 'Bid Strategy',
};

export default function ABTesting() {
  const [activeTab, setActiveTab] = useState<TabType>('active');
  const [selectedTestId, setSelectedTestId] = useState<string | null>(null);
  const [_showNewTestModal, setShowNewTestModal] = useState(false);
  const [powerAnalysisParams, setPowerAnalysisParams] = useState({
    baselineConversionRate: 2.5,
    minimumDetectableEffect: 10,
    confidenceLevel: 0.95 as 0.9 | 0.95 | 0.99,
    dailyTraffic: 10000,
  });

  const { data: activeTests } = useABTests({ status: 'running' });
  const { data: completedTests } = useABTests({ status: 'completed' });
  const { data: draftTests } = useABTests({ status: 'draft' });
  const { data: _selectedTest } = useABTest(selectedTestId || '');
  const { data: testResults } = useABTestResults(selectedTestId || '');
  const { data: ltvImpact } = useLTVImpact(selectedTestId || '');

  const startTest = useStartABTest();
  const pauseTest = usePauseABTest();
  const stopTest = useStopABTest();
  const powerAnalysis = usePowerAnalysis();

  const tabs = [
    { id: 'active' as TabType, label: 'Active Tests', count: activeTests?.length || 0 },
    { id: 'completed' as TabType, label: 'Completed', count: completedTests?.length || 0 },
    { id: 'drafts' as TabType, label: 'Drafts', count: draftTests?.length || 0 },
    { id: 'power-analysis' as TabType, label: 'Power Analysis' },
  ];

  const runPowerAnalysis = () => {
    powerAnalysis.mutate(powerAnalysisParams);
  };

  const renderTestCard = (test: ABTest) => (
    <div
      key={test.id}
      className={cn(
        'rounded-xl border bg-card p-6 shadow-card cursor-pointer transition-all hover:shadow-md',
        selectedTestId === test.id && 'ring-2 ring-primary'
      )}
      onClick={() => setSelectedTestId(test.id)}
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold">{test.name}</h3>
          <p className="text-sm text-muted-foreground">{testTypeLabels[test.testType]} Test</p>
        </div>
        <span className={cn('px-2 py-1 rounded-full text-xs', statusColors[test.status])}>
          {test.status}
        </span>
      </div>

      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{test.hypothesis}</p>

      <div className="grid grid-cols-2 gap-4 text-sm mb-4">
        <div>
          <p className="text-muted-foreground">Variants</p>
          <p className="font-medium">{test.variants.length}</p>
        </div>
        <div>
          <p className="text-muted-foreground">Sample Size</p>
          <p className="font-medium">
            {test.currentSampleSize.toLocaleString()} / {test.targetSampleSize.toLocaleString()}
          </p>
        </div>
        <div>
          <p className="text-muted-foreground">Primary Metric</p>
          <p className="font-medium capitalize">{test.primaryMetric.replace('_', ' ')}</p>
        </div>
        <div>
          <p className="text-muted-foreground">Confidence</p>
          <p className="font-medium">{(test.confidenceLevel * 100).toFixed(0)}%</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-muted rounded-full h-2 mb-4">
        <div
          className="h-2 rounded-full bg-primary"
          style={{
            width: `${Math.min((test.currentSampleSize / test.targetSampleSize) * 100, 100)}%`,
          }}
        />
      </div>

      {/* Actions */}
      {test.status === 'running' && (
        <div className="flex gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              pauseTest.mutate(test.id);
            }}
            className="flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded-lg border hover:bg-muted text-sm"
          >
            <PauseIcon className="h-4 w-4" />
            Pause
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              stopTest.mutate({ testId: test.id });
            }}
            className="flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 text-sm"
          >
            <StopIcon className="h-4 w-4" />
            Stop
          </button>
        </div>
      )}

      {test.status === 'paused' && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            startTest.mutate(test.id);
          }}
          className="w-full flex items-center justify-center gap-1 px-3 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 text-sm"
        >
          <PlayIcon className="h-4 w-4" />
          Resume
        </button>
      )}

      {test.status === 'draft' && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            startTest.mutate(test.id);
          }}
          className="w-full flex items-center justify-center gap-1 px-3 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-sm"
        >
          <PlayIcon className="h-4 w-4" />
          Start Test
        </button>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">A/B Testing</h1>
          <p className="text-muted-foreground">
            Run experiments to optimize campaigns, creatives, and audiences
          </p>
        </div>
        <button
          onClick={() => setShowNewTestModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <PlusIcon className="h-4 w-4" />
          New Test
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-4 py-2 border-b-2 font-medium text-sm transition-colors flex items-center gap-2',
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <span className="px-2 py-0.5 text-xs rounded-full bg-muted">{tab.count}</span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Active Tests Tab */}
      {activeTab === 'active' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Test List */}
          <div className="space-y-4">
            {activeTests?.length === 0 ? (
              <div className="rounded-xl border bg-card p-12 text-center">
                <BeakerIcon className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                <p className="text-lg font-medium">No Active Tests</p>
                <p className="text-muted-foreground">Start a new A/B test to begin experimenting</p>
              </div>
            ) : (
              activeTests?.map(renderTestCard)
            )}
          </div>

          {/* Results Panel */}
          {selectedTestId && testResults && (
            <div className="space-y-4">
              {/* Results Summary */}
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <div className="flex items-center gap-3 mb-4">
                  <ChartBarIcon className="h-6 w-6 text-primary" />
                  <h2 className="text-lg font-semibold">Test Results</h2>
                </div>

                {/* Statistical Significance */}
                <div className="flex items-center gap-2 mb-4">
                  {testResults.isSignificant ? (
                    <>
                      <CheckCircleIcon className="h-5 w-5 text-emerald-500" />
                      <span className="text-emerald-600 font-medium">
                        Statistically Significant
                      </span>
                    </>
                  ) : (
                    <>
                      <XCircleIcon className="h-5 w-5 text-amber-500" />
                      <span className="text-amber-600 font-medium">Not Yet Significant</span>
                    </>
                  )}
                  <span className="text-sm text-muted-foreground">
                    (p-value: {testResults.pValue.toFixed(4)})
                  </span>
                </div>

                {/* Uplift */}
                <div className="rounded-lg bg-muted/50 p-4 mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <ArrowTrendingUpIcon className="h-5 w-5 text-primary" />
                    <span className="font-medium">Conversion Uplift</span>
                  </div>
                  <p className="text-3xl font-bold text-primary">
                    {testResults.uplift > 0 ? '+' : ''}
                    {testResults.uplift.toFixed(1)}%
                  </p>
                  <p className="text-sm text-muted-foreground">
                    95% CI: [{testResults.upliftRange.lower.toFixed(1)}%,{' '}
                    {testResults.upliftRange.upper.toFixed(1)}%]
                  </p>
                </div>

                {/* Variant Results */}
                <div className="space-y-3">
                  {testResults.variants.map((variant) => (
                    <div
                      key={variant.variantId}
                      className={cn(
                        'rounded-lg border p-4',
                        variant.isWinner &&
                          'border-emerald-500 bg-emerald-50 dark:bg-emerald-950/20'
                      )}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{variant.name}</span>
                          {variant.isControl && (
                            <span className="px-2 py-0.5 text-xs rounded bg-muted">Control</span>
                          )}
                          {variant.isWinner && (
                            <span className="px-2 py-0.5 text-xs rounded bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700">
                              Winner
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <p className="text-muted-foreground">Sample Size</p>
                          <p className="font-medium">{variant.sampleSize.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Conversions</p>
                          <p className="font-medium">{variant.conversions.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Conv. Rate</p>
                          <p className="font-medium">{variant.conversionRate.toFixed(2)}%</p>
                        </div>
                      </div>
                      {variant.relativeUplift !== undefined && !variant.isControl && (
                        <p className="text-sm mt-2">
                          <span
                            className={
                              variant.relativeUplift > 0 ? 'text-emerald-600' : 'text-red-600'
                            }
                          >
                            {variant.relativeUplift > 0 ? '+' : ''}
                            {variant.relativeUplift.toFixed(1)}%
                          </span>
                          <span className="text-muted-foreground"> vs control</span>
                        </p>
                      )}
                    </div>
                  ))}
                </div>

                {/* Recommendation */}
                <div className="mt-4 rounded-lg bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 p-4">
                  <div className="flex items-start gap-2">
                    <LightBulbIcon className="h-5 w-5 text-blue-600 mt-0.5" />
                    <div>
                      <p className="font-medium text-blue-900 dark:text-blue-100">Recommendation</p>
                      <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                        {testResults.recommendation}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* LTV Impact */}
              {ltvImpact && (
                <div className="rounded-xl border bg-card p-6 shadow-card">
                  <div className="flex items-center gap-3 mb-4">
                    <SparklesIcon className="h-6 w-6 text-purple-600" />
                    <h2 className="text-lg font-semibold">Projected LTV Impact</h2>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="rounded-lg bg-muted/50 p-4">
                      <p className="text-sm text-muted-foreground">Control LTV</p>
                      <p className="text-2xl font-bold">${ltvImpact.controlLTV.toFixed(2)}</p>
                    </div>
                    <div className="rounded-lg bg-muted/50 p-4">
                      <p className="text-sm text-muted-foreground">Projected Revenue Lift</p>
                      <p className="text-2xl font-bold text-emerald-600">
                        +${ltvImpact.projectedRevenueLift.toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground mt-3">
                    Based on {(ltvImpact.confidenceLevel * 100).toFixed(0)}% confidence level
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Completed Tests Tab */}
      {activeTab === 'completed' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {completedTests?.length === 0 ? (
            <div className="col-span-full rounded-xl border bg-card p-12 text-center">
              <CheckCircleIcon className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
              <p className="text-lg font-medium">No Completed Tests</p>
              <p className="text-muted-foreground">Completed tests will appear here</p>
            </div>
          ) : (
            completedTests?.map(renderTestCard)
          )}
        </div>
      )}

      {/* Drafts Tab */}
      {activeTab === 'drafts' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {draftTests?.length === 0 ? (
            <div className="col-span-full rounded-xl border bg-card p-12 text-center">
              <BeakerIcon className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
              <p className="text-lg font-medium">No Draft Tests</p>
              <p className="text-muted-foreground">Create a new test to get started</p>
            </div>
          ) : (
            draftTests?.map(renderTestCard)
          )}
        </div>
      )}

      {/* Power Analysis Tab */}
      {activeTab === 'power-analysis' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="rounded-xl border bg-card p-6 shadow-card">
            <div className="flex items-center gap-3 mb-6">
              <CalculatorIcon className="h-6 w-6 text-primary" />
              <h2 className="text-lg font-semibold">Power Analysis Calculator</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Baseline Conversion Rate (%)
                </label>
                <input
                  type="number"
                  value={powerAnalysisParams.baselineConversionRate}
                  onChange={(e) =>
                    setPowerAnalysisParams({
                      ...powerAnalysisParams,
                      baselineConversionRate: parseFloat(e.target.value) || 0,
                    })
                  }
                  className="w-full px-3 py-2 rounded-lg border bg-background"
                  step="0.1"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Minimum Detectable Effect (%)
                </label>
                <input
                  type="number"
                  value={powerAnalysisParams.minimumDetectableEffect}
                  onChange={(e) =>
                    setPowerAnalysisParams({
                      ...powerAnalysisParams,
                      minimumDetectableEffect: parseFloat(e.target.value) || 0,
                    })
                  }
                  className="w-full px-3 py-2 rounded-lg border bg-background"
                  step="1"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  The minimum improvement you want to detect
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Confidence Level</label>
                <select
                  value={powerAnalysisParams.confidenceLevel}
                  onChange={(e) =>
                    setPowerAnalysisParams({
                      ...powerAnalysisParams,
                      confidenceLevel: parseFloat(e.target.value) as 0.9 | 0.95 | 0.99,
                    })
                  }
                  className="w-full px-3 py-2 rounded-lg border bg-background"
                >
                  <option value={0.9}>90%</option>
                  <option value={0.95}>95%</option>
                  <option value={0.99}>99%</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Daily Traffic</label>
                <input
                  type="number"
                  value={powerAnalysisParams.dailyTraffic}
                  onChange={(e) =>
                    setPowerAnalysisParams({
                      ...powerAnalysisParams,
                      dailyTraffic: parseInt(e.target.value) || 0,
                    })
                  }
                  className="w-full px-3 py-2 rounded-lg border bg-background"
                  step="100"
                />
              </div>

              <button
                onClick={runPowerAnalysis}
                disabled={powerAnalysis.isPending}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {powerAnalysis.isPending ? 'Calculating...' : 'Calculate Sample Size'}
              </button>
            </div>
          </div>

          {/* Results */}
          {powerAnalysis.data && (
            <div className="rounded-xl border bg-card p-6 shadow-card">
              <h3 className="font-semibold mb-4">Analysis Results</h3>

              <div className="space-y-4">
                <div className="rounded-lg bg-primary/10 p-4">
                  <p className="text-sm text-muted-foreground">
                    Required Sample Size (per variant)
                  </p>
                  <p className="text-3xl font-bold text-primary">
                    {powerAnalysis.data.requiredSampleSize.toLocaleString()}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-lg bg-muted/50 p-4">
                    <p className="text-sm text-muted-foreground">Estimated Duration</p>
                    <p className="text-xl font-bold">{powerAnalysis.data.estimatedDuration} days</p>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-4">
                    <p className="text-sm text-muted-foreground">Statistical Power</p>
                    <p className="text-xl font-bold">
                      {(powerAnalysis.data.currentPower * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>

                {powerAnalysis.data.recommendations.length > 0 && (
                  <div className="rounded-lg bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 p-4">
                    <p className="font-medium text-blue-900 dark:text-blue-100 mb-2">
                      Recommendations
                    </p>
                    <ul className="list-disc list-inside space-y-1">
                      {powerAnalysis.data.recommendations.map((rec, idx) => (
                        <li key={idx} className="text-sm text-blue-700 dark:text-blue-300">
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
