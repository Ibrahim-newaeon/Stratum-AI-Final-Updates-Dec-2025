/**
 * Tenant Audit Log
 *
 * Activity log with search, filters, pagination, and CSV export.
 * Shows all user actions within the tenant.
 */

import { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  MagnifyingGlassIcon,
  ArrowDownTrayIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  UsersIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import {
  useTenantAuditLogs,
  useTenantAuditStats,
  useExportAuditLogs,
  type AuditAction,
} from '@/api/audit';
import { ActivityVolumeChart } from '@/components/shared/ActivityVolumeChart';

const fadeIn = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.3 },
};

const actionConfig: Record<AuditAction, { color: string; bg: string }> = {
  create: { color: 'text-green-400', bg: 'bg-green-500/10' },
  update: { color: 'text-blue-400', bg: 'bg-blue-500/10' },
  delete: { color: 'text-red-400', bg: 'bg-red-500/10' },
  login: { color: 'text-purple-400', bg: 'bg-purple-500/10' },
  logout: { color: 'text-gray-400', bg: 'bg-gray-500/10' },
  export: { color: 'text-amber-400', bg: 'bg-amber-500/10' },
  sync: { color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
  invite: { color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
};

export default function TenantAuditLog() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const tenantIdNum = tenantId ? parseInt(tenantId, 10) : 0;

  const [search, setSearch] = useState('');
  const [actionFilter, setActionFilter] = useState<AuditAction | ''>('');
  const [page, setPage] = useState(1);
  const limit = 20;

  const { data: logs, isLoading: logsLoading } = useTenantAuditLogs(tenantIdNum, {
    page,
    limit,
    action: actionFilter || undefined,
    search: search || undefined,
  });

  const { data: stats } = useTenantAuditStats(tenantIdNum);
  const exportMutation = useExportAuditLogs(tenantIdNum);

  const totalPages = logs ? Math.ceil(logs.total / limit) : 1;

  const formatTimestamp = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const metricCards = [
    {
      label: 'Total Events',
      value: stats?.totalEvents?.toLocaleString() ?? '0',
      icon: ClockIcon,
      color: 'text-blue-500',
    },
    {
      label: 'Successful',
      value: stats?.successful?.toLocaleString() ?? '0',
      icon: CheckCircleIcon,
      color: 'text-green-500',
    },
    {
      label: 'Failed',
      value: stats?.failed?.toLocaleString() ?? '0',
      icon: XCircleIcon,
      color: 'text-red-500',
    },
    {
      label: 'Active Users',
      value: stats?.activeUsers?.toString() ?? '0',
      icon: UsersIcon,
      color: 'text-purple-500',
    },
  ];

  return (
    <>
      <Helmet>
        <title>Audit Log | Stratum AI</title>
      </Helmet>

      <div className="space-y-6 max-w-7xl mx-auto">
        {/* Header */}
        <motion.div className="flex items-center justify-between" {...fadeIn}>
          <div>
            <h1 className="text-2xl font-bold">Audit Log</h1>
            <p className="text-muted-foreground">Track all user activity and system events</p>
          </div>
          <button
            onClick={() => exportMutation.mutate({})}
            disabled={exportMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 hover:bg-white/5 transition-colors text-sm"
          >
            <ArrowDownTrayIcon className="h-4 w-4" />
            {exportMutation.isPending ? 'Exporting...' : 'Export CSV'}
          </button>
        </motion.div>

        {/* Metric Cards */}
        <motion.div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
          {...fadeIn}
          transition={{ delay: 0.1 }}
        >
          {metricCards.map((card) => (
            <div
              key={card.label}
              className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-4"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-white/5">
                  <card.icon className={cn('h-5 w-5', card.color)} />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{card.label}</p>
                  <p className="text-xl font-bold">{card.value}</p>
                </div>
              </div>
            </div>
          ))}
        </motion.div>

        {/* Activity by Day Chart */}
        {stats?.dailyVolume && stats.dailyVolume.length > 0 && (
          <motion.div
            className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-6"
            {...fadeIn}
            transition={{ delay: 0.15 }}
          >
            <h3 className="font-semibold mb-4">Activity by Day</h3>
            <ActivityVolumeChart data={stats.dailyVolume} height={180} />
          </motion.div>
        )}

        {/* Search + Filter */}
        <motion.div
          className="flex items-center gap-3"
          {...fadeIn}
          transition={{ delay: 0.2 }}
        >
          <div className="relative flex-1">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by user, resource, or details..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="w-full pl-9 pr-4 py-2 rounded-lg border border-white/10 bg-white/5 focus:outline-none focus:ring-2 focus:ring-primary/20 text-sm"
            />
          </div>
          <select
            value={actionFilter}
            onChange={(e) => { setActionFilter(e.target.value as AuditAction | ''); setPage(1); }}
            className="px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="">All Actions</option>
            {Object.keys(actionConfig).map((action) => (
              <option key={action} value={action} className="capitalize">
                {action}
              </option>
            ))}
          </select>
        </motion.div>

        {/* Audit Log Table */}
        <motion.div
          className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm overflow-hidden"
          {...fadeIn}
          transition={{ delay: 0.25 }}
        >
          {logsLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/10 bg-white/5">
                    {['Timestamp', 'User', 'Action', 'Resource', 'Details', 'Status', 'IP'].map(
                      (h) => (
                        <th
                          key={h}
                          className="text-left py-3 px-4 text-xs font-medium text-muted-foreground uppercase tracking-wider"
                        >
                          {h}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody>
                  {(logs?.entries || []).length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-muted-foreground text-sm">
                        No audit log entries found
                      </td>
                    </tr>
                  ) : (
                    (logs?.entries || []).map((entry) => {
                      const ac = actionConfig[entry.action] || actionConfig.update;
                      return (
                        <tr
                          key={entry.id}
                          className="border-b border-white/5 hover:bg-white/5 transition-colors"
                        >
                          <td className="py-3 px-4 text-xs text-muted-foreground whitespace-nowrap">
                            {formatTimestamp(entry.timestamp)}
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center">
                                <span className="text-[10px] font-medium text-primary">
                                  {entry.userName
                                    .split(' ')
                                    .map((n) => n[0])
                                    .join('')
                                    .toUpperCase()}
                                </span>
                              </div>
                              <span className="text-sm">{entry.userName}</span>
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={cn(
                                'px-2 py-0.5 rounded-full text-xs font-medium capitalize',
                                ac.bg,
                                ac.color
                              )}
                            >
                              {entry.action}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-sm max-w-[200px] truncate">
                            {entry.resource}
                          </td>
                          <td className="py-3 px-4 text-sm text-muted-foreground max-w-[250px] truncate">
                            {entry.details}
                          </td>
                          <td className="py-3 px-4">
                            {entry.status === 'success' ? (
                              <CheckCircleIcon className="h-4 w-4 text-green-500" />
                            ) : (
                              <XCircleIcon className="h-4 w-4 text-red-500" />
                            )}
                          </td>
                          <td className="py-3 px-4 text-xs text-muted-foreground font-mono">
                            {entry.ipAddress}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {logs && logs.total > limit && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-white/10">
              <span className="text-xs text-muted-foreground">
                Showing {(page - 1) * limit + 1}-{Math.min(page * limit, logs.total)} of{' '}
                {logs.total}
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-1.5 rounded-lg hover:bg-white/5 disabled:opacity-30 transition-colors"
                >
                  <ChevronLeftIcon className="h-4 w-4" />
                </button>
                <span className="text-sm px-3">
                  {page} / {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-1.5 rounded-lg hover:bg-white/5 disabled:opacity-30 transition-colors"
                >
                  <ChevronRightIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </>
  );
}
