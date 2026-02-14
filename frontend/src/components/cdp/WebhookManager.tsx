/**
 * CDP Webhook Manager Component
 * Create and manage webhook destinations for CDP events
 */

import { useState } from 'react';
import {
  CheckCircle2,
  ChevronRight,
  Copy,
  ExternalLink,
  Eye,
  EyeOff,
  Loader2,
  Play,
  Plus,
  RefreshCw,
  Save,
  Search,
  Settings,
  Shield,
  Trash2,
  Webhook,
  XCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  CDPWebhook,
  useCDPWebhooks,
  useCreateWebhook,
  useDeleteWebhook,
  useRotateWebhookSecret,
  useTestWebhook,
  useUpdateWebhook,
  WebhookEventType,
} from '@/api/cdp';

// Available event types
const EVENT_TYPES: { value: WebhookEventType; label: string; description: string }[] = [
  {
    value: 'event.received',
    label: 'Event Received',
    description: 'Triggered when a new event is ingested',
  },
  {
    value: 'profile.created',
    label: 'Profile Created',
    description: 'Triggered when a new profile is created',
  },
  {
    value: 'profile.updated',
    label: 'Profile Updated',
    description: 'Triggered when a profile is updated',
  },
  {
    value: 'profile.merged',
    label: 'Profile Merged',
    description: 'Triggered when profiles are merged',
  },
  {
    value: 'consent.updated',
    label: 'Consent Updated',
    description: 'Triggered when consent is granted/revoked',
  },
  { value: 'all', label: 'All Events', description: 'Receive all event types' },
];

interface WebhookFormProps {
  webhook?: CDPWebhook;
  onSave: () => void;
  onCancel: () => void;
}

function WebhookForm({ webhook, onSave, onCancel }: WebhookFormProps) {
  const [name, setName] = useState(webhook?.name || '');
  const [url, setUrl] = useState(webhook?.url || '');
  const [eventTypes, setEventTypes] = useState<WebhookEventType[]>(webhook?.event_types || []);
  const [maxRetries, setMaxRetries] = useState(webhook?.max_retries || 3);
  const [timeoutSeconds, setTimeoutSeconds] = useState(webhook?.timeout_seconds || 30);

  const createMutation = useCreateWebhook();
  const updateMutation = useUpdateWebhook();

  const toggleEventType = (type: WebhookEventType) => {
    if (type === 'all') {
      setEventTypes(['all']);
      return;
    }

    // Remove 'all' if selecting specific types
    const filteredTypes = eventTypes.filter((t) => t !== 'all');

    if (filteredTypes.includes(type)) {
      setEventTypes(filteredTypes.filter((t) => t !== type));
    } else {
      setEventTypes([...filteredTypes, type]);
    }
  };

  const handleSubmit = async () => {
    try {
      if (webhook) {
        await updateMutation.mutateAsync({
          webhookId: webhook.id,
          update: {
            name,
            url,
            event_types: eventTypes,
            max_retries: maxRetries,
            timeout_seconds: timeoutSeconds,
          },
        });
      } else {
        await createMutation.mutateAsync({
          name,
          url,
          event_types: eventTypes,
          max_retries: maxRetries,
          timeout_seconds: timeoutSeconds,
        });
      }
      onSave();
    } catch (error) {
      // Error handled by mutation
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;
  const isValid = name && url && eventTypes.length > 0;

  return (
    <div className="space-y-6">
      {/* Basic info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1.5">Webhook Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., CRM Sync Webhook"
            className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1.5">Endpoint URL</label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://your-app.com/webhooks/cdp"
            className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </div>

      {/* Event types */}
      <div>
        <label className="block text-sm font-medium mb-3">Event Types</label>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {EVENT_TYPES.map((type) => (
            <div
              key={type.value}
              className={cn(
                'p-3 rounded-lg border cursor-pointer transition-all',
                eventTypes.includes(type.value)
                  ? 'border-primary bg-primary/5'
                  : 'hover:border-primary/50'
              )}
              onClick={() => toggleEventType(type.value)}
            >
              <div className="flex items-center gap-2 mb-1">
                <div
                  className={cn(
                    'w-4 h-4 rounded border flex items-center justify-center',
                    eventTypes.includes(type.value)
                      ? 'bg-primary border-primary'
                      : 'border-muted-foreground/50'
                  )}
                >
                  {eventTypes.includes(type.value) && (
                    <CheckCircle2 className="w-3 h-3 text-primary-foreground" />
                  )}
                </div>
                <span className="font-medium text-sm">{type.label}</span>
              </div>
              <p className="text-xs text-muted-foreground">{type.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Advanced settings */}
      <div className="p-4 rounded-lg border bg-muted/30">
        <h4 className="font-medium mb-3 flex items-center gap-2">
          <Settings className="w-4 h-4" />
          Advanced Settings
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">Max Retries</label>
            <select
              value={maxRetries}
              onChange={(e) => setMaxRetries(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-lg border bg-background"
            >
              <option value={0}>No retries</option>
              <option value={1}>1 retry</option>
              <option value={3}>3 retries</option>
              <option value={5}>5 retries</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Timeout (seconds)</label>
            <select
              value={timeoutSeconds}
              onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-lg border bg-background"
            >
              <option value={10}>10 seconds</option>
              <option value={30}>30 seconds</option>
              <option value={60}>60 seconds</option>
              <option value={120}>120 seconds</option>
            </select>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 pt-4 border-t">
        <button
          onClick={onCancel}
          className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={!isValid || isLoading}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {webhook ? 'Update Webhook' : 'Create Webhook'}
        </button>
      </div>
    </div>
  );
}

interface WebhookDetailProps {
  webhook: CDPWebhook;
  onBack: () => void;
  onRefresh: () => void;
}

function WebhookDetail({ webhook, onBack, onRefresh }: WebhookDetailProps) {
  const [showSecret, setShowSecret] = useState(false);
  const [copiedSecret, setCopiedSecret] = useState(false);

  const testMutation = useTestWebhook();
  const rotateMutation = useRotateWebhookSecret();
  const updateMutation = useUpdateWebhook();

  const handleTest = async () => {
    await testMutation.mutateAsync(webhook.id);
  };

  const handleRotateSecret = async () => {
    if (
      confirm(
        'Are you sure you want to rotate the secret key? This will invalidate the current key.'
      )
    ) {
      await rotateMutation.mutateAsync(webhook.id);
      onRefresh();
    }
  };

  const handleToggleActive = async () => {
    await updateMutation.mutateAsync({
      webhookId: webhook.id,
      update: { is_active: !webhook.is_active },
    });
    onRefresh();
  };

  const copySecret = () => {
    if (webhook.secret_key) {
      navigator.clipboard.writeText(webhook.secret_key);
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
    }
  };

  const testResult = testMutation.data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-2 rounded-lg hover:bg-muted transition-colors">
            <ChevronRight className="w-5 h-5 rotate-180" />
          </button>
          <div>
            <h2 className="text-xl font-semibold">{webhook.name}</h2>
            <p className="text-sm text-muted-foreground flex items-center gap-1">
              <ExternalLink className="w-3 h-3" />
              {webhook.url}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleToggleActive}
            disabled={updateMutation.isPending}
            className={cn(
              'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              webhook.is_active
                ? 'bg-green-500/10 text-green-500 hover:bg-green-500/20'
                : 'bg-gray-500/10 text-gray-500 hover:bg-gray-500/20'
            )}
          >
            {webhook.is_active ? 'Active' : 'Inactive'}
          </button>
        </div>
      </div>

      {/* Test webhook */}
      <div className="p-4 rounded-xl border bg-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium flex items-center gap-2">
            <Play className="w-4 h-4" />
            Test Webhook
          </h3>
          <button
            onClick={handleTest}
            disabled={testMutation.isPending}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 text-sm font-medium transition-colors"
          >
            {testMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            Send Test
          </button>
        </div>
        {testResult && (
          <div
            className={cn(
              'p-3 rounded-lg flex items-center gap-3',
              testResult.success ? 'bg-green-500/10' : 'bg-red-500/10'
            )}
          >
            {testResult.success ? (
              <CheckCircle2 className="w-5 h-5 text-green-500" />
            ) : (
              <XCircle className="w-5 h-5 text-red-500" />
            )}
            <div>
              <div className="font-medium">
                {testResult.success ? 'Test Successful' : 'Test Failed'}
              </div>
              <div className="text-sm text-muted-foreground">
                {testResult.success
                  ? `Status ${testResult.status_code} · ${testResult.response_time_ms}ms`
                  : testResult.error}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Secret key */}
      <div className="p-4 rounded-xl border bg-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium flex items-center gap-2">
            <Shield className="w-4 h-4" />
            Secret Key
          </h3>
          <button
            onClick={handleRotateSecret}
            disabled={rotateMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border hover:bg-muted text-sm font-medium transition-colors"
          >
            {rotateMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Rotate Secret
          </button>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 px-3 py-2 rounded-md bg-muted font-mono text-sm">
            {showSecret ? webhook.secret_key || 'Secret not available' : '••••••••••••••••••••••••'}
          </div>
          <button
            onClick={() => setShowSecret(!showSecret)}
            className="p-2 rounded-md hover:bg-muted transition-colors"
          >
            {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
          <button
            onClick={copySecret}
            disabled={!webhook.secret_key}
            className="p-2 rounded-md hover:bg-muted transition-colors"
          >
            {copiedSecret ? (
              <CheckCircle2 className="w-4 h-4 text-green-500" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          Use this secret to verify webhook signatures using HMAC-SHA256
        </p>
      </div>

      {/* Event types */}
      <div className="p-4 rounded-xl border bg-card">
        <h3 className="font-medium mb-3">Subscribed Events</h3>
        <div className="flex flex-wrap gap-2">
          {webhook.event_types.map((type) => (
            <span
              key={type}
              className="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium"
            >
              {type}
            </span>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground">Last Triggered</div>
          <div className="font-semibold">
            {webhook.last_triggered_at
              ? new Date(webhook.last_triggered_at).toLocaleDateString()
              : 'Never'}
          </div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground">Last Success</div>
          <div className="font-semibold text-green-500">
            {webhook.last_success_at
              ? new Date(webhook.last_success_at).toLocaleDateString()
              : 'Never'}
          </div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground">Last Failure</div>
          <div className="font-semibold text-red-500">
            {webhook.last_failure_at
              ? new Date(webhook.last_failure_at).toLocaleDateString()
              : 'Never'}
          </div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground">Failure Count</div>
          <div className={cn('font-semibold', webhook.failure_count > 0 ? 'text-amber-500' : '')}>
            {webhook.failure_count}
          </div>
        </div>
      </div>

      {/* Configuration */}
      <div className="p-4 rounded-xl border bg-muted/30">
        <h3 className="font-medium mb-3">Configuration</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Max Retries:</span>
            <span className="font-medium ml-2">{webhook.max_retries}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Timeout:</span>
            <span className="font-medium ml-2">{webhook.timeout_seconds}s</span>
          </div>
          <div>
            <span className="text-muted-foreground">Created:</span>
            <span className="font-medium ml-2">
              {new Date(webhook.created_at).toLocaleDateString()}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Updated:</span>
            <span className="font-medium ml-2">
              {new Date(webhook.updated_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function WebhookManager() {
  const [showForm, setShowForm] = useState(false);
  const [selectedWebhook, setSelectedWebhook] = useState<CDPWebhook | null>(null);
  const [viewingWebhook, setViewingWebhook] = useState<CDPWebhook | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const { data: webhooksData, isLoading, refetch } = useCDPWebhooks();
  const deleteMutation = useDeleteWebhook();

  const webhooks = webhooksData?.webhooks || [];
  const filteredWebhooks = webhooks.filter(
    (w) =>
      w.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      w.url.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleEdit = (webhook: CDPWebhook) => {
    setSelectedWebhook(webhook);
    setShowForm(true);
  };

  const handleDelete = async (webhookId: string) => {
    if (confirm('Are you sure you want to delete this webhook?')) {
      await deleteMutation.mutateAsync(webhookId);
      refetch();
    }
  };

  const handleFormSave = () => {
    setShowForm(false);
    setSelectedWebhook(null);
    refetch();
  };

  const getStatusIndicator = (webhook: CDPWebhook) => {
    if (!webhook.is_active) {
      return <span className="w-2 h-2 rounded-full bg-gray-400" />;
    }
    if (webhook.failure_count > 5) {
      return <span className="w-2 h-2 rounded-full bg-red-500" />;
    }
    if (webhook.failure_count > 0) {
      return <span className="w-2 h-2 rounded-full bg-amber-500" />;
    }
    return <span className="w-2 h-2 rounded-full bg-green-500" />;
  };

  if (viewingWebhook) {
    return (
      <WebhookDetail
        webhook={viewingWebhook}
        onBack={() => setViewingWebhook(null)}
        onRefresh={() => {
          refetch();
          // Refresh the viewing webhook
          const updated = webhooks.find((w) => w.id === viewingWebhook.id);
          if (updated) setViewingWebhook(updated);
        }}
      />
    );
  }

  if (showForm) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setShowForm(false);
              setSelectedWebhook(null);
            }}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <ChevronRight className="w-5 h-5 rotate-180" />
          </button>
          <h2 className="text-xl font-semibold">
            {selectedWebhook ? 'Edit Webhook' : 'Create Webhook'}
          </h2>
        </div>
        <WebhookForm
          webhook={selectedWebhook || undefined}
          onSave={handleFormSave}
          onCancel={() => {
            setShowForm(false);
            setSelectedWebhook(null);
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Webhook className="w-6 h-6 text-primary" />
            Webhook Manager
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Configure webhook destinations for CDP events
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Webhook
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search webhooks..."
          className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
        />
      </div>

      {/* Webhooks list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : filteredWebhooks.length === 0 ? (
        <div className="text-center py-12 bg-card border rounded-xl">
          <Webhook className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="font-semibold mb-2">No webhooks configured</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Create a webhook to receive CDP events in real-time
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Webhook
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                  Status
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                  Name
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                  URL
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                  Events
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                  Last Triggered
                </th>
                <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredWebhooks.map((webhook) => (
                <tr
                  key={webhook.id}
                  className="border-b hover:bg-muted/30 cursor-pointer"
                  onClick={() => setViewingWebhook(webhook)}
                >
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      {getStatusIndicator(webhook)}
                      <span
                        className={cn(
                          'text-xs font-medium',
                          webhook.is_active ? 'text-green-500' : 'text-gray-500'
                        )}
                      >
                        {webhook.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-4 font-medium">{webhook.name}</td>
                  <td className="py-3 px-4">
                    <span className="text-sm text-muted-foreground truncate max-w-[200px] block">
                      {webhook.url}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex flex-wrap gap-1">
                      {webhook.event_types.slice(0, 2).map((type) => (
                        <span key={type} className="px-2 py-0.5 rounded-full bg-muted text-xs">
                          {type}
                        </span>
                      ))}
                      {webhook.event_types.length > 2 && (
                        <span className="px-2 py-0.5 rounded-full bg-muted text-xs">
                          +{webhook.event_types.length - 2}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-sm text-muted-foreground">
                    {webhook.last_triggered_at
                      ? new Date(webhook.last_triggered_at).toLocaleDateString()
                      : 'Never'}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div
                      className="flex items-center justify-end gap-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        onClick={() => handleEdit(webhook)}
                        className="p-1.5 rounded-md hover:bg-muted transition-colors"
                        title="Edit"
                      >
                        <Settings className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(webhook.id)}
                        className="p-1.5 rounded-md hover:bg-red-500/10 text-muted-foreground hover:text-red-500 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default WebhookManager;
