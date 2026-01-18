// =============================================================================
// Stratum AI - Custom Report Builder (Enterprise Feature)
// =============================================================================

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  DocumentChartBarIcon,
  PlusIcon,
  TrashIcon,
  ChartBarIcon,
  TableCellsIcon,
  ChartPieIcon,
  ArrowsPointingOutIcon,
  CalendarIcon,
  FunnelIcon,
  ArrowDownTrayIcon,
  ClockIcon,
  PlayIcon,
  PencilIcon,
  EyeIcon,
  DocumentDuplicateIcon,
  CheckIcon,
  XMarkIcon,
  Cog6ToothIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

// =============================================================================
// Types
// =============================================================================

interface DataSource {
  id: string
  name: string
  type: 'campaigns' | 'cdp' | 'trust_engine' | 'pacing' | 'attribution'
  description: string
}

interface Metric {
  id: string
  name: string
  field: string
  aggregation: 'sum' | 'avg' | 'count' | 'min' | 'max' | 'unique'
  format: 'number' | 'currency' | 'percentage' | 'decimal'
}

interface Dimension {
  id: string
  name: string
  field: string
  type: 'string' | 'date' | 'boolean'
}

interface Filter {
  id: string
  field: string
  operator: 'equals' | 'not_equals' | 'contains' | 'gt' | 'lt' | 'gte' | 'lte' | 'between' | 'in'
  value: string | string[]
}

interface Visualization {
  id: string
  type: 'bar' | 'line' | 'pie' | 'table' | 'metric' | 'area' | 'scatter'
  title: string
  metrics: string[]
  dimensions: string[]
  config: Record<string, any>
}

interface ReportSchedule {
  enabled: boolean
  frequency: 'daily' | 'weekly' | 'monthly'
  time: string
  recipients: string[]
  format: 'pdf' | 'csv' | 'excel'
}

interface CustomReport {
  id: string
  name: string
  description: string
  dataSource: string
  metrics: Metric[]
  dimensions: Dimension[]
  filters: Filter[]
  visualizations: Visualization[]
  schedule: ReportSchedule
  dateRange: {
    type: 'last_7_days' | 'last_30_days' | 'last_90_days' | 'custom'
    start?: string
    end?: string
  }
  createdAt: string
  updatedAt: string
  status: 'draft' | 'published'
}

// =============================================================================
// Mock Data
// =============================================================================

const DATA_SOURCES: DataSource[] = [
  { id: 'campaigns', name: 'Campaign Performance', type: 'campaigns', description: 'Ad spend, impressions, clicks, conversions across all platforms' },
  { id: 'cdp', name: 'CDP Profiles & Events', type: 'cdp', description: 'Customer profiles, events, segments, and lifecycle data' },
  { id: 'trust_engine', name: 'Trust Engine', type: 'trust_engine', description: 'Signal health, gate decisions, automation logs' },
  { id: 'pacing', name: 'Pacing & Forecasting', type: 'pacing', description: 'Budget pacing, spend forecasts, alerts' },
  { id: 'attribution', name: 'Attribution', type: 'attribution', description: 'Multi-touch attribution, conversion paths, channel performance' },
]

const AVAILABLE_METRICS: Record<string, Metric[]> = {
  campaigns: [
    { id: 'spend', name: 'Ad Spend', field: 'spend', aggregation: 'sum', format: 'currency' },
    { id: 'impressions', name: 'Impressions', field: 'impressions', aggregation: 'sum', format: 'number' },
    { id: 'clicks', name: 'Clicks', field: 'clicks', aggregation: 'sum', format: 'number' },
    { id: 'conversions', name: 'Conversions', field: 'conversions', aggregation: 'sum', format: 'number' },
    { id: 'ctr', name: 'CTR', field: 'ctr', aggregation: 'avg', format: 'percentage' },
    { id: 'cpc', name: 'CPC', field: 'cpc', aggregation: 'avg', format: 'currency' },
    { id: 'roas', name: 'ROAS', field: 'roas', aggregation: 'avg', format: 'decimal' },
    { id: 'cpa', name: 'CPA', field: 'cpa', aggregation: 'avg', format: 'currency' },
  ],
  cdp: [
    { id: 'total_profiles', name: 'Total Profiles', field: 'total_profiles', aggregation: 'count', format: 'number' },
    { id: 'new_profiles', name: 'New Profiles', field: 'new_profiles', aggregation: 'sum', format: 'number' },
    { id: 'total_events', name: 'Total Events', field: 'total_events', aggregation: 'sum', format: 'number' },
    { id: 'avg_events_per_profile', name: 'Avg Events/Profile', field: 'avg_events', aggregation: 'avg', format: 'decimal' },
    { id: 'segment_size', name: 'Segment Size', field: 'segment_size', aggregation: 'sum', format: 'number' },
    { id: 'ltv', name: 'Customer LTV', field: 'ltv', aggregation: 'avg', format: 'currency' },
  ],
  trust_engine: [
    { id: 'signal_health', name: 'Signal Health', field: 'signal_health', aggregation: 'avg', format: 'percentage' },
    { id: 'gate_passes', name: 'Gate Passes', field: 'gate_passes', aggregation: 'sum', format: 'number' },
    { id: 'gate_holds', name: 'Gate Holds', field: 'gate_holds', aggregation: 'sum', format: 'number' },
    { id: 'gate_blocks', name: 'Gate Blocks', field: 'gate_blocks', aggregation: 'sum', format: 'number' },
    { id: 'automation_runs', name: 'Automation Runs', field: 'automation_runs', aggregation: 'sum', format: 'number' },
  ],
  pacing: [
    { id: 'budget', name: 'Budget', field: 'budget', aggregation: 'sum', format: 'currency' },
    { id: 'spent', name: 'Amount Spent', field: 'spent', aggregation: 'sum', format: 'currency' },
    { id: 'pacing_rate', name: 'Pacing Rate', field: 'pacing_rate', aggregation: 'avg', format: 'percentage' },
    { id: 'forecast_spend', name: 'Forecasted Spend', field: 'forecast_spend', aggregation: 'sum', format: 'currency' },
  ],
  attribution: [
    { id: 'attributed_conversions', name: 'Attributed Conversions', field: 'attributed_conversions', aggregation: 'sum', format: 'number' },
    { id: 'attributed_revenue', name: 'Attributed Revenue', field: 'attributed_revenue', aggregation: 'sum', format: 'currency' },
    { id: 'attribution_weight', name: 'Attribution Weight', field: 'attribution_weight', aggregation: 'avg', format: 'percentage' },
    { id: 'path_length', name: 'Avg Path Length', field: 'path_length', aggregation: 'avg', format: 'decimal' },
  ],
}

const AVAILABLE_DIMENSIONS: Record<string, Dimension[]> = {
  campaigns: [
    { id: 'platform', name: 'Platform', field: 'platform', type: 'string' },
    { id: 'campaign', name: 'Campaign', field: 'campaign_name', type: 'string' },
    { id: 'ad_group', name: 'Ad Group', field: 'ad_group', type: 'string' },
    { id: 'date', name: 'Date', field: 'date', type: 'date' },
    { id: 'device', name: 'Device', field: 'device', type: 'string' },
    { id: 'country', name: 'Country', field: 'country', type: 'string' },
  ],
  cdp: [
    { id: 'lifecycle_stage', name: 'Lifecycle Stage', field: 'lifecycle_stage', type: 'string' },
    { id: 'segment', name: 'Segment', field: 'segment', type: 'string' },
    { id: 'source', name: 'Source', field: 'source', type: 'string' },
    { id: 'date', name: 'Date', field: 'date', type: 'date' },
    { id: 'event_type', name: 'Event Type', field: 'event_type', type: 'string' },
  ],
  trust_engine: [
    { id: 'signal_type', name: 'Signal Type', field: 'signal_type', type: 'string' },
    { id: 'gate_status', name: 'Gate Status', field: 'gate_status', type: 'string' },
    { id: 'automation', name: 'Automation', field: 'automation_name', type: 'string' },
    { id: 'date', name: 'Date', field: 'date', type: 'date' },
  ],
  pacing: [
    { id: 'campaign', name: 'Campaign', field: 'campaign_name', type: 'string' },
    { id: 'platform', name: 'Platform', field: 'platform', type: 'string' },
    { id: 'date', name: 'Date', field: 'date', type: 'date' },
    { id: 'alert_type', name: 'Alert Type', field: 'alert_type', type: 'string' },
  ],
  attribution: [
    { id: 'channel', name: 'Channel', field: 'channel', type: 'string' },
    { id: 'campaign', name: 'Campaign', field: 'campaign_name', type: 'string' },
    { id: 'touchpoint', name: 'Touchpoint', field: 'touchpoint', type: 'string' },
    { id: 'date', name: 'Date', field: 'date', type: 'date' },
    { id: 'model', name: 'Attribution Model', field: 'model', type: 'string' },
  ],
}

const VISUALIZATION_TYPES = [
  { id: 'bar', name: 'Bar Chart', icon: ChartBarIcon },
  { id: 'line', name: 'Line Chart', icon: ArrowsPointingOutIcon },
  { id: 'pie', name: 'Pie Chart', icon: ChartPieIcon },
  { id: 'table', name: 'Table', icon: TableCellsIcon },
  { id: 'metric', name: 'Metric Card', icon: SparklesIcon },
]

const MOCK_REPORTS: CustomReport[] = [
  {
    id: '1',
    name: 'Weekly Performance Summary',
    description: 'Overview of campaign performance across all platforms',
    dataSource: 'campaigns',
    metrics: [
      { id: 'spend', name: 'Ad Spend', field: 'spend', aggregation: 'sum', format: 'currency' },
      { id: 'conversions', name: 'Conversions', field: 'conversions', aggregation: 'sum', format: 'number' },
      { id: 'roas', name: 'ROAS', field: 'roas', aggregation: 'avg', format: 'decimal' },
    ],
    dimensions: [
      { id: 'platform', name: 'Platform', field: 'platform', type: 'string' },
      { id: 'date', name: 'Date', field: 'date', type: 'date' },
    ],
    filters: [],
    visualizations: [
      { id: 'v1', type: 'line', title: 'Spend Over Time', metrics: ['spend'], dimensions: ['date'], config: {} },
      { id: 'v2', type: 'bar', title: 'ROAS by Platform', metrics: ['roas'], dimensions: ['platform'], config: {} },
    ],
    schedule: { enabled: true, frequency: 'weekly', time: '09:00', recipients: ['team@company.com'], format: 'pdf' },
    dateRange: { type: 'last_7_days' },
    createdAt: '2024-01-10T10:00:00Z',
    updatedAt: '2024-01-15T14:30:00Z',
    status: 'published',
  },
  {
    id: '2',
    name: 'CDP Health Report',
    description: 'Customer data platform metrics and segment analysis',
    dataSource: 'cdp',
    metrics: [
      { id: 'total_profiles', name: 'Total Profiles', field: 'total_profiles', aggregation: 'count', format: 'number' },
      { id: 'new_profiles', name: 'New Profiles', field: 'new_profiles', aggregation: 'sum', format: 'number' },
    ],
    dimensions: [
      { id: 'lifecycle_stage', name: 'Lifecycle Stage', field: 'lifecycle_stage', type: 'string' },
    ],
    filters: [],
    visualizations: [
      { id: 'v1', type: 'pie', title: 'Profiles by Stage', metrics: ['total_profiles'], dimensions: ['lifecycle_stage'], config: {} },
    ],
    schedule: { enabled: false, frequency: 'monthly', time: '08:00', recipients: [], format: 'csv' },
    dateRange: { type: 'last_30_days' },
    createdAt: '2024-01-08T09:00:00Z',
    updatedAt: '2024-01-12T16:00:00Z',
    status: 'draft',
  },
  {
    id: '3',
    name: 'Trust Engine Audit',
    description: 'Signal health and automation decision tracking',
    dataSource: 'trust_engine',
    metrics: [
      { id: 'signal_health', name: 'Signal Health', field: 'signal_health', aggregation: 'avg', format: 'percentage' },
      { id: 'gate_passes', name: 'Gate Passes', field: 'gate_passes', aggregation: 'sum', format: 'number' },
    ],
    dimensions: [
      { id: 'signal_type', name: 'Signal Type', field: 'signal_type', type: 'string' },
    ],
    filters: [],
    visualizations: [
      { id: 'v1', type: 'metric', title: 'Avg Signal Health', metrics: ['signal_health'], dimensions: [], config: {} },
      { id: 'v2', type: 'bar', title: 'Gate Decisions', metrics: ['gate_passes'], dimensions: ['signal_type'], config: {} },
    ],
    schedule: { enabled: true, frequency: 'daily', time: '07:00', recipients: ['ops@company.com'], format: 'pdf' },
    dateRange: { type: 'last_7_days' },
    createdAt: '2024-01-05T11:00:00Z',
    updatedAt: '2024-01-14T10:00:00Z',
    status: 'published',
  },
]

// =============================================================================
// Report Builder Modal
// =============================================================================

interface ReportBuilderModalProps {
  report: CustomReport | null
  isOpen: boolean
  onClose: () => void
  onSave: (report: CustomReport) => void
}

function ReportBuilderModal({ report, isOpen, onClose, onSave }: ReportBuilderModalProps) {
  const [activeTab, setActiveTab] = useState<'data' | 'visualizations' | 'schedule'>('data')
  const [formData, setFormData] = useState<CustomReport>(() =>
    report || {
      id: Date.now().toString(),
      name: '',
      description: '',
      dataSource: '',
      metrics: [],
      dimensions: [],
      filters: [],
      visualizations: [],
      schedule: { enabled: false, frequency: 'weekly', time: '09:00', recipients: [], format: 'pdf' },
      dateRange: { type: 'last_7_days' },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      status: 'draft',
    }
  )
  const [newRecipient, setNewRecipient] = useState('')

  if (!isOpen) return null

  const availableMetrics = AVAILABLE_METRICS[formData.dataSource] || []
  const availableDimensions = AVAILABLE_DIMENSIONS[formData.dataSource] || []

  const handleAddMetric = (metric: Metric) => {
    if (!formData.metrics.find(m => m.id === metric.id)) {
      setFormData({ ...formData, metrics: [...formData.metrics, metric] })
    }
  }

  const handleRemoveMetric = (metricId: string) => {
    setFormData({ ...formData, metrics: formData.metrics.filter(m => m.id !== metricId) })
  }

  const handleAddDimension = (dimension: Dimension) => {
    if (!formData.dimensions.find(d => d.id === dimension.id)) {
      setFormData({ ...formData, dimensions: [...formData.dimensions, dimension] })
    }
  }

  const handleRemoveDimension = (dimensionId: string) => {
    setFormData({ ...formData, dimensions: formData.dimensions.filter(d => d.id !== dimensionId) })
  }

  const handleAddVisualization = (type: string) => {
    const newViz: Visualization = {
      id: Date.now().toString(),
      type: type as Visualization['type'],
      title: `New ${type} chart`,
      metrics: formData.metrics.slice(0, 1).map(m => m.id),
      dimensions: formData.dimensions.slice(0, 1).map(d => d.id),
      config: {},
    }
    setFormData({ ...formData, visualizations: [...formData.visualizations, newViz] })
  }

  const handleRemoveVisualization = (vizId: string) => {
    setFormData({ ...formData, visualizations: formData.visualizations.filter(v => v.id !== vizId) })
  }

  const handleAddRecipient = () => {
    if (newRecipient && !formData.schedule.recipients.includes(newRecipient)) {
      setFormData({
        ...formData,
        schedule: {
          ...formData.schedule,
          recipients: [...formData.schedule.recipients, newRecipient],
        },
      })
      setNewRecipient('')
    }
  }

  const handleRemoveRecipient = (email: string) => {
    setFormData({
      ...formData,
      schedule: {
        ...formData.schedule,
        recipients: formData.schedule.recipients.filter(r => r !== email),
      },
    })
  }

  const handleSave = () => {
    onSave({ ...formData, updatedAt: new Date().toISOString() })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-card rounded-xl shadow-xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-xl font-semibold">
              {report ? 'Edit Report' : 'Create Custom Report'}
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Build a custom report with your chosen metrics and visualizations
            </p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-muted rounded-lg">
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b">
          {[
            { id: 'data', label: 'Data Source & Metrics', icon: TableCellsIcon },
            { id: 'visualizations', label: 'Visualizations', icon: ChartBarIcon },
            { id: 'schedule', label: 'Schedule', icon: ClockIcon },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={cn(
                'flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'data' && (
            <div className="space-y-6">
              {/* Report Name & Description */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Report Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary"
                    placeholder="Enter report name..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Date Range</label>
                  <select
                    value={formData.dateRange.type}
                    onChange={(e) => setFormData({
                      ...formData,
                      dateRange: { ...formData.dateRange, type: e.target.value as any }
                    })}
                    className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary"
                  >
                    <option value="last_7_days">Last 7 Days</option>
                    <option value="last_30_days">Last 30 Days</option>
                    <option value="last_90_days">Last 90 Days</option>
                    <option value="custom">Custom Range</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary"
                  rows={2}
                  placeholder="Describe what this report shows..."
                />
              </div>

              {/* Data Source Selection */}
              <div>
                <label className="block text-sm font-medium mb-3">Data Source</label>
                <div className="grid grid-cols-3 gap-3">
                  {DATA_SOURCES.map((source) => (
                    <button
                      key={source.id}
                      onClick={() => setFormData({
                        ...formData,
                        dataSource: source.id,
                        metrics: [],
                        dimensions: [],
                      })}
                      className={cn(
                        'p-4 rounded-lg border text-left transition-all',
                        formData.dataSource === source.id
                          ? 'border-primary bg-primary/5'
                          : 'hover:border-muted-foreground/50'
                      )}
                    >
                      <div className="font-medium text-sm">{source.name}</div>
                      <div className="text-xs text-muted-foreground mt-1">{source.description}</div>
                    </button>
                  ))}
                </div>
              </div>

              {formData.dataSource && (
                <>
                  {/* Metrics Selection */}
                  <div>
                    <label className="block text-sm font-medium mb-3">Select Metrics</label>
                    <div className="flex flex-wrap gap-2 mb-3">
                      {formData.metrics.map((metric) => (
                        <span
                          key={metric.id}
                          className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm"
                        >
                          {metric.name}
                          <button
                            onClick={() => handleRemoveMetric(metric.id)}
                            className="hover:bg-primary/20 rounded-full p-0.5"
                          >
                            <XMarkIcon className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {availableMetrics
                        .filter((m) => !formData.metrics.find((fm) => fm.id === m.id))
                        .map((metric) => (
                          <button
                            key={metric.id}
                            onClick={() => handleAddMetric(metric)}
                            className="px-3 py-1 rounded-full border text-sm hover:border-primary hover:text-primary transition-colors"
                          >
                            + {metric.name}
                          </button>
                        ))}
                    </div>
                  </div>

                  {/* Dimensions Selection */}
                  <div>
                    <label className="block text-sm font-medium mb-3">Select Dimensions</label>
                    <div className="flex flex-wrap gap-2 mb-3">
                      {formData.dimensions.map((dimension) => (
                        <span
                          key={dimension.id}
                          className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-blue-500/10 text-blue-500 text-sm"
                        >
                          {dimension.name}
                          <button
                            onClick={() => handleRemoveDimension(dimension.id)}
                            className="hover:bg-blue-500/20 rounded-full p-0.5"
                          >
                            <XMarkIcon className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {availableDimensions
                        .filter((d) => !formData.dimensions.find((fd) => fd.id === d.id))
                        .map((dimension) => (
                          <button
                            key={dimension.id}
                            onClick={() => handleAddDimension(dimension)}
                            className="px-3 py-1 rounded-full border text-sm hover:border-blue-500 hover:text-blue-500 transition-colors"
                          >
                            + {dimension.name}
                          </button>
                        ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {activeTab === 'visualizations' && (
            <div className="space-y-6">
              {/* Add Visualization */}
              <div>
                <label className="block text-sm font-medium mb-3">Add Visualization</label>
                <div className="flex flex-wrap gap-3">
                  {VISUALIZATION_TYPES.map((vizType) => (
                    <button
                      key={vizType.id}
                      onClick={() => handleAddVisualization(vizType.id)}
                      disabled={formData.metrics.length === 0}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:border-primary hover:text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <vizType.icon className="w-4 h-4" />
                      {vizType.name}
                    </button>
                  ))}
                </div>
                {formData.metrics.length === 0 && (
                  <p className="text-sm text-muted-foreground mt-2">
                    Select at least one metric in the Data tab to add visualizations
                  </p>
                )}
              </div>

              {/* Visualization List */}
              <div>
                <label className="block text-sm font-medium mb-3">
                  Report Visualizations ({formData.visualizations.length})
                </label>
                {formData.visualizations.length === 0 ? (
                  <div className="text-center py-8 border rounded-lg border-dashed">
                    <ChartBarIcon className="w-10 h-10 mx-auto text-muted-foreground mb-2" />
                    <p className="text-muted-foreground">No visualizations added yet</p>
                    <p className="text-sm text-muted-foreground">Click a chart type above to add one</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-4">
                    {formData.visualizations.map((viz, index) => {
                      const VizIcon = VISUALIZATION_TYPES.find(v => v.id === viz.type)?.icon || ChartBarIcon
                      return (
                        <div
                          key={viz.id}
                          className="p-4 rounded-lg border bg-muted/30"
                        >
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <VizIcon className="w-5 h-5 text-primary" />
                              <input
                                type="text"
                                value={viz.title}
                                onChange={(e) => {
                                  const newViz = [...formData.visualizations]
                                  newViz[index] = { ...viz, title: e.target.value }
                                  setFormData({ ...formData, visualizations: newViz })
                                }}
                                className="font-medium bg-transparent border-b border-transparent focus:border-primary outline-none"
                              />
                            </div>
                            <button
                              onClick={() => handleRemoveVisualization(viz.id)}
                              className="p-1 hover:bg-destructive/10 hover:text-destructive rounded"
                            >
                              <TrashIcon className="w-4 h-4" />
                            </button>
                          </div>
                          <div className="space-y-2 text-sm">
                            <div>
                              <span className="text-muted-foreground">Metrics: </span>
                              <select
                                value={viz.metrics[0] || ''}
                                onChange={(e) => {
                                  const newViz = [...formData.visualizations]
                                  newViz[index] = { ...viz, metrics: [e.target.value] }
                                  setFormData({ ...formData, visualizations: newViz })
                                }}
                                className="px-2 py-1 rounded border bg-background text-xs"
                              >
                                {formData.metrics.map((m) => (
                                  <option key={m.id} value={m.id}>{m.name}</option>
                                ))}
                              </select>
                            </div>
                            {viz.type !== 'metric' && (
                              <div>
                                <span className="text-muted-foreground">Group by: </span>
                                <select
                                  value={viz.dimensions[0] || ''}
                                  onChange={(e) => {
                                    const newViz = [...formData.visualizations]
                                    newViz[index] = { ...viz, dimensions: [e.target.value] }
                                    setFormData({ ...formData, visualizations: newViz })
                                  }}
                                  className="px-2 py-1 rounded border bg-background text-xs"
                                >
                                  <option value="">None</option>
                                  {formData.dimensions.map((d) => (
                                    <option key={d.id} value={d.id}>{d.name}</option>
                                  ))}
                                </select>
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'schedule' && (
            <div className="space-y-6">
              {/* Enable Schedule */}
              <div className="flex items-center justify-between p-4 rounded-lg border">
                <div>
                  <div className="font-medium">Scheduled Delivery</div>
                  <div className="text-sm text-muted-foreground">
                    Automatically send this report on a regular schedule
                  </div>
                </div>
                <button
                  onClick={() => setFormData({
                    ...formData,
                    schedule: { ...formData.schedule, enabled: !formData.schedule.enabled }
                  })}
                  className={cn(
                    'relative w-12 h-6 rounded-full transition-colors',
                    formData.schedule.enabled ? 'bg-primary' : 'bg-muted'
                  )}
                >
                  <span
                    className={cn(
                      'absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform',
                      formData.schedule.enabled ? 'translate-x-6' : ''
                    )}
                  />
                </button>
              </div>

              {formData.schedule.enabled && (
                <>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">Frequency</label>
                      <select
                        value={formData.schedule.frequency}
                        onChange={(e) => setFormData({
                          ...formData,
                          schedule: { ...formData.schedule, frequency: e.target.value as any }
                        })}
                        className="w-full px-3 py-2 rounded-lg border bg-background"
                      >
                        <option value="daily">Daily</option>
                        <option value="weekly">Weekly</option>
                        <option value="monthly">Monthly</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">Time</label>
                      <input
                        type="time"
                        value={formData.schedule.time}
                        onChange={(e) => setFormData({
                          ...formData,
                          schedule: { ...formData.schedule, time: e.target.value }
                        })}
                        className="w-full px-3 py-2 rounded-lg border bg-background"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">Format</label>
                      <select
                        value={formData.schedule.format}
                        onChange={(e) => setFormData({
                          ...formData,
                          schedule: { ...formData.schedule, format: e.target.value as any }
                        })}
                        className="w-full px-3 py-2 rounded-lg border bg-background"
                      >
                        <option value="pdf">PDF</option>
                        <option value="csv">CSV</option>
                        <option value="excel">Excel</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Recipients</label>
                    <div className="flex gap-2 mb-3">
                      <input
                        type="email"
                        value={newRecipient}
                        onChange={(e) => setNewRecipient(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAddRecipient()}
                        className="flex-1 px-3 py-2 rounded-lg border bg-background"
                        placeholder="Enter email address..."
                      />
                      <button
                        onClick={handleAddRecipient}
                        className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
                      >
                        Add
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {formData.schedule.recipients.map((email) => (
                        <span
                          key={email}
                          className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-muted text-sm"
                        >
                          {email}
                          <button
                            onClick={() => handleRemoveRecipient(email)}
                            className="hover:bg-muted-foreground/20 rounded-full p-0.5"
                          >
                            <XMarkIcon className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t bg-muted/30">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setFormData({ ...formData, status: 'draft' })
                handleSave()
              }}
              className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
            >
              Save as Draft
            </button>
            <button
              onClick={() => {
                setFormData({ ...formData, status: 'published' })
                handleSave()
              }}
              disabled={!formData.name || !formData.dataSource || formData.metrics.length === 0}
              className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Publish Report
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Main Component
// =============================================================================

export default function CustomReportBuilder() {
  const navigate = useNavigate()
  const [reports, setReports] = useState<CustomReport[]>(MOCK_REPORTS)
  const [isBuilderOpen, setIsBuilderOpen] = useState(false)
  const [editingReport, setEditingReport] = useState<CustomReport | null>(null)
  const [filterStatus, setFilterStatus] = useState<'all' | 'draft' | 'published'>('all')
  const [searchQuery, setSearchQuery] = useState('')

  const filteredReports = reports.filter((report) => {
    const matchesStatus = filterStatus === 'all' || report.status === filterStatus
    const matchesSearch = report.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      report.description.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesStatus && matchesSearch
  })

  const handleCreateReport = () => {
    setEditingReport(null)
    setIsBuilderOpen(true)
  }

  const handleEditReport = (report: CustomReport) => {
    setEditingReport(report)
    setIsBuilderOpen(true)
  }

  const handleSaveReport = (report: CustomReport) => {
    if (editingReport) {
      setReports(reports.map((r) => r.id === report.id ? report : r))
    } else {
      setReports([...reports, report])
    }
  }

  const handleDeleteReport = (reportId: string) => {
    setReports(reports.filter((r) => r.id !== reportId))
  }

  const handleDuplicateReport = (report: CustomReport) => {
    const newReport: CustomReport = {
      ...report,
      id: Date.now().toString(),
      name: `${report.name} (Copy)`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      status: 'draft',
    }
    setReports([...reports, newReport])
  }

  const stats = {
    total: reports.length,
    published: reports.filter((r) => r.status === 'published').length,
    scheduled: reports.filter((r) => r.schedule.enabled).length,
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <DocumentChartBarIcon className="w-8 h-8 text-primary" />
            Custom Report Builder
          </h1>
          <p className="text-muted-foreground mt-1">
            Create custom reports with your own metrics, dimensions, and visualizations
          </p>
        </div>
        <button
          onClick={handleCreateReport}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          Create Report
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-card border">
          <div className="text-sm text-muted-foreground">Total Reports</div>
          <div className="text-2xl font-bold mt-1">{stats.total}</div>
        </div>
        <div className="p-4 rounded-xl bg-card border">
          <div className="text-sm text-muted-foreground">Published</div>
          <div className="text-2xl font-bold mt-1 text-green-500">{stats.published}</div>
        </div>
        <div className="p-4 rounded-xl bg-card border">
          <div className="text-sm text-muted-foreground">Scheduled</div>
          <div className="text-2xl font-bold mt-1 text-blue-500">{stats.scheduled}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search reports..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full max-w-md px-4 py-2 rounded-lg border bg-background"
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Status:</span>
          {['all', 'published', 'draft'].map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status as typeof filterStatus)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm capitalize transition-colors',
                filterStatus === status
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted hover:bg-muted/80'
              )}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Reports Grid */}
      {filteredReports.length === 0 ? (
        <div className="text-center py-12 bg-card rounded-xl border">
          <DocumentChartBarIcon className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">No reports found</h3>
          <p className="text-muted-foreground mb-4">
            {searchQuery ? 'Try a different search term' : 'Create your first custom report to get started'}
          </p>
          {!searchQuery && (
            <button
              onClick={handleCreateReport}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <PlusIcon className="w-5 h-5" />
              Create Report
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredReports.map((report) => {
            const dataSource = DATA_SOURCES.find((ds) => ds.id === report.dataSource)
            return (
              <div
                key={report.id}
                className="bg-card rounded-xl border p-5 hover:border-primary/50 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h3 className="font-semibold">{report.name}</h3>
                    <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                      {report.description}
                    </p>
                  </div>
                  <span
                    className={cn(
                      'px-2 py-1 rounded-full text-xs font-medium',
                      report.status === 'published'
                        ? 'bg-green-500/10 text-green-500'
                        : 'bg-yellow-500/10 text-yellow-500'
                    )}
                  >
                    {report.status}
                  </span>
                </div>

                <div className="space-y-2 text-sm mb-4">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <TableCellsIcon className="w-4 h-4" />
                    <span>{dataSource?.name || 'Unknown source'}</span>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <ChartBarIcon className="w-4 h-4" />
                    <span>{report.metrics.length} metrics, {report.visualizations.length} charts</span>
                  </div>
                  {report.schedule.enabled && (
                    <div className="flex items-center gap-2 text-blue-500">
                      <ClockIcon className="w-4 h-4" />
                      <span className="capitalize">{report.schedule.frequency} at {report.schedule.time}</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 pt-3 border-t">
                  <button
                    onClick={() => handleEditReport(report)}
                    className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg bg-muted hover:bg-muted/80 text-sm"
                  >
                    <PencilIcon className="w-4 h-4" />
                    Edit
                  </button>
                  <button
                    className="flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 text-sm"
                  >
                    <EyeIcon className="w-4 h-4" />
                    View
                  </button>
                  <button
                    onClick={() => handleDuplicateReport(report)}
                    className="p-1.5 rounded-lg hover:bg-muted"
                    title="Duplicate"
                  >
                    <DocumentDuplicateIcon className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDeleteReport(report.id)}
                    className="p-1.5 rounded-lg hover:bg-destructive/10 hover:text-destructive"
                    title="Delete"
                  >
                    <TrashIcon className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Report Builder Modal */}
      <ReportBuilderModal
        report={editingReport}
        isOpen={isBuilderOpen}
        onClose={() => {
          setIsBuilderOpen(false)
          setEditingReport(null)
        }}
        onSave={handleSaveReport}
      />
    </div>
  )
}
