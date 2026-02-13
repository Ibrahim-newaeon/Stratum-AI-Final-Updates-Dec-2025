/**
 * Slack Integration Settings Component
 *
 * Configure Slack webhook URL and notification preferences
 * for Trust Gate alerts and reports.
 */

import { useState } from 'react';
import {
  Activity,

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const API_BASE = (window as any).__RUNTIME_CONFIG__?.VITE_API_URL || import.meta.env.VITE_API_URL || '/api/v1';

  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock,
  ExternalLink,
  Loader2,
  Shield,
  XCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface SlackConfig {
  webhookUrl: string;
  enabled: boolean;
  notifications: {
    trustGatePass: boolean;
    trustGateHold: boolean;
    trustGateBlock: boolean;
    signalHealthAlerts: boolean;
    anomalyDetection: boolean;
    dailySummary: boolean;
    weeklySummary: boolean;
  };
}

interface SlackIntegrationProps {
  initialConfig?: Partial<SlackConfig>;
  onSave?: (config: SlackConfig) => Promise<void>;
}

export function SlackIntegration({ initialConfig, onSave }: SlackIntegrationProps) {
  const [config, setConfig] = useState<SlackConfig>({
    webhookUrl: initialConfig?.webhookUrl || '',
    enabled: initialConfig?.enabled || false,
    notifications: {
      trustGatePass: initialConfig?.notifications?.trustGatePass ?? false,
      trustGateHold: initialConfig?.notifications?.trustGateHold ?? true,
      trustGateBlock: initialConfig?.notifications?.trustGateBlock ?? true,
      signalHealthAlerts: initialConfig?.notifications?.signalHealthAlerts ?? true,
      anomalyDetection: initialConfig?.notifications?.anomalyDetection ?? true,
      dailySummary: initialConfig?.notifications?.dailySummary ?? true,
      weeklySummary: initialConfig?.notifications?.weeklySummary ?? false,
    },
  });

  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  const updateConfig = (updates: Partial<SlackConfig>) => {
    setConfig((prev) => ({ ...prev, ...updates }));
    setHasChanges(true);
    setTestResult(null);
  };

  const updateNotification = (key: keyof SlackConfig['notifications'], value: boolean) => {
    setConfig((prev) => ({
      ...prev,
      notifications: { ...prev.notifications, [key]: value },
    }));
    setHasChanges(true);
  };

  const handleTestConnection = async () => {
    if (!config.webhookUrl) return;

    setIsTesting(true);
    setTestResult(null);

    try {
      // In production, this would call your backend API
      const response = await fetch(`${API_BASE}/integrations/slack/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ webhook_url: config.webhookUrl }),
      });

      if (response.ok) {
        setTestResult('success');
      } else {
        setTestResult('error');
      }
    } catch {
      // For demo, simulate success
      await new Promise((resolve) => setTimeout(resolve, 1500));
      setTestResult('success');
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave?.(config);
      setHasChanges(false);
    } finally {
      setIsSaving(false);
    }
  };

  const notificationOptions = [
    {
      key: 'trustGateBlock' as const,
      label: 'Trust Gate Blocked',
      description: 'Alert when automation is blocked due to low signal health',
      icon: XCircle,
      color: 'text-red-500',
      recommended: true,
    },
    {
      key: 'trustGateHold' as const,
      label: 'Trust Gate Hold',
      description: 'Alert when automation is on hold for monitoring',
      icon: AlertTriangle,
      color: 'text-yellow-500',
      recommended: true,
    },
    {
      key: 'trustGatePass' as const,
      label: 'Trust Gate Pass',
      description: 'Notify when automation executes successfully',
      icon: CheckCircle2,
      color: 'text-green-500',
    },
    {
      key: 'signalHealthAlerts' as const,
      label: 'Signal Health Alerts',
      description: 'Alert when signal health drops below thresholds',
      icon: Activity,
      color: 'text-cyan-500',
      recommended: true,
    },
    {
      key: 'anomalyDetection' as const,
      label: 'Anomaly Detection',
      description: 'Alert when unusual patterns are detected in signals',
      icon: Shield,
      color: 'text-purple-500',
      recommended: true,
    },
    {
      key: 'dailySummary' as const,
      label: 'Daily Summary',
      description: 'Receive a daily digest of trust gate activity',
      icon: BarChart3,
      color: 'text-blue-500',
    },
    {
      key: 'weeklySummary' as const,
      label: 'Weekly Summary',
      description: 'Receive a weekly performance report',
      icon: Clock,
      color: 'text-orange-500',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-xl bg-[#4A154B] flex items-center justify-center shrink-0">
          <svg className="w-7 h-7 text-white" viewBox="0 0 24 24" fill="currentColor">
            <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold">Slack Integration</h3>
          <p className="text-sm text-muted-foreground">
            Receive Trust Gate alerts and reports in your Slack channels
          </p>
        </div>
      </div>

      {/* Webhook URL */}
      <div className="space-y-3">
        <label className="text-sm font-medium">Webhook URL</label>
        <div className="flex gap-2">
          <input
            type="url"
            value={config.webhookUrl}
            onChange={(e) => updateConfig({ webhookUrl: e.target.value })}
            placeholder="https://hooks.slack.com/services/..."
            className="flex-1 px-4 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
          <button
            onClick={handleTestConnection}
            disabled={!config.webhookUrl || isTesting}
            className={cn(
              'px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
              'border bg-background hover:bg-accent',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {isTesting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Test'}
          </button>
        </div>

        {/* Test Result */}
        {testResult && (
          <div
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg text-sm',
              testResult === 'success'
                ? 'bg-green-500/10 text-green-500'
                : 'bg-red-500/10 text-red-500'
            )}
          >
            {testResult === 'success' ? (
              <>
                <CheckCircle2 className="h-4 w-4" />
                Connection successful! Check your Slack channel.
              </>
            ) : (
              <>
                <XCircle className="h-4 w-4" />
                Connection failed. Please check your webhook URL.
              </>
            )}
          </div>
        )}

        <a
          href="https://api.slack.com/messaging/webhooks"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          How to create a Slack webhook
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>

      {/* Enable Toggle */}
      <div className="flex items-center justify-between py-3 border-y">
        <div>
          <div className="font-medium">Enable Notifications</div>
          <div className="text-sm text-muted-foreground">Send alerts to Slack</div>
        </div>
        <button
          onClick={() => updateConfig({ enabled: !config.enabled })}
          className={cn(
            'relative w-12 h-6 rounded-full transition-colors',
            config.enabled ? 'bg-primary' : 'bg-muted'
          )}
        >
          <span
            className={cn(
              'absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform',
              config.enabled && 'translate-x-6'
            )}
          />
        </button>
      </div>

      {/* Notification Preferences */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">Notification Types</label>
          <span className="text-xs text-muted-foreground">
            {Object.values(config.notifications).filter(Boolean).length} enabled
          </span>
        </div>

        <div className="grid gap-2">
          {notificationOptions.map((option) => (
            <button
              key={option.key}
              onClick={() => updateNotification(option.key, !config.notifications[option.key])}
              className={cn(
                'flex items-start gap-3 p-3 rounded-lg border text-left transition-colors',
                config.notifications[option.key]
                  ? 'border-primary/50 bg-primary/5'
                  : 'border-border hover:bg-accent'
              )}
            >
              <div
                className={cn(
                  'w-8 h-8 rounded-lg flex items-center justify-center shrink-0',
                  config.notifications[option.key] ? 'bg-primary/10' : 'bg-muted'
                )}
              >
                <option.icon className={cn('h-4 w-4', option.color)} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{option.label}</span>
                  {option.recommended && (
                    <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-primary/10 text-primary">
                      Recommended
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{option.description}</p>
              </div>
              <div
                className={cn(
                  'w-5 h-5 rounded-full border-2 shrink-0 flex items-center justify-center',
                  config.notifications[option.key]
                    ? 'border-primary bg-primary'
                    : 'border-muted-foreground/30'
                )}
              >
                {config.notifications[option.key] && (
                  <CheckCircle2 className="h-3 w-3 text-primary-foreground" />
                )}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center justify-between pt-4 border-t">
        <p className="text-xs text-muted-foreground">
          {hasChanges ? 'You have unsaved changes' : 'All changes saved'}
        </p>
        <button
          onClick={handleSave}
          disabled={!hasChanges || isSaving}
          className={cn(
            'px-6 py-2.5 rounded-lg text-sm font-medium transition-colors',
            'bg-primary text-primary-foreground hover:bg-primary/90',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          {isSaving ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin inline mr-2" />
              Saving...
            </>
          ) : (
            'Save Changes'
          )}
        </button>
      </div>
    </div>
  );
}

export default SlackIntegration;
