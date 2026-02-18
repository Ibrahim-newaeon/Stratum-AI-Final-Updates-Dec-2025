/**
 * KG Problem Detection - Knowledge Graph problem detection view
 *
 * Displays detected problems across campaigns with severity levels,
 * impact estimates, and resolution actions.
 */

import { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { motion } from 'framer-motion';
import {
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  CurrencyDollarIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import { usePriceMetrics } from '@/hooks/usePriceMetrics';
import { useKGProblems, useResolveKGProblem, type ProblemSeverity } from '@/api/knowledgeGraph';
import { ProblemCard } from '@/components/shared/ProblemCard';

const fadeIn = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.3 },
};

export default function KGProblemDetection() {
  const { showPriceMetrics } = usePriceMetrics()
  const [severityFilter, setSeverityFilter] = useState<ProblemSeverity | 'all'>('all');

  const { data, isLoading } = useKGProblems(
    severityFilter !== 'all' ? { severity: severityFilter } : undefined
  );
  const resolveMutation = useResolveKGProblem();

  const summary = data?.summary;
  const problems = data?.problems || [];

  const filteredProblems =
    severityFilter === 'all'
      ? problems
      : problems.filter((p) => p.severity === severityFilter);

  const handleResolve = (problemId: string) => {
    resolveMutation.mutate(problemId);
  };

  const metricCards = [
    {
      label: 'Critical Issues',
      value: summary?.critical ?? 0,
      icon: ExclamationCircleIcon,
      color: 'text-red-500',
      bgColor: 'bg-red-500/10',
      borderColor: 'border-red-500/20',
    },
    {
      label: 'Warnings',
      value: summary?.warnings ?? 0,
      icon: ExclamationTriangleIcon,
      color: 'text-amber-500',
      bgColor: 'bg-amber-500/10',
      borderColor: 'border-amber-500/20',
    },
    {
      label: 'Resolved (30d)',
      value: summary?.resolved30d ?? 0,
      icon: CheckCircleIcon,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10',
      borderColor: 'border-green-500/20',
    },
    {
      label: 'Revenue at Risk',
      value: `$${((summary?.revenueAtRisk ?? 0) / 1000).toFixed(1)}k`,
      icon: CurrencyDollarIcon,
      color: 'text-red-400',
      bgColor: 'bg-red-500/10',
      borderColor: 'border-red-500/20',
    },
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <>
      <Helmet>
        <title>Problem Detection - Knowledge Graph | Stratum AI</title>
      </Helmet>

      <div className="space-y-6 max-w-7xl mx-auto">
        {/* Header */}
        <motion.div {...fadeIn}>
          <h1 className="text-2xl font-bold">Problem Detection</h1>
          <p className="text-muted-foreground">
            AI-detected issues across your campaigns with revenue impact estimates
          </p>
        </motion.div>

        {/* Metric Cards */}
        <motion.div
          className={cn(
            'grid grid-cols-1 sm:grid-cols-2 gap-4',
            showPriceMetrics ? 'lg:grid-cols-4' : 'lg:grid-cols-3'
          )}
          {...fadeIn}
          transition={{ delay: 0.1 }}
        >
          {metricCards.filter(card => showPriceMetrics || card.label !== 'Revenue at Risk').map((card) => (
            <div
              key={card.label}
              className={cn(
                'rounded-xl border p-4 backdrop-blur-sm',
                card.borderColor,
                card.bgColor
              )}
            >
              <div className="flex items-center gap-3">
                <div className={cn('p-2 rounded-lg', card.bgColor)}>
                  <card.icon className={cn('h-5 w-5', card.color)} />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{card.label}</p>
                  <p className={cn('text-xl font-bold', card.color)}>{card.value}</p>
                </div>
              </div>
            </div>
          ))}
        </motion.div>

        {/* Filter Bar */}
        <motion.div
          className="flex items-center gap-3"
          {...fadeIn}
          transition={{ delay: 0.15 }}
        >
          <FunnelIcon className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Filter:</span>
          {(['all', 'critical', 'warning', 'info'] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => setSeverityFilter(filter)}
              className={cn(
                'px-3 py-1.5 text-sm rounded-lg transition-colors capitalize',
                severityFilter === filter
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'hover:bg-white/5 text-muted-foreground'
              )}
            >
              {filter === 'all' ? 'All Issues' : filter}
            </button>
          ))}
        </motion.div>

        {/* Problem Cards */}
        <motion.div
          className="space-y-4"
          {...fadeIn}
          transition={{ delay: 0.2 }}
        >
          {filteredProblems.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <CheckCircleIcon className="h-12 w-12 mx-auto mb-3 text-green-500" />
              <p className="font-medium">No issues found</p>
              <p className="text-sm">All campaigns are running smoothly</p>
            </div>
          ) : (
            filteredProblems.map((problem) => (
              <ProblemCard
                key={problem.id}
                severity={problem.severity}
                title={problem.title}
                description={problem.description}
                impact={problem.impact}
                affectedCampaigns={problem.affectedCampaigns}
                platform={problem.platform}
                resolved={problem.status === 'resolved'}
                onResolve={
                  problem.severity === 'critical'
                    ? () => handleResolve(problem.id)
                    : undefined
                }
                onReview={() => handleResolve(problem.id)}
              />
            ))
          )}
        </motion.div>
      </div>
    </>
  );
}
