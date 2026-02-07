/**
 * Knowledge Graph Insights Component
 *
 * Displays detected problems and suggested solutions from the
 * Knowledge Graph analysis engine.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  ChevronRight,
  ChevronDown,
  Zap,
  TrendingDown,
  Shield,
  Users,
  GitBranch,
  BarChart3,
  ArrowRight,
  Sparkles,
  RefreshCw,
} from 'lucide-react';
import api from '@/lib/api';

// Types
interface Solution {
  title: string;
  description: string;
  action_type: string;
  priority: number;
  steps: string[];
  affected_entities: Record<string, unknown>[];
  estimated_impact: string | null;
  auto_fixable: boolean;
}

interface Problem {
  id: string;
  category: string;
  severity: string;
  title: string;
  description: string;
  detected_at: string;
  root_cause_path: Record<string, unknown>[];
  affected_nodes: Record<string, unknown>[];
  metrics: Record<string, unknown>;
  solutions: Solution[];
}

interface HealthSummary {
  health_score: number;
  status: string;
  problem_counts: Record<string, number>;
  total_problems: number;
  top_problem: Problem | null;
}

interface ProblemsResponse {
  problems: Problem[];
  total: number;
  by_severity: Record<string, number>;
}

// Severity config
const severityConfig = {
  critical: {
    icon: AlertTriangle,
    color: 'text-red-500',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    badge: 'bg-red-500 text-white',
  },
  high: {
    icon: AlertCircle,
    color: 'text-orange-500',
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/30',
    badge: 'bg-orange-500 text-white',
  },
  medium: {
    icon: Info,
    color: 'text-yellow-500',
    bg: 'bg-yellow-500/10',
    border: 'border-yellow-500/30',
    badge: 'bg-yellow-500 text-black',
  },
  low: {
    icon: CheckCircle2,
    color: 'text-blue-500',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    badge: 'bg-blue-500 text-white',
  },
};

// Category icons
const categoryIcons: Record<string, typeof TrendingDown> = {
  revenue_decline: TrendingDown,
  automation_blocked: Shield,
  signal_degraded: Zap,
  segment_underperforming: Users,
  attribution_gap: GitBranch,
  trust_gate_bottleneck: Shield,
  channel_inefficiency: BarChart3,
};

// Health Score Ring
function HealthScoreRing({ score, status }: { score: number; status: string }) {
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  const statusColors = {
    healthy: '#22c55e',
    degraded: '#f59e0b',
    critical: '#ef4444',
  };

  const color = statusColors[status as keyof typeof statusColors] || statusColors.degraded;

  return (
    <div className="relative w-32 h-32">
      <svg className="w-full h-full transform -rotate-90">
        <circle
          cx="64"
          cy="64"
          r="45"
          stroke="currentColor"
          strokeWidth="8"
          fill="none"
          className="text-white/10"
        />
        <circle
          cx="64"
          cy="64"
          r="45"
          stroke={color}
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold text-white">{Math.round(score)}</span>
        <span className="text-xs text-gray-400 uppercase tracking-wider">{status}</span>
      </div>
    </div>
  );
}

// Problem Card Component
function ProblemCard({ problem, isExpanded, onToggle }: {
  problem: Problem;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const config = severityConfig[problem.severity as keyof typeof severityConfig] || severityConfig.medium;
  const SeverityIcon = config.icon;
  const CategoryIcon = categoryIcons[problem.category] || AlertCircle;

  return (
    <div className={`rounded-xl border ${config.border} ${config.bg} overflow-hidden transition-all duration-300`}>
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full p-4 flex items-start gap-4 text-left hover:bg-white/5 transition-colors"
      >
        <div className={`p-2 rounded-lg ${config.bg} ${config.color}`}>
          <SeverityIcon className="w-5 h-5" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${config.badge}`}>
              {problem.severity.toUpperCase()}
            </span>
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <CategoryIcon className="w-3 h-3" />
              {problem.category.replace(/_/g, ' ')}
            </span>
          </div>
          <h3 className="text-white font-semibold truncate">{problem.title}</h3>
          <p className="text-sm text-gray-400 mt-1 line-clamp-2">{problem.description}</p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            {problem.solutions.length} solution{problem.solutions.length !== 1 ? 's' : ''}
          </span>
          {isExpanded ? (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-white/10 p-4 space-y-4">
          {/* Root Cause Path */}
          {problem.root_cause_path.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-2 flex items-center gap-2">
                <GitBranch className="w-4 h-4" />
                Root Cause Analysis
              </h4>
              <div className="space-y-2">
                {problem.root_cause_path.map((cause, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-sm">
                    <div className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center text-xs text-gray-400">
                      {idx + 1}
                    </div>
                    <div>
                      <span className="text-cyan-400 font-medium">{String(cause.node)}</span>
                      <span className="text-gray-400 mx-2">→</span>
                      <span className="text-white">{String(cause.finding)}</span>
                      {cause.detail && (
                        <p className="text-gray-500 text-xs mt-0.5">{String(cause.detail)}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metrics */}
          {Object.keys(problem.metrics).length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-2 flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                Key Metrics
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {Object.entries(problem.metrics).slice(0, 6).map(([key, value]) => (
                  <div key={key} className="bg-white/5 rounded-lg p-2">
                    <div className="text-xs text-gray-500 truncate">
                      {key.replace(/_/g, ' ')}
                    </div>
                    <div className="text-sm font-medium text-white truncate">
                      {typeof value === 'number'
                        ? value.toLocaleString(undefined, { maximumFractionDigits: 1 })
                        : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Solutions */}
          <div>
            <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              Suggested Solutions
            </h4>
            <div className="space-y-3">
              {problem.solutions.map((solution, idx) => (
                <SolutionCard key={idx} solution={solution} priority={idx + 1} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Solution Card Component
function SolutionCard({ solution, priority }: { solution: Solution; priority: number }) {
  const [showSteps, setShowSteps] = useState(false);

  const actionTypeColors: Record<string, string> = {
    investigate: 'bg-blue-500/20 text-blue-400',
    fix: 'bg-red-500/20 text-red-400',
    adjust: 'bg-amber-500/20 text-amber-400',
    monitor: 'bg-green-500/20 text-green-400',
  };

  return (
    <div className="bg-white/5 rounded-lg p-4 border border-white/10">
      <div className="flex items-start gap-3">
        <div className="w-6 h-6 rounded-full bg-amber-500/20 flex items-center justify-center text-xs font-bold text-amber-400">
          {priority}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h5 className="text-white font-medium">{solution.title}</h5>
            <span className={`px-2 py-0.5 rounded text-xs ${actionTypeColors[solution.action_type] || 'bg-gray-500/20 text-gray-400'}`}>
              {solution.action_type}
            </span>
            {solution.auto_fixable && (
              <span className="px-2 py-0.5 rounded text-xs bg-green-500/20 text-green-400 flex items-center gap-1">
                <Zap className="w-3 h-3" />
                Auto-fix available
              </span>
            )}
          </div>
          <p className="text-sm text-gray-400">{solution.description}</p>

          {solution.estimated_impact && (
            <p className="text-xs text-cyan-400 mt-2 flex items-center gap-1">
              <ArrowRight className="w-3 h-3" />
              {solution.estimated_impact}
            </p>
          )}

          {solution.steps.length > 0 && (
            <div className="mt-3">
              <button
                onClick={() => setShowSteps(!showSteps)}
                className="text-xs text-gray-400 hover:text-white flex items-center gap-1 transition-colors"
              >
                {showSteps ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                {showSteps ? 'Hide' : 'Show'} {solution.steps.length} steps
              </button>

              {showSteps && (
                <ol className="mt-2 space-y-1 text-sm text-gray-400 list-decimal list-inside">
                  {solution.steps.map((step, idx) => (
                    <li key={idx} className="pl-2">{step}</li>
                  ))}
                </ol>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Main Component
export function KGInsights() {
  const [expandedProblem, setExpandedProblem] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);

  // Fetch health summary
  const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useQuery<HealthSummary>({
    queryKey: ['kg-health'],
    queryFn: async () => {
      const res = await api.get('/knowledge-graph/insights/health');
      return res.data;
    },
    refetchInterval: 60000, // Refresh every minute
  });

  // Fetch problems
  const { data: problemsData, isLoading: problemsLoading, refetch: refetchProblems } = useQuery<ProblemsResponse>({
    queryKey: ['kg-problems', severityFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (severityFilter) params.set('severity', severityFilter);
      const res = await api.get(`/knowledge-graph/insights/problems?${params}`);
      return res.data;
    },
    refetchInterval: 60000,
  });

  const handleRefresh = () => {
    refetchHealth();
    refetchProblems();
  };

  const problems = problemsData?.problems || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-amber-400" />
            Knowledge Graph Insights
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            AI-powered problem detection with suggested solutions
          </p>
        </div>
        <button
          onClick={handleRefresh}
          className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Health Summary Card */}
      <div className="bg-[#12121a] rounded-xl border border-white/10 p-6">
        <div className="flex items-center gap-8">
          {healthLoading ? (
            <div className="w-32 h-32 rounded-full bg-white/5 animate-pulse" />
          ) : health ? (
            <HealthScoreRing score={health.health_score} status={health.status} />
          ) : null}

          <div className="flex-1">
            <h3 className="text-lg font-semibold text-white mb-4">System Health Overview</h3>
            <div className="grid grid-cols-4 gap-4">
              {Object.entries(health?.problem_counts || {}).map(([severity, count]) => {
                const config = severityConfig[severity as keyof typeof severityConfig];
                return (
                  <button
                    key={severity}
                    onClick={() => setSeverityFilter(severityFilter === severity ? null : severity)}
                    className={`p-3 rounded-lg border transition-all ${
                      severityFilter === severity
                        ? `${config?.border} ${config?.bg}`
                        : 'border-white/10 bg-white/5 hover:bg-white/10'
                    }`}
                  >
                    <div className={`text-2xl font-bold ${config?.color || 'text-white'}`}>
                      {count}
                    </div>
                    <div className="text-xs text-gray-400 capitalize">{severity}</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Top Problem Preview */}
          {health?.top_problem && (
            <div className="w-80 bg-white/5 rounded-lg p-4 border border-white/10">
              <div className="text-xs text-gray-500 mb-2">Top Priority</div>
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5" />
                <div>
                  <div className="text-sm font-medium text-white line-clamp-1">
                    {health.top_problem.title}
                  </div>
                  <div className="text-xs text-gray-400 mt-1 line-clamp-2">
                    {health.top_problem.solutions[0]?.title || 'View solutions'}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Severity Filter Pills */}
      {severityFilter && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Filtering by:</span>
          <button
            onClick={() => setSeverityFilter(null)}
            className={`px-3 py-1 rounded-full text-sm flex items-center gap-1 ${
              severityConfig[severityFilter as keyof typeof severityConfig]?.badge || 'bg-gray-500 text-white'
            }`}
          >
            {severityFilter}
            <span className="ml-1">×</span>
          </button>
        </div>
      )}

      {/* Problems List */}
      <div className="space-y-3">
        {problemsLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 bg-white/5 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : problems.length === 0 ? (
          <div className="text-center py-12 bg-[#12121a] rounded-xl border border-white/10">
            <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">All Systems Healthy</h3>
            <p className="text-gray-400">No problems detected in the last 7 days.</p>
          </div>
        ) : (
          problems.map((problem) => (
            <ProblemCard
              key={problem.id}
              problem={problem}
              isExpanded={expandedProblem === problem.id}
              onToggle={() => setExpandedProblem(
                expandedProblem === problem.id ? null : problem.id
              )}
            />
          ))
        )}
      </div>
    </div>
  );
}

export default KGInsights;
