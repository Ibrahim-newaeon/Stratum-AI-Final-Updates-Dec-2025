/**
 * WhatsApp Message History
 * View all sent messages with delivery status tracking
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  ChatBubbleLeftRightIcon,
  MagnifyingGlassIcon,
  CheckIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  EyeIcon,
  ArrowPathIcon,
  FunnelIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  DocumentTextIcon,
  PhotoIcon,
  VideoCameraIcon,
  PaperAirplaneIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

interface Message {
  id: number;
  contact_name: string;
  contact_phone: string;
  direction: 'outbound' | 'inbound';
  message_type: 'template' | 'text' | 'image' | 'video' | 'document';
  template_name: string | null;
  content: string;
  status: 'pending' | 'sent' | 'delivered' | 'read' | 'failed';
  sent_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  error_message: string | null;
}

const mockMessages: Message[] = [
  {
    id: 1,
    contact_name: 'John Doe',
    contact_phone: '+1234567890',
    direction: 'outbound',
    message_type: 'template',
    template_name: 'order_confirmation',
    content: 'Hi John, your order #12345 has been confirmed...',
    status: 'read',
    sent_at: '2025-01-30T10:00:00Z',
    delivered_at: '2025-01-30T10:00:05Z',
    read_at: '2025-01-30T10:05:00Z',
    error_message: null,
  },
  {
    id: 2,
    contact_name: 'Jane Smith',
    contact_phone: '+1987654321',
    direction: 'outbound',
    message_type: 'template',
    template_name: 'appointment_reminder',
    content: 'Hi Jane, this is a reminder for your appointment on Feb 1...',
    status: 'delivered',
    sent_at: '2025-01-30T09:30:00Z',
    delivered_at: '2025-01-30T09:30:03Z',
    read_at: null,
    error_message: null,
  },
  {
    id: 3,
    contact_name: 'John Doe',
    contact_phone: '+1234567890',
    direction: 'inbound',
    message_type: 'text',
    template_name: null,
    content: 'Thanks for the confirmation!',
    status: 'delivered',
    sent_at: '2025-01-30T10:10:00Z',
    delivered_at: null,
    read_at: null,
    error_message: null,
  },
  {
    id: 4,
    contact_name: 'Alice Johnson',
    contact_phone: '+447123456789',
    direction: 'outbound',
    message_type: 'template',
    template_name: 'verification_code',
    content: 'Your verification code is 123456...',
    status: 'sent',
    sent_at: '2025-01-30T09:00:00Z',
    delivered_at: null,
    read_at: null,
    error_message: null,
  },
  {
    id: 5,
    contact_name: 'Mohammed Ali',
    contact_phone: '+971501234567',
    direction: 'outbound',
    message_type: 'template',
    template_name: 'promo_winter_sale',
    content: 'Winter Sale is here! Get up to 50% off...',
    status: 'failed',
    sent_at: '2025-01-30T08:00:00Z',
    delivered_at: null,
    read_at: null,
    error_message: 'Phone number not registered on WhatsApp',
  },
  {
    id: 6,
    contact_name: 'Pierre Dupont',
    contact_phone: '+33612345678',
    direction: 'outbound',
    message_type: 'image',
    template_name: null,
    content: 'product-catalog.jpg',
    status: 'read',
    sent_at: '2025-01-29T15:00:00Z',
    delivered_at: '2025-01-29T15:00:02Z',
    read_at: '2025-01-29T15:30:00Z',
    error_message: null,
  },
];

const statusConfig = {
  pending: { label: 'Pending', color: 'text-gray-400', bg: 'bg-gray-500/10', icon: ClockIcon },
  sent: { label: 'Sent', color: 'text-blue-400', bg: 'bg-blue-500/10', icon: CheckIcon },
  delivered: {
    label: 'Delivered',
    color: 'text-green-400',
    bg: 'bg-green-500/10',
    icon: CheckCircleIcon,
  },
  read: { label: 'Read', color: 'text-cyan-400', bg: 'bg-cyan-500/10', icon: EyeIcon },
  failed: {
    label: 'Failed',
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    icon: ExclamationCircleIcon,
  },
};

const messageTypeIcons = {
  template: DocumentTextIcon,
  text: ChatBubbleLeftRightIcon,
  image: PhotoIcon,
  video: VideoCameraIcon,
  document: DocumentTextIcon,
};

export default function WhatsAppMessages() {
  const [messages, setMessages] = useState<Message[]>(mockMessages);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [directionFilter, setDirectionFilter] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [showFilters, setShowFilters] = useState(false);
  const pageSize = 10;

  const filteredMessages = messages.filter((msg) => {
    const matchesSearch =
      msg.contact_name.toLowerCase().includes(search.toLowerCase()) ||
      msg.contact_phone.includes(search) ||
      msg.content.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || msg.status === statusFilter;
    const matchesDirection = directionFilter === 'all' || msg.direction === directionFilter;
    return matchesSearch && matchesStatus && matchesDirection;
  });

  const totalPages = Math.ceil(filteredMessages.length / pageSize);
  const paginatedMessages = filteredMessages.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  // Stats
  const totalMessages = messages.length;
  const sentMessages = messages.filter((m) => m.direction === 'outbound').length;
  const deliveredMessages = messages.filter((m) => ['delivered', 'read'].includes(m.status)).length;
  const readMessages = messages.filter((m) => m.status === 'read').length;
  const failedMessages = messages.filter((m) => m.status === 'failed').length;

  return (
    <div className="space-y-6">
      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <MiniStat label="Total" value={totalMessages} />
        <MiniStat label="Sent" value={sentMessages} color="text-blue-400" />
        <MiniStat label="Delivered" value={deliveredMessages} color="text-green-400" />
        <MiniStat label="Read" value={readMessages} color="text-cyan-400" />
        <MiniStat label="Failed" value={failedMessages} color="text-red-400" />
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by name, phone, or content..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-[#12121a] border border-white/10 rounded-xl focus:border-[#25D366]/50 focus:outline-none"
          />
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={cn(
            'flex items-center gap-2 px-4 py-3 rounded-xl border transition-colors',
            showFilters
              ? 'bg-[#25D366]/10 border-[#25D366]/30 text-[#25D366]'
              : 'bg-[#12121a] border-white/10 text-gray-400 hover:text-white'
          )}
        >
          <FunnelIcon className="w-5 h-5" />
          Filters
        </button>
        <button
          onClick={() => {
            /* Refresh */
          }}
          className="flex items-center gap-2 px-4 py-3 bg-[#12121a] border border-white/10 rounded-xl text-gray-400 hover:text-white transition-colors"
        >
          <ArrowPathIcon className="w-5 h-5" />
          Refresh
        </button>
      </div>

      {/* Filter Options */}
      {showFilters && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="flex flex-wrap gap-4 p-4 bg-[#12121a] rounded-xl border border-white/5"
        >
          <div>
            <label className="block text-sm text-gray-400 mb-2">Status</label>
            <div className="flex gap-2">
              {['all', 'pending', 'sent', 'delivered', 'read', 'failed'].map((status) => (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  className={cn(
                    'px-3 py-1.5 rounded-lg text-sm transition-colors',
                    statusFilter === status
                      ? 'bg-[#25D366] text-white'
                      : 'bg-[#1a1a24] text-gray-400 hover:text-white'
                  )}
                >
                  {status === 'all'
                    ? 'All'
                    : statusConfig[status as keyof typeof statusConfig]?.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Direction</label>
            <div className="flex gap-2">
              {['all', 'outbound', 'inbound'].map((dir) => (
                <button
                  key={dir}
                  onClick={() => setDirectionFilter(dir)}
                  className={cn(
                    'px-3 py-1.5 rounded-lg text-sm transition-colors',
                    directionFilter === dir
                      ? 'bg-[#25D366] text-white'
                      : 'bg-[#1a1a24] text-gray-400 hover:text-white'
                  )}
                >
                  {dir === 'all' ? 'All' : dir === 'outbound' ? 'Sent' : 'Received'}
                </button>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* Messages List */}
      <div className="bg-[#12121a] rounded-2xl border border-white/5 overflow-hidden">
        <div className="divide-y divide-white/5">
          {paginatedMessages.map((message) => {
            const status = statusConfig[message.status];
            const StatusIcon = status.icon;
            const TypeIcon = messageTypeIcons[message.message_type];

            return (
              <div key={message.id} className="p-4 hover:bg-white/[0.02] transition-colors">
                <div className="flex items-start gap-4">
                  {/* Avatar */}
                  <div
                    className={cn(
                      'w-10 h-10 rounded-full flex items-center justify-center font-medium',
                      message.direction === 'outbound'
                        ? 'bg-gradient-to-br from-[#25D366] to-[#128C7E]'
                        : 'bg-gradient-to-br from-cyan-500 to-blue-500'
                    )}
                  >
                    {message.contact_name[0]}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium">{message.contact_name}</span>
                      <span className="text-xs text-gray-500">{message.contact_phone}</span>
                      {message.direction === 'outbound' ? (
                        <PaperAirplaneIcon className="w-3.5 h-3.5 text-gray-400" title="Sent" />
                      ) : (
                        <ChatBubbleLeftRightIcon
                          className="w-3.5 h-3.5 text-cyan-400"
                          title="Received"
                        />
                      )}
                    </div>

                    <div className="flex items-center gap-2 mb-2">
                      <TypeIcon className="w-4 h-4 text-gray-400" />
                      {message.template_name && (
                        <span className="text-xs px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded">
                          {message.template_name}
                        </span>
                      )}
                    </div>

                    <p className="text-sm text-gray-300 line-clamp-2">{message.content}</p>

                    {message.error_message && (
                      <p className="text-xs text-red-400 mt-1">{message.error_message}</p>
                    )}
                  </div>

                  {/* Status & Time */}
                  <div className="text-right">
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                        status.bg,
                        status.color
                      )}
                    >
                      <StatusIcon className="w-3.5 h-3.5" />
                      {status.label}
                    </span>
                    <div className="text-xs text-gray-500 mt-2">
                      {message.sent_at && new Date(message.sent_at).toLocaleString()}
                    </div>

                    {/* Delivery Timeline */}
                    {message.direction === 'outbound' && (
                      <div className="flex items-center justify-end gap-1 mt-2">
                        <TimelineDot active={!!message.sent_at} label="Sent" />
                        <TimelineLine active={!!message.delivered_at} />
                        <TimelineDot active={!!message.delivered_at} label="Delivered" />
                        <TimelineLine active={!!message.read_at} />
                        <TimelineDot active={!!message.read_at} label="Read" />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between p-4 border-t border-white/5">
          <span className="text-sm text-gray-400">
            Showing {(currentPage - 1) * pageSize + 1}-
            {Math.min(currentPage * pageSize, filteredMessages.length)} of {filteredMessages.length}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-2 bg-[#1a1a24] rounded-lg disabled:opacity-50 hover:bg-[#22222e] transition-colors"
            >
              <ChevronLeftIcon className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-2 bg-[#1a1a24] rounded-lg disabled:opacity-50 hover:bg-[#22222e] transition-colors"
            >
              <ChevronRightIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function MiniStat({
  label,
  value,
  color = 'text-white',
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div className="bg-[#12121a] rounded-xl border border-white/5 p-3 text-center">
      <div className={cn('text-xl font-bold', color)}>{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

function TimelineDot({ active, label }: { active: boolean; label: string }) {
  return (
    <div
      className={cn('w-2 h-2 rounded-full', active ? 'bg-[#25D366]' : 'bg-gray-600')}
      title={label}
    />
  );
}

function TimelineLine({ active }: { active: boolean }) {
  return <div className={cn('w-3 h-0.5', active ? 'bg-[#25D366]' : 'bg-gray-600')} />;
}
