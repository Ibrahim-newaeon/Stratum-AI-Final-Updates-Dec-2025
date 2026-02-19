/**
 * Stratum AI - Tenant Settings Page
 *
 * Configuration settings for the current tenant.
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTenantStore } from '@/stores/tenantStore'
import { useUpdateTenantSettings } from '@/api/hooks'
import { useToast } from '@/components/ui/use-toast'
import {
  CogIcon,
  BellIcon,
  ShieldCheckIcon,
  CurrencyDollarIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

interface SettingsSection {
  id: string
  name: string
  icon: React.ComponentType<{ className?: string }>
}

const sections: SettingsSection[] = [
  { id: 'general', name: 'General', icon: CogIcon },
  { id: 'budget', name: 'Budget Guardrails', icon: CurrencyDollarIcon },
  { id: 'notifications', name: 'Notifications', icon: BellIcon },
  { id: 'permissions', name: 'Permissions', icon: ShieldCheckIcon },
  { id: 'team', name: 'Team Access', icon: UserGroupIcon },
]

export default function TenantSettings() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const navigate = useNavigate()
  const { tenant } = useTenantStore()
  const { toast } = useToast()
  const [activeSection, setActiveSection] = useState('general')
  const [settings, setSettings] = useState({
    name: tenant?.name || '',
    timezone: 'Asia/Riyadh',
    currency: 'SAR',
    maxDailyBudget: 5000,
    requireApprovalOver: 1000,
    autoPublish: false,
    emailNotifications: true,
    slackNotifications: false,
    slackWebhook: '',
    approvalRequired: true,
  })

  const tenantIdNum = tenantId ? parseInt(tenantId, 10) : 0
  const updateSettingsMutation = useUpdateTenantSettings(tenantIdNum)

  const handleSave = async () => {
    if (!tenantIdNum) {
      toast({
        title: 'Error',
        description: 'Invalid tenant ID',
        variant: 'destructive',
      })
      return
    }

    try {
      await updateSettingsMutation.mutateAsync({
        timezone: settings.timezone,
        currency: settings.currency,
        email_notifications: settings.emailNotifications,
      } as any)
      toast({
        title: 'Success',
        description: 'Settings saved successfully',
      })
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to save settings',
        variant: 'destructive',
      })
    }
  }

  const renderContent = () => {
    switch (activeSection) {
      case 'general':
        return (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2">Tenant Name</label>
              <input
                type="text"
                value={settings.name}
                onChange={(e) => setSettings({ ...settings, name: e.target.value })}
                className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Timezone</label>
              <select
                value={settings.timezone}
                onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
                className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option value="Asia/Riyadh">Asia/Riyadh (GMT+3)</option>
                <option value="Asia/Dubai">Asia/Dubai (GMT+4)</option>
                <option value="Africa/Cairo">Africa/Cairo (GMT+2)</option>
                <option value="UTC">UTC</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Default Currency</label>
              <select
                value={settings.currency}
                onChange={(e) => setSettings({ ...settings, currency: e.target.value })}
                className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option value="SAR">SAR - Saudi Riyal</option>
                <option value="AED">AED - UAE Dirham</option>
                <option value="EGP">EGP - Egyptian Pound</option>
                <option value="USD">USD - US Dollar</option>
              </select>
            </div>
          </div>
        )

      case 'budget':
        return (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2">
                Maximum Daily Budget ({settings.currency})
              </label>
              <input
                type="number"
                value={settings.maxDailyBudget}
                onChange={(e) => setSettings({ ...settings, maxDailyBudget: Number(e.target.value) })}
                className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Campaigns cannot exceed this daily budget limit
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">
                Require Approval Over ({settings.currency})
              </label>
              <input
                type="number"
                value={settings.requireApprovalOver}
                onChange={(e) => setSettings({ ...settings, requireApprovalOver: Number(e.target.value) })}
                className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Campaigns with daily budgets above this amount require approval
              </p>
            </div>
            <div className="flex items-center justify-between p-4 rounded-lg border">
              <div>
                <p className="font-medium">Auto-Publish Approved Campaigns</p>
                <p className="text-sm text-muted-foreground">
                  Automatically publish campaigns once approved
                </p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, autoPublish: !settings.autoPublish })}
                className={cn(
                  'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                  settings.autoPublish ? 'bg-primary' : 'bg-muted'
                )}
              >
                <span
                  className={cn(
                    'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                    settings.autoPublish ? 'translate-x-6' : 'translate-x-1'
                  )}
                />
              </button>
            </div>
          </div>
        )

      case 'notifications':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between p-4 rounded-lg border">
              <div>
                <p className="font-medium">Email Notifications</p>
                <p className="text-sm text-muted-foreground">
                  Receive email alerts for important events
                </p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, emailNotifications: !settings.emailNotifications })}
                className={cn(
                  'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                  settings.emailNotifications ? 'bg-primary' : 'bg-muted'
                )}
              >
                <span
                  className={cn(
                    'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                    settings.emailNotifications ? 'translate-x-6' : 'translate-x-1'
                  )}
                />
              </button>
            </div>
            <div className="flex items-center justify-between p-4 rounded-lg border">
              <div>
                <p className="font-medium">Slack Notifications</p>
                <p className="text-sm text-muted-foreground">
                  Send alerts to a Slack channel
                </p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, slackNotifications: !settings.slackNotifications })}
                className={cn(
                  'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                  settings.slackNotifications ? 'bg-primary' : 'bg-muted'
                )}
              >
                <span
                  className={cn(
                    'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                    settings.slackNotifications ? 'translate-x-6' : 'translate-x-1'
                  )}
                />
              </button>
            </div>
            {settings.slackNotifications && (
              <div>
                <label className="block text-sm font-medium mb-2">Slack Webhook URL</label>
                <input
                  type="text"
                  value={settings.slackWebhook}
                  onChange={(e) => setSettings({ ...settings, slackWebhook: e.target.value })}
                  placeholder="https://hooks.slack.com/services/..."
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
            )}
          </div>
        )

      case 'permissions':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between p-4 rounded-lg border">
              <div>
                <p className="font-medium">Require Approval for Publishing</p>
                <p className="text-sm text-muted-foreground">
                  All campaigns must be approved before publishing
                </p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, approvalRequired: !settings.approvalRequired })}
                className={cn(
                  'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                  settings.approvalRequired ? 'bg-primary' : 'bg-muted'
                )}
              >
                <span
                  className={cn(
                    'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                    settings.approvalRequired ? 'translate-x-6' : 'translate-x-1'
                  )}
                />
              </button>
            </div>
            <div className="p-4 rounded-lg bg-muted/50">
              <p className="text-sm text-muted-foreground">
                Additional permission settings can be configured in the main dashboard under Settings &rarr; Permissions.
              </p>
            </div>
          </div>
        )

      case 'team':
        return (
          <div className="space-y-6">
            <div className="p-6 rounded-lg border text-center">
              <UserGroupIcon className="h-12 w-12 mx-auto text-muted-foreground" />
              <h3 className="mt-4 font-semibold">Team Management</h3>
              <p className="text-sm text-muted-foreground mt-2">
                Invite team members and manage their access to this tenant.
              </p>
              <button
                onClick={() => navigate(`/app/${tenantId}/team`)}
                className="mt-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
              >
                Manage Team
              </button>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Tenant Settings</h1>
        <p className="text-muted-foreground">
          Configure settings for {tenant?.name || `Tenant ${tenantId}`}
        </p>
      </div>

      {/* Settings Layout */}
      <div className="flex flex-col md:flex-row gap-6">
        {/* Sidebar */}
        <div className="md:w-64 space-y-1">
          {sections.map((section) => {
            const Icon = section.icon
            return (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={cn(
                  'w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  activeSection === section.id
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                )}
              >
                <Icon className="h-5 w-5" />
                {section.name}
              </button>
            )
          })}
        </div>

        {/* Content */}
        <div className="flex-1">
          <div className="rounded-xl border bg-card p-6 shadow-card">
            <h2 className="text-lg font-semibold mb-6">
              {sections.find(s => s.id === activeSection)?.name}
            </h2>
            {renderContent()}
          </div>

          {/* Save Button */}
          <div className="mt-6 flex justify-end">
            <button
              onClick={handleSave}
              disabled={updateSettingsMutation.isPending}
              className={cn(
                'px-6 py-2 rounded-lg bg-primary text-primary-foreground transition-opacity',
                updateSettingsMutation.isPending
                  ? 'opacity-50 cursor-not-allowed'
                  : 'hover:opacity-90'
              )}
            >
              {updateSettingsMutation.isPending ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
