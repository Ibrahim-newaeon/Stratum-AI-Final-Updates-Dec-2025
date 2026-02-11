/**
 * Notification Center - Real-time alerts and activity hub
 *
 * Displays Trust Gate alerts, system notifications, and activity feed
 * with filtering, marking as read, and quick actions.
 */

import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Activity,
  AlertTriangle,
  Bell,
  Check,
  CheckCheck,
  Clock,
  Settings,
  Shield,
  Trash2,
  TrendingUp,
  Users,
  X,
  XCircle,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export type NotificationType =
  | 'trust_gate_pass'
  | 'trust_gate_hold'
  | 'trust_gate_block'
  | 'signal_health'
  | 'anomaly'
  | 'campaign'
  | 'segment'
  | 'system';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  actionUrl?: string;
  metadata?: Record<string, any>;
}

// Demo notifications
const DEMO_NOTIFICATIONS: Notification[] = [
  {
    id: '1',
    type: 'trust_gate_block',
    title: 'Trust Gate Blocked',
    message: 'Budget reallocation for "Summer Sale" blocked due to low signal health (42/100)',
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
    read: false,
    actionUrl: '/dashboard/rules',
  },
  {
    id: '2',
    type: 'anomaly',
    title: 'Anomaly Detected',
    message: 'CTR dropped 45% on Google Ads campaign "Brand Awareness Q1"',
    timestamp: new Date(Date.now() - 15 * 60 * 1000),
    read: false,
    actionUrl: '/dashboard/campaigns',
  },
  {
    id: '3',
    type: 'trust_gate_pass',
    title: 'Automation Executed',
    message: 'Creative rotation completed for "Retargeting" campaign',
    timestamp: new Date(Date.now() - 30 * 60 * 1000),
    read: false,
  },
  {
    id: '4',
    type: 'signal_health',
    title: 'Signal Health Improved',
    message: 'Overall signal health increased to 85/100 (+8 from yesterday)',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
    read: true,
  },
  {
    id: '5',
    type: 'segment',
    title: 'Segment Updated',
    message: '"Champions" segment now has 8,500 profiles (+340 this week)',
    timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000),
    read: true,
  },
  {
    id: '6',
    type: 'trust_gate_hold',
    title: 'Automation on Hold',
    message: 'Bid adjustment paused - monitoring signal quality',
    timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000),
    read: true,
  },
  {
    id: '7',
    type: 'campaign',
    title: 'Campaign Milestone',
    message: '"TikTok Product Launch" reached 1M impressions',
    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000),
    read: true,
  },
  {
    id: '8',
    type: 'system',
    title: 'New Feature Available',
    message: 'Audience Sync now supports Snapchat! Connect your account.',
    timestamp: new Date(Date.now() - 48 * 60 * 60 * 1000),
    read: true,
    actionUrl: '/dashboard/cdp/audience-sync',
  },
];

const getNotificationIcon = (type: NotificationType) => {
  switch (type) {
    case 'trust_gate_pass':
      return { icon: Shield, color: 'text-green-500', bg: 'bg-green-500/10' };
    case 'trust_gate_hold':
      return { icon: AlertTriangle, color: 'text-yellow-500', bg: 'bg-yellow-500/10' };
    case 'trust_gate_block':
      return { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10' };
    case 'signal_health':
      return { icon: Activity, color: 'text-cyan-500', bg: 'bg-cyan-500/10' };
    case 'anomaly':
      return { icon: Zap, color: 'text-purple-500', bg: 'bg-purple-500/10' };
    case 'campaign':
      return { icon: TrendingUp, color: 'text-blue-500', bg: 'bg-blue-500/10' };
    case 'segment':
      return { icon: Users, color: 'text-orange-500', bg: 'bg-orange-500/10' };
    case 'system':
      return { icon: Settings, color: 'text-gray-500', bg: 'bg-gray-500/10' };
    default:
      return { icon: Bell, color: 'text-gray-500', bg: 'bg-gray-500/10' };
  }
};

const formatTimestamp = (date: Date) => {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString();
};

interface NotificationCenterProps {
  isOpen: boolean;
  onClose: () => void;
}

export function NotificationCenter({ isOpen, onClose }: NotificationCenterProps) {
  const [notifications, setNotifications] = useState<Notification[]>(DEMO_NOTIFICATIONS);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');

  const unreadCount = notifications.filter((n) => !n.read).length;

  const filteredNotifications =
    filter === 'unread' ? notifications.filter((n) => !n.read) : notifications;

  const markAsRead = (id: string) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const deleteNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const clearAll = () => {
    setNotifications([]);
  };

  // Close on escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
          />

          {/* Panel */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-md bg-card border-l shadow-2xl flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-4 border-b">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Bell className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h2 className="font-semibold">Notifications</h2>
                  <p className="text-xs text-muted-foreground">
                    {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up!'}
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-accent transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Filters & Actions */}
            <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setFilter('all')}
                  className={cn(
                    'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                    filter === 'all' ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'
                  )}
                >
                  All
                </button>
                <button
                  onClick={() => setFilter('unread')}
                  className={cn(
                    'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                    filter === 'unread' ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'
                  )}
                >
                  Unread ({unreadCount})
                </button>
              </div>
              <div className="flex items-center gap-1">
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="p-1.5 rounded-lg hover:bg-accent transition-colors"
                    title="Mark all as read"
                  >
                    <CheckCheck className="h-4 w-4" />
                  </button>
                )}
                {notifications.length > 0 && (
                  <button
                    onClick={clearAll}
                    className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-destructive transition-colors"
                    title="Clear all"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>

            {/* Notification List */}
            <div className="flex-1 overflow-y-auto">
              {filteredNotifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-64 text-center px-4">
                  <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
                    <Bell className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <h3 className="font-medium mb-1">No notifications</h3>
                  <p className="text-sm text-muted-foreground">
                    {filter === 'unread'
                      ? "You've read all notifications"
                      : "You're all caught up!"}
                  </p>
                </div>
              ) : (
                <div className="divide-y">
                  {filteredNotifications.map((notification) => {
                    const { icon: Icon, color, bg } = getNotificationIcon(notification.type);
                    return (
                      <motion.div
                        key={notification.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        className={cn(
                          'group relative px-4 py-3 hover:bg-accent/50 transition-colors cursor-pointer',
                          !notification.read && 'bg-primary/5'
                        )}
                        onClick={() => {
                          markAsRead(notification.id);
                          if (notification.actionUrl) {
                            window.location.href = notification.actionUrl;
                          }
                        }}
                      >
                        <div className="flex gap-3">
                          <div
                            className={cn(
                              'w-10 h-10 rounded-xl flex items-center justify-center shrink-0',
                              bg
                            )}
                          >
                            <Icon className={cn('h-5 w-5', color)} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2">
                              <h4
                                className={cn(
                                  'text-sm font-medium truncate',
                                  !notification.read && 'font-semibold'
                                )}
                              >
                                {notification.title}
                              </h4>
                              {!notification.read && (
                                <span className="w-2 h-2 rounded-full bg-primary shrink-0 mt-1.5" />
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground line-clamp-2 mt-0.5">
                              {notification.message}
                            </p>
                            <div className="flex items-center gap-2 mt-2">
                              <Clock className="h-3 w-3 text-muted-foreground" />
                              <span className="text-xs text-muted-foreground">
                                {formatTimestamp(notification.timestamp)}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Quick actions on hover */}
                        <div className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                          {!notification.read && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                markAsRead(notification.id);
                              }}
                              className="p-1.5 rounded-lg bg-card border hover:bg-accent transition-colors"
                              title="Mark as read"
                            >
                              <Check className="h-3.5 w-3.5" />
                            </button>
                          )}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteNotification(notification.id);
                            }}
                            className="p-1.5 rounded-lg bg-card border hover:bg-destructive/10 hover:text-destructive transition-colors"
                            title="Delete"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-3 border-t bg-muted/30">
              <button className="w-full text-center text-sm text-primary hover:underline">
                Notification Settings
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

/**
 * Notification Bell Button - Shows unread count badge
 */
interface NotificationBellProps {
  onClick: () => void;
  unreadCount?: number;
}

export function NotificationBell({ onClick, unreadCount = 0 }: NotificationBellProps) {
  return (
    <button onClick={onClick} className="relative p-2 rounded-lg hover:bg-accent transition-colors">
      <Bell className="h-5 w-5" />
      {unreadCount > 0 && (
        <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center px-1 text-[10px] font-bold text-white bg-destructive rounded-full animate-pulse">
          {unreadCount > 9 ? '9+' : unreadCount}
        </span>
      )}
    </button>
  );
}

export default NotificationCenter;
