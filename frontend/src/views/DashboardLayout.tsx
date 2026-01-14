import { useState } from 'react'
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  HomeIcon,
  ChartBarIcon,
  FolderIcon,
  CogIcon,
  BoltIcon,
  PhotoIcon,
  TrophyIcon,
  Bars3Icon,
  XMarkIcon,
  BellIcon,
  BookOpenIcon,
  ChatBubbleLeftRightIcon,
  Squares2X2Icon,
  BuildingOffice2Icon,
  CpuChipIcon,
  SignalIcon,
  ChartPieIcon,
  CircleStackIcon,
  ShieldCheckIcon,
  ArrowRightOnRectangleIcon,
  UserGroupIcon,
  TagIcon,
  ClockIcon,
  ShareIcon,
  ChevronDownIcon,
  ArrowUpOnSquareIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import LearningHub from '@/components/guide/LearningHub'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { useAuth } from '@/contexts/AuthContext'

const navigation = [
  { name: 'nav.overview', href: '/dashboard/overview', icon: HomeIcon, tourId: 'nav-overview', dataTour: 'overview' },
  { name: 'nav.dashboard', href: '/dashboard', icon: Squares2X2Icon, tourId: 'nav-dashboard' },
  { name: 'nav.campaigns', href: '/dashboard/campaigns', icon: ChartBarIcon, tourId: 'nav-campaigns' },
  { name: 'nav.stratum', href: '/dashboard/stratum', icon: TrophyIcon, tourId: 'nav-stratum' },
  { name: 'nav.benchmarks', href: '/dashboard/benchmarks', icon: FolderIcon, tourId: 'nav-benchmarks' },
  { name: 'nav.assets', href: '/dashboard/assets', icon: PhotoIcon, tourId: 'nav-assets' },
  { name: 'nav.rules', href: '/dashboard/rules', icon: BoltIcon, tourId: 'nav-rules' },
  { name: 'nav.whatsapp', href: '/dashboard/whatsapp', icon: ChatBubbleLeftRightIcon, tourId: 'nav-whatsapp' },
]

// CDP Navigation with sub-items
const cdpNavigation = [
  { name: 'CDP Overview', href: '/dashboard/cdp', icon: CircleStackIcon },
  { name: 'Profiles', href: '/dashboard/cdp/profiles', icon: UserGroupIcon },
  { name: 'Segments', href: '/dashboard/cdp/segments', icon: TagIcon },
  { name: 'Events', href: '/dashboard/cdp/events', icon: ClockIcon },
  { name: 'Identity Graph', href: '/dashboard/cdp/identity', icon: ShareIcon },
  { name: 'Audience Sync', href: '/dashboard/cdp/audience-sync', icon: ArrowUpOnSquareIcon },
]

export default function DashboardLayout() {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [learningHubOpen, setLearningHubOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [cdpExpanded, setCdpExpanded] = useState(location.pathname.startsWith('/dashboard/cdp'))

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'ar' : 'en'
    i18n.changeLanguage(newLang)
    // Update document direction for RTL support
    document.documentElement.dir = newLang === 'ar' ? 'rtl' : 'ltr'
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
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
        data-tour="sidebar"
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 transform bg-card border-r transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-auto',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex h-16 items-center justify-between px-4 border-b">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-stratum flex items-center justify-center shadow-glow-sm">
                <span className="text-white font-bold text-lg">S</span>
              </div>
              <span className="text-xl font-bold bg-gradient-stratum bg-clip-text text-transparent">Stratum AI</span>
            </div>
            <button
              className="lg:hidden p-2 rounded-md hover:bg-accent"
              onClick={() => setSidebarOpen(false)}
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto p-4 space-y-1" id="sidebar-nav">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <NavLink
                  key={item.name}
                  to={item.href}
                  id={item.tourId}
                  data-tour={item.dataTour}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-gradient-stratum text-white shadow-glow-sm'
                      : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                  )}
                  onClick={() => setSidebarOpen(false)}
                >
                  <item.icon className="h-5 w-5" />
                  {t(item.name)}
                </NavLink>
              )
            })}

            {/* CDP Section with Submenu */}
            <div className="pt-2">
              <button
                onClick={() => setCdpExpanded(!cdpExpanded)}
                className={cn(
                  'w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                  location.pathname.startsWith('/dashboard/cdp')
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                )}
              >
                <div className="flex items-center gap-3">
                  <CircleStackIcon className="h-5 w-5" />
                  <span>CDP</span>
                </div>
                <ChevronDownIcon
                  className={cn(
                    'h-4 w-4 transition-transform duration-200',
                    cdpExpanded ? 'rotate-180' : ''
                  )}
                />
              </button>

              {cdpExpanded && (
                <div className="ml-4 mt-1 space-y-1 border-l-2 border-muted pl-3">
                  {cdpNavigation.map((item) => {
                    const isActive = location.pathname === item.href
                    return (
                      <NavLink
                        key={item.name}
                        to={item.href}
                        className={cn(
                          'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                          isActive
                            ? 'bg-gradient-stratum text-white shadow-glow-sm'
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
              )}
            </div>
          </nav>

          {/* Admin & Settings at bottom */}
          <div className="border-t p-4 space-y-1">
            {/* Superadmin Dashboard - only for superadmins */}
            {user?.role === 'superadmin' && (
              <NavLink
                to="/dashboard/superadmin"
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                  location.pathname.startsWith('/dashboard/superadmin')
                    ? 'bg-gradient-stratum text-white shadow-glow-sm'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                )}
              >
                <ShieldCheckIcon className="h-5 w-5" />
                Superadmin
              </NavLink>
            )}
            <NavLink
              to="/dashboard/tenants"
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                location.pathname === '/dashboard/tenants'
                  ? 'bg-gradient-stratum text-white shadow-glow-sm'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'
              )}
            >
              <BuildingOffice2Icon className="h-5 w-5" />
              {t('nav.tenants')}
            </NavLink>
            <NavLink
              to="/dashboard/ml-training"
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                location.pathname === '/dashboard/ml-training'
                  ? 'bg-gradient-stratum text-white shadow-glow-sm'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'
              )}
            >
              <CpuChipIcon className="h-5 w-5" />
              {t('nav.mlTraining')}
            </NavLink>
            <NavLink
              to="/dashboard/capi-setup"
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                location.pathname === '/dashboard/capi-setup'
                  ? 'bg-gradient-stratum text-white shadow-glow-sm'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'
              )}
            >
              <SignalIcon className="h-5 w-5" />
              {t('nav.capiSetup')}
            </NavLink>
            <NavLink
              to="/dashboard/data-quality"
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                location.pathname === '/dashboard/data-quality'
                  ? 'bg-gradient-stratum text-white shadow-glow-sm'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'
              )}
            >
              <ChartPieIcon className="h-5 w-5" />
              {t('nav.dataQuality')}
            </NavLink>
            <NavLink
              to="/dashboard/emq-dashboard"
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                location.pathname === '/dashboard/emq-dashboard'
                  ? 'bg-gradient-stratum text-white shadow-glow-sm'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'
              )}
            >
              <CircleStackIcon className="h-5 w-5" />
              {t('nav.emqDashboard')}
            </NavLink>
            <NavLink
              to="/dashboard/settings"
              data-tour="settings"
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                location.pathname === '/dashboard/settings'
                  ? 'bg-gradient-stratum text-white shadow-glow-sm'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'
              )}
            >
              <CogIcon className="h-5 w-5" />
              {t('nav.settings')}
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

            {/* Learning Hub toggle */}
            <button
              className="p-2 rounded-lg hover:bg-accent transition-colors"
              onClick={() => setLearningHubOpen(!learningHubOpen)}
              title="Learning Hub"
            >
              <BookOpenIcon className="h-5 w-5" />
            </button>

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
              <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-destructive animate-pulse" />
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
                    <NavLink
                      to="/dashboard/settings"
                      className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-muted transition-colors"
                      onClick={() => setUserMenuOpen(false)}
                    >
                      <CogIcon className="w-4 h-4" />
                      {t('common.settings')}
                    </NavLink>
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

      {/* Learning Hub Sidebar */}
      <LearningHub isOpen={learningHubOpen} onClose={() => setLearningHubOpen(false)} />
    </div>
  )
}
