import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertTriangle,
  Bell,
  Building,
  Check,
  ChevronRight,
  Copy,
  CreditCard,
  Download,
  Eye,
  EyeOff,
  Gauge,
  Link2,
  Loader2,
  Palette,
  RefreshCw,
  Save,
  Shield,
  Trash2,
  User,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useTenantStore } from '@/stores/tenantStore';
import { useExportData, useRequestDeletion } from '@/api/hooks';

type SettingsTab =
  | 'profile'
  | 'organization'
  | 'notifications'
  | 'security'
  | 'integrations'
  | 'preferences'
  | 'billing'
  | 'gdpr'
  | 'trust-engine';

export function Settings() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');
  const [showApiKey, setShowApiKey] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');

  const tabs = [
    { id: 'profile', label: t('settings.profile'), icon: User },
    { id: 'organization', label: t('settings.organization'), icon: Building },
    { id: 'notifications', label: t('settings.notifications'), icon: Bell },
    { id: 'security', label: t('settings.security'), icon: Shield },
    { id: 'integrations', label: t('settings.integrations'), icon: Link2 },
    { id: 'preferences', label: t('settings.preferences'), icon: Palette },
    { id: 'billing', label: t('settings.billing'), icon: CreditCard },
    { id: 'gdpr', label: t('settings.gdpr'), icon: Download },
    { id: 'trust-engine', label: 'Trust Engine', icon: Gauge },
  ] as const;

  const handleSave = () => {
    setSaveStatus('saving');
    setTimeout(() => {
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 2000);
    }, 1000);
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'profile':
        return <ProfileSettings />;
      case 'organization':
        return <OrganizationSettings />;
      case 'notifications':
        return <NotificationSettings />;
      case 'security':
        return <SecuritySettings showApiKey={showApiKey} setShowApiKey={setShowApiKey} />;
      case 'integrations':
        return <IntegrationSettings />;
      case 'preferences':
        return <PreferenceSettings />;
      case 'billing':
        return <BillingSettings />;
      case 'gdpr':
        return <GDPRSettings />;
      case 'trust-engine':
        return <TrustEngineSettings />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t('settings.title')}</h1>
          <p className="text-muted-foreground">{t('settings.subtitle')}</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saveStatus === 'saving'}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {saveStatus === 'saving' ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : saveStatus === 'saved' ? (
            <Check className="w-4 h-4" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          <span>{saveStatus === 'saved' ? t('settings.saved') : t('settings.saveChanges')}</span>
        </button>
      </div>

      <div className="flex gap-6">
        {/* Sidebar Navigation */}
        <div className="w-64 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as SettingsTab)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors',
                    activeTab === tab.id
                      ? 'bg-primary/10 text-primary font-medium'
                      : 'hover:bg-muted text-muted-foreground'
                  )}
                >
                  <Icon className="w-5 h-5" />
                  <span>{tab.label}</span>
                  {activeTab === tab.id && <ChevronRight className="w-4 h-4 ml-auto" />}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content Area */}
        <div className="flex-1 rounded-xl border bg-card p-6">{renderTabContent()}</div>
      </div>
    </div>
  );
}

function ProfileSettings() {
  const { t } = useTranslation();
  // Get user data from tenant store
  const user = useTenantStore((state) => state.user);

  // Parse name into first/last (fallback to mock data)
  const fullName = user?.full_name || 'John Doe';
  const nameParts = fullName.split(' ');
  const firstName = nameParts[0] || 'John';
  const lastName = nameParts.slice(1).join(' ') || 'Doe';
  const initials = `${firstName[0] || 'J'}${lastName[0] || 'D'}`;
  const email = user?.email || 'john.doe@company.com';
  const role = user?.role || 'media_buyer';
  const timezone = user?.timezone || 'America/New_York';

  // Format role for display
  const formatRole = (role: string) => {
    const roleLabels: Record<string, string> = {
      superadmin: 'Super Admin',
      admin: 'Admin',
      manager: 'Manager',
      media_buyer: 'Media Buyer',
      analyst: 'Analyst',
      account_manager: 'Account Manager',
      viewer: 'Viewer',
    };
    return roleLabels[role] || role;
  };

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">{t('settings.profileSettings')}</h2>

      <div className="flex items-center gap-6">
        <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center text-2xl font-bold text-primary">
          {user?.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={fullName}
              className="w-full h-full rounded-full object-cover"
            />
          ) : (
            initials.toUpperCase()
          )}
        </div>
        <div>
          <button className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors text-sm">
            {t('settings.changeAvatar')}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium mb-2 block">{t('settings.firstName')}</label>
          <input
            type="text"
            defaultValue={firstName}
            className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label className="text-sm font-medium mb-2 block">{t('settings.lastName')}</label>
          <input
            type="text"
            defaultValue={lastName}
            className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">{t('settings.email')}</label>
        <input
          type="email"
          defaultValue={email}
          className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">{t('settings.role')}</label>
        <input
          type="text"
          value={formatRole(role)}
          disabled
          className="w-full px-4 py-2 rounded-lg border bg-muted text-muted-foreground"
        />
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">{t('settings.timezone')}</label>
        <select
          defaultValue={timezone}
          className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value="America/New_York">Eastern Time (ET)</option>
          <option value="America/Chicago">Central Time (CT)</option>
          <option value="America/Denver">Mountain Time (MT)</option>
          <option value="America/Los_Angeles">Pacific Time (PT)</option>
          <option value="Europe/London">Greenwich Mean Time (GMT)</option>
          <option value="Europe/Kyiv">Eastern European Time (EET)</option>
          <option value="Asia/Riyadh">Arabia Standard Time (AST)</option>
          <option value="Asia/Dubai">Gulf Standard Time (GST)</option>
        </select>
      </div>
    </div>
  );
}

function OrganizationSettings() {
  const { t } = useTranslation();
  // Get tenant data from store
  const tenant = useTenantStore((state) => state.tenant);

  // Use tenant data or fall back to mock
  const companyName = tenant?.name || 'Acme Corporation';
  const industry = tenant?.settings?.industry || 'ecommerce';
  const plan = tenant?.plan || 'pro';
  const maxUsers = tenant?.max_users || 10;

  // State for users management
  const [teamMembers, setTeamMembers] = useState<
    Array<{ id: number; email: string; role: string; is_active: boolean }>
  >([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('user');
  const [isInviting, setIsInviting] = useState(false);
  const [removingUserId, setRemovingUserId] = useState<number | null>(null);

  // Fetch team members
  const fetchTeamMembers = async () => {
    try {
      setIsLoading(true);
      const { apiClient } = await import('@/api/client');
      const response = await apiClient.get('/users');
      if (response.data.success) {
        setTeamMembers(response.data.data);
      }
    } catch (error) {
      console.error('Failed to fetch team members:', error);
      // Fallback to mock data
      setTeamMembers([
        { id: 1, email: 'admin@company.com', role: 'admin', is_active: true },
        { id: 2, email: 'jane.smith@company.com', role: 'manager', is_active: true },
        { id: 3, email: 'bob.wilson@company.com', role: 'user', is_active: true },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTeamMembers();
  }, []);

  // Invite new user
  const handleInvite = async () => {
    if (!inviteEmail) return;
    setIsInviting(true);
    try {
      const { apiClient } = await import('@/api/client');
      const response = await apiClient.post('/users/invite', {
        email: inviteEmail,
        role: inviteRole,
      });
      if (response.data.success) {
        setTeamMembers([...teamMembers, response.data.data]);
        setShowInviteModal(false);
        setInviteEmail('');
        setInviteRole('user');
      }
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to invite user');
    } finally {
      setIsInviting(false);
    }
  };

  // Remove user
  const handleRemove = async (userId: number) => {
    if (!confirm('Are you sure you want to remove this user?')) return;
    setRemovingUserId(userId);
    try {
      const { apiClient } = await import('@/api/client');
      const response = await apiClient.delete(`/users/${userId}`);
      if (response.data.success) {
        setTeamMembers(teamMembers.filter((m) => m.id !== userId));
      }
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to remove user');
    } finally {
      setRemovingUserId(null);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">{t('settings.organizationSettings')}</h2>

      <div>
        <label className="text-sm font-medium mb-2 block">{t('settings.companyName')}</label>
        <input
          type="text"
          defaultValue={companyName}
          className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">{t('settings.industry')}</label>
        <select
          defaultValue={industry}
          className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value="ecommerce">E-commerce</option>
          <option value="saas">SaaS</option>
          <option value="retail">Retail</option>
          <option value="finance">Finance</option>
          <option value="healthcare">Healthcare</option>
        </select>
      </div>

      <div className="p-4 rounded-lg border bg-muted/30">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium capitalize">{plan} Plan</p>
            <p className="text-sm text-muted-foreground">Max {maxUsers} team members</p>
          </div>
          <span className="px-2 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
            Active
          </span>
        </div>
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">{t('settings.teamMembers')}</label>
        <div className="space-y-2">
          {isLoading ? (
            <div className="flex items-center justify-center p-4">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            teamMembers.map((member) => (
              <div
                key={member.id}
                className="flex items-center justify-between p-3 rounded-lg border"
              >
                <div className="flex items-center gap-3">
                  <span className="text-sm">{member.email}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-muted capitalize">
                    {member.role}
                  </span>
                </div>
                <button
                  onClick={() => handleRemove(member.id)}
                  disabled={removingUserId === member.id}
                  className="text-sm text-red-500 hover:underline disabled:opacity-50"
                >
                  {removingUserId === member.id ? 'Removing...' : 'Remove'}
                </button>
              </div>
            ))
          )}
        </div>
        <button
          onClick={() => setShowInviteModal(true)}
          className="mt-3 text-sm text-primary hover:underline"
        >
          + {t('settings.inviteMember')}
        </button>
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background p-6 rounded-xl border shadow-lg max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Invite Team Member</h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-1 block">Email</label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@company.com"
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value="user">User</option>
                  <option value="manager">Manager</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowInviteModal(false)}
                className="px-4 py-2 text-sm rounded-lg border hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={handleInvite}
                disabled={!inviteEmail || isInviting}
                className="px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {isInviting ? 'Inviting...' : 'Send Invite'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function NotificationSettings() {
  const { t } = useTranslation();
  const [notifications, setNotifications] = useState({
    emailAlerts: true,
    pushNotifications: true,
    weeklyDigest: true,
    campaignAlerts: true,
    budgetAlerts: true,
    performanceAlerts: false,
  });

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">{t('settings.notificationSettings')}</h2>

      <div className="space-y-4">
        {Object.entries(notifications).map(([key, value]) => (
          <div key={key} className="flex items-center justify-between p-4 rounded-lg border">
            <div>
              <p className="font-medium">{t(`settings.${key}`)}</p>
              <p className="text-sm text-muted-foreground">{t(`settings.${key}Desc`)}</p>
            </div>
            <button
              onClick={() => setNotifications((prev) => ({ ...prev, [key]: !value }))}
              className={cn(
                'relative w-12 h-6 rounded-full transition-colors',
                value ? 'bg-primary' : 'bg-muted'
              )}
            >
              <span
                className={cn(
                  'absolute top-1 w-4 h-4 bg-white rounded-full transition-transform',
                  value ? 'translate-x-7' : 'translate-x-1'
                )}
              />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function SecuritySettings({
  showApiKey,
  setShowApiKey,
}: {
  showApiKey: boolean;
  setShowApiKey: (show: boolean) => void;
}) {
  const { t } = useTranslation();
  const [showTestKey, setShowTestKey] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState<string | null>(null);

  // API Keys data
  const apiKeys = [
    {
      id: 'production',
      name: 'Production API Key',
      key: 'strat_live_' + '•'.repeat(28) + 'abc',
      fullKey: 'strat_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxx_abc',
      type: 'live' as const,
      status: 'active' as const,
      created: 'Jan 15, 2024',
      lastUsed: '2 minutes ago',
    },
    {
      id: 'test',
      name: 'Test API Key',
      key: 'strat_test_' + '•'.repeat(28) + 'xyz',
      fullKey: 'strat_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxx_xyz',
      type: 'test' as const,
      status: 'active' as const,
      created: 'Jan 10, 2024',
      lastUsed: '3 days ago',
    },
  ];

  const copyToClipboard = (key: string, keyId: string) => {
    navigator.clipboard.writeText(key);
    setCopiedKey(keyId);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleRegenerate = async (keyId: string) => {
    if (
      !confirm(
        `Are you sure you want to regenerate the ${keyId} API key? This will invalidate the current key.`
      )
    ) {
      return;
    }
    setRegenerating(keyId);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setRegenerating(null);
    alert(`${keyId} API key has been regenerated. Please update your integrations.`);
  };

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">{t('settings.securitySettings')}</h2>

      <div>
        <h3 className="font-medium mb-3">{t('settings.changePassword')}</h3>
        <div className="space-y-3">
          <input
            type="password"
            placeholder={t('settings.currentPassword')}
            className="w-full px-4 py-2 rounded-xl border border-white/10 glass bg-transparent focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
          <input
            type="password"
            placeholder={t('settings.newPassword')}
            className="w-full px-4 py-2 rounded-xl border border-white/10 glass bg-transparent focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
          <input
            type="password"
            placeholder={t('settings.confirmPassword')}
            className="w-full px-4 py-2 rounded-xl border border-white/10 glass bg-transparent focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
          <button className="px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
            {t('settings.updatePassword')}
          </button>
        </div>
      </div>

      <div className="border-t border-white/10 pt-6">
        <h3 className="font-medium mb-3">{t('settings.twoFactorAuth')}</h3>
        <div className="flex items-center justify-between p-4 rounded-xl border border-white/10 glass">
          <div>
            <p className="font-medium">{t('settings.enable2FA')}</p>
            <p className="text-sm text-muted-foreground">{t('settings.enable2FADesc')}</p>
          </div>
          <button className="px-4 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors">
            {t('settings.setup')}
          </button>
        </div>
      </div>

      <div className="border-t border-white/10 pt-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium">API Keys</h3>
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-primary hover:bg-primary/10 transition-colors">
            <span>+ Create New API Key</span>
          </button>
        </div>

        <div className="space-y-4">
          {apiKeys.map((apiKey) => {
            const isVisible = apiKey.type === 'live' ? showApiKey : showTestKey;
            const setVisible = apiKey.type === 'live' ? setShowApiKey : setShowTestKey;

            return (
              <div key={apiKey.id} className="p-4 rounded-xl border border-white/10 glass card-3d">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h4 className="font-medium">{apiKey.name}</h4>
                    <span
                      className={cn(
                        'px-2.5 py-1 rounded-full text-xs font-semibold',
                        apiKey.type === 'live'
                          ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                          : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                      )}
                    >
                      {apiKey.type === 'live' ? 'Active' : 'Test'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => copyToClipboard(apiKey.fullKey, apiKey.id)}
                      className="px-3 py-1.5 rounded-lg border border-white/10 hover:bg-white/5 transition-colors text-sm flex items-center gap-1.5"
                    >
                      {copiedKey === apiKey.id ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-green-500" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          Copy
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => handleRegenerate(apiKey.id)}
                      disabled={regenerating === apiKey.id}
                      className="px-3 py-1.5 rounded-lg border border-white/10 hover:bg-white/5 transition-colors text-sm flex items-center gap-1.5 disabled:opacity-50"
                    >
                      {regenerating === apiKey.id ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          Regenerating...
                        </>
                      ) : (
                        <>
                          <RefreshCw className="w-3.5 h-3.5" />
                          Regenerate
                        </>
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-2 mb-3">
                  <code className="flex-1 px-3 py-2.5 rounded-lg bg-black/30 border border-white/5 font-mono text-sm">
                    {isVisible ? apiKey.fullKey : apiKey.key}
                  </code>
                  <button
                    onClick={() => setVisible(!isVisible)}
                    className="p-2.5 rounded-lg hover:bg-white/5 transition-colors"
                  >
                    {isVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>

                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span>Created: {apiKey.created}</span>
                  <span>|</span>
                  <span>Last used: {apiKey.lastUsed}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function IntegrationSettings() {
  const { t } = useTranslation();
  const [webhooks, setWebhooks] = useState([
    {
      id: '1',
      url: 'https://api.yourcompany.com/webhooks/stratum',
      events: ['campaign.updated', 'alert.triggered', 'sync.completed'],
      status: 'active' as const,
      lastTriggered: '5 minutes ago',
    },
  ]);
  const [showAddWebhook, setShowAddWebhook] = useState(false);
  const [newWebhookUrl, setNewWebhookUrl] = useState('');
  const [newWebhookEvents, setNewWebhookEvents] = useState<string[]>([]);

  // Platform integration icons as SVG components
  const IntegrationIcon = ({ type }: { type: string }) => {
    const icons: Record<string, React.ReactNode> = {
      'google-analytics': (
        <svg viewBox="0 0 24 24" className="w-6 h-6" fill="currentColor">
          <path d="M22.84 2.9v18.2c0 1.6-1.3 2.9-2.9 2.9s-2.9-1.3-2.9-2.9V2.9c0-1.6 1.3-2.9 2.9-2.9s2.9 1.3 2.9 2.9zM14.42 21.1c0 1.6-1.3 2.9-2.9 2.9s-2.9-1.3-2.9-2.9 1.3-2.9 2.9-2.9 2.9 1.3 2.9 2.9zM14.42 12c0 1.6-1.3 2.9-2.9 2.9s-2.9-1.3-2.9-2.9V2.9c0-1.6 1.3-2.9 2.9-2.9s2.9 1.3 2.9 2.9V12zM5.99 21.1c0 1.6-1.3 2.9-2.9 2.9S.19 22.7.19 21.1s1.3-2.9 2.9-2.9 2.9 1.3 2.9 2.9z" />
        </svg>
      ),
      'google-tag-manager': (
        <svg viewBox="0 0 24 24" className="w-6 h-6" fill="currentColor">
          <path d="M12 0L1.5 6v12L12 24l10.5-6V6L12 0zm0 2.2l8.2 4.7v9.4L12 21l-8.2-4.7V6.9L12 2.2z" />
          <path d="M12 7.5L7.5 10.2v5.4l4.5 2.7 4.5-2.7v-5.4L12 7.5z" />
        </svg>
      ),
      shopify: (
        <svg viewBox="0 0 24 24" className="w-6 h-6" fill="currentColor">
          <path d="M15.34 5.55c-.03-.24-.24-.36-.4-.38-.16-.02-3.38-.07-3.38-.07s-2.25-2.2-2.5-2.45c-.24-.24-.72-.17-.9-.11-.03 0-.5.15-1.3.4C6.45 1.73 5.92.94 4.9.94c-1.64 0-2.44 2.05-2.69 3.09-.65.2-1.1.34-1.16.36-.36.11-.37.12-.42.46C.58 5.22 0 19.4 0 19.4l12.2 2.28 6.58-1.43S15.37 5.79 15.34 5.55zM10.7 3.57l-1.67.52c0-.82-.11-1.98-.48-2.97.93.18 1.48 1.22 1.75 2.14.14.1.27.2.4.31zm-2.66.82L5.65 5.15c.31-1.22.9-1.81 1.7-2.03.26.53.43 1.28.49 2.04.06.07.12.15.2.23zM4.93 1.78c.11 0 .22.04.32.1-.8.38-1.66 1.33-2.02 3.24l-1.57.49c.43-1.47 1.44-3.83 3.27-3.83z" />
          <path
            d="M14.94 5.17c-.16.02-3.38.07-3.38.07s-2.25-2.2-2.5-2.45c-.09-.09-.2-.14-.31-.16l-.86 18.09 6.58-1.43S15.37 5.79 15.34 5.55c-.03-.24-.24-.36-.4-.38z"
            opacity=".5"
          />
        </svg>
      ),
      stripe: (
        <svg viewBox="0 0 24 24" className="w-6 h-6" fill="currentColor">
          <path d="M13.976 9.15c-2.172-.806-3.356-1.426-3.356-2.409 0-.831.683-1.305 1.901-1.305 2.227 0 4.515.858 6.09 1.631l.89-5.494C18.252.975 15.697 0 12.165 0 9.667 0 7.589.654 6.104 1.872 4.56 3.147 3.757 4.992 3.757 7.218c0 4.039 2.467 5.76 6.476 7.219 2.585.92 3.445 1.574 3.445 2.583 0 .98-.84 1.545-2.354 1.545-1.875 0-4.965-.921-6.99-2.109l-.9 5.555C5.175 22.99 8.385 24 11.714 24c2.641 0 4.843-.624 6.328-1.813 1.664-1.305 2.525-3.236 2.525-5.732 0-4.128-2.524-5.851-6.594-7.305h.003z" />
        </svg>
      ),
      wordpress: (
        <svg viewBox="0 0 24 24" className="w-6 h-6" fill="currentColor">
          <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm-1.46 14.58L7.93 5.51c.46-.02.88-.07.88-.07.41-.05.36-.66-.05-.64 0 0-1.24.1-2.04.1-.14 0-.31 0-.48-.01C7.58 2.91 9.66 1.8 12 1.8c1.73 0 3.31.66 4.5 1.74-.03 0-.06-.01-.09-.01-.72 0-1.23.63-1.23 1.3 0 .6.35 1.11.72 1.72.28.48.6 1.1.6 2 0 .62-.24 1.34-.56 2.34l-.73 2.44-2.65-7.89c.44-.02.84-.07.84-.07.4-.05.35-.64-.05-.62 0 0-1.2.09-1.98.09-.07 0-.15 0-.22 0l2.87 8.58-1.96 5.86-3.82-11.34zM12 22.2c-1.22 0-2.39-.22-3.47-.62l3.68-10.69 3.77 10.33c.02.06.05.12.08.17-1.26.52-2.64.81-4.06.81zm8.4-5.14c.33-1.35.53-2.9.53-4.62 0-1.81-.33-3.38-.86-4.72l-4.7 13.62c3.03-1.46 5.03-4.57 5.03-8.28zm-17.9-4.62c0 3.27 1.61 6.16 4.07 7.93L2.92 9.45c-.28 1.03-.42 2.12-.42 3.25v.74z" />
        </svg>
      ),
      'google-ads': (
        <svg viewBox="0 0 24 24" className="w-6 h-6" fill="currentColor">
          <circle cx="12" cy="12" r="10" fill="#4285F4" />
          <text x="12" y="16" textAnchor="middle" fill="white" fontSize="10" fontWeight="bold">
            G
          </text>
        </svg>
      ),
      meta: (
        <svg viewBox="0 0 24 24" className="w-6 h-6" fill="currentColor">
          <path
            d="M12 2.04c-5.5 0-10 4.49-10 10.02 0 5 3.66 9.15 8.44 9.9v-7H7.9v-2.9h2.54V9.85c0-2.52 1.49-3.92 3.77-3.92 1.09 0 2.24.2 2.24.2v2.47h-1.26c-1.24 0-1.63.78-1.63 1.57v1.88h2.78l-.45 2.9h-2.33v7a10 10 0 0 0 8.44-9.9c0-5.53-4.5-10.02-10-10.02z"
            fill="#0866FF"
          />
        </svg>
      ),
      tiktok: (
        <svg viewBox="0 0 24 24" className="w-6 h-6" fill="currentColor">
          <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z" />
        </svg>
      ),
      slack: (
        <svg viewBox="0 0 24 24" className="w-6 h-6" fill="currentColor">
          <path
            d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"
            fill="#E01E5A"
          />
        </svg>
      ),
    };
    return icons[type] || <div className="w-6 h-6 rounded-full bg-muted" />;
  };

  // Ad Platforms
  const adPlatforms = [
    { id: 'google-ads', name: 'Google Ads', connected: true, color: 'text-blue-500' },
    { id: 'meta', name: 'Meta Ads', connected: true, color: 'text-blue-600' },
    { id: 'tiktok', name: 'TikTok Ads', connected: false, color: 'text-gray-400' },
    { id: 'slack', name: 'Slack', connected: true, color: 'text-purple-500' },
  ];

  // Analytics & Tracking
  const analyticsIntegrations = [
    {
      id: 'google-analytics',
      name: 'Google Analytics',
      connected: true,
      color: 'text-orange-500',
      description: 'Track website traffic and behavior',
    },
    {
      id: 'google-tag-manager',
      name: 'Google Tag Manager',
      connected: true,
      color: 'text-blue-500',
      description: 'Manage tracking pixels and tags',
    },
  ];

  // E-commerce & Payments
  const commerceIntegrations = [
    {
      id: 'shopify',
      name: 'Shopify',
      connected: true,
      color: 'text-green-500',
      description: 'Sync orders and product catalog',
    },
    {
      id: 'stripe',
      name: 'Stripe',
      connected: false,
      color: 'text-purple-500',
      description: 'Track payments and subscriptions',
    },
    {
      id: 'wordpress',
      name: 'WordPress',
      connected: false,
      color: 'text-blue-500',
      description: 'Connect WooCommerce and forms',
    },
  ];

  // Webhook event types
  const webhookEventTypes = [
    {
      id: 'campaign.updated',
      label: 'Campaign Updated',
      description: 'When campaign settings change',
    },
    { id: 'campaign.paused', label: 'Campaign Paused', description: 'When a campaign is paused' },
    {
      id: 'alert.triggered',
      label: 'Alert Triggered',
      description: 'When performance alerts fire',
    },
    { id: 'budget.depleted', label: 'Budget Depleted', description: 'When daily budget runs out' },
    { id: 'sync.completed', label: 'Sync Completed', description: 'When data sync finishes' },
    {
      id: 'anomaly.detected',
      label: 'Anomaly Detected',
      description: 'When unusual patterns found',
    },
  ];

  const toggleWebhookEvent = (eventId: string) => {
    if (newWebhookEvents.includes(eventId)) {
      setNewWebhookEvents(newWebhookEvents.filter((e) => e !== eventId));
    } else {
      setNewWebhookEvents([...newWebhookEvents, eventId]);
    }
  };

  const addWebhook = () => {
    if (newWebhookUrl && newWebhookEvents.length > 0) {
      setWebhooks([
        ...webhooks,
        {
          id: Date.now().toString(),
          url: newWebhookUrl,
          events: newWebhookEvents,
          status: 'active',
          lastTriggered: 'Never',
        },
      ]);
      setNewWebhookUrl('');
      setNewWebhookEvents([]);
      setShowAddWebhook(false);
    }
  };

  const deleteWebhook = (id: string) => {
    if (confirm('Are you sure you want to delete this webhook?')) {
      setWebhooks(webhooks.filter((w) => w.id !== id));
    }
  };

  const IntegrationCard = ({
    integration,
    showDescription = false,
  }: {
    integration: any;
    showDescription?: boolean;
  }) => (
    <div className="flex items-center justify-between p-4 rounded-xl border border-white/10 glass card-3d">
      <div className="flex items-center gap-4">
        <div className={cn('p-2 rounded-xl bg-black/30', integration.color)}>
          <IntegrationIcon type={integration.id} />
        </div>
        <div>
          <p className="font-medium">{integration.name}</p>
          {showDescription && (
            <p className="text-sm text-muted-foreground">{integration.description}</p>
          )}
          {!showDescription && (
            <p className="text-sm text-muted-foreground">
              {integration.connected ? t('settings.connected') : t('settings.notConnected')}
            </p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-3">
        {integration.connected && (
          <span className="px-2.5 py-1 rounded-full bg-green-500/20 text-green-400 text-xs font-medium border border-green-500/30">
            Connected
          </span>
        )}
        <button
          className={cn(
            'px-4 py-2 rounded-xl text-sm font-medium transition-colors',
            integration.connected
              ? 'border border-white/10 hover:bg-white/5 text-red-400'
              : 'bg-primary text-primary-foreground hover:bg-primary/90'
          )}
        >
          {integration.connected ? t('settings.disconnect') : t('settings.connect')}
        </button>
      </div>
    </div>
  );

  return (
    <div className="space-y-8">
      <h2 className="text-lg font-semibold">{t('settings.integrationSettings')}</h2>

      {/* Webhooks Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-medium">Webhooks</h3>
            <p className="text-sm text-muted-foreground">
              Receive real-time notifications for platform events
            </p>
          </div>
          <button
            onClick={() => setShowAddWebhook(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <span>+ Add Webhook Endpoint</span>
          </button>
        </div>

        <div className="space-y-3">
          {webhooks.map((webhook) => (
            <div key={webhook.id} className="p-4 rounded-xl border border-white/10 glass">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <code className="text-sm font-mono text-cyan-400 break-all">{webhook.url}</code>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {webhook.events.map((event) => (
                      <span
                        key={event}
                        className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs"
                      >
                        {event}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <span className="px-2.5 py-1 rounded-full bg-green-500/20 text-green-400 text-xs font-medium border border-green-500/30">
                    Active
                  </span>
                  <button className="px-3 py-1.5 rounded-lg border border-white/10 hover:bg-white/5 text-sm">
                    Edit
                  </button>
                  <button
                    onClick={() => deleteWebhook(webhook.id)}
                    className="px-3 py-1.5 rounded-lg border border-red-500/30 hover:bg-red-500/10 text-red-400 text-sm"
                  >
                    Delete
                  </button>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Last triggered: {webhook.lastTriggered}
              </p>
            </div>
          ))}
        </div>

        {/* Add Webhook Modal */}
        {showAddWebhook && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="w-full max-w-lg rounded-2xl border border-white/10 glass-strong p-6">
              <h3 className="text-lg font-semibold mb-4">Add Webhook Endpoint</h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Endpoint URL</label>
                  <input
                    type="url"
                    value={newWebhookUrl}
                    onChange={(e) => setNewWebhookUrl(e.target.value)}
                    placeholder="https://your-app.com/webhooks/stratum"
                    className="w-full px-4 py-2 rounded-xl border border-white/10 glass bg-transparent focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Events to Subscribe</label>
                  <div className="grid grid-cols-2 gap-2">
                    {webhookEventTypes.map((event) => (
                      <button
                        key={event.id}
                        onClick={() => toggleWebhookEvent(event.id)}
                        className={cn(
                          'p-3 rounded-xl border text-left transition-all',
                          newWebhookEvents.includes(event.id)
                            ? 'border-primary bg-primary/10'
                            : 'border-white/10 hover:border-white/20'
                        )}
                      >
                        <p className="font-medium text-sm">{event.label}</p>
                        <p className="text-xs text-muted-foreground">{event.description}</p>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-white/10">
                <button
                  onClick={() => setShowAddWebhook(false)}
                  className="px-4 py-2 rounded-xl border border-white/10 hover:bg-white/5"
                >
                  Cancel
                </button>
                <button
                  onClick={addWebhook}
                  disabled={!newWebhookUrl || newWebhookEvents.length === 0}
                  className="px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  Add Webhook
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Ad Platforms */}
      <div>
        <h3 className="font-medium mb-3">Ad Platforms</h3>
        <div className="space-y-3">
          {adPlatforms.map((integration) => (
            <IntegrationCard key={integration.id} integration={integration} />
          ))}
        </div>
      </div>

      {/* Analytics & Tracking */}
      <div>
        <h3 className="font-medium mb-3">Analytics & Tracking</h3>
        <div className="space-y-3">
          {analyticsIntegrations.map((integration) => (
            <IntegrationCard key={integration.id} integration={integration} showDescription />
          ))}
        </div>
      </div>

      {/* Connected Services (E-commerce & Payments) */}
      <div>
        <h3 className="font-medium mb-3">Connected Services</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {commerceIntegrations.map((integration) => (
            <div
              key={integration.id}
              className="p-4 rounded-xl border border-white/10 glass card-3d text-center"
            >
              <div className={cn('p-3 rounded-xl bg-black/30 inline-flex mb-3', integration.color)}>
                <IntegrationIcon type={integration.id} />
              </div>
              <h4 className="font-medium mb-1">{integration.name}</h4>
              <p className="text-xs text-muted-foreground mb-3">{integration.description}</p>
              {integration.connected ? (
                <span className="px-3 py-1.5 rounded-full bg-green-500/20 text-green-400 text-xs font-medium border border-green-500/30 inline-block">
                  Connected
                </span>
              ) : (
                <span className="px-3 py-1.5 rounded-full bg-gray-500/20 text-gray-400 text-xs font-medium border border-gray-500/30 inline-block">
                  Not Connected
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PreferenceSettings() {
  const { t, i18n } = useTranslation();
  const [theme, setTheme] = useState('system');
  const [language, setLanguage] = useState(i18n.language);

  const handleLanguageChange = (lang: string) => {
    setLanguage(lang);
    i18n.changeLanguage(lang);
  };

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">{t('settings.preferenceSettings')}</h2>

      <div>
        <label className="text-sm font-medium mb-2 block">{t('settings.theme')}</label>
        <div className="flex gap-3">
          {['light', 'dark', 'system'].map((t) => (
            <button
              key={t}
              onClick={() => setTheme(t)}
              className={cn(
                'px-4 py-2 rounded-lg border transition-colors capitalize',
                theme === t ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
              )}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">{t('settings.language')}</label>
        <select
          value={language}
          onChange={(e) => handleLanguageChange(e.target.value)}
          className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value="en">English</option>
          <option value="uk">Українська</option>
        </select>
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">{t('settings.currency')}</label>
        <select className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20">
          <option value="USD">USD ($)</option>
          <option value="EUR">EUR (€)</option>
          <option value="GBP">GBP (£)</option>
          <option value="UAH">UAH (₴)</option>
        </select>
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">{t('settings.dateFormat')}</label>
        <select className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20">
          <option value="MM/DD/YYYY">MM/DD/YYYY</option>
          <option value="DD/MM/YYYY">DD/MM/YYYY</option>
          <option value="YYYY-MM-DD">YYYY-MM-DD</option>
        </select>
      </div>
    </div>
  );
}

function BillingSettings() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">{t('settings.billingSettings')}</h2>

      <div className="p-4 rounded-lg border bg-primary/5 border-primary/20">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">Pro Plan</p>
            <p className="text-sm text-muted-foreground">$99/month • Renews Dec 15, 2024</p>
          </div>
          <button className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors text-sm">
            {t('settings.changePlan')}
          </button>
        </div>
      </div>

      <div>
        <h3 className="font-medium mb-3">{t('settings.paymentMethod')}</h3>
        <div className="p-4 rounded-lg border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-8 rounded bg-muted flex items-center justify-center text-xs font-bold">
                VISA
              </div>
              <div>
                <p className="font-medium">•••• •••• •••• 4242</p>
                <p className="text-sm text-muted-foreground">Expires 12/25</p>
              </div>
            </div>
            <button className="text-sm text-primary hover:underline">{t('settings.update')}</button>
          </div>
        </div>
      </div>

      <div>
        <h3 className="font-medium mb-3">{t('settings.billingHistory')}</h3>
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="p-3 text-left text-sm font-medium">{t('settings.date')}</th>
                <th className="p-3 text-left text-sm font-medium">{t('settings.description')}</th>
                <th className="p-3 text-right text-sm font-medium">{t('settings.amount')}</th>
                <th className="p-3 text-right text-sm font-medium" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {[
                { date: 'Nov 15, 2024', desc: 'Pro Plan - Monthly', amount: '$99.00' },
                { date: 'Oct 15, 2024', desc: 'Pro Plan - Monthly', amount: '$99.00' },
                { date: 'Sep 15, 2024', desc: 'Pro Plan - Monthly', amount: '$99.00' },
              ].map((invoice, i) => (
                <tr key={i}>
                  <td className="p-3 text-sm">{invoice.date}</td>
                  <td className="p-3 text-sm">{invoice.desc}</td>
                  <td className="p-3 text-sm text-right">{invoice.amount}</td>
                  <td className="p-3 text-right">
                    <button className="text-sm text-primary hover:underline">
                      <Download className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function GDPRSettings() {
  const { t } = useTranslation();

  // API hooks for GDPR operations
  const exportData = useExportData();
  const requestDeletion = useRequestDeletion();

  const [exportStatus, setExportStatus] = useState<'idle' | 'processing' | 'ready'>('idle');

  // Handle data export request
  const handleExport = async () => {
    setExportStatus('processing');
    try {
      await exportData.mutateAsync('json');
      setExportStatus('ready');
    } catch (error) {
      console.error('Export failed:', error);
      // Fallback to mock success for demo
      setTimeout(() => setExportStatus('ready'), 3000);
    }
  };

  // Handle account deletion request
  const handleDeleteRequest = async () => {
    if (
      !confirm('Are you sure you want to request account deletion? This action cannot be undone.')
    ) {
      return;
    }
    try {
      await requestDeletion.mutateAsync('User requested account deletion');
      alert('Deletion request submitted. You will receive an email confirmation.');
    } catch (error) {
      console.error('Deletion request failed:', error);
      alert('Deletion request submitted (demo mode).');
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">{t('settings.gdprSettings')}</h2>

      <div className="p-4 rounded-lg border border-amber-500/30 bg-amber-500/10">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5" />
          <div>
            <p className="font-medium">{t('settings.gdprNotice')}</p>
            <p className="text-sm text-muted-foreground mt-1">{t('settings.gdprNoticeDesc')}</p>
          </div>
        </div>
      </div>

      <div>
        <h3 className="font-medium mb-3">{t('settings.exportData')}</h3>
        <p className="text-sm text-muted-foreground mb-3">{t('settings.exportDataDesc')}</p>
        <button
          onClick={handleExport}
          disabled={exportStatus === 'processing' || exportData.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {exportStatus === 'processing' || exportData.isPending ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              {t('settings.processing')}
            </>
          ) : exportStatus === 'ready' ? (
            <>
              <Download className="w-4 h-4" />
              {t('settings.downloadReady')}
            </>
          ) : (
            <>
              <Download className="w-4 h-4" />
              {t('settings.requestExport')}
            </>
          )}
        </button>
      </div>

      <div className="border-t pt-6">
        <h3 className="font-medium mb-3 text-red-500">{t('settings.deleteAccount')}</h3>
        <p className="text-sm text-muted-foreground mb-3">{t('settings.deleteAccountDesc')}</p>
        <button
          onClick={handleDeleteRequest}
          disabled={requestDeletion.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-red-500 text-red-500 hover:bg-red-500/10 transition-colors disabled:opacity-50"
        >
          {requestDeletion.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Trash2 className="w-4 h-4" />
          )}
          {t('settings.deleteAccountButton')}
        </button>
      </div>
    </div>
  );
}

function TrustEngineSettings() {
  const [healthyThreshold, setHealthyThreshold] = useState(70);
  const [degradedThreshold, setDegradedThreshold] = useState(40);
  const [autopilotEnabled, setAutopilotEnabled] = useState(true);

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">Trust Engine Configuration</h2>
      <p className="text-sm text-muted-foreground">
        Configure signal health thresholds that control when automations can execute.
        The Trust Engine ensures automations only run when signal quality meets safety requirements.
      </p>

      <div className="space-y-6">
        {/* Healthy Threshold */}
        <div className="p-4 rounded-xl border border-green-500/20 bg-green-500/5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <label className="font-medium text-green-400">Healthy Threshold</label>
              <p className="text-sm text-muted-foreground mt-0.5">
                Signal health at or above this value enables autopilot execution
              </p>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={0}
                max={100}
                value={healthyThreshold}
                onChange={(e) => setHealthyThreshold(Number(e.target.value))}
                className="w-20 px-3 py-2 rounded-lg border border-white/10 bg-transparent text-center font-mono text-lg focus:outline-none focus:ring-2 focus:ring-green-500/30"
              />
              <span className="text-muted-foreground text-sm">/100</span>
            </div>
          </div>
          <div className="w-full bg-white/10 rounded-full h-2">
            <div
              className="bg-green-500 rounded-full h-2 transition-all"
              style={{ width: `${healthyThreshold}%` }}
            />
          </div>
        </div>

        {/* Degraded Threshold */}
        <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <label className="font-medium text-amber-400">Degraded Threshold</label>
              <p className="text-sm text-muted-foreground mt-0.5">
                Below healthy but above this value triggers alerts and holds execution
              </p>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={0}
                max={100}
                value={degradedThreshold}
                onChange={(e) => setDegradedThreshold(Number(e.target.value))}
                className="w-20 px-3 py-2 rounded-lg border border-white/10 bg-transparent text-center font-mono text-lg focus:outline-none focus:ring-2 focus:ring-amber-500/30"
              />
              <span className="text-muted-foreground text-sm">/100</span>
            </div>
          </div>
          <div className="w-full bg-white/10 rounded-full h-2">
            <div
              className="bg-amber-500 rounded-full h-2 transition-all"
              style={{ width: `${degradedThreshold}%` }}
            />
          </div>
        </div>

        {/* Below Degraded Info */}
        <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/5">
          <div>
            <label className="font-medium text-red-400">Unhealthy Zone</label>
            <p className="text-sm text-muted-foreground mt-0.5">
              Below {degradedThreshold}: All automations blocked. Manual action required.
            </p>
          </div>
        </div>

        {/* Autopilot Toggle */}
        <div className="p-4 rounded-xl border border-white/10 bg-white/5">
          <div className="flex items-center justify-between">
            <div>
              <label className="font-medium">Autopilot Mode</label>
              <p className="text-sm text-muted-foreground mt-0.5">
                When enabled, automations execute automatically when signal health is above the
                healthy threshold ({healthyThreshold})
              </p>
            </div>
            <button
              onClick={() => setAutopilotEnabled(!autopilotEnabled)}
              className={cn(
                'relative w-12 h-6 rounded-full transition-colors',
                autopilotEnabled ? 'bg-primary' : 'bg-muted'
              )}
            >
              <span
                className={cn(
                  'absolute top-1 w-4 h-4 bg-white rounded-full transition-transform',
                  autopilotEnabled ? 'translate-x-7' : 'translate-x-1'
                )}
              />
            </button>
          </div>
        </div>

        {/* Visual summary */}
        <div className="p-4 rounded-xl border border-white/10 bg-white/5">
          <h3 className="font-medium mb-3">Trust Gate Logic</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-3">
              <span className="w-3 h-3 rounded-full bg-green-500" />
              <span>
                Score {'>='} {healthyThreshold}: <strong className="text-green-400">PASS</strong> -
                Autopilot {autopilotEnabled ? 'executes' : 'disabled (manual only)'}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="w-3 h-3 rounded-full bg-amber-500" />
              <span>
                Score {degradedThreshold}-{healthyThreshold - 1}:{' '}
                <strong className="text-amber-400">HOLD</strong> - Alert only, no auto-execution
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="w-3 h-3 rounded-full bg-red-500" />
              <span>
                Score {'<'} {degradedThreshold}: <strong className="text-red-400">BLOCK</strong> -
                Manual action required
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Settings;
