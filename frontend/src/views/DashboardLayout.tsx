import { useState } from 'react'
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion, AnimatePresence } from 'framer-motion'
import { fadeInUp, staggerContainer, listItem, dropdownVariants, transitions } from '@/lib/animations'
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
  PresentationChartBarIcon,
  FunnelIcon,
  CalculatorIcon,
  ShieldExclamationIcon,
  AdjustmentsHorizontalIcon,
  DocumentChartBarIcon,
  UserMinusIcon,
  DocumentTextIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import { BackgroundEffects } from '@/components/ui/background-effects'
import LearningHub from '@/components/guide/LearningHub'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { CommandPalette } from '@/components/ui/command-palette'
import { DemoBanner } from '@/components/demo/DemoBanner'
import { NotificationCenter, NotificationBell } from '@/components/notifications/NotificationCenter'
import { WhatsNewModal, useWhatsNew } from '@/components/changelog/WhatsNew'
import { KeyboardShortcutsModal } from '@/components/ui/keyboard-shortcuts'
import { OnboardingChecklist } from '@/components/onboarding/OnboardingChecklist'
import { useAuth } from '@/contexts/AuthContext'

const navigation = [
  { name: 'nav.overview', href: '/dashboard/overview', icon: HomeIcon, tourId: 'nav-overview', dataTour: 'overview' },
  { name: 'nav.dashboard', href: '/dashboard', icon: Squares2X2Icon, tourId: 'nav-dashboard' },
  { name: 'nav.campaigns', href: '/dashboard/campaigns', icon: ChartBarIcon, tourId: 'nav-campaigns' },
  { name: 'nav.stratum', href: '/dashboard/stratum', icon: TrophyIcon, tourId: 'nav-stratum' },
  { name: 'nav.benchmarks', href: '/dashboard/benchmarks', icon: FolderIcon, tourId: 'nav-benchmarks' },
  { name: 'nav.assets', href: '/dashboard/assets', icon: PhotoIcon, tourId: 'nav-assets' },
  { name: 'nav.rules', href: '/dashboard/rules', icon: BoltIcon, tourId: 'nav-rules' },
  { name: 'Custom Autopilot', href: '/dashboard/custom-autopilot-rules', icon: AdjustmentsHorizontalIcon, tourId: 'nav-custom-autopilot' },
  { name: 'Custom Reports', href: '/dashboard/custom-reports', icon: DocumentChartBarIcon, tourId: 'nav-custom-reports' },
  { name: 'nav.whatsapp', href: '/dashboard/whatsapp', icon: ChatBubbleLeftRightIcon, tourId: 'nav-whatsapp' },
]

// CDP Navigation with sub-items
const cdpNavigation = [
  { name: 'CDP Overview', href: '/dashboard/cdp', icon: CircleStackIcon },
  { name: 'Profiles', href: '/dashboard/cdp/profiles', icon: UserGroupIcon },
  { name: 'Segments', href: '/dashboard/cdp/segments', icon: TagIcon },
  { name: 'Events', href: '/dashboard/cdp/events', icon: ClockIcon },
  { name: 'Identity Graph', href: '/dashboard/cdp/identity', icon: ShareIcon },
  { name: 'RFM Analysis', href: '/dashboard/cdp/rfm', icon: PresentationChartBarIcon },
  { name: 'Funnels', href: '/dashboard/cdp/funnels', icon: FunnelIcon },
  { name: 'Computed Traits', href: '/dashboard/cdp/computed-traits', icon: CalculatorIcon },
  { name: 'Consent', href: '/dashboard/cdp/consent', icon: ShieldExclamationIcon },
  { name: 'Predictive Churn', href: '/dashboard/cdp/predictive-churn', icon: UserMinusIcon },
  { name: 'Audience Sync', href: '/dashboard/cdp/audience-sync', icon: ArrowUpOnSquareIcon },
]

export default function DashboardLayout() {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [learningHubOpen, setLearningHubOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [cdpExpanded, setCdpExpanded] = useState(location.pathname.startsWith('/dashboard/cdp'))
  const [superadminExpanded, setSuperadminExpanded] = useState(location.pathname.startsWith('/dashboard/superadmin'))
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [whatsNewOpen, setWhatsNewOpen] = useState(false)
  const [shortcutsOpen, setShortcutsOpen] = useState(false)
  const { hasNewUpdates } = useWhatsNew()

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
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Demo mode banner */}
      <DemoBanner variant="top" />

      {/* 2026 Dark Theme Background Effects */}
      <BackgroundEffects showOrbs={true} />

      <div className="flex flex-1 overflow-hidden">
      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40 bg-black/50 lg:hidden backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside
        data-tour="sidebar"
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 border-r border-white/10 transition-all duration-300 ease-in-out',
          'bg-[#0a0a0a]',
          // Mobile: slide in/out
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
          // Desktop: collapse/expand
          'lg:translate-x-0',
          sidebarCollapsed ? 'lg:w-0 lg:border-r-0 lg:overflow-hidden' : 'lg:w-64'
        )}
      >
        <div className={cn(
          "flex h-full flex-col w-64 transition-opacity duration-200",
          sidebarCollapsed ? "lg:opacity-0" : "lg:opacity-100"
        )}>
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

              <AnimatePresence>
                {cdpExpanded && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                    className="ml-4 mt-1 space-y-1 border-l-2 border-muted pl-3 overflow-hidden"
                  >
                    {cdpNavigation.map((item, index) => {
                      const isActive = location.pathname === item.href
                      return (
                        <motion.div
                          key={item.name}
                          initial={{ opacity: 0, x: -12 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: index * 0.03, duration: 0.2 }}
                        >
                          <NavLink
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
                        </motion.div>
                      )
                    })}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </nav>

          {/* Admin & Settings at bottom */}
          <div className="border-t p-4 space-y-1">
            {/* Superadmin Section with Submenu - only for superadmins */}
            {user?.role === 'superadmin' && (
              <div className="pt-2">
                <button
                  onClick={() => setSuperadminExpanded(!superadminExpanded)}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                    location.pathname.startsWith('/dashboard/superadmin')
                      ? 'bg-purple-500/10 text-purple-400'
                      : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <ShieldCheckIcon className="h-5 w-5" />
                    <span>Superadmin</span>
                  </div>
                  <ChevronDownIcon className={cn('h-4 w-4 transition-transform', superadminExpanded && 'rotate-180')} />
                </button>
                {superadminExpanded && (
                  <div className="mt-1 ml-4 pl-4 border-l border-white/10 space-y-1">
                    <NavLink
                      to="/dashboard/superadmin"
                      end
                      className={cn(
                        'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-200',
                        location.pathname === '/dashboard/superadmin'
                          ? 'bg-purple-500/20 text-purple-300'
                          : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                      )}
                    >
                      <ChartPieIcon className="h-4 w-4" />
                      Dashboard
                    </NavLink>
                    <NavLink
                      to="/dashboard/superadmin/cms"
                      className={cn(
                        'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-200',
                        location.pathname === '/dashboard/superadmin/cms'
                          ? 'bg-purple-500/20 text-purple-300'
                          : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                      )}
                    >
                      <DocumentTextIcon className="h-4 w-4" />
                      CMS
                    </NavLink>
                  </div>
                )}
              </div>
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

      {/* Sidebar Toggle Button - Desktop only */}
      <button
        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        className={cn(
          'hidden lg:flex fixed top-1/2 -translate-y-1/2 z-50 h-8 w-8 items-center justify-center rounded-full bg-[#1a1a1a] border border-white/10 text-muted-foreground hover:text-white hover:bg-[#2a2a2a] transition-all duration-300 shadow-lg',
          sidebarCollapsed ? 'left-2' : 'left-[252px]'
        )}
        title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {sidebarCollapsed ? (
          <ChevronRightIcon className="h-4 w-4" />
        ) : (
          <ChevronLeftIcon className="h-4 w-4" />
        )}
      </button>

      {/* Main content */}
      <div className={cn(
        "flex flex-1 flex-col overflow-hidden transition-all duration-300",
        sidebarCollapsed ? "lg:ml-0" : "lg:ml-64"
      )}>
        {/* Top header */}
        <header className="flex h-16 items-center justify-between border-b border-white/10 glass-strong px-4 lg:px-6">
          <button
            className="lg:hidden p-2 rounded-md hover:bg-accent"
            onClick={() => setSidebarOpen(true)}
          >
            <Bars3Icon className="h-6 w-6" />
          </button>

          <div className="flex-1 flex items-center justify-center">
            {/* Command Palette - Global Search */}
            <CommandPalette />
          </div>

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

            {/* What's New */}
            <button
              onClick={() => setWhatsNewOpen(true)}
              className="relative p-2 rounded-lg hover:bg-accent transition-colors"
              title="What's New"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              {hasNewUpdates && (
                <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-purple-500 animate-pulse" />
              )}
            </button>

            {/* Notifications */}
            <NotificationBell onClick={() => setNotificationsOpen(true)} unreadCount={3} />

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
              <AnimatePresence>
                {userMenuOpen && (
                  <>
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setUserMenuOpen(false)}
                    />
                    <motion.div
                      variants={dropdownVariants}
                      initial="hidden"
                      animate="visible"
                      exit="exit"
                      className="absolute right-0 mt-2 w-48 py-2 rounded-lg border bg-card shadow-lg z-50"
                    >
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
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-background p-4 lg:p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Learning Hub Sidebar */}
      <LearningHub isOpen={learningHubOpen} onClose={() => setLearningHubOpen(false)} />

      {/* Notification Center */}
      <NotificationCenter isOpen={notificationsOpen} onClose={() => setNotificationsOpen(false)} />

      {/* What's New Modal */}
      <WhatsNewModal isOpen={whatsNewOpen} onClose={() => setWhatsNewOpen(false)} />

      {/* Keyboard Shortcuts Modal */}
      <KeyboardShortcutsModal isOpen={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />

      {/* Onboarding Checklist */}
      <OnboardingChecklist variant="sidebar" />
      </div>
    </div>
  )
}
