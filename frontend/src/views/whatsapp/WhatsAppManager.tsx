/**
 * WhatsApp Manager - Main Dashboard
 * Comprehensive WhatsApp Business management interface
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  ChatBubbleLeftRightIcon,
  UserGroupIcon,
  DocumentTextIcon,
  MegaphoneIcon,
  ClockIcon,
  ChartBarIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  PaperAirplaneIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import WhatsAppContacts from './WhatsAppContacts';
import WhatsAppTemplates from './WhatsAppTemplates';
import WhatsAppBroadcast from './WhatsAppBroadcast';
import WhatsAppMessages from './WhatsAppMessages';

type TabId = 'overview' | 'contacts' | 'templates' | 'broadcast' | 'messages';

interface TabConfig {
  id: TabId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
}

const tabs: TabConfig[] = [
  {
    id: 'overview',
    label: 'Overview',
    icon: ChartBarIcon,
    description: 'Dashboard & Analytics',
  },
  {
    id: 'contacts',
    label: 'Contacts',
    icon: UserGroupIcon,
    description: 'Manage Recipients',
  },
  {
    id: 'templates',
    label: 'Templates',
    icon: DocumentTextIcon,
    description: 'Message Templates',
  },
  {
    id: 'broadcast',
    label: 'Broadcast',
    icon: MegaphoneIcon,
    description: 'Send Campaigns',
  },
  {
    id: 'messages',
    label: 'Messages',
    icon: ClockIcon,
    description: 'Message History',
  },
];

// Mock stats for overview
const mockStats = {
  totalContacts: 12453,
  optedIn: 11234,
  optedOut: 1219,
  templates: 8,
  approvedTemplates: 6,
  pendingTemplates: 2,
  messagesSent: 45678,
  messagesDelivered: 44123,
  messagesRead: 38456,
  broadcastsThisMonth: 12,
};

export default function WhatsAppManager() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  const renderContent = () => {
    switch (activeTab) {
      case 'contacts':
        return <WhatsAppContacts />;
      case 'templates':
        return <WhatsAppTemplates />;
      case 'broadcast':
        return <WhatsAppBroadcast />;
      case 'messages':
        return <WhatsAppMessages />;
      default:
        return <OverviewDashboard stats={mockStats} onNavigate={setActiveTab} />;
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-xl bg-gradient-to-br from-[#25D366] to-[#128C7E]">
            <ChatBubbleLeftRightIcon className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold">WhatsApp Business Manager</h1>
        </div>
        <p className="text-gray-400">Manage contacts, templates, and broadcast campaigns</p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-3 rounded-xl transition-all whitespace-nowrap',
                isActive
                  ? 'bg-gradient-to-r from-[#25D366] to-[#128C7E] text-white shadow-lg shadow-[#25D366]/20'
                  : 'bg-[#12121a] text-gray-400 hover:text-white hover:bg-[#1a1a24] border border-white/5'
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        {renderContent()}
      </motion.div>
    </div>
  );
}

// Overview Dashboard Component
function OverviewDashboard({
  stats,
  onNavigate,
}: {
  stats: typeof mockStats;
  onNavigate: (tab: TabId) => void;
}) {
  const deliveryRate = ((stats.messagesDelivered / stats.messagesSent) * 100).toFixed(1);
  const readRate = ((stats.messagesRead / stats.messagesDelivered) * 100).toFixed(1);
  const optInRate = ((stats.optedIn / stats.totalContacts) * 100).toFixed(1);

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Contacts"
          value={stats.totalContacts.toLocaleString()}
          subtitle={`${optInRate}% opted in`}
          icon={UserGroupIcon}
          color="cyan"
          onClick={() => onNavigate('contacts')}
        />
        <StatCard
          title="Templates"
          value={stats.templates.toString()}
          subtitle={`${stats.approvedTemplates} approved, ${stats.pendingTemplates} pending`}
          icon={DocumentTextIcon}
          color="purple"
          onClick={() => onNavigate('templates')}
        />
        <StatCard
          title="Messages Sent"
          value={stats.messagesSent.toLocaleString()}
          subtitle={`${deliveryRate}% delivered`}
          icon={PaperAirplaneIcon}
          color="green"
          onClick={() => onNavigate('messages')}
        />
        <StatCard
          title="Broadcasts"
          value={stats.broadcastsThisMonth.toString()}
          subtitle="This month"
          icon={MegaphoneIcon}
          color="orange"
          onClick={() => onNavigate('broadcast')}
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <QuickActionCard
          title="Create Template"
          description="Design a new message template for Meta approval"
          icon={DocumentTextIcon}
          onClick={() => onNavigate('templates')}
          color="purple"
        />
        <QuickActionCard
          title="Send Broadcast"
          description="Send approved template to multiple contacts"
          icon={MegaphoneIcon}
          onClick={() => onNavigate('broadcast')}
          color="green"
        />
        <QuickActionCard
          title="Import Contacts"
          description="Bulk import contacts from CSV or manually"
          icon={UserGroupIcon}
          onClick={() => onNavigate('contacts')}
          color="cyan"
        />
      </div>

      {/* Message Stats */}
      <div className="bg-[#12121a] rounded-2xl border border-white/5 p-6">
        <h3 className="text-lg font-semibold mb-4">Message Delivery Performance</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Delivery Rate</span>
              <span className="text-[#25D366] font-medium">{deliveryRate}%</span>
            </div>
            <div className="h-2 bg-[#1a1a24] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-[#25D366] to-[#128C7E] rounded-full"
                style={{ width: `${deliveryRate}%` }}
              />
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Read Rate</span>
              <span className="text-cyan-400 font-medium">{readRate}%</span>
            </div>
            <div className="h-2 bg-[#1a1a24] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-cyan-400 rounded-full"
                style={{ width: `${readRate}%` }}
              />
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Opt-in Rate</span>
              <span className="text-purple-400 font-medium">{optInRate}%</span>
            </div>
            <div className="h-2 bg-[#1a1a24] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-purple-400 rounded-full"
                style={{ width: `${optInRate}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Template Status */}
      <div className="bg-[#12121a] rounded-2xl border border-white/5 p-6">
        <h3 className="text-lg font-semibold mb-4">Template Status</h3>
        <div className="space-y-3">
          <StatusRow
            icon={CheckCircleIcon}
            label="Approved Templates"
            value={stats.approvedTemplates}
            color="green"
          />
          <StatusRow
            icon={ClockIcon}
            label="Pending Approval"
            value={stats.pendingTemplates}
            color="yellow"
          />
          <StatusRow
            icon={ExclamationCircleIcon}
            label="Rejected Templates"
            value={0}
            color="red"
          />
        </div>
      </div>
    </div>
  );
}

// Stat Card Component
function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
  onClick,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  color: 'cyan' | 'purple' | 'green' | 'orange';
  onClick: () => void;
}) {
  const colorClasses = {
    cyan: 'from-cyan-500/20 to-cyan-500/5 border-cyan-500/20',
    purple: 'from-purple-500/20 to-purple-500/5 border-purple-500/20',
    green: 'from-[#25D366]/20 to-[#25D366]/5 border-[#25D366]/20',
    orange: 'from-orange-500/20 to-orange-500/5 border-orange-500/20',
  };

  const iconColors = {
    cyan: 'text-cyan-400',
    purple: 'text-purple-400',
    green: 'text-[#25D366]',
    orange: 'text-orange-400',
  };

  return (
    <button
      onClick={onClick}
      className={cn(
        'bg-gradient-to-br rounded-2xl border p-6 text-left transition-all hover:scale-[1.02] hover:shadow-lg',
        colorClasses[color]
      )}
    >
      <div className="flex items-start justify-between mb-4">
        <Icon className={cn('w-6 h-6', iconColors[color])} />
      </div>
      <div className="text-3xl font-bold mb-1">{value}</div>
      <div className="text-sm text-gray-400">{title}</div>
      <div className="text-xs text-gray-500 mt-1">{subtitle}</div>
    </button>
  );
}

// Quick Action Card
function QuickActionCard({
  title,
  description,
  icon: Icon,
  onClick,
  color,
}: {
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  onClick: () => void;
  color: 'cyan' | 'purple' | 'green';
}) {
  const colorClasses = {
    cyan: 'hover:border-cyan-500/30 group-hover:text-cyan-400',
    purple: 'hover:border-purple-500/30 group-hover:text-purple-400',
    green: 'hover:border-[#25D366]/30 group-hover:text-[#25D366]',
  };

  return (
    <button
      onClick={onClick}
      className={cn(
        'group bg-[#12121a] rounded-2xl border border-white/5 p-6 text-left transition-all hover:bg-[#1a1a24]',
        colorClasses[color]
      )}
    >
      <Icon className="w-8 h-8 text-gray-400 group-hover:text-current transition-colors mb-4" />
      <h4 className="font-semibold mb-1">{title}</h4>
      <p className="text-sm text-gray-500">{description}</p>
    </button>
  );
}

// Status Row
function StatusRow({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  color: 'green' | 'yellow' | 'red';
}) {
  const colorClasses = {
    green: 'text-green-400',
    yellow: 'text-yellow-400',
    red: 'text-red-400',
  };

  return (
    <div className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
      <div className="flex items-center gap-3">
        <Icon className={cn('w-5 h-5', colorClasses[color])} />
        <span className="text-gray-300">{label}</span>
      </div>
      <span className="font-medium">{value}</span>
    </div>
  );
}
