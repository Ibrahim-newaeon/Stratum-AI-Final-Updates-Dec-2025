/**
 * Dashboard Layout — figma shell.
 *
 * Composes the primitives:
 *   <Sidebar groups={buildDashboardNav(role)} mobileOpen={...} />
 *   header (custom — preserves CommandPalette, TenantSwitcher, profile menu)
 *   <Outlet />
 *
 * The legacy ~200-line bespoke sidebar is gone — collapsible groups,
 * sub-nav (CDP), role-based filtering, and mobile drawer are now all
 * handled by the Sidebar primitive.
 */

import { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'framer-motion';
import { dropdownVariants } from '@/lib/animations';
import { Bell, BookOpen, Gift, LogOut, Menu, Search, Settings, ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';
import LearningHub from '@/components/guide/LearningHub';
import { CommandPalette } from '@/components/ui/command-palette';
import { DemoBanner } from '@/components/demo/DemoBanner';
import { TrialBanner } from '@/components/billing/TrialBanner';
import { NotificationCenter } from '@/components/notifications/NotificationCenter';
import { useWhatsNew, WhatsNewModal } from '@/components/changelog/WhatsNew';
import { KeyboardShortcutsModal } from '@/components/ui/keyboard-shortcuts';
import { OnboardingChecklist } from '@/components/onboarding/OnboardingChecklist';
import { useAuth } from '@/contexts/AuthContext';
import type { AppRole } from '@/components/auth/ProtectedRoute';
import { TrustGateIndicator } from '@/components/ui/TrustGateIndicator';
import { OnboardingChat, OnboardingChatButton } from '@/components/onboarding';
import { FeedbackWidget } from '@/components/feedback/FeedbackWidget';
import { CopilotChat } from '@/components/dashboard/CopilotChat';
import ClientContextSwitcher from '@/components/client/ClientContextSwitcher';
import TenantSwitcher from '@/components/tenant/TenantSwitcher';
import { Sidebar } from '@/components/primitives/nav/Sidebar';
import { ThemeToggle } from '@/components/primitives/theme/ThemeToggle';
import { buildDashboardNav } from '@/components/primitives/nav/dashboardNav';

export default function DashboardLayout() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [whatsNewOpen, setWhatsNewOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [onboardingChatOpen, setOnboardingChatOpen] = useState(false);
  const [learningHubOpen, setLearningHubOpen] = useState(false);
  const { hasNewUpdates } = useWhatsNew();

  const role = (user?.role as AppRole | undefined) ?? undefined;
  const navGroups = buildDashboardNav(role);

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

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'ar' : 'en';
    i18n.changeLanguage(newLang);
    document.documentElement.dir = newLang === 'ar' ? 'rtl' : 'ltr';
  };

  const brand = (
    <div className="flex items-center gap-3">
      <img
        src="/images/stratum-logo.png"
        alt="Stratum AI"
        className="h-7"
        loading="lazy"
        decoding="async"
      />
    </div>
  );

  const sidebarFooter = (
    <div className="flex items-center gap-3">
      <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
        <span className="text-xs font-semibold text-primary font-mono">{getUserInitials()}</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">{user?.name || 'User'}</p>
        <p className="text-xs text-muted-foreground truncate capitalize">
          {user?.role || 'analyst'}
        </p>
      </div>
      <button
        onClick={handleLogout}
        className={cn(
          'p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/5',
          'transition-colors duration-200',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
        )}
        aria-label="Log out"
        title="Log out"
      >
        <LogOut className="h-4 w-4" />
      </button>
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-background font-sans">
      <DemoBanner variant="top" />

      <div className="flex flex-1 overflow-hidden relative z-10">
        <Sidebar
          brand={brand}
          groups={navGroups}
          currentPath={location.pathname}
          footer={sidebarFooter}
          mobileOpen={mobileOpen}
          onMobileOpenChange={setMobileOpen}
        />

        <main className="flex flex-1 flex-col overflow-hidden">
          <header className="flex h-16 items-center justify-between px-6 bg-background border-b border-border">
            <div className="flex items-center gap-4">
              <button
                className={cn(
                  'lg:hidden p-2 rounded-lg text-muted-foreground hover:text-foreground transition-colors duration-200',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                )}
                onClick={() => setMobileOpen(true)}
                aria-label="Open navigation"
              >
                <Menu className="h-5 w-5" />
              </button>
              <h1 className="text-sm font-medium text-foreground hidden sm:block">
                {location.pathname
                  .split('/')
                  .filter(Boolean)
                  .slice(1)
                  .map((part) => (
                    <span key={part} className="capitalize">
                      {part.replace(/-/g, ' ')}
                    </span>
                  ))
                  .reduce(
                    (prev, curr, i) => (
                      <span key={i}>
                        {prev}
                        <span className="mx-2 text-border">/</span>
                        {curr}
                      </span>
                    ),
                    <span key="root" className="text-muted-foreground">
                      Dashboard
                    </span>
                  )}
              </h1>
            </div>

            <div className="flex-1 max-w-md mx-4 hidden md:block">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <CommandPalette />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <TenantSwitcher />
              <ClientContextSwitcher />

              <ThemeToggle />

              <button
                onClick={() => setLearningHubOpen(!learningHubOpen)}
                className={cn(
                  'p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/40',
                  'transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                )}
                aria-label="Learning Hub"
                title="Learning Hub"
              >
                <BookOpen className="h-5 w-5" />
              </button>

              <button
                onClick={() => setWhatsNewOpen(true)}
                className={cn(
                  'relative p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/40',
                  'transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                )}
                aria-label="What's New"
                title="What's New"
              >
                <Gift className="h-5 w-5" />
                {hasNewUpdates && (
                  <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-destructive" />
                )}
              </button>

              <button
                onClick={() => setNotificationsOpen(true)}
                className={cn(
                  'relative p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/40',
                  'transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                )}
                aria-label="Notifications"
                title="Notifications"
              >
                <Bell className="h-5 w-5" />
                <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-primary" />
              </button>

              <button
                className={cn(
                  'hidden sm:flex px-2.5 py-1 rounded-md text-xs font-medium font-mono',
                  'text-muted-foreground border border-border hover:text-foreground hover:border-border',
                  'transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                )}
                onClick={toggleLanguage}
              >
                {i18n.language === 'en' ? 'AR' : 'EN'}
              </button>

              <div className="relative">
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className={cn(
                    'flex items-center gap-2 p-1.5 rounded-lg transition-colors duration-200 hover:bg-muted/40',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                  )}
                >
                  <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
                    <span className="text-xs font-semibold text-primary font-mono">
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
                        className="absolute right-0 mt-2 w-52 py-1 rounded-xl z-50 bg-card border border-border shadow-xl"
                      >
                        <div className="px-3 py-2 border-b border-border">
                          <p className="text-sm font-medium text-foreground">{user?.name}</p>
                          <p className="text-xs text-muted-foreground">{user?.email}</p>
                          {role === 'superadmin' && (
                            <p className="mt-1 text-[10px] font-mono uppercase tracking-wider text-primary">
                              Platform owner
                            </p>
                          )}
                        </div>
                        {role === 'superadmin' && (
                          <NavLink
                            to="/console"
                            className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg mx-1 text-primary hover:bg-primary/10 transition-colors duration-200"
                            onClick={() => setUserMenuOpen(false)}
                          >
                            <ShieldCheck className="w-4 h-4" />
                            Switch to platform console
                          </NavLink>
                        )}
                        <NavLink
                          to="/dashboard/settings"
                          className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg mx-1 text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors duration-200"
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
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg mx-1 text-destructive hover:bg-destructive/5 transition-colors duration-200"
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

          <main className="flex-1 overflow-y-auto p-6 lg:p-8">
            <div className="mb-4">
              <TrialBanner />
            </div>

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

        <LearningHub isOpen={learningHubOpen} onClose={() => setLearningHubOpen(false)} />
        <NotificationCenter
          isOpen={notificationsOpen}
          onClose={() => setNotificationsOpen(false)}
        />
        <WhatsNewModal isOpen={whatsNewOpen} onClose={() => setWhatsNewOpen(false)} />
        <KeyboardShortcutsModal isOpen={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
        <TrustGateIndicator />
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
        <FeedbackWidget />
        <CopilotChat />
      </div>
    </div>
  );
}
