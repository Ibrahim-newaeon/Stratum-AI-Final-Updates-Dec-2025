/**
 * WhatsApp Broadcast Manager
 * Send approved templates to multiple contacts with scheduling
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MegaphoneIcon,
  UserGroupIcon,
  DocumentTextIcon,
  PaperAirplaneIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  CalendarIcon,
  XMarkIcon,
  MagnifyingGlassIcon,
  TagIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

interface Template {
  id: number;
  name: string;
  category: string;
  body_text: string;
  usage_count: number;
}

interface Segment {
  id: number;
  name: string;
  count: number;
  description: string;
}

interface BroadcastHistory {
  id: number;
  template_name: string;
  recipients: number;
  sent: number;
  delivered: number;
  read: number;
  failed: number;
  sent_at: string;
  status: 'completed' | 'in_progress' | 'scheduled' | 'failed';
}

const mockTemplates: Template[] = [
  {
    id: 1,
    name: 'order_confirmation',
    category: 'UTILITY',
    body_text: 'Hi {{1}}, your order #{{2}} has been confirmed...',
    usage_count: 1245,
  },
  {
    id: 2,
    name: 'appointment_reminder',
    category: 'UTILITY',
    body_text: 'Hi {{1}}, this is a reminder for your appointment on {{2}}...',
    usage_count: 856,
  },
  {
    id: 4,
    name: 'verification_code',
    category: 'AUTHENTICATION',
    body_text: 'Your verification code is {{1}}...',
    usage_count: 3421,
  },
];

const mockSegments: Segment[] = [
  {
    id: 1,
    name: 'All Opted-In Contacts',
    count: 11234,
    description: 'All contacts with opt-in status',
  },
  { id: 2, name: 'Active Customers', count: 5678, description: 'Made purchase in last 30 days' },
  { id: 3, name: 'High Value Customers', count: 1234, description: 'Total spend > $500' },
  { id: 4, name: 'New Subscribers', count: 890, description: 'Joined in last 7 days' },
  { id: 5, name: 'Abandoned Cart', count: 456, description: 'Cart abandoned in last 24h' },
];

const mockHistory: BroadcastHistory[] = [
  {
    id: 1,
    template_name: 'order_confirmation',
    recipients: 500,
    sent: 500,
    delivered: 485,
    read: 412,
    failed: 15,
    sent_at: '2025-01-30T10:00:00Z',
    status: 'completed',
  },
  {
    id: 2,
    template_name: 'appointment_reminder',
    recipients: 1200,
    sent: 1200,
    delivered: 1150,
    read: 980,
    failed: 50,
    sent_at: '2025-01-29T09:00:00Z',
    status: 'completed',
  },
  {
    id: 3,
    template_name: 'promo_winter_sale',
    recipients: 5000,
    sent: 2500,
    delivered: 2400,
    read: 0,
    failed: 100,
    sent_at: '2025-01-30T14:00:00Z',
    status: 'in_progress',
  },
  {
    id: 4,
    template_name: 'verification_code',
    recipients: 300,
    sent: 0,
    delivered: 0,
    read: 0,
    failed: 0,
    sent_at: '2025-01-31T08:00:00Z',
    status: 'scheduled',
  },
];

export default function WhatsAppBroadcast() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [history, setHistory] = useState<BroadcastHistory[]>(mockHistory);

  const totalSent = history.reduce((acc, h) => acc + h.sent, 0);
  const totalDelivered = history.reduce((acc, h) => acc + h.delivered, 0);
  const totalRead = history.reduce((acc, h) => acc + h.read, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">Broadcast Campaigns</h2>
          <p className="text-gray-400 text-sm">Send approved templates to multiple contacts</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#25D366] to-[#128C7E] rounded-xl hover:opacity-90 transition-opacity"
        >
          <MegaphoneIcon className="w-4 h-4" />
          New Broadcast
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Broadcasts"
          value={history.length.toString()}
          subtitle="This month"
          icon={MegaphoneIcon}
        />
        <StatCard
          title="Messages Sent"
          value={totalSent.toLocaleString()}
          subtitle={`${((totalDelivered / totalSent) * 100).toFixed(1)}% delivered`}
          icon={PaperAirplaneIcon}
        />
        <StatCard
          title="Delivered"
          value={totalDelivered.toLocaleString()}
          subtitle={`${((totalRead / totalDelivered) * 100).toFixed(1)}% read`}
          icon={CheckCircleIcon}
        />
        <StatCard
          title="Read"
          value={totalRead.toLocaleString()}
          subtitle="Engagement"
          icon={ChartBarIcon}
        />
      </div>

      {/* Broadcast History */}
      <div className="bg-[#12121a] rounded-2xl border border-white/5 overflow-hidden">
        <div className="p-5 border-b border-white/5">
          <h3 className="font-semibold">Broadcast History</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5">
                <th className="p-4 text-left text-sm font-medium text-gray-400">Template</th>
                <th className="p-4 text-left text-sm font-medium text-gray-400">Recipients</th>
                <th className="p-4 text-left text-sm font-medium text-gray-400">Delivery</th>
                <th className="p-4 text-left text-sm font-medium text-gray-400">Status</th>
                <th className="p-4 text-left text-sm font-medium text-gray-400">Sent At</th>
              </tr>
            </thead>
            <tbody>
              {history.map((broadcast) => {
                const deliveryRate =
                  broadcast.sent > 0
                    ? ((broadcast.delivered / broadcast.sent) * 100).toFixed(1)
                    : '0';
                const readRate =
                  broadcast.delivered > 0
                    ? ((broadcast.read / broadcast.delivered) * 100).toFixed(1)
                    : '0';

                return (
                  <tr
                    key={broadcast.id}
                    className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
                  >
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-[#25D366]/10 rounded-lg">
                          <DocumentTextIcon className="w-4 h-4 text-[#25D366]" />
                        </div>
                        <span className="font-medium">{broadcast.template_name}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <UserGroupIcon className="w-4 h-4 text-gray-400" />
                        <span>{broadcast.recipients.toLocaleString()}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-4 text-sm">
                          <span className="text-gray-400">
                            Sent:{' '}
                            <span className="text-white">{broadcast.sent.toLocaleString()}</span>
                          </span>
                          <span className="text-gray-400">
                            Delivered: <span className="text-green-400">{deliveryRate}%</span>
                          </span>
                          <span className="text-gray-400">
                            Read: <span className="text-cyan-400">{readRate}%</span>
                          </span>
                        </div>
                        <div className="flex gap-1 h-1.5">
                          <div
                            className="bg-[#25D366] rounded-full"
                            style={{ width: `${(broadcast.sent / broadcast.recipients) * 100}%` }}
                          />
                          <div
                            className="bg-green-500/50 rounded-full"
                            style={{
                              width: `${(broadcast.delivered / broadcast.recipients) * 100 - (broadcast.sent / broadcast.recipients) * 100}%`,
                            }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="p-4">
                      <StatusBadge status={broadcast.status} />
                    </td>
                    <td className="p-4 text-gray-400 text-sm">
                      {new Date(broadcast.sent_at).toLocaleString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Broadcast Modal */}
      <AnimatePresence>
        {showCreateModal && (
          <CreateBroadcastModal
            templates={mockTemplates}
            segments={mockSegments}
            onClose={() => setShowCreateModal(false)}
            onCreate={(broadcast) => {
              setHistory((prev) => [{ ...broadcast, id: prev.length + 1 }, ...prev]);
              setShowCreateModal(false);
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="bg-[#12121a] rounded-2xl border border-white/5 p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className="p-2 bg-[#25D366]/10 rounded-lg">
          <Icon className="w-5 h-5 text-[#25D366]" />
        </div>
        <span className="text-sm text-gray-400">{title}</span>
      </div>
      <div className="text-2xl font-bold mb-1">{value}</div>
      <div className="text-xs text-gray-500">{subtitle}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: BroadcastHistory['status'] }) {
  const config = {
    completed: {
      label: 'Completed',
      color: 'text-green-400',
      bg: 'bg-green-500/10',
      icon: CheckCircleIcon,
    },
    in_progress: {
      label: 'In Progress',
      color: 'text-cyan-400',
      bg: 'bg-cyan-500/10',
      icon: ClockIcon,
    },
    scheduled: {
      label: 'Scheduled',
      color: 'text-yellow-400',
      bg: 'bg-yellow-500/10',
      icon: CalendarIcon,
    },
    failed: {
      label: 'Failed',
      color: 'text-red-400',
      bg: 'bg-red-500/10',
      icon: ExclamationTriangleIcon,
    },
  };

  const cfg = config[status];
  const Icon = cfg.icon;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
        cfg.bg,
        cfg.color
      )}
    >
      <Icon className="w-3.5 h-3.5" />
      {cfg.label}
    </span>
  );
}

// Create Broadcast Modal
function CreateBroadcastModal({
  templates,
  segments,
  onClose,
  onCreate,
}: {
  templates: Template[];
  segments: Segment[];
  onClose: () => void;
  onCreate: (broadcast: Omit<BroadcastHistory, 'id'>) => void;
}) {
  const [step, setStep] = useState(1);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [selectedSegments, setSelectedSegments] = useState<number[]>([]);
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [scheduleType, setScheduleType] = useState<'now' | 'scheduled'>('now');
  const [scheduledDate, setScheduledDate] = useState('');
  const [scheduledTime, setScheduledTime] = useState('');

  const totalRecipients = segments
    .filter((s) => selectedSegments.includes(s.id))
    .reduce((acc, s) => acc + s.count, 0);

  const handleSubmit = () => {
    if (!selectedTemplate) return;

    onCreate({
      template_name: selectedTemplate.name,
      recipients: totalRecipients,
      sent: 0,
      delivered: 0,
      read: 0,
      failed: 0,
      sent_at:
        scheduleType === 'now' ? new Date().toISOString() : `${scheduledDate}T${scheduledTime}:00Z`,
      status: scheduleType === 'now' ? 'in_progress' : 'scheduled',
    });
  };

  const toggleSegment = (id: number) => {
    setSelectedSegments((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm overflow-y-auto"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="w-full max-w-3xl bg-[#12121a] rounded-2xl border border-white/10 p-6 my-8"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-semibold">Create Broadcast</h3>
            <p className="text-sm text-gray-400">Step {step} of 3</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg">
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Progress Bar */}
        <div className="flex gap-2 mb-8">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={cn(
                'flex-1 h-1 rounded-full transition-colors',
                s <= step ? 'bg-[#25D366]' : 'bg-white/10'
              )}
            />
          ))}
        </div>

        {/* Step 1: Select Template */}
        {step === 1 && (
          <div className="space-y-4">
            <h4 className="font-medium">Select Template</h4>
            <div className="relative mb-4">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search templates..."
                className="w-full pl-10 pr-4 py-3 bg-[#0a0a0f] border border-white/10 rounded-xl focus:border-[#25D366]/50 focus:outline-none"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-80 overflow-y-auto">
              {templates.map((template) => (
                <button
                  key={template.id}
                  onClick={() => setSelectedTemplate(template)}
                  className={cn(
                    'p-4 rounded-xl border text-left transition-all',
                    selectedTemplate?.id === template.id
                      ? 'border-[#25D366] bg-[#25D366]/10'
                      : 'border-white/10 hover:border-white/20 bg-[#0a0a0f]'
                  )}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{template.name}</span>
                    <span className="text-xs text-gray-500 px-2 py-0.5 bg-white/5 rounded">
                      {template.category}
                    </span>
                  </div>
                  <p className="text-sm text-gray-400 line-clamp-2">{template.body_text}</p>
                  <p className="text-xs text-gray-500 mt-2">Used {template.usage_count} times</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Select Audience */}
        {step === 2 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-medium">Select Audience</h4>
              <span className="text-sm text-gray-400">
                {totalRecipients.toLocaleString()} recipients selected
              </span>
            </div>
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {segments.map((segment) => (
                <button
                  key={segment.id}
                  onClick={() => toggleSegment(segment.id)}
                  className={cn(
                    'w-full p-4 rounded-xl border text-left transition-all flex items-center gap-4',
                    selectedSegments.includes(segment.id)
                      ? 'border-[#25D366] bg-[#25D366]/10'
                      : 'border-white/10 hover:border-white/20 bg-[#0a0a0f]'
                  )}
                >
                  <div
                    className={cn(
                      'w-5 h-5 rounded border-2 flex items-center justify-center transition-colors',
                      selectedSegments.includes(segment.id)
                        ? 'border-[#25D366] bg-[#25D366]'
                        : 'border-gray-500'
                    )}
                  >
                    {selectedSegments.includes(segment.id) && (
                      <CheckCircleIcon className="w-4 h-4 text-white" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <TagIcon className="w-4 h-4 text-gray-400" />
                      <span className="font-medium">{segment.name}</span>
                    </div>
                    <p className="text-sm text-gray-400">{segment.description}</p>
                  </div>
                  <div className="text-right">
                    <div className="font-medium">{segment.count.toLocaleString()}</div>
                    <div className="text-xs text-gray-500">contacts</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 3: Schedule & Confirm */}
        {step === 3 && (
          <div className="space-y-6">
            <div>
              <h4 className="font-medium mb-4">Template Variables</h4>
              <div className="bg-[#0a0a0f] rounded-xl p-4 mb-4">
                <p className="text-sm text-gray-400 mb-3">Preview:</p>
                <p className="text-sm">
                  {selectedTemplate?.body_text.replace(/\{\{(\d+)\}\}/g, (_, n) => {
                    return variables[n] || `[Variable ${n}]`;
                  })}
                </p>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {[1, 2, 3].map((num) => (
                  <div key={num}>
                    <label className="block text-sm text-gray-400 mb-1">{`{{${num}}}`}</label>
                    <input
                      type="text"
                      placeholder={`Variable ${num}`}
                      value={variables[num] || ''}
                      onChange={(e) => setVariables({ ...variables, [num]: e.target.value })}
                      className="w-full px-3 py-2 bg-[#0a0a0f] border border-white/10 rounded-lg text-sm"
                    />
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="font-medium mb-4">Schedule</h4>
              <div className="flex gap-3">
                <button
                  onClick={() => setScheduleType('now')}
                  className={cn(
                    'flex-1 p-4 rounded-xl border transition-colors',
                    scheduleType === 'now'
                      ? 'border-[#25D366] bg-[#25D366]/10'
                      : 'border-white/10 hover:border-white/20'
                  )}
                >
                  <PaperAirplaneIcon className="w-6 h-6 mb-2 text-[#25D366]" />
                  <div className="font-medium">Send Now</div>
                  <div className="text-sm text-gray-400">Start immediately</div>
                </button>
                <button
                  onClick={() => setScheduleType('scheduled')}
                  className={cn(
                    'flex-1 p-4 rounded-xl border transition-colors',
                    scheduleType === 'scheduled'
                      ? 'border-[#25D366] bg-[#25D366]/10'
                      : 'border-white/10 hover:border-white/20'
                  )}
                >
                  <CalendarIcon className="w-6 h-6 mb-2 text-[#25D366]" />
                  <div className="font-medium">Schedule</div>
                  <div className="text-sm text-gray-400">Pick date & time</div>
                </button>
              </div>
              {scheduleType === 'scheduled' && (
                <div className="grid grid-cols-2 gap-3 mt-4">
                  <input
                    type="date"
                    value={scheduledDate}
                    onChange={(e) => setScheduledDate(e.target.value)}
                    className="px-4 py-3 bg-[#0a0a0f] border border-white/10 rounded-xl"
                  />
                  <input
                    type="time"
                    value={scheduledTime}
                    onChange={(e) => setScheduledTime(e.target.value)}
                    className="px-4 py-3 bg-[#0a0a0f] border border-white/10 rounded-xl"
                  />
                </div>
              )}
            </div>

            {/* Summary */}
            <div className="bg-[#0a0a0f] rounded-xl p-4">
              <h4 className="font-medium mb-3">Summary</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Template</span>
                  <span>{selectedTemplate?.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Recipients</span>
                  <span>{totalRecipients.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Schedule</span>
                  <span>
                    {scheduleType === 'now'
                      ? 'Send immediately'
                      : `${scheduledDate} ${scheduledTime}`}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex gap-3 mt-8">
          {step > 1 && (
            <button
              onClick={() => setStep((s) => s - 1)}
              className="px-6 py-3 bg-[#1a1a24] border border-white/10 rounded-xl hover:bg-[#22222e] transition-colors"
            >
              Back
            </button>
          )}
          <button
            onClick={onClose}
            className="px-6 py-3 bg-[#1a1a24] border border-white/10 rounded-xl hover:bg-[#22222e] transition-colors"
          >
            Cancel
          </button>
          <div className="flex-1" />
          {step < 3 ? (
            <button
              onClick={() => setStep((s) => s + 1)}
              disabled={
                (step === 1 && !selectedTemplate) || (step === 2 && selectedSegments.length === 0)
              }
              className="px-6 py-3 bg-gradient-to-r from-[#25D366] to-[#128C7E] rounded-xl hover:opacity-90 transition-opacity font-medium disabled:opacity-50"
            >
              Continue
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-[#25D366] to-[#128C7E] rounded-xl hover:opacity-90 transition-opacity font-medium"
            >
              <PaperAirplaneIcon className="w-4 h-4" />
              {scheduleType === 'now' ? 'Send Broadcast' : 'Schedule Broadcast'}
            </button>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
