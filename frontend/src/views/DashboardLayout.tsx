/**
 * Dashboard Layout — COMMAND CENTER DESIGN SYSTEM
 * Premium sidebar + header layout for Stratum AI
 */

import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'framer-motion';
import { dropdownVariants } from '@/lib/animations';
import {
  LayoutDashboard,
  BarChart3,
  Image,
  Zap,
  Brain,
  TrendingUp,
  FolderKanban,
    Settings,
  Users,
  CreditCard,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  Search,
  Bell,
    ChevronDown,
  Sparkles,
  ShieldCheck,
  Rocket,
  PieChart,
      Radio,
  Database,
    Tag,
  Clock,
  Share2,
  Funnel,
  Calculator,
    UserMinus,
    Mail,
      MessageSquareText,
  Gift,
  BookOpen,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import LearningHub from '@/components/guide/LearningHub';
import { CommandPalette } from '@/components/ui/command-palette';
import { DemoBanner } from '@/components/demo/DemoBanner';
import {
    NotificationCenter,
} from '@/components/notifications/NotificationCenter';
import { useWhatsNew, WhatsNewModal } from '@/components/changelog/WhatsNew';
import { KeyboardShortcutsModal } from '@/components/ui/keyboard-shortcuts';
import { OnboardingChecklist } from '@/components/onboarding/OnboardingChecklist';
import { useAuth } from '@/contexts/AuthContext';
import type { AppRole } from '@/components/auth/ProtectedRoute';
import { TrustGateIndicator } from '@/components/ui/TrustGateIndicator';
import { OnboardingChat, OnboardingChatButton } from '@/components/onboarding';
import { FeedbackWidget } from '@/components/feedback/FeedbackWidget';
import ClientContextSwitcher from '@/components/client/ClientContextSwitcher';
import TenantSwitcher from '@/components/tenant/TenantSwitcher';

/* ═══════════════════════════════════════════════════════════════
   SIDEBAR VISIBILITY — mirrors backend SIDEBAR_VISIBILITY
   ═══════════════════════════════════════════════════════════════ */
const SIDEBAR_VISIBILITY: Record<AppRole, string[]> = {
  superadmin: [
    'dashboard', 'clients', 'campaigns', 'demographics', 'analytics',
    'reports', 'creatives', 'rules', 'ml', 'notifications',
    'settings', 'users', 'tenants', 'audit', 'billing', 'profile',
    'cdp', 'knowledge-graph', 'newsletter', 'superadmin',
    'benchmarks', 'competitors', 'custom-autopilot', 'custom-reports',
    'integrations', 'stratum', 'whatsapp',
  ],
  admin: [
    'dashboard', 'clients', 'campaigns', 'demographics', 'analytics',
    'reports', 'creatives', 'rules', 'ml', 'notifications',
    'settings', 'users', 'audit', 'billing', 'profile',
    'cdp', 'knowledge-graph', 'newsletter',
    'benchmarks', 'competitors', 'custom-autopilot', 'custom-reports',
    'integrations', 'stratum', 'whatsapp',
    'tenants',
  ],
  manager: [
    'dashboard', 'clients', 'campaigns', 'demographics', 'analytics',
    'reports', 'creatives', 'rules', 'notifications', 'profile',
    'cdp', 'knowledge-graph', 'newsletter',
    'benchmarks', 'competitors', 'stratum', 'whatsapp',
  ],
  analyst: [
    'dashboard', 'clients', 'campaigns', 'demographics', 'analytics',
    'reports', 'creatives', 'rules', 'notifications', 'profile',
    'cdp', 'newsletter',
    'benchmarks', 'stratum', 'whatsapp',
  ],
  viewer: [
    'dashboard', 'campaigns', 'demographics', 'analytics',
    'reports', 'creatives', 'notifications', 'profile',
  ],
};

function canSeeSection(role: string | undefined, section: string): boolean {
  if (!role) return false;
  const visible = SIDEBAR_VISIBILITY[role as AppRole];
  if (!visible) return false;
  return visible.includes(section);
}

/* ═══════════════════════════════════════════════════════════════
   NAVIGATION DATA
   ═══════════════════════════════════════════════════════════════ */
interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  section: string;
  tourId?: string;
  dataTour?: string;
}

const mainNav: NavItem[] = [
  { name: 'nav.overview', href: '/dashboard/overview', icon: LayoutDashboard, section: 'dashboard', tourId: 'nav-overview', dataTour: 'overview' },
  { name: 'nav.campaigns', href: '/dashboard/campaigns', icon: BarChart3, section: 'campaigns', tourId: 'nav-campaigns' },
  { name: 'nav.analytics', href: '/dashboard/custom-dashboard', icon: PieChart, section: 'dashboard', tourId: 'nav-dashboard' },
  { name: 'nav.assets', href: '/dashboard/assets', icon: Image, section: 'creatives', tourId: 'nav-assets' },
  { name: 'nav.rules', href: '/dashboard/rules', icon: Zap, section: 'rules', tourId: 'nav-rules' },
];

const intelligenceNav: NavItem[] = [
  { name: 'Insights', href: '/dashboard/knowledge-graph/insights', icon: Brain, section: 'knowledge-graph' },
  { name: 'Predictions', href: '/dashboard/stratum', icon: TrendingUp, section: 'stratum', tourId: 'nav-stratum' },
  { name: 'Benchmarks', href: '/dashboard/benchmarks', icon: FolderKanban, section: 'benchmarks', tourId: 'nav-benchmarks' },
  { name: 'Simulator', href: '/dashboard/custom-autopilot-rules', icon: Sparkles, section: 'custom-autopilot' },
];

const platformNav: NavItem[] = [
  { name: 'Integrations', href: '/dashboard/integrations', icon: Radio, section: 'integrations' },
  { name: 'CDP', href: '/dashboard/cdp', icon: Database, section: 'cdp' },
  { name: 'WhatsApp', href: '/dashboard/whatsapp', icon: MessageSquareText, section: 'whatsapp', tourId: 'nav-whatsapp' },
  { name: 'Newsletter', href: '/dashboard/newsletter', icon: Mail, section: 'newsletter' },
];

const settingsNav: NavItem[] = [
  { name: 'nav.settings', href: '/dashboard/settings', icon: Settings, section: 'settings', dataTour: 'settings' },
  { name: 'Team', href: '/dashboard/tenants', icon: Users, section: 'tenants' },
  { name: 'Billing', href: '/dashboard/ml-training', icon: CreditCard, section: 'billing' },
];

const cdpSubNav: NavItem[] = [
  { name: 'Overview', href: '/dashboard/cdp', icon: Database, section: 'cdp' },
  { name: 'Profiles', href: '/dashboard/cdp/profiles', icon: Users, section: 'cdp' },
  { name: 'Segments', href: '/dashboard/cdp/segments', icon: Tag, section: 'cdp' },
  { name: 'Events', href: '/dashboard/cdp/events', icon: Clock, section: 'cdp' },
  { name: 'Identity Graph', href: '/dashboard/cdp/identity', icon: Share2, section: 'cdp' },
  { name: 'Funnels', href: '/dashboard/cdp/funnels', icon: Funnel, section: 'cdp' },
  { name: 'Computed Traits', href: '/dashboard/cdp/computed-traits', icon: Calculator, section: 'cdp' },
  { name: 'Predictive Churn', href: '/dashboard/cdp/predictive-churn', icon: UserMinus, section: 'cdp' },
];

/* ═══════════════════════════════════════════════════════════════
   COMPONENT
   ═══════════════════════════════════════════════════════════════ */
export default function DashboardLayout() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [whatsNewOpen, setWhatsNewOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [onboardingChatOpen, setOnboardingChatOpen] = useState(false);
  const [learningHubOpen, setLearningHubOpen] = useState(false);
  const [cdpExpanded, setCdpExpanded] = useState(location.pathname.startsWith('/dashboard/cdp'));
  const [superadminExpanded, setSuperadminExpanded] = useState(location.pathname.startsWith('/dashboard/superadmin'));
  const { hasNewUpdates } = useWhatsNew();

  useEffect(() => {
    document.documentElement.classList.remove('light');
    document.documentElement.classList.add('dark');
    localStorage.setItem('stratum-theme', 'dark');
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getUserInitials = () => {
    if (!user?.name) return 'U';
    const names = user.name.split(' ');
    return names.map((n) => n[0]).join('').toUpperCase().slice(0, 2);
  };

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'ar' : 'en';
    i18n.changeLanguage(newLang);
    document.documentElement.dir = newLang === 'ar' ? 'rtl' : 'ltr';
  };

  /* ── Nav Link Renderer ────────────────────────────────────── */
  const renderNavLink = (item: NavItem, variant: 'default' | 'sub' = 'default') => {
    const isActive = location.pathname === item.href;
    return (
      <NavLink
        key={item.name}
        to={item.href}
        id={item.tourId}
        data-tour={item.dataTour}
        onClick={() => setSidebarOpen(false)}
        className={cn(
          'group flex items-center gap-3 rounded-lg text-sm font-medium transition-colors duration-200',
          variant === 'default' ? 'px-3 py-2' : 'px-3 py-1.5',
          isActive
            ? 'border-l-2 border-[#FF8C00] bg-[#FF8C00]/5 text-[#FF8C00]'
            : 'text-[#8B92A8] hover:text-[#F0EDE5] hover:bg-[#F0EDE5]/[0.03]'
        )}
      >
        <item.icon className={cn('flex-shrink-0', variant === 'default' ? 'h-5 w-5' : 'h-4 w-4')} />
        <span className="truncate">{t(item.name)}</span>
      </NavLink>
    );
  };

  /* ── Section Header ───────────────────────────────────────── */
  const SectionHeader = ({ title }: { title: string }) => (
    <div className="px-3 pt-5 pb-2">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-[#5A6278]">
        {title}
      </span>
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-[#080C14]" style={{ fontFamily: 'Satoshi, system-ui, sans-serif' }}>
      <DemoBanner variant="top" />

      <div className="flex flex-1 overflow-hidden relative z-10">
        {/* Mobile overlay */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
              onClick={() => setSidebarOpen(false)}
            />
          )}
        </AnimatePresence>

        {/* ═══════════════════════════════════════════════════════
            SIDEBAR
           ═══════════════════════════════════════════════════════ */}
        <aside
          data-tour="sidebar"
          aria-label="Main navigation"
          className={cn(
            'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-[#1E2740] bg-[#0A0E17] transition-[width] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full',
            'lg:translate-x-0',
            sidebarCollapsed ? 'lg:w-0 lg:overflow-hidden lg:border-r-0' : 'w-[240px] lg:w-[240px]'
          )}
        >
          <div className={cn('flex h-full flex-col w-[240px]', sidebarCollapsed ? 'lg:opacity-0' : 'lg:opacity-100')}>
            {/* Logo */}
            <div className="flex h-16 items-center justify-between px-4 border-b border-[#1E2740]">
              <div className="flex items-center gap-3">
                <img src="/images/stratum-logo.png" alt="Stratum AI" className="h-7" loading="lazy" decoding="async" />
              </div>
              <button
                onClick={() => setSidebarCollapsed(true)}
                className="hidden lg:flex p-1.5 rounded-md text-[#5A6278] hover:text-[#F0EDE5] transition-colors duration-200"
                aria-label="Collapse sidebar"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                className="lg:hidden p-1.5 rounded-md text-[#5A6278] hover:text-[#F0EDE5] transition-colors duration-200"
                onClick={() => setSidebarOpen(false)}
                aria-label="Close navigation"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Navigation */}
            <nav className="flex-1 overflow-y-auto px-3 py-2 scrollbar-thin" id="sidebar-nav">
              {/* Main */}
              <SectionHeader title={t('nav.main') || 'Main'} />
              <div className="space-y-0.5">
                {mainNav.filter((item) => canSeeSection(user?.role, item.section)).map((item) => renderNavLink(item))}
              </div>

              {/* Intelligence */}
              <SectionHeader title={t('nav.intelligence') || 'Intelligence'} />
              <div className="space-y-0.5">
                {intelligenceNav.filter((item) => canSeeSection(user?.role, item.section)).map((item) => renderNavLink(item))}
              </div>

              {/* Platform */}
              <SectionHeader title={t('nav.platform') || 'Platform'} />
              <div className="space-y-0.5">
                {platformNav.filter((item) => canSeeSection(user?.role, item.section)).map((item) => {
                  if (item.name === 'CDP') {
                    return (
                      <div key={item.name}>
                        <button
                          onClick={() => setCdpExpanded(!cdpExpanded)}
                          aria-expanded={cdpExpanded}
                          className={cn(
                            'w-full flex items-center justify-between gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200',
                            location.pathname.startsWith('/dashboard/cdp')
                              ? 'border-l-2 border-[#FF8C00] bg-[#FF8C00]/5 text-[#FF8C00]'
                              : 'text-[#8B92A8] hover:text-[#F0EDE5] hover:bg-[#F0EDE5]/[0.03]'
                          )}
                        >
                          <div className="flex items-center gap-3">
                            <Database className="h-5 w-5 flex-shrink-0" />
                            <span>CDP</span>
                          </div>
                          <ChevronDown className={cn('h-4 w-4 transition-transform duration-200', cdpExpanded && 'rotate-180')} />
                        </button>
                        <AnimatePresence>
                          {cdpExpanded && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              exit={{ opacity: 0, height: 0 }}
                              transition={{ duration: 0.2 }}
                              className="mt-1 ml-2 pl-3 space-y-0.5 overflow-hidden border-l border-[#1E2740]"
                            >
                              {cdpSubNav.filter((sub) => canSeeSection(user?.role, sub.section)).map((sub) => renderNavLink(sub, 'sub'))}
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    );
                  }
                  return renderNavLink(item);
                })}
              </div>

              {/* Settings */}
              <SectionHeader title={t('nav.settings') || 'Settings'} />
              <div className="space-y-0.5">
                {settingsNav.filter((item) => canSeeSection(user?.role, item.section)).map((item) => renderNavLink(item))}
              </div>

              {/* Superadmin */}
              {user?.role === 'superadmin' && (
                <div className="mt-4">
                  <SectionHeader title="Admin" />
                  <div className="space-y-0.5">
                    <button
                      onClick={() => setSuperadminExpanded(!superadminExpanded)}
                      aria-expanded={superadminExpanded}
                      className={cn(
                        'w-full flex items-center justify-between gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200',
                        location.pathname.startsWith('/dashboard/superadmin')
                          ? 'border-l-2 border-[#FF8C00] bg-[#FF8C00]/5 text-[#FF8C00]'
                          : 'text-[#8B92A8] hover:text-[#F0EDE5] hover:bg-[#F0EDE5]/[0.03]'
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <ShieldCheck className="h-5 w-5 flex-shrink-0" />
                        <span>Superadmin</span>
                      </div>
                      <ChevronDown className={cn('h-4 w-4 transition-transform duration-200', superadminExpanded && 'rotate-180')} />
                    </button>
                    <AnimatePresence>
                      {superadminExpanded && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          transition={{ duration: 0.2 }}
                          className="mt-1 ml-2 pl-3 space-y-0.5 overflow-hidden border-l border-[#1E2740]"
                        >
                          {[
                            { href: '/dashboard/superadmin', icon: PieChart, name: 'Dashboard' },
                            { href: '/dashboard/superadmin/users', icon: Users, name: 'Users' },
                            { href: '/dashboard/superadmin/launch-readiness', icon: Rocket, name: 'Launch Readiness' },
                          ].map((sub) => {
                            const isActive = location.pathname === sub.href;
                            return (
                              <NavLink
                                key={sub.href}
                                to={sub.href}
                                className={cn(
                                  'flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm transition-colors duration-200',
                                  isActive
                                    ? 'border-l-2 border-[#FF8C00] bg-[#FF8C00]/5 text-[#FF8C00]'
                                    : 'text-[#8B92A8] hover:text-[#F0EDE5] hover:bg-[#F0EDE5]/[0.03]'
                                )}
                              >
                                <sub.icon className="h-4 w-4 flex-shrink-0" />
                                {sub.name}
                              </NavLink>
                            );
                          })}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              )}
            </nav>

            {/* User Section */}
            <div className="p-3 border-t border-[#1E2740]">
              <div className="flex items-center gap-3 px-2 py-2">
                <div className="h-9 w-9 rounded-lg bg-[#FF8C00]/10 flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-semibold text-[#FF8C00]">{getUserInitials()}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[#F0EDE5] truncate">{user?.name || 'User'}</p>
                  <p className="text-xs text-[#5A6278] truncate capitalize">{user?.role || 'analyst'}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-1.5 rounded-md text-[#5A6278] hover:text-[#E85D5D] hover:bg-[#E85D5D]/5 transition-colors duration-200"
                  aria-label="Log out"
                  title="Log out"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </aside>

        {/* Sidebar expand button (desktop) */}
        {sidebarCollapsed && (
          <button
            onClick={() => setSidebarCollapsed(false)}
            aria-label="Expand sidebar"
            className="hidden lg:flex fixed top-4 left-4 z-50 h-8 w-8 items-center justify-center rounded-lg bg-[#0F1320] border border-[#1E2740] text-[#FF8C00] hover:border-[#FF8C00]/30 transition-colors duration-200"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        )}

        {/* ═══════════════════════════════════════════════════════
            MAIN CONTENT
           ═══════════════════════════════════════════════════════ */}
        <main
          className={cn(
            'flex flex-1 flex-col overflow-hidden transition-[margin] duration-300',
            sidebarCollapsed ? 'lg:ml-0' : 'lg:ml-[240px]'
          )}
        >
          {/* Header */}
          <header className="flex h-16 items-center justify-between px-6 bg-[#080C14] border-b border-[#1E2740]">
            {/* Left: Mobile hamburger + breadcrumb */}
            <div className="flex items-center gap-4">
              <button
                className="lg:hidden p-2 rounded-lg text-[#5A6278] hover:text-[#F0EDE5] transition-colors duration-200"
                onClick={() => setSidebarOpen(true)}
                aria-label="Open navigation"
              >
                <Menu className="h-5 w-5" />
              </button>
              <h1 className="text-sm font-medium text-[#F0EDE5] hidden sm:block">
                {location.pathname.split('/').filter(Boolean).slice(1).map((part) => (
                  <span key={part} className="capitalize">{part.replace(/-/g, ' ')}</span>
                )).reduce((prev, curr, i) => (
                  <span key={i}>
                    {prev}
                    <span className="mx-2 text-[#1E2740]">/</span>
                    {curr}
                  </span>
                ), <span key="root" className="text-[#5A6278]">Dashboard</span>)}
              </h1>
            </div>

            {/* Center: Global Search */}
            <div className="flex-1 max-w-md mx-4 hidden md:block">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#5A6278]" />
                <CommandPalette />
              </div>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-2">
              <TenantSwitcher />
              <ClientContextSwitcher />

              <button
                onClick={() => setLearningHubOpen(!learningHubOpen)}
                className="p-2 rounded-lg text-[#8B92A8] hover:text-[#F0EDE5] hover:bg-[#F0EDE5]/[0.03] transition-colors duration-200"
                aria-label="Learning Hub"
                title="Learning Hub"
              >
                <BookOpen className="h-5 w-5" />
              </button>

              <button
                onClick={() => setWhatsNewOpen(true)}
                className="relative p-2 rounded-lg text-[#8B92A8] hover:text-[#F0EDE5] hover:bg-[#F0EDE5]/[0.03] transition-colors duration-200"
                aria-label="What's New"
                title="What's New"
              >
                <Gift className="h-5 w-5" />
                {hasNewUpdates && (
                  <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-[#E85D5D]" />
                )}
              </button>

              <button
                onClick={() => setNotificationsOpen(true)}
                className="relative p-2 rounded-lg text-[#8B92A8] hover:text-[#F0EDE5] hover:bg-[#F0EDE5]/[0.03] transition-colors duration-200"
                aria-label="Notifications"
                title="Notifications"
              >
                <Bell className="h-5 w-5" />
                <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-[#FF1F6D]" />
              </button>

              <button
                className="hidden sm:flex px-2.5 py-1 rounded-md text-xs font-medium text-[#8B92A8] border border-[#1E2740] hover:text-[#F0EDE5] hover:border-[#1E2740] transition-colors duration-200"
                onClick={toggleLanguage}
              >
                {i18n.language === 'en' ? 'AR' : 'EN'}
              </button>

              {/* User dropdown */}
              <div className="relative">
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 p-1.5 rounded-lg transition-colors duration-200 hover:bg-[#F0EDE5]/[0.03]"
                >
                  <div className="h-8 w-8 rounded-lg bg-[#FF8C00]/10 flex items-center justify-center">
                    <span className="text-xs font-semibold text-[#FF8C00]">{getUserInitials()}</span>
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
                        className="absolute right-0 mt-2 w-52 py-1 rounded-xl z-50 bg-[#0F1320] border border-[#1E2740] shadow-xl"
                      >
                        <div className="px-3 py-2 border-b border-[#1E2740]">
                          <p className="text-sm font-medium text-[#F0EDE5]">{user?.name}</p>
                          <p className="text-xs text-[#5A6278]">{user?.email}</p>
                        </div>
                        <NavLink
                          to="/dashboard/settings"
                          className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg mx-1 text-[#8B92A8] hover:text-[#F0EDE5] hover:bg-[#F0EDE5]/[0.03] transition-colors duration-200"
                          onClick={() => setUserMenuOpen(false)}
                        >
                          <Settings className="w-4 h-4" />
                          {t('common.settings')}
                        </NavLink>
                        <button
                          onClick={() => {
                            setUserMenuOpen(false);
                            handleLogout();
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg mx-1 text-[#E85D5D] hover:bg-[#E85D5D]/5 transition-colors duration-200"
                        >
                          <LogOut className="w-4 h-4" />
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
          <main className="flex-1 overflow-y-auto p-6 lg:p-8">
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
        </main>

        {/* Floating widgets */}
        <LearningHub isOpen={learningHubOpen} onClose={() => setLearningHubOpen(false)} />
        <NotificationCenter isOpen={notificationsOpen} onClose={() => setNotificationsOpen(false)} />
        <WhatsNewModal isOpen={whatsNewOpen} onClose={() => setWhatsNewOpen(false)} />
        <KeyboardShortcutsModal isOpen={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
        <TrustGateIndicator />
        {!onboardingChatOpen && <OnboardingChatButton onClick={() => setOnboardingChatOpen(true)} />}
        <OnboardingChat
          isOpen={onboardingChatOpen}
          onClose={() => setOnboardingChatOpen(false)}
          onComplete={() => navigate('/dashboard')}
          initialName={user?.name}
          initialEmail={user?.email}
          language={i18n.language}
        />
        <FeedbackWidget />
      </div>
    </div>
  );
}
