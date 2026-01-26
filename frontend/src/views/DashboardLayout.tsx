/**
 * Dashboard Layout - DARK THEME EDITION
 * Matches landing page with purple/cyan gradients
 */

import { useState, useEffect } from 'react'
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion, AnimatePresence } from 'framer-motion'
import { dropdownVariants } from '@/lib/animations'
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
  GiftIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import LearningHub from '@/components/guide/LearningHub'
import { CommandPalette } from '@/components/ui/command-palette'
import { DemoBanner } from '@/components/demo/DemoBanner'
import { NotificationCenter, NotificationBell } from '@/components/notifications/NotificationCenter'
import { WhatsNewModal, useWhatsNew } from '@/components/changelog/WhatsNew'
import { KeyboardShortcutsModal } from '@/components/ui/keyboard-shortcuts'
import { OnboardingChecklist } from '@/components/onboarding/OnboardingChecklist'
import { useAuth } from '@/contexts/AuthContext'

// Dark Theme - Purple/Cyan Gradients (matches landing page)
const theme = {
  purple: '#a855f7',
  cyan: '#06b6d4',
  purpleLight: 'rgba(168, 85, 247, 0.15)',
  cyanLight: 'rgba(6, 182, 212, 0.15)',
  bgBase: '#030303',
  bgElevated: '#0a0a0a',
  bgSurface: '#111111',
  textPrimary: '#ffffff',
  textSecondary: 'rgba(255, 255, 255, 0.7)',
  textMuted: 'rgba(255, 255, 255, 0.5)',
  border: 'rgba(255, 255, 255, 0.08)',
  success: '#22c55e',
  danger: '#ef4444',
  // Gradient for accents
  gradient: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 100%)',
}

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

  // Set dark theme
  useEffect(() => {
    document.documentElement.classList.remove('light')
    document.documentElement.classList.add('dark')
    localStorage.setItem('stratum-theme', 'dark')
  }, [])

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'ar' : 'en'
    i18n.changeLanguage(newLang)
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
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: theme.bgElevated }}>
      <DemoBanner variant="top" />

      <div className="flex flex-1 overflow-hidden relative z-10">
        {/* Mobile sidebar overlay */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40 lg:hidden"
              style={{ background: 'rgba(0, 0, 0, 0.3)' }}
              onClick={() => setSidebarOpen(false)}
            />
          )}
        </AnimatePresence>

        {/* Sidebar */}
        <aside
          data-tour="sidebar"
          className={cn(
            'fixed inset-y-0 left-0 z-50 w-64 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full',
            'lg:translate-x-0',
            sidebarCollapsed ? 'lg:w-0 lg:overflow-hidden' : 'lg:w-64'
          )}
          style={{
            background: theme.bgBase,
            borderRight: `1px solid ${theme.border}`,
          }}
        >
          <div className={cn(
            "flex h-full flex-col w-64 transition-opacity duration-200",
            sidebarCollapsed ? "lg:opacity-0" : "lg:opacity-100"
          )}>
            {/* Logo */}
            <div
              className="flex h-16 items-center justify-between px-4"
              style={{ borderBottom: `1px solid ${theme.border}` }}
            >
              <div className="flex items-center gap-3">
                <div
                  className="h-8 w-8 rounded-lg flex items-center justify-center"
                  style={{ background: theme.gradient }}
                >
                  <span className="text-white font-bold text-sm">S</span>
                </div>
                <span
                  className="text-lg font-bold"
                  style={{
                    background: theme.gradient,
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                  }}
                >
                  Stratum AI
                </span>
              </div>
              <button
                onClick={() => setSidebarCollapsed(true)}
                className="hidden lg:flex p-1.5 rounded-md transition-colors"
                style={{ color: theme.textMuted }}
              >
                <ChevronLeftIcon className="h-4 w-4" />
              </button>
              <button
                className="lg:hidden p-1.5 rounded-md transition-colors"
                style={{ color: theme.textMuted }}
                onClick={() => setSidebarOpen(false)}
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>

            {/* Navigation */}
            <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1" id="sidebar-nav">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href
                return (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    id={item.tourId}
                    data-tour={item.dataTour}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150"
                    style={{
                      background: isActive ? theme.purpleLight : 'transparent',
                      color: isActive ? theme.purple : theme.textSecondary,
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = theme.bgElevated
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'transparent'
                      }
                    }}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <item.icon
                      className="h-5 w-5"
                      style={{ color: isActive ? theme.purple : theme.textMuted }}
                    />
                    {t(item.name)}
                  </NavLink>
                )
              })}

              {/* CDP Section */}
              <div className="pt-2">
                <button
                  onClick={() => setCdpExpanded(!cdpExpanded)}
                  className="w-full flex items-center justify-between gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150"
                  style={{
                    background: location.pathname.startsWith('/dashboard/cdp') ? theme.purpleLight : 'transparent',
                    color: location.pathname.startsWith('/dashboard/cdp') ? theme.purple : theme.textSecondary,
                  }}
                >
                  <div className="flex items-center gap-3">
                    <CircleStackIcon
                      className="h-5 w-5"
                      style={{
                        color: location.pathname.startsWith('/dashboard/cdp') ? theme.purple : theme.textMuted
                      }}
                    />
                    <span>CDP</span>
                  </div>
                  <ChevronDownIcon
                    className={cn('h-4 w-4 transition-transform duration-200', cdpExpanded && 'rotate-180')}
                    style={{ color: theme.textMuted }}
                  />
                </button>

                <AnimatePresence>
                  {cdpExpanded && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                      className="mt-1 ml-3 pl-3 space-y-0.5 overflow-hidden"
                      style={{ borderLeft: `2px solid ${theme.purpleLight}` }}
                    >
                      {cdpNavigation.map((item, index) => {
                        const isActive = location.pathname === item.href
                        return (
                          <motion.div
                            key={item.name}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.02, duration: 0.15 }}
                          >
                            <NavLink
                              to={item.href}
                              className="flex items-center gap-3 px-3 py-1.5 rounded-md text-sm transition-all duration-150"
                              style={{
                                background: isActive ? theme.purpleLight : 'transparent',
                                color: isActive ? theme.purple : theme.textSecondary,
                              }}
                              onClick={() => setSidebarOpen(false)}
                            >
                              <item.icon
                                className="h-4 w-4"
                                style={{ color: isActive ? theme.purple : theme.textMuted }}
                              />
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

            {/* Bottom section */}
            <div className="px-3 py-4 space-y-1" style={{ borderTop: `1px solid ${theme.border}` }}>
              {/* Superadmin */}
              {user?.role === 'superadmin' && (
                <div>
                  <button
                    onClick={() => setSuperadminExpanded(!superadminExpanded)}
                    className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150"
                    style={{
                      background: location.pathname.startsWith('/dashboard/superadmin') ? theme.purpleLight : 'transparent',
                      color: location.pathname.startsWith('/dashboard/superadmin') ? theme.purple : theme.textSecondary,
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <ShieldCheckIcon className="h-5 w-5" style={{ color: theme.textMuted }} />
                      <span>Superadmin</span>
                    </div>
                    <ChevronDownIcon
                      className={cn('h-4 w-4 transition-transform', superadminExpanded && 'rotate-180')}
                      style={{ color: theme.textMuted }}
                    />
                  </button>
                  {superadminExpanded && (
                    <div className="mt-1 ml-3 pl-3 space-y-0.5" style={{ borderLeft: `2px solid ${theme.purpleLight}` }}>
                      {[
                        { href: '/dashboard/superadmin', icon: ChartPieIcon, name: 'Dashboard', end: true },
                        { href: '/dashboard/superadmin/cms', icon: DocumentTextIcon, name: 'CMS' },
                        { href: '/dashboard/superadmin/users', icon: UserGroupIcon, name: 'Users' },
                      ].map((item) => (
                        <NavLink
                          key={item.href}
                          to={item.href}
                          end={item.end}
                          className="flex items-center gap-3 px-3 py-1.5 rounded-md text-sm transition-all duration-150"
                          style={{
                            background: location.pathname === item.href ? theme.purpleLight : 'transparent',
                            color: location.pathname === item.href ? theme.purple : theme.textSecondary,
                          }}
                        >
                          <item.icon className="h-4 w-4" style={{ color: theme.textMuted }} />
                          {item.name}
                        </NavLink>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Other nav items */}
              {[
                { href: '/dashboard/tenants', icon: BuildingOffice2Icon, name: 'nav.tenants' },
                { href: '/dashboard/ml-training', icon: CpuChipIcon, name: 'nav.mlTraining' },
                { href: '/dashboard/capi-setup', icon: SignalIcon, name: 'nav.capiSetup' },
                { href: '/dashboard/data-quality', icon: ChartPieIcon, name: 'nav.dataQuality' },
                { href: '/dashboard/emq-dashboard', icon: CircleStackIcon, name: 'nav.emqDashboard' },
                { href: '/dashboard/settings', icon: CogIcon, name: 'nav.settings', dataTour: 'settings' },
              ].map((item) => {
                const isActive = location.pathname === item.href
                return (
                  <NavLink
                    key={item.href}
                    to={item.href}
                    data-tour={item.dataTour}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150"
                    style={{
                      background: isActive ? theme.purpleLight : 'transparent',
                      color: isActive ? theme.purple : theme.textSecondary,
                    }}
                  >
                    <item.icon
                      className="h-5 w-5"
                      style={{ color: isActive ? theme.purple : theme.textMuted }}
                    />
                    {t(item.name)}
                  </NavLink>
                )
              })}
            </div>

            {/* User section */}
            <div className="px-3 py-4" style={{ borderTop: `1px solid ${theme.border}` }}>
              <div className="flex items-center gap-3 px-2">
                <div
                  className="h-8 w-8 rounded-full flex items-center justify-center"
                  style={{ background: theme.purpleLight }}
                >
                  <span className="text-xs font-medium" style={{ color: theme.purple }}>
                    {getUserInitials()}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: theme.textPrimary }}>
                    {user?.name || 'User'}
                  </p>
                  <p className="text-xs truncate capitalize" style={{ color: theme.textMuted }}>
                    {user?.role || 'user'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* Sidebar expand button */}
        {sidebarCollapsed && (
          <button
            onClick={() => setSidebarCollapsed(false)}
            className="hidden lg:flex fixed top-4 left-4 z-50 h-8 w-8 items-center justify-center rounded-lg transition-all duration-200"
            style={{
              background: theme.bgBase,
              border: `1px solid ${theme.border}`,
              color: theme.purple,
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
            }}
          >
            <ChevronRightIcon className="h-4 w-4" />
          </button>
        )}

        {/* Main content */}
        <div className={cn(
          "flex flex-1 flex-col overflow-hidden transition-all duration-300",
          sidebarCollapsed ? "lg:ml-0" : "lg:ml-64"
        )}>
          {/* Header */}
          <header
            className="flex h-14 items-center justify-between px-4 lg:px-6"
            style={{
              background: theme.bgBase,
              borderBottom: `1px solid ${theme.border}`,
            }}
          >
            <button
              className="lg:hidden p-2 rounded-lg transition-colors"
              style={{ color: theme.textMuted }}
              onClick={() => setSidebarOpen(true)}
            >
              <Bars3Icon className="h-5 w-5" />
            </button>

            <div className="flex-1 flex items-center justify-center">
              <CommandPalette />
            </div>

            {/* Header actions */}
            <div className="flex items-center gap-2">
              <button
                className="p-2 rounded-lg transition-colors"
                style={{ color: theme.textMuted }}
                onClick={() => setLearningHubOpen(!learningHubOpen)}
                title="Learning Hub"
                onMouseEnter={(e) => e.currentTarget.style.color = theme.purple}
                onMouseLeave={(e) => e.currentTarget.style.color = theme.textMuted}
              >
                <BookOpenIcon className="h-5 w-5" />
              </button>

              <button
                className="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
                style={{
                  color: theme.textMuted,
                  border: `1px solid ${theme.border}`,
                }}
                onClick={toggleLanguage}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = theme.purple
                  e.currentTarget.style.color = theme.purple
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = theme.border
                  e.currentTarget.style.color = theme.textMuted
                }}
              >
                {i18n.language === 'en' ? 'AR' : 'EN'}
              </button>

              <button
                onClick={() => setWhatsNewOpen(true)}
                className="relative p-2 rounded-lg transition-colors"
                style={{ color: theme.textMuted }}
                title="What's New"
                onMouseEnter={(e) => e.currentTarget.style.color = theme.purple}
                onMouseLeave={(e) => e.currentTarget.style.color = theme.textMuted}
              >
                <GiftIcon className="h-5 w-5" />
                {hasNewUpdates && (
                  <span
                    className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full"
                    style={{ background: theme.danger }}
                  />
                )}
              </button>

              <NotificationBell onClick={() => setNotificationsOpen(true)} unreadCount={3} />

              {/* User menu */}
              <div className="relative">
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 p-1.5 rounded-lg transition-colors"
                  style={{ background: userMenuOpen ? theme.bgElevated : 'transparent' }}
                >
                  <div
                    className="h-7 w-7 rounded-full flex items-center justify-center"
                    style={{ background: theme.purpleLight }}
                  >
                    <span className="text-xs font-medium" style={{ color: theme.purple }}>
                      {getUserInitials()}
                    </span>
                  </div>
                </button>

                <AnimatePresence>
                  {userMenuOpen && (
                    <>
                      <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />
                      <motion.div
                        variants={dropdownVariants}
                        initial="hidden"
                        animate="visible"
                        exit="exit"
                        className="absolute right-0 mt-2 w-48 py-1 rounded-lg z-50"
                        style={{
                          background: theme.bgBase,
                          border: `1px solid ${theme.border}`,
                          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
                        }}
                      >
                        <div className="px-3 py-2" style={{ borderBottom: `1px solid ${theme.border}` }}>
                          <p className="text-sm font-medium" style={{ color: theme.textPrimary }}>
                            {user?.name}
                          </p>
                          <p className="text-xs" style={{ color: theme.textMuted }}>
                            {user?.email}
                          </p>
                        </div>
                        <NavLink
                          to="/dashboard/settings"
                          className="flex items-center gap-2 px-3 py-2 text-sm transition-colors"
                          style={{ color: theme.textSecondary }}
                          onClick={() => setUserMenuOpen(false)}
                          onMouseEnter={(e) => e.currentTarget.style.background = theme.bgElevated}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                          <CogIcon className="w-4 h-4" />
                          {t('common.settings')}
                        </NavLink>
                        <button
                          onClick={handleLogout}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors"
                          style={{ color: theme.danger }}
                          onMouseEnter={(e) => e.currentTarget.style.background = theme.bgElevated}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
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

          <OnboardingChecklist variant="horizontal" />

          {/* Page content */}
          <main className="flex-1 overflow-y-auto p-4 lg:p-6">
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                className="h-full"
              >
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </main>
        </div>

        <LearningHub isOpen={learningHubOpen} onClose={() => setLearningHubOpen(false)} />
        <NotificationCenter isOpen={notificationsOpen} onClose={() => setNotificationsOpen(false)} />
        <WhatsNewModal isOpen={whatsNewOpen} onClose={() => setWhatsNewOpen(false)} />
        <KeyboardShortcutsModal isOpen={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
      </div>
    </div>
  )
}
