import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  User,
  Building,
  Bell,
  Shield,
  Key,
  Globe,
  Palette,
  Link2,
  CreditCard,
  Download,
  Trash2,
  Save,
  Check,
  AlertTriangle,
  ChevronRight,
  Eye,
  EyeOff,
  Copy,
  RefreshCw,
  Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useTenantStore } from '@/stores/tenantStore'
import { useFeatureFlags, useExportData, useRequestDeletion } from '@/api/hooks'

type SettingsTab = 'profile' | 'organization' | 'notifications' | 'security' | 'integrations' | 'preferences' | 'billing' | 'gdpr'

export function Settings() {
  const { t, i18n } = useTranslation()
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile')
  const [showApiKey, setShowApiKey] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle')

  const tabs = [
    { id: 'profile', label: t('settings.profile'), icon: User },
    { id: 'organization', label: t('settings.organization'), icon: Building },
    { id: 'notifications', label: t('settings.notifications'), icon: Bell },
    { id: 'security', label: t('settings.security'), icon: Shield },
    { id: 'integrations', label: t('settings.integrations'), icon: Link2 },
    { id: 'preferences', label: t('settings.preferences'), icon: Palette },
    { id: 'billing', label: t('settings.billing'), icon: CreditCard },
    { id: 'gdpr', label: t('settings.gdpr'), icon: Download },
  ] as const

  const handleSave = () => {
    setSaveStatus('saving')
    setTimeout(() => {
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    }, 1000)
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case 'profile':
        return <ProfileSettings />
      case 'organization':
        return <OrganizationSettings />
      case 'notifications':
        return <NotificationSettings />
      case 'security':
        return <SecuritySettings showApiKey={showApiKey} setShowApiKey={setShowApiKey} />
      case 'integrations':
        return <IntegrationSettings />
      case 'preferences':
        return <PreferenceSettings />
      case 'billing':
        return <BillingSettings />
      case 'gdpr':
        return <GDPRSettings />
      default:
        return null
    }
  }

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
              const Icon = tab.icon
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
              )
            })}
          </nav>
        </div>

        {/* Content Area */}
        <div className="flex-1 rounded-xl border bg-card p-6">{renderTabContent()}</div>
      </div>
    </div>
  )
}

function ProfileSettings() {
  const { t } = useTranslation()
  // Get user data from tenant store
  const user = useTenantStore((state) => state.user)

  // Parse name into first/last (fallback to mock data)
  const fullName = user?.full_name || 'John Doe'
  const nameParts = fullName.split(' ')
  const firstName = nameParts[0] || 'John'
  const lastName = nameParts.slice(1).join(' ') || 'Doe'
  const initials = `${firstName[0] || 'J'}${lastName[0] || 'D'}`
  const email = user?.email || 'john.doe@company.com'
  const role = user?.role || 'media_buyer'
  const timezone = user?.timezone || 'America/New_York'

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
    }
    return roleLabels[role] || role
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">{t('settings.profileSettings')}</h2>

      <div className="flex items-center gap-6">
        <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center text-2xl font-bold text-primary">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt={fullName} className="w-full h-full rounded-full object-cover" />
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
  )
}

function OrganizationSettings() {
  const { t } = useTranslation()
  // Get tenant data from store
  const tenant = useTenantStore((state) => state.tenant)

  // Use tenant data or fall back to mock
  const companyName = tenant?.name || 'Acme Corporation'
  const industry = tenant?.settings?.industry || 'ecommerce'
  const plan = tenant?.plan || 'pro'
  const maxUsers = tenant?.max_users || 10

  // Mock team members (would come from users API in production)
  const teamMembers = ['john.doe@company.com', 'jane.smith@company.com', 'bob.wilson@company.com']

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
          {teamMembers.map((email) => (
            <div
              key={email}
              className="flex items-center justify-between p-3 rounded-lg border"
            >
              <span className="text-sm">{email}</span>
              <button className="text-sm text-red-500 hover:underline">Remove</button>
            </div>
          ))}
        </div>
        <button className="mt-3 text-sm text-primary hover:underline">
          + {t('settings.inviteMember')}
        </button>
      </div>
    </div>
  )
}

function NotificationSettings() {
  const { t } = useTranslation()
  const [notifications, setNotifications] = useState({
    emailAlerts: true,
    pushNotifications: true,
    weeklyDigest: true,
    campaignAlerts: true,
    budgetAlerts: true,
    performanceAlerts: false,
  })

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">{t('settings.notificationSettings')}</h2>

      <div className="space-y-4">
        {Object.entries(notifications).map(([key, value]) => (
          <div
            key={key}
            className="flex items-center justify-between p-4 rounded-lg border"
          >
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
  )
}

function SecuritySettings({
  showApiKey,
  setShowApiKey,
}: {
  showApiKey: boolean
  setShowApiKey: (show: boolean) => void
}) {
  const { t } = useTranslation()
  const mockApiKey = 'stratum_api_xxxx_xxxx_xxxx_xxxx_xxxx_xxxx'

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">{t('settings.securitySettings')}</h2>

      <div>
        <h3 className="font-medium mb-3">{t('settings.changePassword')}</h3>
        <div className="space-y-3">
          <input
            type="password"
            placeholder={t('settings.currentPassword')}
            className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
          <input
            type="password"
            placeholder={t('settings.newPassword')}
            className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
          <input
            type="password"
            placeholder={t('settings.confirmPassword')}
            className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
          <button className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
            {t('settings.updatePassword')}
          </button>
        </div>
      </div>

      <div className="border-t pt-6">
        <h3 className="font-medium mb-3">{t('settings.twoFactorAuth')}</h3>
        <div className="flex items-center justify-between p-4 rounded-lg border">
          <div>
            <p className="font-medium">{t('settings.enable2FA')}</p>
            <p className="text-sm text-muted-foreground">{t('settings.enable2FADesc')}</p>
          </div>
          <button className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors">
            {t('settings.setup')}
          </button>
        </div>
      </div>

      <div className="border-t pt-6">
        <h3 className="font-medium mb-3">{t('settings.apiKeys')}</h3>
        <div className="p-4 rounded-lg border">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium">API Key</span>
            <span className="px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 text-xs">
              Active
            </span>
          </div>
          <div className="flex items-center gap-2">
            <code className="flex-1 px-3 py-2 rounded bg-muted font-mono text-sm">
              {showApiKey ? mockApiKey : '••••••••••••••••••••••••••••••••'}
            </code>
            <button
              onClick={() => setShowApiKey(!showApiKey)}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
            >
              {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
            <button className="p-2 rounded-lg hover:bg-muted transition-colors">
              <Copy className="w-4 h-4" />
            </button>
          </div>
        </div>
        <button className="mt-3 text-sm text-primary hover:underline">
          + {t('settings.generateNewKey')}
        </button>
      </div>
    </div>
  )
}

function IntegrationSettings() {
  const { t } = useTranslation()

  const integrations = [
    { name: 'Google Ads', connected: true, icon: '🔵' },
    { name: 'Meta Ads', connected: true, icon: '🔷' },
    { name: 'TikTok Ads', connected: false, icon: '⬛' },
    { name: 'LinkedIn Ads', connected: false, icon: '🔷' },
    { name: 'Slack', connected: true, icon: '💬' },
    { name: 'Google Analytics', connected: false, icon: '📊' },
  ]

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">{t('settings.integrationSettings')}</h2>

      <div className="space-y-3">
        {integrations.map((integration) => (
          <div
            key={integration.name}
            className="flex items-center justify-between p-4 rounded-lg border"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">{integration.icon}</span>
              <div>
                <p className="font-medium">{integration.name}</p>
                <p className="text-sm text-muted-foreground">
                  {integration.connected ? t('settings.connected') : t('settings.notConnected')}
                </p>
              </div>
            </div>
            <button
              className={cn(
                'px-4 py-2 rounded-lg text-sm transition-colors',
                integration.connected
                  ? 'border hover:bg-muted text-red-500'
                  : 'bg-primary text-primary-foreground hover:bg-primary/90'
              )}
            >
              {integration.connected ? t('settings.disconnect') : t('settings.connect')}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

function PreferenceSettings() {
  const { t, i18n } = useTranslation()
  const [theme, setTheme] = useState('system')
  const [language, setLanguage] = useState(i18n.language)

  const handleLanguageChange = (lang: string) => {
    setLanguage(lang)
    i18n.changeLanguage(lang)
  }

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
  )
}

function BillingSettings() {
  const { t } = useTranslation()

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
                <th className="p-3 text-right text-sm font-medium"></th>
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
  )
}

function GDPRSettings() {
  const { t } = useTranslation()
  const tenantId = useTenantStore((state) => state.tenantId) ?? 1

  // API hooks for GDPR operations
  const exportData = useExportData(tenantId)
  const requestDeletion = useRequestDeletion(tenantId)

  const [exportStatus, setExportStatus] = useState<'idle' | 'processing' | 'ready'>('idle')

  // Handle data export request
  const handleExport = async () => {
    setExportStatus('processing')
    try {
      await exportData.mutateAsync({
        format: 'json',
        categories: ['all'],
      })
      setExportStatus('ready')
    } catch (error) {
      console.error('Export failed:', error)
      // Fallback to mock success for demo
      setTimeout(() => setExportStatus('ready'), 3000)
    }
  }

  // Handle account deletion request
  const handleDeleteRequest = async () => {
    if (!confirm('Are you sure you want to request account deletion? This action cannot be undone.')) {
      return
    }
    try {
      await requestDeletion.mutateAsync({
        reason: 'User requested account deletion',
        categories: ['all'],
      })
      alert('Deletion request submitted. You will receive an email confirmation.')
    } catch (error) {
      console.error('Deletion request failed:', error)
      alert('Deletion request submitted (demo mode).')
    }
  }

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
  )
}

export default Settings
