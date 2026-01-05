/**
 * Stratum AI - Attribution Page
 *
 * Multi-touch attribution analysis with data-driven models (Markov, Shapley).
 */

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  useAttributionSummary,
  useTopConversionPaths,
  useAttributionComparison,
  useTrainedModels,
  useTrainMarkovModel,
  useTrainShapleyModel,
} from '@/api/hooks'
import {
  ChartPieIcon,
  ArrowPathIcon,
  BeakerIcon,
  LightBulbIcon,
  ArrowsRightLeftIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

type TabType = 'overview' | 'models' | 'paths' | 'compare'
type AttributionModel = 'first_touch' | 'last_touch' | 'linear' | 'time_decay' | 'position_based' | 'markov' | 'shapley'

const modelLabels: Record<AttributionModel, string> = {
  first_touch: 'First Touch',
  last_touch: 'Last Touch',
  linear: 'Linear',
  time_decay: 'Time Decay',
  position_based: 'Position Based',
  markov: 'Markov Chain',
  shapley: 'Shapley Value',
}

export default function Attribution() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [selectedModel, setSelectedModel] = useState<AttributionModel>('linear')
  const [dateRange] = useState({
    startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],
  })

  const { data: summary, isLoading: loadingSummary } = useAttributionSummary({
    ...dateRange,
    model: selectedModel,
  })
  const { data: topPaths } = useTopConversionPaths({ ...dateRange, limit: 10 })
  const { data: comparison } = useAttributionComparison({
    ...dateRange,
    models: ['first_touch', 'last_touch', 'linear', 'markov', 'shapley'],
  })
  const { data: trainedModels } = useTrainedModels()
  const trainMarkov = useTrainMarkovModel()
  const trainShapley = useTrainShapleyModel()

  const tabs = [
    { id: 'overview' as TabType, label: 'Overview' },
    { id: 'models' as TabType, label: 'AI Models' },
    { id: 'paths' as TabType, label: 'Conversion Paths' },
    { id: 'compare' as TabType, label: 'Model Comparison' },
  ]

  const models: AttributionModel[] = ['first_touch', 'last_touch', 'linear', 'time_decay', 'position_based', 'markov', 'shapley']

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Multi-Touch Attribution</h1>
          <p className="text-muted-foreground">
            Understand the true impact of each channel on conversions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value as AttributionModel)}
            className="px-3 py-2 rounded-lg border bg-background"
          >
            {models.map((model) => (
              <option key={model} value={model}>
                {modelLabels[model]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-4 py-2 border-b-2 font-medium text-sm transition-colors',
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Summary Stats */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <p className="text-sm text-muted-foreground">Total Conversions</p>
                <p className="text-2xl font-bold">{summary.totalConversions.toLocaleString()}</p>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <p className="text-sm text-muted-foreground">Total Revenue</p>
                <p className="text-2xl font-bold">${summary.totalRevenue.toLocaleString()}</p>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <p className="text-sm text-muted-foreground">Unique Channels</p>
                <p className="text-2xl font-bold">{summary.channelBreakdown.length}</p>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <p className="text-sm text-muted-foreground">Model</p>
                <p className="text-xl font-bold">{modelLabels[selectedModel]}</p>
              </div>
            </div>
          )}

          {/* Channel Attribution */}
          {summary && (
            <div className="rounded-xl border bg-card p-6 shadow-card">
              <h2 className="text-lg font-semibold mb-4">Channel Attribution</h2>
              <div className="space-y-4">
                {summary.channelBreakdown.map((channel) => (
                  <div key={channel.channel}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-medium">{channel.channel}</span>
                      <div className="flex gap-4">
                        <span className="text-muted-foreground">
                          {channel.conversions.toLocaleString()} conversions
                        </span>
                        <span className="font-medium">
                          ${channel.attributedRevenue.toLocaleString()}
                        </span>
                      </div>
                    </div>
                    <div className="w-full bg-muted rounded-full h-2">
                      <div
                        className="h-2 rounded-full bg-primary"
                        style={{ width: `${channel.attributionWeight * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Model Info */}
          <div className="rounded-xl border bg-card p-6 shadow-card">
            <div className="flex items-start gap-3">
              <LightBulbIcon className="h-5 w-5 text-amber-500 mt-0.5" />
              <div>
                <h3 className="font-medium">About {modelLabels[selectedModel]}</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {selectedModel === 'first_touch' && 'Gives 100% credit to the first touchpoint in the customer journey.'}
                  {selectedModel === 'last_touch' && 'Gives 100% credit to the last touchpoint before conversion.'}
                  {selectedModel === 'linear' && 'Distributes credit equally across all touchpoints in the journey.'}
                  {selectedModel === 'time_decay' && 'Gives more credit to touchpoints closer to the conversion time.'}
                  {selectedModel === 'position_based' && 'Gives 40% to first, 40% to last, and 20% distributed among middle touchpoints.'}
                  {selectedModel === 'markov' && 'Uses transition probabilities to determine each channel\'s contribution to conversions.'}
                  {selectedModel === 'shapley' && 'Uses game theory to fairly distribute credit based on each channel\'s marginal contribution.'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Models Tab */}
      {activeTab === 'models' && (
        <div className="space-y-6">
          {/* Train New Models */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-xl border bg-card p-6 shadow-card">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/20">
                  <BeakerIcon className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <h3 className="font-medium">Markov Chain Model</h3>
                  <p className="text-sm text-muted-foreground">
                    Probabilistic model based on channel transitions
                  </p>
                </div>
              </div>
              <button
                onClick={() => trainMarkov.mutate(dateRange)}
                disabled={trainMarkov.isPending}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50"
              >
                {trainMarkov.isPending ? (
                  <ArrowPathIcon className="h-4 w-4 animate-spin" />
                ) : (
                  <SparklesIcon className="h-4 w-4" />
                )}
                Train Markov Model
              </button>
            </div>

            <div className="rounded-xl border bg-card p-6 shadow-card">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/20">
                  <ChartPieIcon className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-medium">Shapley Value Model</h3>
                  <p className="text-sm text-muted-foreground">
                    Game theory-based fair attribution
                  </p>
                </div>
              </div>
              <button
                onClick={() => trainShapley.mutate(dateRange)}
                disabled={trainShapley.isPending}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {trainShapley.isPending ? (
                  <ArrowPathIcon className="h-4 w-4 animate-spin" />
                ) : (
                  <SparklesIcon className="h-4 w-4" />
                )}
                Train Shapley Model
              </button>
            </div>
          </div>

          {/* Trained Models */}
          <div className="rounded-xl border bg-card shadow-card overflow-hidden">
            <div className="p-4 border-b">
              <h3 className="font-medium">Trained Models</h3>
            </div>
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium">Model</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Type</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Trained</th>
                  <th className="px-4 py-3 text-right text-sm font-medium">Accuracy</th>
                  <th className="px-4 py-3 text-center text-sm font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {trainedModels?.map((model) => (
                  <tr key={model.id} className="hover:bg-muted/30">
                    <td className="px-4 py-3 font-medium">{model.name}</td>
                    <td className="px-4 py-3 text-sm capitalize">{model.modelType.replace('_', ' ')}</td>
                    <td className="px-4 py-3 text-sm">
                      {new Date(model.trainedAt).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right font-medium">
                      {model.accuracy ? `${(model.accuracy * 100).toFixed(1)}%` : '-'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={cn(
                          'px-2 py-1 rounded-full text-xs',
                          model.status === 'active' && 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300',
                          model.status === 'training' && 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
                          model.status === 'failed' && 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                        )}
                      >
                        {model.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Conversion Paths Tab */}
      {activeTab === 'paths' && (
        <div className="rounded-xl border bg-card shadow-card overflow-hidden">
          <div className="p-4 border-b">
            <h3 className="font-medium">Top Conversion Paths</h3>
            <p className="text-sm text-muted-foreground">
              Most common channel sequences leading to conversions
            </p>
          </div>
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium">Path</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Conversions</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Revenue</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Avg. Time</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {topPaths?.map((path, idx) => (
                <tr key={idx} className="hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      {path.path.map((channel, i) => (
                        <span key={i} className="flex items-center gap-1">
                          <span className="px-2 py-1 rounded bg-muted text-xs font-medium">
                            {channel}
                          </span>
                          {i < path.path.length - 1 && (
                            <ArrowsRightLeftIcon className="h-3 w-3 text-muted-foreground" />
                          )}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-medium">
                    {path.conversions.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right font-medium">
                    ${path.totalRevenue.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-muted-foreground">
                    {path.avgTimeToConversion.toFixed(1)} days
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Model Comparison Tab */}
      {activeTab === 'compare' && comparison && (
        <div className="rounded-xl border bg-card shadow-card overflow-hidden">
          <div className="p-4 border-b">
            <h3 className="font-medium">Attribution Model Comparison</h3>
            <p className="text-sm text-muted-foreground">
              See how different models attribute revenue to each channel
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium">Channel</th>
                  {comparison.models.map((model) => (
                    <th key={model} className="px-4 py-3 text-right text-sm font-medium">
                      {modelLabels[model as AttributionModel] || model}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {comparison.channels.map((channel) => (
                  <tr key={channel.channel} className="hover:bg-muted/30">
                    <td className="px-4 py-3 font-medium">{channel.channel}</td>
                    {comparison.models.map((model) => (
                      <td key={model} className="px-4 py-3 text-right">
                        ${channel.attributionByModel[model]?.toLocaleString() || '0'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
