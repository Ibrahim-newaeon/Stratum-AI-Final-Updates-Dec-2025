/**
 * Stratum AI - Tenant Layout Component
 *
 * Layout wrapper for tenant-scoped routes (/app/:tenantId/*).
 * Provides navigation, tenant context, and campaign builder access.
 */

import { useState, useEffect } from 'react'
import { Outlet, NavLink, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  HomeIcon,
  ChartBarIcon,
  CogIcon,
  Bars3Icon,
  XMarkIcon,
  BellIcon,
  BookOpenIcon,
  LinkIcon,
  BuildingStorefrontIcon,
  PlusCircleIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon,
  ArrowLeftIcon,
  ArrowRightOnRectangleIcon,
  // Sprint feature icons
  CircleStackIcon,
  ChartPieIcon,
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  DocumentChartBarIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { useAuth } from '@/contexts/AuthContext'
import { useTenantStore } from '@/stores/tenantStore'

// Tenant-scoped navigation items
const getNavigation = (tenantId: string) => [
  { name: 'Overview', href: `/app/${tenantId}/overview`, icon: HomeIcon },
  { name: 'Campaigns', href: `/app/${tenantId}/campaigns`, icon: ChartBarIcon },
]

// Campaign Builder sub-navigation
const getCampaignBuilderNav = (tenantId: string) => [
  { name: 'Connect Platforms', href: `/app/${tenantId}/campaigns/connect`, icon: LinkIcon },
  { name: 'Ad Accounts', href: `/app/${tenantId}/campaigns/accounts`, icon: BuildingStorefrontIcon },
  { name: 'Create Campaign', href: `/app/${tenantId}/campaigns/new`, icon: PlusCircleIcon },
  { name: 'Drafts', href: `/app/${tenantId}/campaigns/drafts`, icon: DocumentTextIcon },
  { name: 'Publish Logs', href: `/app/${tenantId}/campaigns/logs`, icon: ClipboardDocumentListIcon },
]

// Analytics & Insights sub-navigation
const getAnalyticsNav = (tenantId: string) => [
  { name: 'Attribution', href: `/app/${tenantId}/attribution`, icon: ChartPieIcon },
  { name: 'Profit ROAS', href: `/app/${tenantId}/profit`, icon: CurrencyDollarIcon },
  { name: 'Pacing', href: `/app/${tenantId}/pacing`, icon: ArrowTrendingUpIcon },
  { name: 'Reporting', href: `/app/${tenantId}/reporting`, icon: DocumentChartBarIcon },
  { name: 'Integrations', href: `/app/${tenantId}/integrations`, icon: CircleStackIcon },
]

export default function TenantLayout() {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const { tenantId } = useParams<{ tenantId: string }>()
  const { user, logout } = useAuth()
  const { setTenantId, tenant } = useTenantStore()

  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  // Set tenant context when tenantId changes
  useEffect(() => {
    if (tenantId) {
      setTenantId(Number(tenantId))
    }
  }, [tenantId, setTenantId])

  const navigation = tenantId ? getNavigation(tenantId) : []
  const campaignBuilderNav = tenantId ? getCampaignBuilderNav(tenantId) : []
  const analyticsNav = tenantId ? getAnalyticsNav(tenantId) : []

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'ar' : 'en'
    i18n.changeLanguage(newLang)
    document.documentElement.dir = newLang === 'ar' ? 'rtl' : 'ltr'
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleBackToMain = () => {
    navigate('/app/overview')
  }

  const getUserInitials = () => {
    if (!user?.name) return 'U'
    const names = user.name.split(' ')
    return names.map(n => n[0]).join('').toUpperCase().slice(0, 2)
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 transform bg-card border-r transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-auto',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-full flex-col">
          {/* Logo and tenant info */}
          <div className="flex h-16 items-center justify-between px-4 border-b">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-stratum flex items-center justify-center shadow-glow-sm">
                <span className="text-white font-bold text-lg">S</span>
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-bold bg-gradient-stratum bg-clip-text text-transparent">
                  {tenant?.name || 'Tenant'}
                </span>
                <span className="text-xs text-muted-foreground">ID: {tenantId}</span>
              </div>
            </div>
            <button
              className="lg:hidden p-2 rounded-md hover:bg-accent"
              onClick={() => setSidebarOpen(false)}
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          {/* Back to main dashboard */}
          <div className="px-4 py-2 border-b">
            <button
              onClick={handleBackToMain}
              className="flex items-center gap-2 w-full px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
            >
              <ArrowLeftIcon className="h-4 w-4" />
              Back to Dashboard
            </button>
          </div>

          {/* Main Navigation */}
          <nav className="flex-1 overflow-y-auto p-4">
            <div className="space-y-1">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href
                return (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                      isActive
                        ? 'bg-gradient-stratum text-white shadow-glow-sm'
                        : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                    )}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <item.icon className="h-5 w-5" />
                    {item.name}
                  </NavLink>
                )
              })}
            </div>

            {/* Campaign Builder Section */}
            <div className="mt-6">
              <h3 className="px-3 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Campaign Builder
              </h3>
              <div className="space-y-1">
                {campaignBuilderNav.map((item) => {
                  const isActive = location.pathname === item.href
                  return (
                    <NavLink
                      key={item.name}
                      to={item.href}
                      className={cn(
                        'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                        isActive
                          ? 'bg-primary/10 text-primary border-l-2 border-primary'
                          : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                      )}
                      onClick={() => setSidebarOpen(false)}
                    >
                      <item.icon className="h-4 w-4" />
                      {item.name}
                    </NavLink>
                  )
                })}
              </div>
            </div>

            {/* Analytics & Insights Section */}
            <div className="mt-6">
              <h3 className="px-3 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Analytics & Insights
              </h3>
              <div className="space-y-1">
                {analyticsNav.map((item) => {
                  const isActive = location.pathname === item.href
                  return (
                    <NavLink
                      key={item.name}
                      to={item.href}
                      className={cn(
                        'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                        isActive
                          ? 'bg-primary/10 text-primary border-l-2 border-primary'
                          : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                      )}
                      onClick={() => setSidebarOpen(false)}
                    >
                      <item.icon className="h-4 w-4" />
                      {item.name}
                    </NavLink>
                  )
                })}
              </div>
            </div>
          </nav>

          {/* Settings at bottom */}
          <div className="border-t p-4">
            <NavLink
              to={tenantId ? `/app/${tenantId}/settings` : '#'}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                location.pathname.includes('/settings')
                  ? 'bg-gradient-stratum text-white shadow-glow-sm'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'
              )}
            >
              <CogIcon className="h-5 w-5" />
              Tenant Settings
            </NavLink>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top header */}
        <header className="flex h-16 items-center justify-between border-b bg-card px-4 lg:px-6">
          <button
            className="lg:hidden p-2 rounded-md hover:bg-accent"
            onClick={() => setSidebarOpen(true)}
          >
            <Bars3Icon className="h-6 w-6" />
          </button>

          <div className="flex-1" />

          {/* Header actions */}
          <div className="flex items-center gap-3">
            {/* Theme toggle */}
            <ThemeToggle />

            {/* Language toggle */}
            <button
              className="px-3 py-1.5 rounded-lg border text-sm font-medium hover:bg-accent transition-colors"
              onClick={toggleLanguage}
            >
              {i18n.language === 'en' ? 'AR' : 'EN'}
            </button>

            {/* Notifications */}
            <button className="p-2 rounded-lg hover:bg-accent transition-colors relative">
              <BellIcon className="h-5 w-5" />
            </button>

            {/* User menu */}
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 p-2 rounded-lg hover:bg-accent transition-colors"
              >
                <div className="h-7 w-7 rounded-full bg-gradient-stratum flex items-center justify-center">
                  <span className="text-white text-xs font-medium">{getUserInitials()}</span>
                </div>
                <div className="hidden lg:block text-left">
                  <span className="text-sm font-medium block">{user?.name || 'User'}</span>
                  <span className="text-xs text-muted-foreground capitalize">{user?.role || 'user'}</span>
                </div>
              </button>

              {/* Dropdown menu */}
              {userMenuOpen && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setUserMenuOpen(false)}
                  />
                  <div className="absolute right-0 mt-2 w-48 py-2 rounded-lg border bg-card shadow-lg z-50">
                    <div className="px-4 py-2 border-b">
                      <p className="text-sm font-medium">{user?.name}</p>
                      <p className="text-xs text-muted-foreground">{user?.email}</p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-500 hover:bg-red-500/10 transition-colors"
                    >
                      <ArrowRightOnRectangleIcon className="w-4 h-4" />
                      {t('common.logout')}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-background p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
