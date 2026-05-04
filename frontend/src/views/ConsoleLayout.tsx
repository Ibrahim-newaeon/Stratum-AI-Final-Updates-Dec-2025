/**
 * Console Layout — Platform Owner shell.
 *
 * Mounts at /console/* and is gated to role=superadmin via
 * ProtectedRoute at the route level. Distinct from DashboardLayout
 * so platform-level concerns (cross-tenant tooling, feature flags,
 * dead letter queue) never clutter the agency operator's mental
 * model.
 *
 * Visually identical to DashboardLayout aside from a "PLATFORM
 * CONSOLE" pill in the brand slot, so owners always know which
 * shell they're in. Profile dropdown surfaces a "← Back to
 * dashboard" link that returns to /dashboard/overview.
 */

import { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'framer-motion';
import { dropdownVariants } from '@/lib/animations';
import { ArrowLeft, Bell, LogOut, Menu, Search, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { CommandPalette } from '@/components/ui/command-palette';
import { NotificationCenter } from '@/components/notifications/NotificationCenter';
import { useAuth } from '@/contexts/AuthContext';
import { Sidebar } from '@/components/primitives/nav/Sidebar';
import { ThemeToggle } from '@/components/primitives/theme/ThemeToggle';
import { consoleNavGroups } from '@/components/primitives/nav/consoleNav';

export default function ConsoleLayout() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getUserInitials = () => {
    if (!user?.name) return 'O';
    const names = user.name.split(' ');
    return names
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
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
      <span
        className={cn(
          'text-[10px] font-mono uppercase tracking-[0.12em]',
          'px-2 py-0.5 rounded-full',
          'bg-primary/10 text-primary border border-primary/30'
        )}
      >
        Console
      </span>
    </div>
  );

  const sidebarFooter = (
    <div className="space-y-2">
      <NavLink
        to="/dashboard/overview"
        className={cn(
          'group flex items-center gap-3 px-3 py-2 rounded-lg text-sm',
          'text-muted-foreground hover:text-foreground hover:bg-muted/40',
          'transition-colors duration-200',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
        )}
      >
        <ArrowLeft className="h-4 w-4 flex-shrink-0" />
        <span>Back to dashboard</span>
      </NavLink>
      <div className="flex items-center gap-3 pt-1">
        <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
          <span className="text-xs font-semibold text-primary font-mono">{getUserInitials()}</span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground truncate">{user?.name || 'Owner'}</p>
          <p className="text-xs text-muted-foreground truncate">Platform owner</p>
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
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-background font-sans">
      <div className="flex flex-1 overflow-hidden relative z-10">
        <Sidebar
          brand={brand}
          groups={consoleNavGroups}
          currentPath={location.pathname}
          footer={sidebarFooter}
          mobileOpen={mobileOpen}
          onMobileOpenChange={setMobileOpen}
          storageKey="stratum-console-groups"
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
              <h1 className="text-sm font-medium text-foreground hidden sm:flex items-center gap-2">
                <span className="text-muted-foreground">Console</span>
                {location.pathname !== '/console' && (
                  <>
                    <span className="text-border">/</span>
                    <span className="capitalize">
                      {location.pathname.split('/').pop()?.replace(/-/g, ' ')}
                    </span>
                  </>
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
              <ThemeToggle />

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
                        className="absolute right-0 mt-2 w-56 py-1 rounded-xl z-50 bg-card border border-border shadow-xl"
                      >
                        <div className="px-3 py-2 border-b border-border">
                          <p className="text-sm font-medium text-foreground">{user?.name}</p>
                          <p className="text-xs text-muted-foreground">{user?.email}</p>
                          <p className="mt-1 text-[10px] font-mono uppercase tracking-wider text-primary">
                            Platform owner
                          </p>
                        </div>
                        <NavLink
                          to="/dashboard/overview"
                          className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg mx-1 text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors duration-200"
                          onClick={() => setUserMenuOpen(false)}
                        >
                          <ArrowLeft className="w-4 h-4" />
                          Back to dashboard
                        </NavLink>
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

        <NotificationCenter
          isOpen={notificationsOpen}
          onClose={() => setNotificationsOpen(false)}
        />
      </div>
    </div>
  );
}
