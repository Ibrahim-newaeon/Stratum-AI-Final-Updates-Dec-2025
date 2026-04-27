/**
 * Stratum AI — Push Notifications Dashboard Widget
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, Send, Users, Smartphone, Globe, ArrowRight, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const RECENT_PUSHES = [
  { id: 'push_001', title: 'ROAS Alert: Campaign #452', body: 'ROAS dropped to 1.2x', sent: 12, delivered: 11, time: '5m ago' },
  { id: 'push_002', title: 'Budget Pacing Warning', body: 'Daily budget 85% spent', sent: 8, delivered: 8, time: '1h ago' },
  { id: 'push_003', title: 'Weekly Report Ready', body: 'Your analytics digest is ready', sent: 45, delivered: 43, time: '3h ago' },
];

export function PushNotificationsWidget() {
  const navigate = useNavigate();
  const [permission, setPermission] = useState<NotificationPermission>('default');

  const requestPermission = async () => {
    const result = await Notification.requestPermission();
    setPermission(result);
  };

  const subscribers = 65;
  const sent24h = 3;

  return (
    <div className="dashboard-card h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-rose-500 to-pink-500 flex items-center justify-center">
            <Bell className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">Push Notifications</h3>
            <p className="text-xs text-muted-foreground">Web push · VAPID</p>
          </div>
        </div>
        <button
          onClick={() => navigate('/push-notifications')}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Manage <ArrowRight className="w-3 h-3 inline" />
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="bg-white/[0.02] rounded-lg p-2 text-center">
          <Users className="w-4 h-4 text-sky-400 mx-auto mb-1" />
          <div className="text-lg font-bold">{subscribers}</div>
          <div className="text-[10px] text-muted-foreground">Subscribers</div>
        </div>
        <div className="bg-white/[0.02] rounded-lg p-2 text-center">
          <Send className="w-4 h-4 text-emerald-400 mx-auto mb-1" />
          <div className="text-lg font-bold">{sent24h}</div>
          <div className="text-[10px] text-muted-foreground">Sent 24h</div>
        </div>
        <div className="bg-white/[0.02] rounded-lg p-2 text-center">
          <Smartphone className="w-4 h-4 text-purple-400 mx-auto mb-1" />
          <div className="text-lg font-bold">95%</div>
          <div className="text-[10px] text-muted-foreground">Delivery</div>
        </div>
      </div>

      {/* Permission Banner */}
      {permission !== 'granted' && (
        <button
          onClick={requestPermission}
          className="w-full mb-3 bg-primary/10 hover:bg-primary/20 text-primary text-xs py-2 rounded-lg transition-colors flex items-center justify-center gap-1.5"
        >
          <Bell className="w-3 h-3" /> Enable Browser Push Notifications
        </button>
      )}

      {/* Recent Pushes */}
      <div className="flex-1 overflow-auto">
        <div className="text-[10px] text-muted-foreground uppercase mb-2">Recent Notifications</div>
        <div className="space-y-1.5">
          {RECENT_PUSHES.map((push) => (
            <div key={push.id} className="flex items-center gap-2 bg-white/[0.02] rounded-lg px-2.5 py-2">
              <div className="w-6 h-6 rounded bg-rose-500/15 flex items-center justify-center shrink-0">
                <Bell className="w-3 h-3 text-rose-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium truncate">{push.title}</div>
                <div className="text-[10px] text-muted-foreground">{push.delivered}/{push.sent} delivered · {push.time}</div>
              </div>
              <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
            </div>
          ))}
        </div>
      </div>

      {/* Quick Send */}
      <button
        onClick={() => navigate('/push-notifications')}
        className="mt-3 w-full text-xs text-center py-2 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary transition-colors flex items-center justify-center gap-1.5"
      >
        <Send className="w-3 h-3" /> Send New Notification
      </button>
    </div>
  );
}
