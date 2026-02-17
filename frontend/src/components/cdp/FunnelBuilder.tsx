/**
 * CDP Funnel Builder & Analysis Component
 * Create and analyze conversion funnels with step-by-step metrics
 */

import { useState } from 'react';
import {
  ArrowDown,
  BarChart3,
  Calendar,
  ChevronDown,
  ChevronRight,
  Clock,
  Filter,
  GitBranch,
  Loader2,
  Plus,
  RefreshCw,
  Save,
  Search,
  Target,
  Trash2,
  TrendingDown,
  Users,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  CDPFunnel,
  FunnelCreate,
  FunnelStep,
  useAnalyzeFunnel,
  useComputeFunnel,
  useCreateFunnel,
  useDeleteFunnel,
  useFunnelDropOffs,
  useFunnels,
  useUpdateFunnel,
} from '@/api/cdp';

// Step condition operators
const CONDITION_OPERATORS = [
  { value: 'equals', label: 'equals' },
  { value: 'not_equals', label: 'not equals' },
  { value: 'contains', label: 'contains' },
  { value: 'greater_than', label: 'greater than' },
  { value: 'less_than', label: 'less than' },
];

// Common event names for suggestions
const COMMON_EVENTS = [
  'PageView',
  'AddToCart',
  'ViewProduct',
  'StartCheckout',
  'Purchase',
  'SignUp',
  'Login',
  'Search',
  'FormSubmit',
];

interface StepBuilderProps {
  step: FunnelStep;
  index: number;
  onChange: (step: FunnelStep) => void;
  onRemove: () => void;
  canRemove: boolean;
}

function StepBuilder({ step, index, onChange, onRemove, canRemove }: StepBuilderProps) {
  const [showConditions, setShowConditions] = useState(false);

  const addCondition = () => {
    onChange({
      ...step,
      conditions: [...(step.conditions || []), { field: '', operator: 'equals', value: '' }],
    });
  };

  const updateCondition = (condIndex: number, field: string, value: unknown) => {
    const newConditions = [...(step.conditions || [])];
    newConditions[condIndex] = { ...newConditions[condIndex], [field]: value };
    onChange({ ...step, conditions: newConditions });
  };

  const removeCondition = (condIndex: number) => {
    onChange({
      ...step,
      conditions: (step.conditions || []).filter((_, i) => i !== condIndex),
    });
  };

  return (
    <div className="relative pl-8">
      {/* Step connector */}
      {index > 0 && <div className="absolute left-3 -top-6 w-0.5 h-6 bg-border" />}
      <div className="absolute left-0 top-4 w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-bold">
        {index + 1}
      </div>

      <div className="p-4 rounded-lg border bg-card">
        <div className="flex items-center gap-3 mb-3">
          <div className="flex-1">
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Step Name
            </label>
            <input
              type="text"
              value={step.step_name}
              onChange={(e) => onChange({ ...step, step_name: e.target.value })}
              placeholder="e.g., View Product"
              className="w-full px-3 py-1.5 rounded-md border bg-background text-sm"
            />
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Event Name
            </label>
            <div className="relative">
              <input
                type="text"
                value={step.event_name}
                onChange={(e) => onChange({ ...step, event_name: e.target.value })}
                placeholder="e.g., ViewProduct"
                list={`events-${index}`}
                className="w-full px-3 py-1.5 rounded-md border bg-background text-sm"
              />
              <datalist id={`events-${index}`}>
                {COMMON_EVENTS.map((event) => (
                  <option key={event} value={event} />
                ))}
              </datalist>
            </div>
          </div>
          {canRemove && (
            <button
              onClick={onRemove}
              className="mt-4 p-1.5 rounded-md hover:bg-red-500/10 text-muted-foreground hover:text-red-500 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Conditions toggle */}
        <button
          onClick={() => setShowConditions(!showConditions)}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {showConditions ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
          <Filter className="w-3.5 h-3.5" />
          {step.conditions?.length || 0} Conditions
        </button>

        {/* Conditions */}
        {showConditions && (
          <div className="mt-3 space-y-2">
            {(step.conditions || []).map((condition, condIndex) => (
              <div key={condIndex} className="flex items-center gap-2 p-2 bg-muted/30 rounded-md">
                <input
                  type="text"
                  value={condition.field}
                  onChange={(e) => updateCondition(condIndex, 'field', e.target.value)}
                  placeholder="property"
                  className="flex-1 px-2 py-1 rounded border bg-background text-xs"
                />
                <select
                  value={condition.operator}
                  onChange={(e) => updateCondition(condIndex, 'operator', e.target.value)}
                  className="px-2 py-1 rounded border bg-background text-xs"
                >
                  {CONDITION_OPERATORS.map((op) => (
                    <option key={op.value} value={op.value}>
                      {op.label}
                    </option>
                  ))}
                </select>
                <input
                  type="text"
                  value={condition.value as string}
                  onChange={(e) => updateCondition(condIndex, 'value', e.target.value)}
                  placeholder="value"
                  className="flex-1 px-2 py-1 rounded border bg-background text-xs"
                />
                <button
                  onClick={() => removeCondition(condIndex)}
                  className="p-1 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-500"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
            <button
              onClick={addCondition}
              className="flex items-center gap-1 text-xs text-primary hover:text-primary/80"
            >
              <Plus className="w-3 h-3" />
              Add Condition
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

interface FunnelFormProps {
  funnel?: CDPFunnel;
  onSave: () => void;
  onCancel: () => void;
}

function FunnelForm({ funnel, onSave, onCancel }: FunnelFormProps) {
  const [name, setName] = useState(funnel?.name || '');
  const [description, setDescription] = useState(funnel?.description || '');
  const [steps, setSteps] = useState<FunnelStep[]>(
    funnel?.steps || [
      { step_name: '', event_name: '' },
      { step_name: '', event_name: '' },
    ]
  );
  const [conversionWindowDays, setConversionWindowDays] = useState(
    funnel?.conversion_window_days || 30
  );
  const [stepTimeoutHours, _setStepTimeoutHours] = useState<number | undefined>(
    funnel?.step_timeout_hours
  );
  const [autoRefresh, setAutoRefresh] = useState(funnel?.auto_refresh ?? true);
  const [refreshIntervalHours, setRefreshIntervalHours] = useState(
    funnel?.refresh_interval_hours || 24
  );

  const createMutation = useCreateFunnel();
  const updateMutation = useUpdateFunnel();

  const addStep = () => {
    if (steps.length < 20) {
      setSteps([...steps, { step_name: '', event_name: '' }]);
    }
  };

  const updateStep = (index: number, step: FunnelStep) => {
    const newSteps = [...steps];
    newSteps[index] = step;
    setSteps(newSteps);
  };

  const removeStep = (index: number) => {
    if (steps.length > 2) {
      setSteps(steps.filter((_, i) => i !== index));
    }
  };

  const handleSubmit = async () => {
    const data: FunnelCreate = {
      name,
      description,
      steps,
      conversion_window_days: conversionWindowDays,
      step_timeout_hours: stepTimeoutHours,
      auto_refresh: autoRefresh,
      refresh_interval_hours: refreshIntervalHours,
    };

    try {
      if (funnel) {
        await updateMutation.mutateAsync({ funnelId: funnel.id, update: data });
      } else {
        await createMutation.mutateAsync(data);
      }
      onSave();
    } catch (error) {
      // Error handled by mutation
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;
  const isValid = name && steps.length >= 2 && steps.every((s) => s.step_name && s.event_name);

  return (
    <div className="space-y-6">
      {/* Basic info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1.5">Funnel Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., E-commerce Checkout Funnel"
            className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1.5">Conversion Window</label>
          <select
            value={conversionWindowDays}
            onChange={(e) => setConversionWindowDays(Number(e.target.value))}
            className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
          >
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
            <option value={60}>60 days</option>
            <option value={90}>90 days</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1.5">Description</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe this funnel..."
          rows={2}
          className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 resize-none"
        />
      </div>

      {/* Steps builder */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <label className="block text-sm font-medium">Funnel Steps ({steps.length}/20)</label>
          {steps.length < 20 && (
            <button
              onClick={addStep}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-primary/10 text-primary hover:bg-primary/20 text-sm font-medium transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Step
            </button>
          )}
        </div>
        <div className="space-y-6">
          {steps.map((step, index) => (
            <StepBuilder
              key={index}
              step={step}
              index={index}
              onChange={(s) => updateStep(index, s)}
              onRemove={() => removeStep(index)}
              canRemove={steps.length > 2}
            />
          ))}
        </div>
      </div>

      {/* Auto-refresh settings */}
      <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/30 border">
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="autoRefresh"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className="w-4 h-4 rounded border-gray-300"
          />
          <label htmlFor="autoRefresh" className="text-sm font-medium">
            Auto-refresh metrics
          </label>
        </div>
        {autoRefresh && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">every</span>
            <select
              value={refreshIntervalHours}
              onChange={(e) => setRefreshIntervalHours(Number(e.target.value))}
              className="px-2 py-1 rounded border bg-background text-sm"
            >
              <option value={1}>1 hour</option>
              <option value={6}>6 hours</option>
              <option value={12}>12 hours</option>
              <option value={24}>24 hours</option>
            </select>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 pt-4 border-t">
        <button
          onClick={onCancel}
          className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={!isValid || isLoading}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {funnel ? 'Update Funnel' : 'Create Funnel'}
        </button>
      </div>
    </div>
  );
}

interface FunnelAnalysisViewProps {
  funnel: CDPFunnel;
  onBack: () => void;
}

function FunnelAnalysisView({ funnel, onBack }: FunnelAnalysisViewProps) {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedStep, setSelectedStep] = useState<number | null>(null);

  const analyzeMutation = useAnalyzeFunnel();
  const { data: dropOffs, isLoading: dropOffsLoading } = useFunnelDropOffs(
    funnel.id,
    selectedStep || 0,
    { limit: 10 },
    { enabled: selectedStep !== null && selectedStep > 0 }
  );

  const handleAnalyze = async () => {
    await analyzeMutation.mutateAsync({
      funnelId: funnel.id,
      params: { start_date: startDate || undefined, end_date: endDate || undefined },
    });
  };

  const analysis = analyzeMutation.data;
  const metrics = analysis?.step_analysis || funnel.step_metrics || [];

  // Helper to get conversion rate from either metric type
  const getConversionRate = (step: (typeof metrics)[number]) => {
    if ('conversion_rate' in step) return step.conversion_rate;
    if ('conversion_rate_from_start' in step) return step.conversion_rate_from_start;
    return 0;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-2 rounded-lg hover:bg-muted transition-colors">
            <ChevronRight className="w-5 h-5 rotate-180" />
          </button>
          <div>
            <h2 className="text-xl font-semibold">{funnel.name}</h2>
            <p className="text-sm text-muted-foreground">{funnel.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'px-2 py-0.5 rounded-full text-xs font-medium',
              funnel.status === 'active'
                ? 'bg-green-500/10 text-green-500'
                : 'bg-gray-500/10 text-gray-500'
            )}
          >
            {funnel.status}
          </span>
        </div>
      </div>

      {/* Date filter */}
      <div className="flex items-center gap-4 p-4 rounded-lg border bg-card">
        <Calendar className="w-4 h-4 text-muted-foreground" />
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="px-3 py-1.5 rounded-md border bg-background text-sm"
          />
          <span className="text-muted-foreground">to</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="px-3 py-1.5 rounded-md border bg-background text-sm"
          />
        </div>
        <button
          onClick={handleAnalyze}
          disabled={analyzeMutation.isPending}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 text-sm font-medium transition-colors"
        >
          {analyzeMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <BarChart3 className="w-4 h-4" />
          )}
          Analyze
        </button>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border bg-card">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Users className="w-4 h-4" />
            Total Entered
          </div>
          <div className="text-2xl font-bold">
            {(analysis?.total_entered || funnel.total_entered).toLocaleString()}
          </div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Target className="w-4 h-4" />
            Total Converted
          </div>
          <div className="text-2xl font-bold">
            {(analysis?.total_converted || funnel.total_converted).toLocaleString()}
          </div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Zap className="w-4 h-4" />
            Conversion Rate
          </div>
          <div className="text-2xl font-bold text-green-500">
            {(
              (analysis?.overall_conversion_rate || funnel.overall_conversion_rate || 0) * 100
            ).toFixed(1)}
            %
          </div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Clock className="w-4 h-4" />
            Avg. Time
          </div>
          <div className="text-2xl font-bold">
            {analysis?.avg_conversion_time_seconds
              ? `${Math.round(analysis.avg_conversion_time_seconds / 3600)}h`
              : '-'}
          </div>
        </div>
      </div>

      {/* Funnel visualization */}
      <div className="p-6 rounded-xl border bg-card">
        <h3 className="font-medium mb-6">Funnel Steps</h3>
        <div className="space-y-4">
          {metrics.map((step, index) => {
            const prevCount =
              index === 0
                ? analysis?.total_entered || funnel.total_entered
                : metrics[index - 1].count;
            const dropOffPct = prevCount > 0 ? ((prevCount - step.count) / prevCount) * 100 : 0;
            const isSelected = selectedStep === step.step;

            return (
              <div key={index}>
                <div
                  className={cn(
                    'relative p-4 rounded-lg border cursor-pointer transition-all',
                    isSelected ? 'border-primary bg-primary/5' : 'hover:border-primary/50'
                  )}
                  onClick={() => setSelectedStep(isSelected ? null : step.step)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-bold">
                        {step.step}
                      </div>
                      <div>
                        <div className="font-medium">{step.name}</div>
                        <div className="text-xs text-muted-foreground">{step.event_name}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold">{step.count.toLocaleString()}</div>
                      <div className="text-xs text-muted-foreground">
                        {((getConversionRate(step) || 0) * 100).toFixed(1)}% from start
                      </div>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-500"
                      style={{ width: `${(getConversionRate(step) || 0) * 100}%` }}
                    />
                  </div>

                  {/* Drop-off indicator */}
                  {index > 0 && step.drop_off_count > 0 && (
                    <div className="absolute -top-3 right-4 flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/10 text-red-500 text-xs font-medium">
                      <TrendingDown className="w-3 h-3" />
                      {dropOffPct.toFixed(1)}% dropped
                    </div>
                  )}
                </div>

                {/* Drop-off arrow */}
                {index < metrics.length - 1 && (
                  <div className="flex justify-center py-2">
                    <ArrowDown className="w-5 h-5 text-muted-foreground" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Drop-offs panel */}
      {selectedStep !== null && selectedStep > 0 && (
        <div className="p-4 rounded-xl border bg-card">
          <h3 className="font-medium flex items-center gap-2 mb-4">
            <TrendingDown className="w-4 h-4 text-red-500" />
            Profiles that dropped off at Step {selectedStep}
          </h3>
          {dropOffsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
            </div>
          ) : dropOffs?.profiles && dropOffs.profiles.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">
                      Profile ID
                    </th>
                    <th className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">
                      Lifecycle
                    </th>
                    <th className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">
                      Events
                    </th>
                    <th className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">
                      Last Seen
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {dropOffs.profiles.map((profile) => (
                    <tr key={profile.id} className="border-b hover:bg-muted/30">
                      <td className="py-2 px-3">
                        <code className="text-xs bg-muted px-2 py-1 rounded">
                          {profile.id.slice(0, 12)}...
                        </code>
                      </td>
                      <td className="py-2 px-3 capitalize text-sm">{profile.lifecycle_stage}</td>
                      <td className="py-2 px-3 text-sm">{profile.total_events}</td>
                      <td className="py-2 px-3 text-sm text-muted-foreground">
                        {new Date(profile.last_seen_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">No drop-off data available</div>
          )}
        </div>
      )}
    </div>
  );
}

export function FunnelBuilder() {
  const [showForm, setShowForm] = useState(false);
  const [selectedFunnel, setSelectedFunnel] = useState<CDPFunnel | null>(null);
  const [analyzingFunnel, setAnalyzingFunnel] = useState<CDPFunnel | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const { data: funnelsData, isLoading, refetch } = useFunnels();
  const deleteMutation = useDeleteFunnel();
  const computeMutation = useComputeFunnel();

  const funnels = funnelsData?.funnels || [];
  const filteredFunnels = funnels.filter(
    (f) =>
      f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleEdit = (funnel: CDPFunnel) => {
    setSelectedFunnel(funnel);
    setShowForm(true);
  };

  const handleDelete = async (funnelId: string) => {
    if (confirm('Are you sure you want to delete this funnel?')) {
      await deleteMutation.mutateAsync(funnelId);
      refetch();
    }
  };

  const handleCompute = async (funnelId: string) => {
    await computeMutation.mutateAsync(funnelId);
    refetch();
  };

  const handleFormSave = () => {
    setShowForm(false);
    setSelectedFunnel(null);
    refetch();
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      active: 'bg-green-500/10 text-green-500',
      computing: 'bg-blue-500/10 text-blue-500',
      stale: 'bg-amber-500/10 text-amber-500',
      draft: 'bg-gray-500/10 text-gray-500',
    };
    return (
      <span
        className={cn(
          'px-2 py-0.5 rounded-full text-xs font-medium',
          styles[status] || styles.draft
        )}
      >
        {status}
      </span>
    );
  };

  if (analyzingFunnel) {
    return <FunnelAnalysisView funnel={analyzingFunnel} onBack={() => setAnalyzingFunnel(null)} />;
  }

  if (showForm) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setShowForm(false);
              setSelectedFunnel(null);
            }}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <ChevronRight className="w-5 h-5 rotate-180" />
          </button>
          <h2 className="text-xl font-semibold">
            {selectedFunnel ? 'Edit Funnel' : 'Create Funnel'}
          </h2>
        </div>
        <FunnelForm
          funnel={selectedFunnel || undefined}
          onSave={handleFormSave}
          onCancel={() => {
            setShowForm(false);
            setSelectedFunnel(null);
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <GitBranch className="w-6 h-6 text-primary" />
            Funnel Builder
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Create and analyze conversion funnels to understand user journeys
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Funnel
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search funnels..."
          className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
        />
      </div>

      {/* Funnels list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : filteredFunnels.length === 0 ? (
        <div className="text-center py-12 bg-card border rounded-xl">
          <GitBranch className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="font-semibold mb-2">No funnels yet</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Create your first funnel to start tracking conversions
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Funnel
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredFunnels.map((funnel) => (
            <div
              key={funnel.id}
              className="p-4 rounded-xl border bg-card hover:shadow-md transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold">{funnel.name}</h3>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {funnel.description || `${funnel.steps.length} steps`}
                  </p>
                </div>
                {getStatusBadge(funnel.status)}
              </div>

              <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4">
                <div className="flex items-center gap-1">
                  <Users className="w-4 h-4" />
                  <span>{funnel.total_entered.toLocaleString()}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Target className="w-4 h-4" />
                  <span>{((funnel.overall_conversion_rate || 0) * 100).toFixed(1)}%</span>
                </div>
              </div>

              {/* Mini funnel visualization */}
              <div className="flex items-center gap-1 mb-4">
                {funnel.steps.map((step, index) => (
                  <div
                    key={index}
                    className="flex-1 h-2 bg-primary/20 rounded-full overflow-hidden"
                    title={step.step_name}
                  >
                    <div
                      className="h-full bg-primary"
                      style={{
                        width: `${
                          funnel.step_metrics?.[index]?.conversion_rate
                            ? funnel.step_metrics[index].conversion_rate * 100
                            : 100
                        }%`,
                      }}
                    />
                  </div>
                ))}
              </div>

              <div className="flex items-center gap-2 pt-3 border-t">
                <button
                  onClick={() => setAnalyzingFunnel(funnel)}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md bg-primary/10 text-primary hover:bg-primary/20 text-sm font-medium transition-colors"
                >
                  <BarChart3 className="w-4 h-4" />
                  Analyze
                </button>
                <button
                  onClick={() => handleEdit(funnel)}
                  className="px-3 py-1.5 rounded-md bg-muted hover:bg-muted/80 text-sm font-medium transition-colors"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleCompute(funnel.id)}
                  disabled={computeMutation.isPending}
                  className="px-3 py-1.5 rounded-md hover:bg-muted text-sm font-medium transition-colors"
                >
                  <RefreshCw
                    className={cn('w-4 h-4', computeMutation.isPending && 'animate-spin')}
                  />
                </button>
                <button
                  onClick={() => handleDelete(funnel.id)}
                  className="px-3 py-1.5 rounded-md hover:bg-red-500/10 text-muted-foreground hover:text-red-500 text-sm font-medium transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default FunnelBuilder;
