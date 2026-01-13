/**
 * Stratum AI - Reporting Page
 *
 * Automated report generation, scheduling, and delivery management.
 */

import { useState } from 'react'
import {
  useReportTemplates,
  useReportSchedules,
  useReportExecutions,
  useDeliveryChannelConfigs,
  useGenerateReport,
  usePauseReportSchedule,
  useResumeReportSchedule,
} from '@/api/hooks'
import {
  DocumentTextIcon,
  PlayIcon,
  PauseIcon,
  PlusIcon,
  EnvelopeIcon,
  ChatBubbleLeftIcon,
  ArrowDownTrayIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

type TabType = 'templates' | 'schedules' | 'history' | 'delivery'

export default function Reporting() {
  const [activeTab, setActiveTab] = useState<TabType>('templates')

  const { data: templates } = useReportTemplates()
  const { data: schedules } = useReportSchedules()
  const { data: executions } = useReportExecutions({ limit: 20 })
  const { data: deliveryConfigs } = useDeliveryChannelConfigs()
  const generateReport = useGenerateReport()
  const pauseSchedule = usePauseReportSchedule()
  const resumeSchedule = useResumeReportSchedule()

  const tabs = [
    { id: 'templates' as TabType, label: 'Templates' },
    { id: 'schedules' as TabType, label: 'Schedules' },
    { id: 'history' as TabType, label: 'History' },
    { id: 'delivery' as TabType, label: 'Delivery Settings' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Automated Reporting</h1>
          <p className="text-muted-foreground">
            Create, schedule, and deliver automated performance reports
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90">
          <PlusIcon className="h-4 w-4" />
          New Template
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

      {/* Templates Tab */}
      {activeTab === 'templates' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates?.map((template) => (
            <div key={template.id} className="rounded-xl border bg-card p-6 shadow-card">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <DocumentTextIcon className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium">{template.name}</h3>
                    <p className="text-sm text-muted-foreground capitalize">
                      {template.reportType.replace('_', ' ')}
                    </p>
                  </div>
                </div>
              </div>

              {template.description && (
                <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                  {template.description}
                </p>
              )}

              <div className="flex flex-wrap gap-2 mb-4">
                {(template.config?.sections ?? []).map((section: string, idx: number) => (
                  <span
                    key={idx}
                    className="px-2 py-1 rounded-full text-xs bg-muted"
                  >
                    {section}
                  </span>
                ))}
              </div>

              <div className="flex items-center justify-between pt-4 border-t">
                <span className="text-xs text-muted-foreground">
                  Format: {template.defaultFormat.toUpperCase()}
                </span>
                <button
                  onClick={() => generateReport.mutate({
                    templateId: template.id,
                    startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                    endDate: new Date().toISOString().split('T')[0],
                  })}
                  disabled={generateReport.isPending}
                  className="flex items-center gap-1 text-sm text-primary hover:underline"
                >
                  <PlayIcon className="h-4 w-4" />
                  Generate
                </button>
              </div>
            </div>
          ))}

          {/* Add Template Card */}
          <button className="rounded-xl border-2 border-dashed bg-card p-6 flex flex-col items-center justify-center gap-3 text-muted-foreground hover:text-foreground hover:border-primary transition-colors">
            <PlusIcon className="h-8 w-8" />
            <span className="font-medium">Create Template</span>
          </button>
        </div>
      )}

      {/* Schedules Tab */}
      {activeTab === 'schedules' && (
        <div className="rounded-xl border bg-card shadow-card overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium">Schedule</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Template</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Frequency</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Next Run</th>
                <th className="px-4 py-3 text-center text-sm font-medium">Status</th>
                <th className="px-4 py-3 text-center text-sm font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {schedules?.map((schedule) => (
                <tr key={schedule.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <p className="font-medium">{schedule.name}</p>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {templates?.find((t) => t.id === schedule.templateId)?.name || 'Unknown'}
                  </td>
                  <td className="px-4 py-3 text-sm capitalize">
                    {schedule.frequency}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="flex items-center gap-1">
                      <ClockIcon className="h-4 w-4 text-muted-foreground" />
                      {schedule.nextRunAt
                        ? new Date(schedule.nextRunAt).toLocaleString()
                        : '-'}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {schedule.isActive ? (
                      <span className="px-2 py-1 rounded-full text-xs bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300">
                        Active
                      </span>
                    ) : (
                      <span className="px-2 py-1 rounded-full text-xs bg-gray-100 dark:bg-gray-900/20 text-gray-700 dark:text-gray-300">
                        Paused
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-2">
                      {schedule.isActive ? (
                        <button
                          onClick={() => pauseSchedule.mutate(schedule.id)}
                          className="p-1 rounded hover:bg-muted"
                          title="Pause"
                        >
                          <PauseIcon className="h-4 w-4" />
                        </button>
                      ) : (
                        <button
                          onClick={() => resumeSchedule.mutate(schedule.id)}
                          className="p-1 rounded hover:bg-muted"
                          title="Resume"
                        >
                          <PlayIcon className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        onClick={() => generateReport.mutate({
                          templateId: schedule.templateId,
                          startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                          endDate: new Date().toISOString().split('T')[0],
                        })}
                        className="p-1 rounded hover:bg-muted"
                        title="Run Now"
                      >
                        <ArrowDownTrayIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="rounded-xl border bg-card shadow-card overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium">Report</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Generated</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Period</th>
                <th className="px-4 py-3 text-center text-sm font-medium">Status</th>
                <th className="px-4 py-3 text-center text-sm font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {executions?.map((execution) => (
                <tr key={execution.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <p className="font-medium">
                      {templates?.find((t) => t.id === execution.templateId)?.name || 'Unknown'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {execution.executionType === 'scheduled' ? 'Scheduled' : 'Manual'}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {new Date(execution.startedAt).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {new Date(execution.dateRangeStart).toLocaleDateString()} -{' '}
                    {new Date(execution.dateRangeEnd).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {execution.status === 'completed' ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300">
                        <CheckCircleIcon className="h-3 w-3" />
                        Completed
                      </span>
                    ) : execution.status === 'failed' ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300">
                        <XCircleIcon className="h-3 w-3" />
                        Failed
                      </span>
                    ) : (
                      <span className="px-2 py-1 rounded-full text-xs bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300">
                        {execution.status}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {execution.filePath && (
                      <a
                        href={execution.filePath}
                        className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <ArrowDownTrayIcon className="h-4 w-4" />
                        Download
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Delivery Settings Tab */}
      {activeTab === 'delivery' && (
        <div className="space-y-6">
          {/* Email Configuration */}
          <div className="rounded-xl border bg-card p-6 shadow-card">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/20">
                  <EnvelopeIcon className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-medium">Email Delivery</h3>
                  <p className="text-sm text-muted-foreground">
                    Send reports directly to email addresses
                  </p>
                </div>
              </div>
              <span
                className={cn(
                  'px-2 py-1 rounded-full text-xs',
                  deliveryConfigs?.find((c) => c.channel === 'email')?.isActive
                    ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300'
                    : 'bg-gray-100 dark:bg-gray-900/20 text-gray-700 dark:text-gray-300'
                )}
              >
                {deliveryConfigs?.find((c) => c.channel === 'email')?.isActive ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <div className="p-4 rounded-lg bg-muted/50 text-sm">
              <p className="text-muted-foreground">
                Default recipients and SMTP settings can be configured here.
              </p>
            </div>
          </div>

          {/* Slack Configuration */}
          <div className="rounded-xl border bg-card p-6 shadow-card">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/20">
                  <ChatBubbleLeftIcon className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <h3 className="font-medium">Slack Delivery</h3>
                  <p className="text-sm text-muted-foreground">
                    Post reports to Slack channels
                  </p>
                </div>
              </div>
              <span
                className={cn(
                  'px-2 py-1 rounded-full text-xs',
                  deliveryConfigs?.find((c) => c.channel === 'slack')?.isActive
                    ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300'
                    : 'bg-gray-100 dark:bg-gray-900/20 text-gray-700 dark:text-gray-300'
                )}
              >
                {deliveryConfigs?.find((c) => c.channel === 'slack')?.isActive ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <div className="p-4 rounded-lg bg-muted/50 text-sm">
              <p className="text-muted-foreground">
                Configure Slack webhook URL and default channels.
              </p>
            </div>
          </div>

          {/* WhatsApp Configuration */}
          <div className="rounded-xl border bg-card p-6 shadow-card">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-900/20">
                  <ChatBubbleLeftIcon className="h-5 w-5 text-emerald-600" />
                </div>
                <div>
                  <h3 className="font-medium">WhatsApp Delivery</h3>
                  <p className="text-sm text-muted-foreground">
                    Send report summaries via WhatsApp
                  </p>
                </div>
              </div>
              <span
                className={cn(
                  'px-2 py-1 rounded-full text-xs',
                  deliveryConfigs?.find((c) => (c.channel as string) === 'whatsapp')?.isActive
                    ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300'
                    : 'bg-gray-100 dark:bg-gray-900/20 text-gray-700 dark:text-gray-300'
                )}
              >
                {deliveryConfigs?.find((c) => (c.channel as string) === 'whatsapp')?.isActive ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <div className="p-4 rounded-lg bg-muted/50 text-sm">
              <p className="text-muted-foreground">
                Configure WhatsApp Business API for report delivery.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
