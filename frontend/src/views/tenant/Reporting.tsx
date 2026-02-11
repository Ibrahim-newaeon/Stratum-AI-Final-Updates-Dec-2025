/**
 * Stratum AI - Automated Reporting
 *
 * Full-featured report management: templates, scheduling, generation, and delivery.
 */

import { useState } from 'react';
import {
  useDeliveryChannelConfigs,
  useGenerateReport,
  usePauseReportSchedule,
  useReportExecutions,
  useReportSchedules,
  useReportTemplates,
  useResumeReportSchedule,
  useCreateReportTemplate,
  useUpdateReportTemplate,
  useDeleteReportTemplate,
  useCreateReportSchedule,
  useDeleteReportSchedule,
} from '@/api/hooks';
import {
  useRunScheduleNow,
  useCreateDeliveryChannelConfig,
  useDeleteDeliveryChannelConfig,
  useVerifyDeliveryChannel,
  type ReportType,
  type ReportFormat,
  type ScheduleFrequency,
  type DeliveryChannel,
  type ReportTemplate,
  type ScheduledReport,
} from '@/api/reporting';
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  CalendarDaysIcon,
  ChatBubbleLeftIcon,
  CheckCircleIcon,
  ClockIcon,
  Cog6ToothIcon,
  DocumentChartBarIcon,
  DocumentTextIcon,
  EnvelopeIcon,
  GlobeAltIcon,
  PauseIcon,
  PencilSquareIcon,
  PlayIcon,
  PlusIcon,
  TrashIcon,
  XCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import { useToast } from '@/components/ui/use-toast';

type TabType = 'templates' | 'schedules' | 'history' | 'delivery';

const REPORT_TYPES: { value: ReportType; label: string }[] = [
  { value: 'campaign_performance', label: 'Campaign Performance' },
  { value: 'attribution_summary', label: 'Attribution Summary' },
  { value: 'pacing_status', label: 'Pacing Status' },
  { value: 'profit_roas', label: 'Profit & ROAS' },
  { value: 'pipeline_metrics', label: 'Pipeline Metrics' },
  { value: 'executive_summary', label: 'Executive Summary' },
  { value: 'custom', label: 'Custom Report' },
];

const REPORT_FORMATS: { value: ReportFormat; label: string }[] = [
  { value: 'pdf', label: 'PDF' },
  { value: 'csv', label: 'CSV' },
  { value: 'excel', label: 'Excel' },
  { value: 'json', label: 'JSON' },
  { value: 'html', label: 'HTML' },
];

const FREQUENCIES: { value: ScheduleFrequency; label: string }[] = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'biweekly', label: 'Bi-weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
];

const DAYS_OF_WEEK = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

const DELIVERY_CHANNELS: { value: DeliveryChannel; label: string; icon: typeof EnvelopeIcon; color: string }[] = [
  { value: 'email', label: 'Email', icon: EnvelopeIcon, color: 'blue' },
  { value: 'slack', label: 'Slack', icon: ChatBubbleLeftIcon, color: 'purple' },
  { value: 'teams', label: 'Microsoft Teams', icon: ChatBubbleLeftIcon, color: 'indigo' },
  { value: 'webhook', label: 'Webhook', icon: GlobeAltIcon, color: 'orange' },
];

export default function Reporting() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<TabType>('templates');

  // Template editor state
  const [showTemplateEditor, setShowTemplateEditor] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ReportTemplate | null>(null);
  const [templateForm, setTemplateForm] = useState({
    name: '',
    description: '',
    reportType: 'campaign_performance' as ReportType,
    defaultFormat: 'pdf' as ReportFormat,
    sections: '' as string, // comma-separated
  });

  // Schedule editor state
  const [showScheduleEditor, setShowScheduleEditor] = useState(false);
  const [scheduleForm, setScheduleForm] = useState({
    name: '',
    templateId: '',
    frequency: 'weekly' as ScheduleFrequency,
    dayOfWeek: 1,
    dayOfMonth: 1,
    hour: 8,
    minute: 0,
    timezone: 'UTC',
    deliveryChannels: [] as DeliveryChannel[],
    emailRecipients: '',
    slackChannel: '',
  });

  // Generate report modal state
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [generateTemplateId, setGenerateTemplateId] = useState('');
  const [generateForm, setGenerateForm] = useState({
    startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],
    format: 'pdf' as ReportFormat,
  });

  // Delivery channel editor state
  const [showDeliveryEditor, setShowDeliveryEditor] = useState(false);
  const [deliveryForm, setDeliveryForm] = useState({
    channel: 'email' as DeliveryChannel,
    name: '',
    config: {} as Record<string, string>,
  });

  // Delete confirmation state
  const [deleteConfirm, setDeleteConfirm] = useState<{ type: 'template' | 'schedule'; id: string } | null>(null);

  // Data hooks
  const { data: templates, isLoading: templatesLoading } = useReportTemplates();
  const { data: schedules, isLoading: schedulesLoading } = useReportSchedules();
  const { data: executions, isLoading: executionsLoading } = useReportExecutions({ limit: 20 });
  const { data: deliveryConfigs, isLoading: deliveryLoading } = useDeliveryChannelConfigs();

  // Mutation hooks
  const generateReport = useGenerateReport();
  const pauseSchedule = usePauseReportSchedule();
  const resumeSchedule = useResumeReportSchedule();
  const createTemplate = useCreateReportTemplate();
  const updateTemplate = useUpdateReportTemplate();
  const deleteTemplate = useDeleteReportTemplate();
  const createSchedule = useCreateReportSchedule();
  const deleteSchedule = useDeleteReportSchedule();
  const runScheduleNow = useRunScheduleNow();
  const createDeliveryChannel = useCreateDeliveryChannelConfig();
  const deleteDeliveryChannel = useDeleteDeliveryChannelConfig();
  const verifyChannel = useVerifyDeliveryChannel();

  const tabs = [
    { id: 'templates' as TabType, label: 'Templates', count: templates?.length },
    { id: 'schedules' as TabType, label: 'Schedules', count: schedules?.length },
    { id: 'history' as TabType, label: 'History', count: executions?.length },
    { id: 'delivery' as TabType, label: 'Delivery Settings', count: deliveryConfigs?.length },
  ];

  // --- Template handlers ---
  const openTemplateEditor = (template?: ReportTemplate) => {
    if (template) {
      setEditingTemplate(template);
      setTemplateForm({
        name: template.name,
        description: template.description || '',
        reportType: template.reportType,
        defaultFormat: template.defaultFormat,
        sections: (template.config?.sections || []).join(', '),
      });
    } else {
      setEditingTemplate(null);
      setTemplateForm({
        name: '',
        description: '',
        reportType: 'campaign_performance',
        defaultFormat: 'pdf',
        sections: '',
      });
    }
    setShowTemplateEditor(true);
  };

  const handleSaveTemplate = async () => {
    const data = {
      name: templateForm.name,
      description: templateForm.description || undefined,
      reportType: templateForm.reportType,
      defaultFormat: templateForm.defaultFormat,
      config: {
        sections: templateForm.sections
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
      },
    };

    try {
      if (editingTemplate) {
        await updateTemplate.mutateAsync({ templateId: editingTemplate.id, data });
        toast({ title: 'Template Updated', description: `"${data.name}" has been updated.` });
      } else {
        await createTemplate.mutateAsync(data);
        toast({ title: 'Template Created', description: `"${data.name}" is ready to use.` });
      }
      setShowTemplateEditor(false);
    } catch {
      toast({ title: 'Error', description: 'Failed to save template.', variant: 'destructive' });
    }
  };

  // --- Schedule handlers ---
  const openScheduleEditor = () => {
    setScheduleForm({
      name: '',
      templateId: templates?.[0]?.id || '',
      frequency: 'weekly',
      dayOfWeek: 1,
      dayOfMonth: 1,
      hour: 8,
      minute: 0,
      timezone: 'UTC',
      deliveryChannels: [],
      emailRecipients: '',
      slackChannel: '',
    });
    setShowScheduleEditor(true);
  };

  const handleSaveSchedule = async () => {
    const deliveryConfig: Record<string, unknown> = {};
    if (scheduleForm.deliveryChannels.includes('email') && scheduleForm.emailRecipients) {
      deliveryConfig.email = {
        recipients: scheduleForm.emailRecipients.split(',').map((e) => e.trim()).filter(Boolean),
      };
    }
    if (scheduleForm.deliveryChannels.includes('slack') && scheduleForm.slackChannel) {
      deliveryConfig.slack = { channel: scheduleForm.slackChannel };
    }

    try {
      await createSchedule.mutateAsync({
        name: scheduleForm.name,
        templateId: scheduleForm.templateId,
        frequency: scheduleForm.frequency,
        dayOfWeek: scheduleForm.frequency === 'weekly' ? scheduleForm.dayOfWeek : undefined,
        dayOfMonth: scheduleForm.frequency === 'monthly' ? scheduleForm.dayOfMonth : undefined,
        hour: scheduleForm.hour,
        minute: scheduleForm.minute,
        timezone: scheduleForm.timezone,
        deliveryChannels: scheduleForm.deliveryChannels,
        deliveryConfig,
      });
      toast({ title: 'Schedule Created', description: `"${scheduleForm.name}" has been scheduled.` });
      setShowScheduleEditor(false);
    } catch {
      toast({ title: 'Error', description: 'Failed to create schedule.', variant: 'destructive' });
    }
  };

  // --- Generate report handler ---
  const openGenerateModal = (templateId: string) => {
    setGenerateTemplateId(templateId);
    setGenerateForm({
      startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      endDate: new Date().toISOString().split('T')[0],
      format: 'pdf',
    });
    setShowGenerateModal(true);
  };

  const handleGenerate = async () => {
    try {
      await generateReport.mutateAsync({
        templateId: generateTemplateId,
        startDate: generateForm.startDate,
        endDate: generateForm.endDate,
        format: generateForm.format,
      });
      toast({ title: 'Report Generated', description: 'Your report is being processed.' });
      setShowGenerateModal(false);
      setActiveTab('history');
    } catch {
      toast({ title: 'Error', description: 'Failed to generate report.', variant: 'destructive' });
    }
  };

  // --- Delivery channel handler ---
  const handleSaveDeliveryChannel = async () => {
    try {
      await createDeliveryChannel.mutateAsync({
        channel: deliveryForm.channel,
        name: deliveryForm.name,
        config: deliveryForm.config,
      });
      toast({ title: 'Channel Added', description: `${deliveryForm.name} delivery configured.` });
      setShowDeliveryEditor(false);
    } catch {
      toast({ title: 'Error', description: 'Failed to add delivery channel.', variant: 'destructive' });
    }
  };

  // --- Delete handler ---
  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      if (deleteConfirm.type === 'template') {
        await deleteTemplate.mutateAsync(deleteConfirm.id);
        toast({ title: 'Deleted', description: 'Template has been removed.' });
      } else {
        await deleteSchedule.mutateAsync(deleteConfirm.id);
        toast({ title: 'Deleted', description: 'Schedule has been removed.' });
      }
      setDeleteConfirm(null);
    } catch {
      toast({ title: 'Error', description: 'Failed to delete.', variant: 'destructive' });
    }
  };

  // --- Run schedule now handler ---
  const handleRunNow = async (schedule: ScheduledReport) => {
    try {
      await runScheduleNow.mutateAsync(schedule.id);
      toast({ title: 'Running', description: `"${schedule.name}" is generating now.` });
    } catch {
      toast({ title: 'Error', description: 'Failed to trigger report.', variant: 'destructive' });
    }
  };

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
        <div className="flex items-center gap-3">
          {activeTab === 'schedules' && (
            <button
              onClick={openScheduleEditor}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-primary/30 text-primary hover:bg-primary/10 transition-colors"
            >
              <CalendarDaysIcon className="h-4 w-4" />
              New Schedule
            </button>
          )}
          {activeTab === 'delivery' && (
            <button
              onClick={() => {
                setDeliveryForm({ channel: 'email', name: '', config: {} });
                setShowDeliveryEditor(true);
              }}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-primary/30 text-primary hover:bg-primary/10 transition-colors"
            >
              <PlusIcon className="h-4 w-4" />
              Add Channel
            </button>
          )}
          <button
            onClick={() => openTemplateEditor()}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <PlusIcon className="h-4 w-4" />
            New Template
          </button>
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
                'px-4 py-2 border-b-2 font-medium text-sm transition-colors flex items-center gap-2',
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <span className="px-1.5 py-0.5 rounded-full text-xs bg-muted">{tab.count}</span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* ========== Templates Tab ========== */}
      {activeTab === 'templates' && (
        <>
          {templatesLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
            </div>
          ) : !templates || templates.length === 0 ? (
            <div className="rounded-xl border bg-card p-12 text-center">
              <DocumentChartBarIcon className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
              <p className="text-muted-foreground mb-2">No report templates yet</p>
              <p className="text-sm text-muted-foreground/70 mb-6">
                Templates define what data to include in your reports.
              </p>
              <button
                onClick={() => openTemplateEditor()}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
              >
                <PlusIcon className="h-4 w-4" />
                Create your first template
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {templates.map((template) => (
                <div key={template.id} className="rounded-xl border bg-card p-6 shadow-card group">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-primary/10">
                        <DocumentTextIcon className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <h3 className="font-medium">{template.name}</h3>
                        <p className="text-sm text-muted-foreground capitalize">
                          {template.reportType.replace(/_/g, ' ')}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => openTemplateEditor(template)}
                        className="p-1 rounded hover:bg-muted"
                        title="Edit"
                      >
                        <PencilSquareIcon className="h-4 w-4 text-muted-foreground" />
                      </button>
                      <button
                        onClick={() => setDeleteConfirm({ type: 'template', id: template.id })}
                        className="p-1 rounded hover:bg-muted"
                        title="Delete"
                      >
                        <TrashIcon className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                      </button>
                    </div>
                  </div>

                  {template.description && (
                    <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                      {template.description}
                    </p>
                  )}

                  <div className="flex flex-wrap gap-2 mb-4">
                    {(template.config?.sections ?? []).map((section: string, idx: number) => (
                      <span key={idx} className="px-2 py-1 rounded-full text-xs bg-muted">
                        {section}
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center justify-between pt-4 border-t">
                    <span className="text-xs text-muted-foreground">
                      Format: {template.defaultFormat.toUpperCase()}
                    </span>
                    <button
                      onClick={() => openGenerateModal(template.id)}
                      className="flex items-center gap-1 text-sm text-primary hover:underline"
                    >
                      <PlayIcon className="h-4 w-4" />
                      Generate
                    </button>
                  </div>
                </div>
              ))}

              {/* Add Template Card */}
              <button
                onClick={() => openTemplateEditor()}
                className="rounded-xl border-2 border-dashed bg-card p-6 flex flex-col items-center justify-center gap-3 text-muted-foreground hover:text-foreground hover:border-primary transition-colors min-h-[200px]"
              >
                <PlusIcon className="h-8 w-8" />
                <span className="font-medium">Create Template</span>
              </button>
            </div>
          )}
        </>
      )}

      {/* ========== Schedules Tab ========== */}
      {activeTab === 'schedules' && (
        <>
          {schedulesLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
            </div>
          ) : !schedules || schedules.length === 0 ? (
            <div className="rounded-xl border bg-card p-12 text-center">
              <CalendarDaysIcon className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
              <p className="text-muted-foreground mb-2">No scheduled reports</p>
              <p className="text-sm text-muted-foreground/70 mb-6">
                Automate report delivery on a recurring schedule.
              </p>
              <button
                onClick={openScheduleEditor}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
              >
                <PlusIcon className="h-4 w-4" />
                Schedule your first report
              </button>
            </div>
          ) : (
            <div className="rounded-xl border bg-card shadow-card overflow-hidden">
              <table className="w-full">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium">Schedule</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Template</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Frequency</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Next Run</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Last Run</th>
                    <th className="px-4 py-3 text-center text-sm font-medium">Status</th>
                    <th className="px-4 py-3 text-center text-sm font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {schedules.map((schedule) => (
                    <tr key={schedule.id} className="hover:bg-muted/30 group">
                      <td className="px-4 py-3">
                        <p className="font-medium">{schedule.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {schedule.runCount} runs &middot; {schedule.failureCount} failures
                        </p>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {templates?.find((t) => t.id === schedule.templateId)?.name || 'Unknown'}
                      </td>
                      <td className="px-4 py-3 text-sm capitalize">{schedule.frequency}</td>
                      <td className="px-4 py-3 text-sm">
                        <div className="flex items-center gap-1">
                          <ClockIcon className="h-4 w-4 text-muted-foreground" />
                          {schedule.nextRunAt
                            ? new Date(schedule.nextRunAt).toLocaleString()
                            : '-'}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {schedule.lastRunAt ? (
                          <div className="flex items-center gap-1">
                            {schedule.lastRunStatus === 'completed' ? (
                              <CheckCircleIcon className="h-4 w-4 text-emerald-500" />
                            ) : schedule.lastRunStatus === 'failed' ? (
                              <XCircleIcon className="h-4 w-4 text-destructive" />
                            ) : (
                              <ClockIcon className="h-4 w-4 text-muted-foreground" />
                            )}
                            {new Date(schedule.lastRunAt).toLocaleDateString()}
                          </div>
                        ) : (
                          <span className="text-muted-foreground">Never</span>
                        )}
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
                        <div className="flex items-center justify-center gap-1">
                          {schedule.isActive ? (
                            <button
                              onClick={() => pauseSchedule.mutate(schedule.id)}
                              className="p-1.5 rounded hover:bg-muted"
                              title="Pause"
                            >
                              <PauseIcon className="h-4 w-4" />
                            </button>
                          ) : (
                            <button
                              onClick={() => resumeSchedule.mutate(schedule.id)}
                              className="p-1.5 rounded hover:bg-muted"
                              title="Resume"
                            >
                              <PlayIcon className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            onClick={() => handleRunNow(schedule)}
                            className="p-1.5 rounded hover:bg-muted"
                            title="Run Now"
                          >
                            <ArrowPathIcon className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() =>
                              setDeleteConfirm({ type: 'schedule', id: schedule.id })
                            }
                            className="p-1.5 rounded hover:bg-muted opacity-0 group-hover:opacity-100 transition-opacity"
                            title="Delete"
                          >
                            <TrashIcon className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* ========== History Tab ========== */}
      {activeTab === 'history' && (
        <>
          {executionsLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
            </div>
          ) : !executions || executions.length === 0 ? (
            <div className="rounded-xl border bg-card p-12 text-center">
              <DocumentChartBarIcon className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
              <p className="text-muted-foreground mb-2">No reports generated yet</p>
              <p className="text-sm text-muted-foreground/70">
                Generate a report from a template to see it here.
              </p>
            </div>
          ) : (
            <div className="rounded-xl border bg-card shadow-card overflow-hidden">
              <table className="w-full">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium">Report</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Generated</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Period</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Format</th>
                    <th className="px-4 py-3 text-center text-sm font-medium">Status</th>
                    <th className="px-4 py-3 text-center text-sm font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {executions.map((execution) => (
                    <tr key={execution.id} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium">
                          {templates?.find((t) => t.id === execution.templateId)?.name ||
                            execution.reportType.replace(/_/g, ' ')}
                        </p>
                        <p className="text-xs text-muted-foreground capitalize">
                          {execution.executionType}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {new Date(execution.startedAt).toLocaleString()}
                        {execution.durationSeconds && (
                          <p className="text-xs text-muted-foreground">
                            {execution.durationSeconds}s
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {new Date(execution.dateRangeStart).toLocaleDateString()} &ndash;{' '}
                        {new Date(execution.dateRangeEnd).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 text-sm uppercase">{execution.format}</td>
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
                        ) : execution.status === 'running' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300">
                            <ArrowPathIcon className="h-3 w-3 animate-spin" />
                            Running
                          </span>
                        ) : (
                          <span className="px-2 py-1 rounded-full text-xs bg-muted capitalize">
                            {execution.status}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {execution.fileUrl || execution.filePath ? (
                          <a
                            href={execution.fileUrl || execution.filePath}
                            className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <ArrowDownTrayIcon className="h-4 w-4" />
                            Download
                          </a>
                        ) : execution.status === 'failed' && execution.errorMessage ? (
                          <span className="text-xs text-destructive" title={execution.errorMessage}>
                            {execution.errorMessage.substring(0, 30)}...
                          </span>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* ========== Delivery Settings Tab ========== */}
      {activeTab === 'delivery' && (
        <>
          {deliveryLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
            </div>
          ) : (
            <div className="space-y-4">
              {/* Configured channels */}
              {deliveryConfigs && deliveryConfigs.length > 0 ? (
                deliveryConfigs.map((config) => {
                  const channelInfo = DELIVERY_CHANNELS.find((c) => c.value === config.channel);
                  const Icon = channelInfo?.icon || GlobeAltIcon;
                  return (
                    <div key={config.id} className="rounded-xl border bg-card p-6 shadow-card">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg bg-${channelInfo?.color || 'gray'}-100 dark:bg-${channelInfo?.color || 'gray'}-900/20`}>
                            <Icon className={`h-5 w-5 text-${channelInfo?.color || 'gray'}-600`} />
                          </div>
                          <div>
                            <h3 className="font-medium">{config.name}</h3>
                            <p className="text-sm text-muted-foreground capitalize">
                              {config.channel} delivery
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {config.isVerified && (
                            <span className="inline-flex items-center gap-1 text-xs text-emerald-600">
                              <CheckCircleIcon className="h-3 w-3" />
                              Verified
                            </span>
                          )}
                          <span
                            className={cn(
                              'px-2 py-1 rounded-full text-xs',
                              config.isActive
                                ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300'
                                : 'bg-gray-100 dark:bg-gray-900/20 text-gray-700 dark:text-gray-300'
                            )}
                          >
                            {config.isActive ? 'Enabled' : 'Disabled'}
                          </span>
                          <button
                            onClick={() => verifyChannel.mutate(config.id)}
                            disabled={verifyChannel.isPending}
                            className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
                            title="Verify channel"
                          >
                            <CheckCircleIcon className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => deleteDeliveryChannel.mutate(config.id)}
                            className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-destructive"
                            title="Remove channel"
                          >
                            <TrashIcon className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="rounded-xl border bg-card p-12 text-center">
                  <Cog6ToothIcon className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
                  <p className="text-muted-foreground mb-2">No delivery channels configured</p>
                  <p className="text-sm text-muted-foreground/70 mb-6">
                    Add a channel to enable automated report delivery.
                  </p>
                  <button
                    onClick={() => {
                      setDeliveryForm({ channel: 'email', name: '', config: {} });
                      setShowDeliveryEditor(true);
                    }}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                  >
                    <PlusIcon className="h-4 w-4" />
                    Add delivery channel
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* ========== Template Editor Modal ========== */}
      {showTemplateEditor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-card border rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-card z-10">
              <h3 className="text-lg font-semibold">
                {editingTemplate ? 'Edit Template' : 'New Report Template'}
              </h3>
              <button onClick={() => setShowTemplateEditor(false)} className="p-2 text-muted-foreground hover:text-foreground">
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">Name *</label>
                <input
                  type="text"
                  value={templateForm.name}
                  onChange={(e) => setTemplateForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="e.g. Weekly Performance Report"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1.5">Description</label>
                <textarea
                  value={templateForm.description}
                  onChange={(e) => setTemplateForm((f) => ({ ...f, description: e.target.value }))}
                  rows={2}
                  className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                  placeholder="What does this report cover?"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1.5">Report Type</label>
                  <select
                    value={templateForm.reportType}
                    onChange={(e) => setTemplateForm((f) => ({ ...f, reportType: e.target.value as ReportType }))}
                    className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  >
                    {REPORT_TYPES.map((rt) => (
                      <option key={rt.value} value={rt.value}>{rt.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1.5">Default Format</label>
                  <select
                    value={templateForm.defaultFormat}
                    onChange={(e) => setTemplateForm((f) => ({ ...f, defaultFormat: e.target.value as ReportFormat }))}
                    className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  >
                    {REPORT_FORMATS.map((rf) => (
                      <option key={rf.value} value={rf.value}>{rf.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1.5">Sections</label>
                <input
                  type="text"
                  value={templateForm.sections}
                  onChange={(e) => setTemplateForm((f) => ({ ...f, sections: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="overview, metrics, charts, recommendations (comma-separated)"
                />
                <p className="text-xs text-muted-foreground mt-1">Comma-separated section names</p>
              </div>
            </div>

            <div className="flex justify-end gap-3 p-4 border-t sticky bottom-0 bg-card">
              <button onClick={() => setShowTemplateEditor(false)} className="px-4 py-2 text-muted-foreground hover:text-foreground">
                Cancel
              </button>
              <button
                onClick={handleSaveTemplate}
                disabled={!templateForm.name || createTemplate.isPending || updateTemplate.isPending}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium disabled:opacity-50 hover:bg-primary/90 transition-colors"
              >
                {createTemplate.isPending || updateTemplate.isPending
                  ? 'Saving...'
                  : editingTemplate ? 'Update Template' : 'Create Template'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========== Schedule Editor Modal ========== */}
      {showScheduleEditor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-card border rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-card z-10">
              <h3 className="text-lg font-semibold">New Report Schedule</h3>
              <button onClick={() => setShowScheduleEditor(false)} className="p-2 text-muted-foreground hover:text-foreground">
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">Schedule Name *</label>
                <input
                  type="text"
                  value={scheduleForm.name}
                  onChange={(e) => setScheduleForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="e.g. Weekly Monday Report"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1.5">Template *</label>
                <select
                  value={scheduleForm.templateId}
                  onChange={(e) => setScheduleForm((f) => ({ ...f, templateId: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                >
                  <option value="">Select template...</option>
                  {templates?.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1.5">Frequency</label>
                  <select
                    value={scheduleForm.frequency}
                    onChange={(e) => setScheduleForm((f) => ({ ...f, frequency: e.target.value as ScheduleFrequency }))}
                    className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  >
                    {FREQUENCIES.map((freq) => (
                      <option key={freq.value} value={freq.value}>{freq.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1.5">Timezone</label>
                  <select
                    value={scheduleForm.timezone}
                    onChange={(e) => setScheduleForm((f) => ({ ...f, timezone: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  >
                    <option value="UTC">UTC</option>
                    <option value="America/New_York">Eastern (US)</option>
                    <option value="America/Chicago">Central (US)</option>
                    <option value="America/Los_Angeles">Pacific (US)</option>
                    <option value="Europe/London">London</option>
                    <option value="Asia/Dubai">Dubai</option>
                  </select>
                </div>
              </div>

              {scheduleForm.frequency === 'weekly' && (
                <div>
                  <label className="block text-sm font-medium mb-1.5">Day of Week</label>
                  <select
                    value={scheduleForm.dayOfWeek}
                    onChange={(e) => setScheduleForm((f) => ({ ...f, dayOfWeek: Number(e.target.value) }))}
                    className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  >
                    {DAYS_OF_WEEK.map((day, idx) => (
                      <option key={idx} value={idx}>{day}</option>
                    ))}
                  </select>
                </div>
              )}

              {scheduleForm.frequency === 'monthly' && (
                <div>
                  <label className="block text-sm font-medium mb-1.5">Day of Month</label>
                  <input
                    type="number"
                    min={1}
                    max={28}
                    value={scheduleForm.dayOfMonth}
                    onChange={(e) => setScheduleForm((f) => ({ ...f, dayOfMonth: Number(e.target.value) }))}
                    className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1.5">Hour (0-23)</label>
                  <input
                    type="number"
                    min={0}
                    max={23}
                    value={scheduleForm.hour}
                    onChange={(e) => setScheduleForm((f) => ({ ...f, hour: Number(e.target.value) }))}
                    className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1.5">Minute (0-59)</label>
                  <input
                    type="number"
                    min={0}
                    max={59}
                    value={scheduleForm.minute}
                    onChange={(e) => setScheduleForm((f) => ({ ...f, minute: Number(e.target.value) }))}
                    className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
              </div>

              {/* Delivery Channels */}
              <div className="border-t pt-4">
                <label className="block text-sm font-medium mb-2">Delivery Channels</label>
                <div className="space-y-2">
                  {DELIVERY_CHANNELS.map((ch) => (
                    <label key={ch.value} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={scheduleForm.deliveryChannels.includes(ch.value)}
                        onChange={(e) => {
                          setScheduleForm((f) => ({
                            ...f,
                            deliveryChannels: e.target.checked
                              ? [...f.deliveryChannels, ch.value]
                              : f.deliveryChannels.filter((c) => c !== ch.value),
                          }));
                        }}
                        className="rounded"
                      />
                      <ch.icon className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">{ch.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {scheduleForm.deliveryChannels.includes('email') && (
                <div>
                  <label className="block text-sm font-medium mb-1.5">Email Recipients</label>
                  <input
                    type="text"
                    value={scheduleForm.emailRecipients}
                    onChange={(e) => setScheduleForm((f) => ({ ...f, emailRecipients: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                    placeholder="email1@example.com, email2@example.com"
                  />
                </div>
              )}

              {scheduleForm.deliveryChannels.includes('slack') && (
                <div>
                  <label className="block text-sm font-medium mb-1.5">Slack Channel</label>
                  <input
                    type="text"
                    value={scheduleForm.slackChannel}
                    onChange={(e) => setScheduleForm((f) => ({ ...f, slackChannel: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                    placeholder="#reports"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 p-4 border-t sticky bottom-0 bg-card">
              <button onClick={() => setShowScheduleEditor(false)} className="px-4 py-2 text-muted-foreground hover:text-foreground">
                Cancel
              </button>
              <button
                onClick={handleSaveSchedule}
                disabled={!scheduleForm.name || !scheduleForm.templateId || createSchedule.isPending}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium disabled:opacity-50 hover:bg-primary/90 transition-colors"
              >
                {createSchedule.isPending ? 'Creating...' : 'Create Schedule'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========== Generate Report Modal ========== */}
      {showGenerateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-card border rounded-xl w-full max-w-md">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-semibold">Generate Report</h3>
              <button onClick={() => setShowGenerateModal(false)} className="p-2 text-muted-foreground hover:text-foreground">
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="p-3 rounded-lg bg-muted/50">
                <p className="text-sm font-medium">
                  {templates?.find((t) => t.id === generateTemplateId)?.name || 'Unknown'}
                </p>
                <p className="text-xs text-muted-foreground capitalize">
                  {templates?.find((t) => t.id === generateTemplateId)?.reportType.replace(/_/g, ' ')}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1.5">Start Date</label>
                  <input
                    type="date"
                    value={generateForm.startDate}
                    onChange={(e) => setGenerateForm((f) => ({ ...f, startDate: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1.5">End Date</label>
                  <input
                    type="date"
                    value={generateForm.endDate}
                    onChange={(e) => setGenerateForm((f) => ({ ...f, endDate: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1.5">Format</label>
                <select
                  value={generateForm.format}
                  onChange={(e) => setGenerateForm((f) => ({ ...f, format: e.target.value as ReportFormat }))}
                  className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                >
                  {REPORT_FORMATS.map((rf) => (
                    <option key={rf.value} value={rf.value}>{rf.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-3 p-4 border-t">
              <button onClick={() => setShowGenerateModal(false)} className="px-4 py-2 text-muted-foreground hover:text-foreground">
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={generateReport.isPending}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium disabled:opacity-50 hover:bg-primary/90 transition-colors"
              >
                {generateReport.isPending ? 'Generating...' : 'Generate Report'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========== Delivery Channel Editor Modal ========== */}
      {showDeliveryEditor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-card border rounded-xl w-full max-w-md">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-semibold">Add Delivery Channel</h3>
              <button onClick={() => setShowDeliveryEditor(false)} className="p-2 text-muted-foreground hover:text-foreground">
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">Channel Type</label>
                <select
                  value={deliveryForm.channel}
                  onChange={(e) => setDeliveryForm((f) => ({ ...f, channel: e.target.value as DeliveryChannel, config: {} }))}
                  className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                >
                  {DELIVERY_CHANNELS.map((ch) => (
                    <option key={ch.value} value={ch.value}>{ch.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1.5">Name *</label>
                <input
                  type="text"
                  value={deliveryForm.name}
                  onChange={(e) => setDeliveryForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder={`e.g. ${deliveryForm.channel === 'email' ? 'Team Email' : deliveryForm.channel === 'slack' ? '#reports channel' : 'Webhook endpoint'}`}
                />
              </div>

              {deliveryForm.channel === 'email' && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-1.5">SMTP Host</label>
                    <input
                      type="text"
                      value={deliveryForm.config.smtp_host || ''}
                      onChange={(e) => setDeliveryForm((f) => ({ ...f, config: { ...f.config, smtp_host: e.target.value } }))}
                      className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                      placeholder="smtp.gmail.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Default Recipients</label>
                    <input
                      type="text"
                      value={deliveryForm.config.recipients || ''}
                      onChange={(e) => setDeliveryForm((f) => ({ ...f, config: { ...f.config, recipients: e.target.value } }))}
                      className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                      placeholder="user@example.com, team@example.com"
                    />
                  </div>
                </>
              )}

              {deliveryForm.channel === 'slack' && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Webhook URL *</label>
                    <input
                      type="text"
                      value={deliveryForm.config.webhook_url || ''}
                      onChange={(e) => setDeliveryForm((f) => ({ ...f, config: { ...f.config, webhook_url: e.target.value } }))}
                      className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                      placeholder="https://hooks.slack.com/services/..."
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Channel</label>
                    <input
                      type="text"
                      value={deliveryForm.config.channel || ''}
                      onChange={(e) => setDeliveryForm((f) => ({ ...f, config: { ...f.config, channel: e.target.value } }))}
                      className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                      placeholder="#reports"
                    />
                  </div>
                </>
              )}

              {deliveryForm.channel === 'teams' && (
                <div>
                  <label className="block text-sm font-medium mb-1.5">Webhook URL *</label>
                  <input
                    type="text"
                    value={deliveryForm.config.webhook_url || ''}
                    onChange={(e) => setDeliveryForm((f) => ({ ...f, config: { ...f.config, webhook_url: e.target.value } }))}
                    className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                    placeholder="https://outlook.office.com/webhook/..."
                  />
                </div>
              )}

              {deliveryForm.channel === 'webhook' && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Webhook URL *</label>
                    <input
                      type="text"
                      value={deliveryForm.config.webhook_url || ''}
                      onChange={(e) => setDeliveryForm((f) => ({ ...f, config: { ...f.config, webhook_url: e.target.value } }))}
                      className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                      placeholder="https://your-api.com/reports/webhook"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Auth Header (optional)</label>
                    <input
                      type="text"
                      value={deliveryForm.config.auth_header || ''}
                      onChange={(e) => setDeliveryForm((f) => ({ ...f, config: { ...f.config, auth_header: e.target.value } }))}
                      className="w-full px-4 py-2.5 bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                      placeholder="Bearer your-token"
                    />
                  </div>
                </>
              )}
            </div>

            <div className="flex justify-end gap-3 p-4 border-t">
              <button onClick={() => setShowDeliveryEditor(false)} className="px-4 py-2 text-muted-foreground hover:text-foreground">
                Cancel
              </button>
              <button
                onClick={handleSaveDeliveryChannel}
                disabled={!deliveryForm.name || createDeliveryChannel.isPending}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium disabled:opacity-50 hover:bg-primary/90 transition-colors"
              >
                {createDeliveryChannel.isPending ? 'Adding...' : 'Add Channel'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========== Delete Confirmation Modal ========== */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-card border rounded-xl p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold mb-2">
              Delete {deleteConfirm.type === 'template' ? 'Template' : 'Schedule'}
            </h3>
            <p className="text-muted-foreground mb-6">
              Are you sure? This action cannot be undone.
              {deleteConfirm.type === 'template' &&
                ' Any schedules using this template will also be affected.'}
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-muted-foreground hover:text-foreground"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteTemplate.isPending || deleteSchedule.isPending}
                className="px-4 py-2 bg-destructive text-destructive-foreground rounded-lg font-medium disabled:opacity-50 hover:bg-destructive/90 transition-colors"
              >
                {deleteTemplate.isPending || deleteSchedule.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
