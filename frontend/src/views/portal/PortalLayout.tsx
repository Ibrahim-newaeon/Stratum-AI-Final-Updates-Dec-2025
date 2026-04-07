/**
 * Portal Layout - Shell for Client Portal Routes
 *
 * Provides the layout wrapper for portal (VIEWER) users.
 * Minimal navigation: Dashboard, Campaigns (read-only), Requests, Profile.
 */

import { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import {
  HomeIcon,
  ChartBarIcon,
  DocumentTextIcon,
  UserCircleIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  XMarkIcon,
  BellIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

const portalNavItems = [
  { name: 'Dashboard', href: '/portal', icon: HomeIcon, end: true },
  { name: 'Campaigns', href: '/portal/campaigns', icon: ChartBarIcon },
  { name: 'Requests', href: '/portal/requests', icon: DocumentTextIcon },
  { name: 'Profile', href: '/portal/profile', icon: UserCircleIcon },
];

export default function PortalLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const userInitials = user?.name
    ?.split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) || 'U';

  return (
    <div className="min-h-screen bg-[#050B18] text-white">
      {/* Top Navigation Bar */}
      <header className="border-b border-white/5 bg-[#0A1628]/80 backdrop-blur-xl sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo + Brand */}
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-[#FF1F6D] to-[#FF8C00] flex items-center justify-center shadow-lg shadow-[#FF1F6D]/20">
                <span className="text-white font-bold text-sm">S</span>
              </div>
              <div>
                <h1 className="text-sm font-semibold text-white/90">Client Portal</h1>
                <p className="text-xs text-white/40">{user?.organization || 'Portal'}</p>
              </div>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-1">
              {portalNavItems.map((item) => {
                const isActive = item.end
                  ? location.pathname === item.href
                  : location.pathname.startsWith(item.href);
                return (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    className={cn(
                      'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all',
                      isActive
                        ? 'bg-white/10 text-white'
                        : 'text-white/50 hover:text-white/80 hover:bg-white/5'
                    )}
                  >
                    <item.icon className="w-4 h-4" />
                    {item.name}
                  </NavLink>
                );
              })}
            </nav>

            {/* Right Side */}
            <div className="flex items-center gap-3">
              {/* Notifications */}
              <button className="p-2 rounded-lg hover:bg-white/5 transition-colors relative">
                <BellIcon className="w-5 h-5 text-white/50" />
              </button>

              {/* User */}
              <div className="hidden md:flex items-center gap-2">
                <span className="text-sm text-white/60">{user?.name}</span>
                <div className="h-8 w-8 rounded-full bg-gradient-to-br from-[#FF1F6D] to-[#FF8C00] flex items-center justify-center">
                  <span className="text-white text-xs font-medium">{userInitials}</span>
                </div>
              </div>

              {/* Logout */}
              <button
                onClick={handleLogout}
                className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-red-400 hover:bg-red-500/10 transition-colors"
              >
                <ArrowRightOnRectangleIcon className="w-4 h-4" />
                Logout
              </button>

              {/* Mobile menu toggle */}
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="md:hidden p-2 rounded-lg hover:bg-white/5"
              >
                {mobileMenuOpen ? (
                  <XMarkIcon className="w-6 h-6 text-white/70" />
                ) : (
                  <Bars3Icon className="w-6 h-6 text-white/70" />
                )}
              </button>
            </div>
          </div>

          {/* Mobile Navigation */}
          {mobileMenuOpen && (
            <div className="md:hidden py-3 border-t border-white/5 space-y-1">
              {portalNavItems.map((item) => {
                const isActive = item.end
                  ? location.pathname === item.href
                  : location.pathname.startsWith(item.href);
                return (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                      isActive
                        ? 'bg-white/10 text-white'
                        : 'text-white/50 hover:text-white/80 hover:bg-white/5'
                    )}
                  >
                    <item.icon className="w-5 h-5" />
                    {item.name}
                  </NavLink>
                );
              })}
              <button
                onClick={handleLogout}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-red-400 hover:bg-red-500/10 w-full transition-colors"
              >
                <ArrowRightOnRectangleIcon className="w-5 h-5" />
                Logout
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Page Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
