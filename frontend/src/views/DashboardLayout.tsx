/**
 * Dashboard Layout - DARK THEME EDITION
 * Matches landing page with purple/cyan gradients
 */

import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'framer-motion';
import { dropdownVariants } from '@/lib/animations';
import {
  AdjustmentsHorizontalIcon,
  ArrowRightOnRectangleIcon,
  ArrowUpOnSquareIcon,
  Bars3Icon,
  BoltIcon,
  BookOpenIcon,
  BuildingOffice2Icon,
  CalculatorIcon,
  ChartBarIcon,
  ChartPieIcon,
  ChatBubbleLeftRightIcon,
  ChevronDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CircleStackIcon,
  ClockIcon,
  CogIcon,
  CpuChipIcon,
  DocumentChartBarIcon,
  DocumentTextIcon,
  EyeIcon,
  FolderIcon,
  FunnelIcon,
  GiftIcon,
  HomeIcon,
  PhotoIcon,
  PresentationChartBarIcon,
  ShareIcon,
  ShieldCheckIcon,
  ShieldExclamationIcon,
  SignalIcon,
  Squares2X2Icon,
  TagIcon,
  TrophyIcon,
  UserGroupIcon,
  UserMinusIcon,
  XMarkIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
  MapIcon,
  CurrencyDollarIcon,
  EnvelopeIcon,
  DocumentDuplicateIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import LearningHub from '@/components/guide/LearningHub';
import { CommandPalette } from '@/components/ui/command-palette';
import { DemoBanner } from '@/components/demo/DemoBanner';
import {
  NotificationBell,
  NotificationCenter,
} from '@/components/notifications/NotificationCenter';
import { useWhatsNew, WhatsNewModal } from '@/components/changelog/WhatsNew';
import { KeyboardShortcutsModal } from '@/components/ui/keyboard-shortcuts';
import { OnboardingChecklist } from '@/components/onboarding/OnboardingChecklist';
import { useAuth } from '@/contexts/AuthContext';
import type { AppRole } from '@/components/auth/ProtectedRoute';
import { NeuralNetworkBg } from '@/components/ui/NeuralNetworkBg';
import { TrustGateIndicator } from '@/components/ui/TrustGateIndicator';
import { OnboardingChat, OnboardingChatButton } from '@/components/onboarding';
import { FeedbackWidget } from '@/components/feedback/FeedbackWidget';
import ClientContextSwitcher from '@/components/client/ClientContextSwitcher';

/**
 * Sidebar visibility per role — mirrors backend SIDEBAR_VISIBILITY.
 * Each role sees only the sections listed here.
 */
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

/** Check if current user role can see a given sidebar section */
function canSeeSection(role: string | undefined, section: string): boolean {
  if (!role) return false;
  const visible = SIDEBAR_VISIBILITY[role as AppRole];
  if (!visible) return false;
  return visible.includes(section);
}

// Stratum AI Dashboard Theme - Midnight Teal Glass
const theme = {
  primary: '#00c7be',                     // Midnight Teal
  primaryLight: 'rgba(0, 199, 190, 0.15)',
  gold: '#e2b347',                        // CTA accent
  green: '#34c759',                       // Jade
  orange: '#f59e0b',
  purple: '#a78bfa',
  cyan: '#00c7be',
  bgBase: '#0b1215',                      // Midnight Ocean
  bgCard: 'rgba(255, 255, 255, 0.05)',    // Glass surface
  bgSurface: 'rgba(255, 255, 255, 0.08)',
  bgOverlay: 'rgba(11, 18, 21, 0.75)',
  textPrimary: 'rgba(245, 245, 247, 0.92)',
  textSecondary: 'rgba(245, 245, 247, 0.6)',
  textMuted: 'rgba(245, 245, 247, 0.35)',
  border: 'rgba(255, 255, 255, 0.08)',
  borderHover: 'rgba(255, 255, 255, 0.15)',
  borderGold: 'rgba(226, 179, 71, 0.2)',
  success: '#34c759',
  danger: '#ff6b6b',
};

const navigation = [
  {
    name: 'nav.overview',
    href: '/dashboard/overview',
    icon: HomeIcon,
    tourId: 'nav-overview',
    dataTour: 'overview',
    section: 'dashboard',
  },
  { name: 'nav.dashboard', href: '/dashboard', icon: Squares2X2Icon, tourId: 'nav-dashboard', section: 'dashboard' },
  {
    name: 'nav.campaigns',
    href: '/dashboard/campaigns',
    icon: ChartBarIcon,
    tourId: 'nav-campaigns',
    section: 'campaigns',
  },
  { name: 'nav.stratum', href: '/dashboard/stratum', icon: TrophyIcon, tourId: 'nav-stratum', section: 'stratum' },
  {
    name: 'nav.benchmarks',
    href: '/dashboard/benchmarks',
    icon: FolderIcon,
    tourId: 'nav-benchmarks',
    section: 'benchmarks',
  },
  {
    name: 'Competitor Intelligence',
    href: '/dashboard/competitors',
    icon: EyeIcon,
    tourId: 'nav-competitors',
    section: 'competitors',
  },
  { name: 'nav.assets', href: '/dashboard/assets', icon: PhotoIcon, tourId: 'nav-assets', section: 'creatives' },
  { name: 'nav.rules', href: '/dashboard/rules', icon: BoltIcon, tourId: 'nav-rules', section: 'rules' },
  {
    name: 'Custom Autopilot',
    href: '/dashboard/custom-autopilot-rules',
    icon: AdjustmentsHorizontalIcon,
    tourId: 'nav-custom-autopilot',
    section: 'custom-autopilot',
  },
  {
    name: 'Custom Reports',
    href: '/dashboard/custom-reports',
    icon: DocumentChartBarIcon,
    tourId: 'nav-custom-reports',
    section: 'custom-reports',
  },
  {
    name: 'nav.whatsapp',
    href: '/dashboard/whatsapp',
    icon: ChatBubbleLeftRightIcon,
    tourId: 'nav-whatsapp',
    section: 'whatsapp',
  },
];

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
];

const kgNavigation = [
  { name: 'Insights', href: '/dashboard/knowledge-graph/insights', icon: SparklesIcon },
  { name: 'Problem Detection', href: '/dashboard/knowledge-graph/problems', icon: ExclamationTriangleIcon },
  { name: 'Revenue Attribution', href: '/dashboard/knowledge-graph/revenue', icon: CurrencyDollarIcon },
  { name: 'Journey Explorer', href: '/dashboard/knowledge-graph/journeys', icon: MapIcon },
];

const newsletterNavigation = [
  { name: 'Overview', href: '/dashboard/newsletter', icon: EnvelopeIcon },
  { name: 'Campaigns', href: '/dashboard/newsletter/campaigns', icon: DocumentTextIcon },
  { name: 'Templates', href: '/dashboard/newsletter/templates', icon: DocumentDuplicateIcon },
  { name: 'Subscribers', href: '/dashboard/newsletter/subscribers', icon: UserGroupIcon },
];

export default function DashboardLayout() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [learningHubOpen, setLearningHubOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [cdpExpanded, setCdpExpanded] = useState(location.pathname.startsWith('/dashboard/cdp'));
  const [kgExpanded, setKgExpanded] = useState(location.pathname.startsWith('/dashboard/knowledge-graph'));
  const [newsletterExpanded, setNewsletterExpanded] = useState(location.pathname.startsWith('/dashboard/newsletter'));
  const [superadminExpanded, setSuperadminExpanded] = useState(
    location.pathname.startsWith('/dashboard/superadmin')
  );
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [whatsNewOpen, setWhatsNewOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [onboardingChatOpen, setOnboardingChatOpen] = useState(false);
  const { hasNewUpdates } = useWhatsNew();

  // Set dark theme
  useEffect(() => {
    document.documentElement.classList.remove('light');
    document.documentElement.classList.add('dark');
    localStorage.setItem('stratum-theme', 'dark');
  }, []);

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'ar' : 'en';
    i18n.changeLanguage(newLang);
    document.documentElement.dir = newLang === 'ar' ? 'rtl' : 'ltr';
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getUserInitials = () => {
    if (!user?.name) return 'U';
    const names = user.name.split(' ');
    return names
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: theme.bgBase }}>
      {/* Neural Network Background */}
      <NeuralNetworkBg />

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
            backdropFilter: 'blur(40px) saturate(1.8)',
            WebkitBackdropFilter: 'blur(40px) saturate(1.8)',
            borderRight: `1px solid ${theme.border}`,
          }}
        >
          <div
            className={cn(
              'flex h-full flex-col w-64 transition-opacity duration-200',
              sidebarCollapsed ? 'lg:opacity-0' : 'lg:opacity-100'
            )}
          >
            {/* Logo */}
            <div
              className="flex h-16 items-center justify-between px-4"
              style={{ borderBottom: `1px solid ${theme.border}` }}
            >
              <div className="flex items-center gap-3">
                <img src="/images/stratum-logo.svg" alt="Stratum AI" className="h-7" style={{ filter: 'invert(1) brightness(2)' }} />
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
              {navigation.filter((item) => canSeeSection(user?.role, item.section)).map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    id={item.tourId}
                    data-tour={item.dataTour}
                    className="flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-150"
                    style={{
                      background: isActive ? theme.primaryLight : 'transparent',
                      color: isActive ? theme.primary : theme.textSecondary,
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = theme.bgSurface;
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'transparent';
                      }
                    }}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <item.icon
                      className="h-5 w-5"
                      style={{ color: isActive ? theme.primary : theme.textMuted }}
                    />
                    {t(item.name)}
                  </NavLink>
                );
              })}

              {/* CDP Section — visible to superadmin, admin, manager, analyst */}
              {canSeeSection(user?.role, 'cdp') && (
              <div className="pt-2">
                <button
                  onClick={() => setCdpExpanded(!cdpExpanded)}
                  className="w-full flex items-center justify-between gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-150"
                  style={{
                    background: location.pathname.startsWith('/dashboard/cdp')
                      ? theme.primaryLight
                      : 'transparent',
                    color: location.pathname.startsWith('/dashboard/cdp')
                      ? theme.primary
                      : theme.textSecondary,
                  }}
                >
                  <div className="flex items-center gap-3">
                    <CircleStackIcon
                      className="h-5 w-5"
                      style={{
                        color: location.pathname.startsWith('/dashboard/cdp')
                          ? theme.primary
                          : theme.textMuted,
                      }}
                    />
                    <span>CDP</span>
                  </div>
                  <ChevronDownIcon
                    className={cn(
                      'h-4 w-4 transition-transform duration-200',
                      cdpExpanded && 'rotate-180'
                    )}
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
                      style={{ borderLeft: `2px solid ${theme.primaryLight}` }}
                    >
                      {cdpNavigation.map((item, index) => {
                        const isActive = location.pathname === item.href;
                        return (
                          <motion.div
                            key={item.name}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.02, duration: 0.15 }}
                          >
                            <NavLink
                              to={item.href}
                              className="flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm transition-all duration-150"
                              style={{
                                background: isActive ? theme.primaryLight : 'transparent',
                                color: isActive ? theme.primary : theme.textSecondary,
                              }}
                              onClick={() => setSidebarOpen(false)}
                            >
                              <item.icon
                                className="h-4 w-4"
                                style={{ color: isActive ? theme.primary : theme.textMuted }}
                              />
                              {item.name}
                            </NavLink>
                          </motion.div>
                        );
                      })}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              )}

              {/* Knowledge Graph Section — visible to superadmin, admin, manager */}
              {canSeeSection(user?.role, 'knowledge-graph') && (
              <div className="pt-2">
                <button
                  onClick={() => setKgExpanded(!kgExpanded)}
                  className="w-full flex items-center justify-between gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-150"
                  style={{
                    background: location.pathname.startsWith('/dashboard/knowledge-graph')
                      ? theme.primaryLight
                      : 'transparent',
                    color: location.pathname.startsWith('/dashboard/knowledge-graph')
                      ? theme.primary
                      : theme.textSecondary,
                  }}
                >
                  <div className="flex items-center gap-3">
                    <SparklesIcon
                      className="h-5 w-5"
                      style={{
                        color: location.pathname.startsWith('/dashboard/knowledge-graph')
                          ? theme.primary
                          : theme.textMuted,
                      }}
                    />
                    <span>Knowledge Graph</span>
                  </div>
                  <ChevronDownIcon
                    className={cn(
                      'h-4 w-4 transition-transform duration-200',
                      kgExpanded && 'rotate-180'
                    )}
                    style={{ color: theme.textMuted }}
                  />
                </button>

                <AnimatePresence>
                  {kgExpanded && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                      className="mt-1 ml-3 pl-3 space-y-0.5 overflow-hidden"
                      style={{ borderLeft: `2px solid ${theme.primaryLight}` }}
                    >
                      {kgNavigation.map((item, index) => {
                        const isActive = location.pathname === item.href;
                        return (
                          <motion.div
                            key={item.name}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.02, duration: 0.15 }}
                          >
                            <NavLink
                              to={item.href}
                              className="flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm transition-all duration-150"
                              style={{
                                background: isActive ? theme.primaryLight : 'transparent',
                                color: isActive ? theme.primary : theme.textSecondary,
                              }}
                              onClick={() => setSidebarOpen(false)}
                            >
                              <item.icon
                                className="h-4 w-4"
                                style={{ color: isActive ? theme.primary : theme.textMuted }}
                              />
                              {item.name}
                            </NavLink>
                          </motion.div>
                        );
                      })}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              )}

              {/* Newsletter Section — visible to superadmin, admin, manager, analyst */}
              {canSeeSection(user?.role, 'newsletter') && (
              <div className="pt-2">
                <button
                  onClick={() => setNewsletterExpanded(!newsletterExpanded)}
                  className="w-full flex items-center justify-between gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-150"
                  style={{
                    background: location.pathname.startsWith('/dashboard/newsletter')
                      ? theme.primaryLight
                      : 'transparent',
                    color: location.pathname.startsWith('/dashboard/newsletter')
                      ? theme.primary
                      : theme.textSecondary,
                  }}
                >
                  <div className="flex items-center gap-3">
                    <EnvelopeIcon
                      className="h-5 w-5"
                      style={{
                        color: location.pathname.startsWith('/dashboard/newsletter')
                          ? theme.primary
                          : theme.textMuted,
                      }}
                    />
                    <span>Newsletter</span>
                  </div>
                  <ChevronDownIcon
                    className={cn(
                      'h-4 w-4 transition-transform duration-200',
                      newsletterExpanded && 'rotate-180'
                    )}
                    style={{ color: theme.textMuted }}
                  />
                </button>

                <AnimatePresence>
                  {newsletterExpanded && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                      className="mt-1 ml-3 pl-3 space-y-0.5 overflow-hidden"
                      style={{ borderLeft: `2px solid ${theme.primaryLight}` }}
                    >
                      {newsletterNavigation.map((item, index) => {
                        const isActive = location.pathname === item.href;
                        return (
                          <motion.div
                            key={item.name}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.02, duration: 0.15 }}
                          >
                            <NavLink
                              to={item.href}
                              className="flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm transition-all duration-150"
                              style={{
                                background: isActive ? theme.primaryLight : 'transparent',
                                color: isActive ? theme.primary : theme.textSecondary,
                              }}
                              onClick={() => setSidebarOpen(false)}
                            >
                              <item.icon
                                className="h-4 w-4"
                                style={{ color: isActive ? theme.primary : theme.textMuted }}
                              />
                              {item.name}
                            </NavLink>
                          </motion.div>
                        );
                      })}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              )}
            </nav>

            {/* Bottom section */}
            <div className="px-3 py-4 space-y-1" style={{ borderTop: `1px solid ${theme.border}` }}>
              {/* Superadmin */}
              {user?.role === 'superadmin' && (
                <div>
                  <button
                    onClick={() => setSuperadminExpanded(!superadminExpanded)}
                    className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm font-medium transition-all duration-150"
                    style={{
                      background: location.pathname.startsWith('/dashboard/superadmin')
                        ? theme.primaryLight
                        : 'transparent',
                      color: location.pathname.startsWith('/dashboard/superadmin')
                        ? theme.primary
                        : theme.textSecondary,
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <ShieldCheckIcon className="h-5 w-5" style={{ color: theme.textMuted }} />
                      <span>Superadmin</span>
                    </div>
                    <ChevronDownIcon
                      className={cn(
                        'h-4 w-4 transition-transform',
                        superadminExpanded && 'rotate-180'
                      )}
                      style={{ color: theme.textMuted }}
                    />
                  </button>
                  {superadminExpanded && (
                    <div
                      className="mt-1 ml-3 pl-3 space-y-0.5"
                      style={{ borderLeft: `2px solid ${theme.primaryLight}` }}
                    >
                      {[
                        {
                          href: '/dashboard/superadmin',
                          icon: ChartPieIcon,
                          name: 'Dashboard',
                          end: true,
                        },
                        { href: '/dashboard/superadmin/cms', icon: DocumentTextIcon, name: 'CMS' },
                        { href: '/dashboard/superadmin/users', icon: UserGroupIcon, name: 'Users' },
                      ].map((item) => (
                        <NavLink
                          key={item.href}
                          to={item.href}
                          end={item.end}
                          className="flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm transition-all duration-150"
                          style={{
                            background:
                              location.pathname === item.href ? theme.primaryLight : 'transparent',
                            color:
                              location.pathname === item.href ? theme.primary : theme.textSecondary,
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

              {/* Other nav items — filtered by role */}
              {[
                { href: '/dashboard/tenants', icon: BuildingOffice2Icon, name: 'nav.tenants', section: 'tenants' },
                { href: '/dashboard/ml-training', icon: CpuChipIcon, name: 'nav.mlTraining', section: 'ml' },
                { href: '/dashboard/integrations', icon: SignalIcon, name: 'nav.integrations', section: 'integrations' },
                {
                  href: '/dashboard/settings',
                  icon: CogIcon,
                  name: 'nav.settings',
                  dataTour: 'settings',
                  section: 'settings',
                },
              ].filter((item) => canSeeSection(user?.role, item.section)).map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <NavLink
                    key={item.href}
                    to={item.href}
                    data-tour={item.dataTour}
                    className="flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-150"
                    style={{
                      background: isActive ? theme.primaryLight : 'transparent',
                      color: isActive ? theme.primary : theme.textSecondary,
                    }}
                  >
                    <item.icon
                      className="h-5 w-5"
                      style={{ color: isActive ? theme.primary : theme.textMuted }}
                    />
                    {t(item.name)}
                  </NavLink>
                );
              })}
            </div>

            {/* User section */}
            <div className="px-3 py-4" style={{ borderTop: `1px solid ${theme.border}` }}>
              <div className="flex items-center gap-3 px-2">
                <div
                  className="h-8 w-8 rounded-xl flex items-center justify-center"
                  style={{ background: theme.primaryLight }}
                >
                  <span className="text-xs font-medium" style={{ color: theme.primary }}>
                    {getUserInitials()}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: theme.textPrimary }}>
                    {user?.name || 'User'}
                  </p>
                  <p className="text-xs truncate capitalize" style={{ color: theme.textMuted }}>
                    {user?.role || 'analyst'}
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
            className="hidden lg:flex fixed top-4 left-4 z-50 h-8 w-8 items-center justify-center rounded-xl transition-all duration-200"
            style={{
              background: theme.bgCard,
              backdropFilter: 'blur(40px)',
              border: `1px solid ${theme.border}`,
              color: theme.primary,
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
            }}
          >
            <ChevronRightIcon className="h-4 w-4" />
          </button>
        )}

        {/* Main content */}
        <div
          className={cn(
            'flex flex-1 flex-col overflow-hidden transition-all duration-300',
            sidebarCollapsed ? 'lg:ml-0' : 'lg:ml-64'
          )}
        >
          {/* Header */}
          <header
            className="flex h-14 items-center justify-between px-4 lg:px-6"
            style={{
              background: theme.bgCard,
              backdropFilter: 'blur(40px)',
              WebkitBackdropFilter: 'blur(40px)',
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
              {/* Client Context Switcher (visible for MANAGER/ANALYST roles) */}
              <ClientContextSwitcher />

              <button
                className="p-2 rounded-xl transition-colors"
                style={{ color: theme.textMuted }}
                onClick={() => setLearningHubOpen(!learningHubOpen)}
                title="Learning Hub"
                onMouseEnter={(e) => (e.currentTarget.style.color = theme.primary)}
                onMouseLeave={(e) => (e.currentTarget.style.color = theme.textMuted)}
              >
                <BookOpenIcon className="h-5 w-5" />
              </button>

              <button
                className="px-2.5 py-1 rounded-lg text-xs font-medium transition-colors"
                style={{
                  color: theme.textMuted,
                  border: `1px solid ${theme.border}`,
                }}
                onClick={toggleLanguage}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = theme.borderHover;
                  e.currentTarget.style.color = theme.primary;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = theme.border;
                  e.currentTarget.style.color = theme.textMuted;
                }}
              >
                {i18n.language === 'en' ? 'AR' : 'EN'}
              </button>

              <button
                onClick={() => setWhatsNewOpen(true)}
                className="relative p-2 rounded-xl transition-colors"
                style={{ color: theme.textMuted }}
                title="What's New"
                onMouseEnter={(e) => (e.currentTarget.style.color = theme.primary)}
                onMouseLeave={(e) => (e.currentTarget.style.color = theme.textMuted)}
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
                  className="flex items-center gap-2 p-1.5 rounded-xl transition-colors"
                  style={{ background: userMenuOpen ? theme.bgSurface : 'transparent' }}
                >
                  <div
                    className="h-7 w-7 rounded-xl flex items-center justify-center"
                    style={{ background: theme.primaryLight }}
                  >
                    <span className="text-xs font-medium" style={{ color: theme.primary }}>
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
                        className="absolute right-0 mt-2 w-48 py-1 rounded-2xl z-50"
                        style={{
                          background: theme.bgCard,
                          backdropFilter: 'blur(40px)',
                          border: `1px solid ${theme.border}`,
                          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)',
                        }}
                      >
                        <div
                          className="px-3 py-2"
                          style={{ borderBottom: `1px solid ${theme.border}` }}
                        >
                          <p className="text-sm font-medium" style={{ color: theme.textPrimary }}>
                            {user?.name}
                          </p>
                          <p className="text-xs" style={{ color: theme.textMuted }}>
                            {user?.email}
                          </p>
                        </div>
                        <NavLink
                          to="/dashboard/settings"
                          className="flex items-center gap-2 px-3 py-2 text-sm transition-colors rounded-lg mx-1"
                          style={{ color: theme.textSecondary }}
                          onClick={() => setUserMenuOpen(false)}
                          onMouseEnter={(e) => (e.currentTarget.style.background = theme.bgSurface)}
                          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                        >
                          <CogIcon className="w-4 h-4" />
                          {t('common.settings')}
                        </NavLink>
                        <button
                          onClick={handleLogout}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors rounded-lg mx-1"
                          style={{ color: theme.danger }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = theme.bgSurface)}
                          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
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
        <NotificationCenter
          isOpen={notificationsOpen}
          onClose={() => setNotificationsOpen(false)}
        />
        <WhatsNewModal isOpen={whatsNewOpen} onClose={() => setWhatsNewOpen(false)} />
        <KeyboardShortcutsModal isOpen={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />

        {/* Trust Gate Indicator - Fixed bottom-left */}
        <TrustGateIndicator />

        {/* Root Agent Onboarding Chat - For guided onboarding */}
        {!onboardingChatOpen && (
          <OnboardingChatButton onClick={() => setOnboardingChatOpen(true)} />
        )}

        <OnboardingChat
          isOpen={onboardingChatOpen}
          onClose={() => setOnboardingChatOpen(false)}
          onComplete={() => navigate('/dashboard')}
          initialName={user?.name}
          initialEmail={user?.email}
          language={i18n.language}
        />

        {/* In-App Feedback Widget */}
        <FeedbackWidget />
      </div>
    </div>
  );
}
