/**
 * Stratum AI - Model Explainability Page
 *
 * SHAP/LIME-based model explanations for ML predictions.
 */

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { apiClient, ApiResponse } from '@/api/client'
import {
  SparklesIcon,
  LightBulbIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  InformationCircleIcon,
  CpuChipIcon,
  BeakerIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

// Types
type ModelType = 'roas_optimizer' | 'conversion_predictor' | 'ltv_predictor' | 'attribution'
type ExplanationType = 'shap' | 'lime' | 'feature_importance'

interface FeatureImportance {
  feature: string
  importance: number
  direction: 'positive' | 'negative' | 'neutral'
  description: string
}

interface SHAPExplanation {
  baseValue: number
  predictedValue: number
  features: {
    name: string
    value: number
    shapValue: number
    contribution: 'positive' | 'negative'
  }[]
  plot: string // Base64 encoded image or chart data
}

interface LIMEExplanation {
  prediction: number
  intercept: number
  features: {
    name: string
    weight: number
    value: number
    contribution: number
  }[]
  localFidelity: number
}

interface ModelInfo {
  id: string
  name: string
  type: ModelType
  version: string
  trainedAt: string
  metrics: {
    accuracy?: number
    precision?: number
    recall?: number
    f1?: number
    auc?: number
    mae?: number
    rmse?: number
  }
  featureCount: number
  sampleCount: number
}

interface PredictionExplanation {
  predictionId: string
  modelType: ModelType
  inputFeatures: Record<string, number | string>
  prediction: number
  confidence: number
  shap?: SHAPExplanation
  lime?: LIMEExplanation
  featureImportance: FeatureImportance[]
  insights: string[]
}

// API Functions
const explainabilityApi = {
  getModels: async () => {
    const response = await apiClient.get<ApiResponse<ModelInfo[]>>('/ml/models')
    return response.data.data
  },

  getModelInfo: async (modelType: ModelType) => {
    const response = await apiClient.get<ApiResponse<ModelInfo>>(`/ml/models/${modelType}`)
    return response.data.data
  },

  getFeatureImportance: async (modelType: ModelType) => {
    const response = await apiClient.get<ApiResponse<FeatureImportance[]>>(`/ml/models/${modelType}/feature-importance`)
    return response.data.data
  },

  explainPrediction: async (params: {
    modelType: ModelType
    inputData: Record<string, number | string>
    explanationType: ExplanationType
  }) => {
    const response = await apiClient.post<ApiResponse<PredictionExplanation>>('/ml/explain', params)
    return response.data.data
  },

  getSHAPSummary: async (modelType: ModelType) => {
    const response = await apiClient.get<ApiResponse<{
      summaryPlot: string
      features: Array<{ name: string; meanAbsShap: number; stdShap: number }>
    }>>(`/ml/models/${modelType}/shap-summary`)
    return response.data.data
  },

  getLTVPrediction: async (params: { customerId?: string; segment?: string }) => {
    const response = await apiClient.post<ApiResponse<{
      predictedLTV: number
      confidence: number
      timeHorizon: string
      breakdown: Array<{ period: string; value: number }>
      factors: FeatureImportance[]
    }>>('/ml/predictions/ltv', params)
    return response.data.data
  },
}

// Hooks
function useModels() {
  return useQuery({
    queryKey: ['ml', 'models'],
    queryFn: explainabilityApi.getModels,
  })
}

function useModelInfo(modelType: ModelType) {
  return useQuery({
    queryKey: ['ml', 'models', modelType],
    queryFn: () => explainabilityApi.getModelInfo(modelType),
    enabled: !!modelType,
  })
}

function useFeatureImportance(modelType: ModelType) {
  return useQuery({
    queryKey: ['ml', 'models', modelType, 'feature-importance'],
    queryFn: () => explainabilityApi.getFeatureImportance(modelType),
    enabled: !!modelType,
  })
}

function useSHAPSummary(modelType: ModelType) {
  return useQuery({
    queryKey: ['ml', 'models', modelType, 'shap-summary'],
    queryFn: () => explainabilityApi.getSHAPSummary(modelType),
    enabled: !!modelType,
  })
}

// useExplainPrediction is reserved for future use
// function _useExplainPrediction() {
//   return useMutation({
//     mutationFn: explainabilityApi.explainPrediction,
//   })
// }

function useLTVPrediction() {
  return useMutation({
    mutationFn: explainabilityApi.getLTVPrediction,
  })
}

const modelTypeLabels: Record<ModelType, string> = {
  roas_optimizer: 'ROAS Optimizer',
  conversion_predictor: 'Conversion Predictor',
  ltv_predictor: 'LTV Predictor',
  attribution: 'Attribution Model',
}

export default function ModelExplainability() {
  const { tenantId: _tenantId } = useParams<{ tenantId: string }>()
  const [selectedModel, setSelectedModel] = useState<ModelType>('roas_optimizer')
  const [activeTab, setActiveTab] = useState<'overview' | 'shap' | 'lime' | 'ltv'>('overview')

  const { data: _models } = useModels()
  const { data: modelInfo } = useModelInfo(selectedModel)
  const { data: featureImportance } = useFeatureImportance(selectedModel)
  const { data: shapSummary } = useSHAPSummary(selectedModel)
  const ltvPrediction = useLTVPrediction()

  const tabs = [
    { id: 'overview' as const, label: 'Overview' },
    { id: 'shap' as const, label: 'SHAP Analysis' },
    { id: 'lime' as const, label: 'LIME Explanations' },
    { id: 'ltv' as const, label: 'LTV Predictions' },
  ]

  const maxImportance = featureImportance
    ? Math.max(...featureImportance.map((f) => Math.abs(f.importance)))
    : 1

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Model Explainability</h1>
          <p className="text-muted-foreground">
            Understand how ML models make predictions with SHAP and LIME
          </p>
        </div>
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value as ModelType)}
          className="px-4 py-2 rounded-lg border bg-background"
        >
          {Object.entries(modelTypeLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
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
          {/* Model Info */}
          {modelInfo && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <div className="flex items-center gap-2 mb-2">
                  <CpuChipIcon className="h-5 w-5 text-primary" />
                  <p className="text-sm text-muted-foreground">Model</p>
                </div>
                <p className="text-xl font-bold">{modelInfo.name}</p>
                <p className="text-sm text-muted-foreground">v{modelInfo.version}</p>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <p className="text-sm text-muted-foreground mb-2">Features</p>
                <p className="text-2xl font-bold">{modelInfo.featureCount}</p>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <p className="text-sm text-muted-foreground mb-2">Training Samples</p>
                <p className="text-2xl font-bold">{modelInfo.sampleCount.toLocaleString()}</p>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <p className="text-sm text-muted-foreground mb-2">
                  {modelInfo.metrics.accuracy !== undefined ? 'Accuracy' : 'RMSE'}
                </p>
                <p className="text-2xl font-bold">
                  {modelInfo.metrics.accuracy !== undefined
                    ? `${(modelInfo.metrics.accuracy * 100).toFixed(1)}%`
                    : modelInfo.metrics.rmse?.toFixed(3)}
                </p>
              </div>
            </div>
          )}

          {/* Feature Importance */}
          <div className="rounded-xl border bg-card p-6 shadow-card">
            <div className="flex items-center gap-3 mb-6">
              <ChartBarIcon className="h-6 w-6 text-primary" />
              <h2 className="text-lg font-semibold">Feature Importance</h2>
            </div>

            <div className="space-y-4">
              {featureImportance?.slice(0, 15).map((feature) => (
                <div key={feature.feature}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{feature.feature}</span>
                      {feature.direction === 'positive' && (
                        <ArrowTrendingUpIcon className="h-4 w-4 text-emerald-500" />
                      )}
                      {feature.direction === 'negative' && (
                        <ArrowTrendingDownIcon className="h-4 w-4 text-red-500" />
                      )}
                    </div>
                    <span className="text-muted-foreground">
                      {(feature.importance * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div
                      className={cn(
                        'h-2 rounded-full',
                        feature.direction === 'positive' && 'bg-emerald-500',
                        feature.direction === 'negative' && 'bg-red-500',
                        feature.direction === 'neutral' && 'bg-blue-500'
                      )}
                      style={{ width: `${(Math.abs(feature.importance) / maxImportance) * 100}%` }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Model Info Card */}
          <div className="rounded-xl border bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800 p-6">
            <div className="flex items-start gap-3">
              <InformationCircleIcon className="h-6 w-6 text-blue-600 mt-0.5" />
              <div>
                <h3 className="font-medium text-blue-900 dark:text-blue-100">About Model Explainability</h3>
                <p className="text-sm text-blue-700 dark:text-blue-300 mt-2">
                  <strong>SHAP (SHapley Additive exPlanations)</strong> uses game theory to calculate
                  feature contributions. Each feature's SHAP value represents its contribution to pushing
                  the prediction away from the baseline.
                </p>
                <p className="text-sm text-blue-700 dark:text-blue-300 mt-2">
                  <strong>LIME (Local Interpretable Model-agnostic Explanations)</strong> creates
                  locally faithful explanations by training interpretable models on perturbations of
                  the input.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SHAP Tab */}
      {activeTab === 'shap' && (
        <div className="space-y-6">
          {/* SHAP Summary */}
          <div className="rounded-xl border bg-card p-6 shadow-card">
            <div className="flex items-center gap-3 mb-6">
              <SparklesIcon className="h-6 w-6 text-purple-600" />
              <h2 className="text-lg font-semibold">SHAP Feature Summary</h2>
            </div>

            {shapSummary && (
              <div className="space-y-4">
                {shapSummary.features.slice(0, 15).map((feature) => (
                  <div key={feature.name} className="flex items-center gap-4">
                    <div className="w-40 text-sm font-medium truncate">{feature.name}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <div
                          className="h-6 bg-gradient-to-r from-blue-500 to-red-500 rounded"
                          style={{
                            width: `${(feature.meanAbsShap / shapSummary.features[0].meanAbsShap) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                    <div className="w-20 text-right text-sm text-muted-foreground">
                      {feature.meanAbsShap.toFixed(4)}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-6 p-4 rounded-lg bg-muted/50">
              <p className="text-sm">
                <span className="font-medium">How to read:</span> Features are ranked by their
                mean absolute SHAP value across all samples. Higher values indicate features that
                have more impact on predictions. The color gradient shows the distribution of
                SHAP values (blue = negative impact, red = positive impact).
              </p>
            </div>
          </div>

          {/* SHAP Interaction */}
          <div className="rounded-xl border bg-card p-6 shadow-card">
            <h3 className="font-semibold mb-4">Feature Interactions</h3>
            <p className="text-muted-foreground">
              SHAP interaction values help identify which feature pairs have the strongest
              combined effects on predictions.
            </p>
            <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { pair: 'Budget × CTR', strength: 0.82 },
                { pair: 'Audience × Creative', strength: 0.75 },
                { pair: 'Time × Platform', strength: 0.68 },
                { pair: 'Bid × Competition', strength: 0.61 },
              ].map((interaction) => (
                <div key={interaction.pair} className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm font-medium">{interaction.pair}</p>
                  <p className="text-2xl font-bold text-purple-600">
                    {(interaction.strength * 100).toFixed(0)}%
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* LIME Tab */}
      {activeTab === 'lime' && (
        <div className="space-y-6">
          <div className="rounded-xl border bg-card p-6 shadow-card">
            <div className="flex items-center gap-3 mb-6">
              <BeakerIcon className="h-6 w-6 text-emerald-600" />
              <h2 className="text-lg font-semibold">LIME Local Explanations</h2>
            </div>

            <p className="text-muted-foreground mb-6">
              LIME explains individual predictions by learning a simple, interpretable model
              around the prediction point. Select a prediction to see its local explanation.
            </p>

            {/* Sample LIME explanation */}
            <div className="border rounded-lg p-4">
              <h4 className="font-medium mb-4">Sample Prediction Explanation</h4>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="p-3 rounded-lg bg-muted/50">
                  <p className="text-sm text-muted-foreground">Predicted Value</p>
                  <p className="text-2xl font-bold">3.2x ROAS</p>
                </div>
                <div className="p-3 rounded-lg bg-muted/50">
                  <p className="text-sm text-muted-foreground">Local Fidelity</p>
                  <p className="text-2xl font-bold">94.2%</p>
                </div>
              </div>

              <h5 className="text-sm font-medium mb-3">Feature Contributions</h5>
              <div className="space-y-3">
                {[
                  { name: 'High-quality creative', weight: 0.42, direction: 'positive' },
                  { name: 'Target audience match', weight: 0.28, direction: 'positive' },
                  { name: 'Competitive bid', weight: 0.15, direction: 'positive' },
                  { name: 'Weekend timing', weight: -0.12, direction: 'negative' },
                  { name: 'Broad targeting', weight: -0.08, direction: 'negative' },
                ].map((feature) => (
                  <div key={feature.name} className="flex items-center gap-3">
                    <div className="w-40 text-sm">{feature.name}</div>
                    <div className="flex-1 flex items-center gap-1">
                      {feature.direction === 'positive' ? (
                        <div
                          className="h-4 bg-emerald-500 rounded"
                          style={{ width: `${feature.weight * 100}%` }}
                        />
                      ) : (
                        <div
                          className="h-4 bg-red-500 rounded"
                          style={{ width: `${Math.abs(feature.weight) * 100}%` }}
                        />
                      )}
                    </div>
                    <div className="w-16 text-right text-sm">
                      {feature.direction === 'positive' ? '+' : ''}{(feature.weight * 100).toFixed(0)}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* LTV Tab */}
      {activeTab === 'ltv' && (
        <div className="space-y-6">
          <div className="rounded-xl border bg-card p-6 shadow-card">
            <div className="flex items-center gap-3 mb-6">
              <SparklesIcon className="h-6 w-6 text-primary" />
              <h2 className="text-lg font-semibold">Lifetime Value Predictions</h2>
            </div>

            <p className="text-muted-foreground mb-6">
              ML-powered LTV predictions help you understand customer value and optimize
              acquisition strategies.
            </p>

            {/* LTV Calculator */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <h4 className="font-medium">Predict LTV by Segment</h4>
                <select className="w-full px-3 py-2 rounded-lg border bg-background">
                  <option>All Customers</option>
                  <option>High-Value Segment</option>
                  <option>New Customers (0-30 days)</option>
                  <option>Returning Customers</option>
                  <option>At-Risk Customers</option>
                </select>
                <button
                  onClick={() => ltvPrediction.mutate({ segment: 'all' })}
                  disabled={ltvPrediction.isPending}
                  className="w-full px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {ltvPrediction.isPending ? 'Calculating...' : 'Calculate LTV'}
                </button>
              </div>

              {/* LTV Results */}
              {ltvPrediction.data && (
                <div className="space-y-4">
                  <div className="rounded-lg bg-primary/10 p-4">
                    <p className="text-sm text-muted-foreground">Predicted LTV</p>
                    <p className="text-3xl font-bold text-primary">
                      ${ltvPrediction.data.predictedLTV.toFixed(2)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {ltvPrediction.data.timeHorizon} | {(ltvPrediction.data.confidence * 100).toFixed(0)}% confidence
                    </p>
                  </div>

                  <div className="space-y-2">
                    <p className="text-sm font-medium">Key Factors</p>
                    {ltvPrediction.data.factors.slice(0, 5).map((factor) => (
                      <div key={factor.feature} className="flex items-center justify-between text-sm">
                        <span>{factor.feature}</span>
                        <span className={cn(
                          factor.direction === 'positive' ? 'text-emerald-600' : 'text-red-600'
                        )}>
                          {factor.direction === 'positive' ? '+' : '-'}{(factor.importance * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* LTV Insights */}
          <div className="rounded-xl border bg-card p-6 shadow-card">
            <h3 className="font-semibold mb-4">LTV-Based Recommendations</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800">
                <LightBulbIcon className="h-5 w-5 text-emerald-600 mb-2" />
                <h4 className="font-medium text-emerald-900 dark:text-emerald-100">High-Value Segment</h4>
                <p className="text-sm text-emerald-700 dark:text-emerald-300 mt-1">
                  Increase bid by 20% for audiences with predicted LTV &gt; $500
                </p>
              </div>
              <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800">
                <LightBulbIcon className="h-5 w-5 text-blue-600 mb-2" />
                <h4 className="font-medium text-blue-900 dark:text-blue-100">Retention Focus</h4>
                <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                  At-risk customers have 3x higher LTV when retained vs new acquisition
                </p>
              </div>
              <div className="p-4 rounded-lg bg-purple-50 dark:bg-purple-950/20 border border-purple-200 dark:border-purple-800">
                <LightBulbIcon className="h-5 w-5 text-purple-600 mb-2" />
                <h4 className="font-medium text-purple-900 dark:text-purple-100">CAC Optimization</h4>
                <p className="text-sm text-purple-700 dark:text-purple-300 mt-1">
                  Target CAC:LTV ratio of 1:3 for sustainable growth
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
