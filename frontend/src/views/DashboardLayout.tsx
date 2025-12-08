import { useState } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
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
  UserCircleIcon,
  BookOpenIcon,
  ChatBubbleLeftRightIcon,
  Squares2X2Icon,
  BuildingOffice2Icon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import LearningHub from '@/components/guide/LearningHub'
import { ThemeToggle } from '@/components/ui/ThemeToggle'

const navigation = [
  { name: 'nav.overview', href: '/overview', icon: HomeIcon, tourId: 'nav-overview' },
  { name: 'nav.dashboard', href: '/dashboard', icon: Squares2X2Icon, tourId: 'nav-dashboard' },
  { name: 'nav.campaigns', href: '/campaigns', icon: ChartBarIcon, tourId: 'nav-campaigns' },
  { name: 'nav.stratum', href: '/stratum', icon: TrophyIcon, tourId: 'nav-stratum' },
  { name: 'nav.benchmarks', href: '/benchmarks', icon: FolderIcon, tourId: 'nav-benchmarks' },
  { name: 'nav.assets', href: '/assets', icon: PhotoIcon, tourId: 'nav-assets' },
  { name: 'nav.rules', href: '/rules', icon: BoltIcon, tourId: 'nav-rules' },
  { name: 'nav.whatsapp', href: '/whatsapp', icon: ChatBubbleLeftRightIcon, tourId: 'nav-whatsapp' },
]

export default function DashboardLayout() {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [learningHubOpen, setLearningHubOpen] = useState(false)

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'ar' : 'en'
    i18n.changeLanguage(newLang)
    // Update document direction for RTL support
    document.documentElement.dir = newLang === 'ar' ? 'rtl' : 'ltr'
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
          </nav>

          {/* Admin & Settings at bottom */}
          <div className="border-t p-4 space-y-1">
            <NavLink
              to="/tenants"
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                location.pathname === '/tenants'
                  ? 'bg-gradient-stratum text-white shadow-glow-sm'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'
              )}
            >
              <BuildingOffice2Icon className="h-5 w-5" />
              {t('nav.tenants')}
            </NavLink>
            <NavLink
              to="/settings"
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                location.pathname === '/settings'
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
            <button className="flex items-center gap-2 p-2 rounded-lg hover:bg-accent transition-colors">
              <div className="h-7 w-7 rounded-full bg-gradient-stratum flex items-center justify-center">
                <span className="text-white text-xs font-medium">DU</span>
              </div>
              <span className="hidden lg:block text-sm font-medium">Demo User</span>
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-background p-4 lg:p-6">
          <Outlet />
        </main>
      </div>

      {/* Learning Hub Sidebar */}
      <LearningHub open={learningHubOpen} onClose={() => setLearningHubOpen(false)} />
    </div>
  )
}
