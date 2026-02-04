/**
 * CMS Layout
 * Dedicated layout for the Content Management System
 */

import { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import {
  ArrowLeftOnRectangleIcon,
  Bars3Icon,
  ChevronDownIcon,
  Cog6ToothIcon,
  CurrencyDollarIcon,
  DocumentTextIcon,
  EnvelopeIcon,
  HomeIcon,
  PencilSquareIcon,
  QuestionMarkCircleIcon,
  RectangleStackIcon,
  SparklesIcon,
  TagIcon,
  UserCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  badge?: string;
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/cms', icon: HomeIcon },
  { name: 'Posts', href: '/cms/posts', icon: DocumentTextIcon },
  { name: 'Pages', href: '/cms/pages', icon: RectangleStackIcon },
  { name: 'Categories', href: '/cms/categories', icon: TagIcon },
  { name: 'Authors', href: '/cms/authors', icon: UserCircleIcon },
  { name: 'Contact Submissions', href: '/cms/contacts', icon: EnvelopeIcon },
];

const landingContent: NavItem[] = [
  { name: 'Features', href: '/cms/landing/features', icon: SparklesIcon },
  { name: 'FAQ', href: '/cms/landing/faq', icon: QuestionMarkCircleIcon },
  { name: 'Pricing', href: '/cms/landing/pricing', icon: CurrencyDollarIcon },
];

export default function CMSLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [landingExpanded, setLandingExpanded] = useState(
    location.pathname.includes('/cms/landing')
  );

  const handleLogout = () => {
    logout();
    navigate('/cms-login');
  };

  const isActive = (href: string) => {
    if (href === '/cms') {
      return location.pathname === '/cms';
    }
    return location.pathname.startsWith(href);
  };

  const NavContent = () => (
    <>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-6 border-b border-white/10">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center">
          <PencilSquareIcon className="w-6 h-6 text-white" />
        </div>
        <div>
          <span className="text-lg font-bold text-white">Stratum</span>
          <span className="text-lg font-light text-purple-400 ml-1">CMS</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {/* Main nav */}
        <div className="space-y-1">
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              end={item.href === '/cms'}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive: active }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                  active || isActive(item.href)
                    ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                    : 'text-white/60 hover:text-white hover:bg-white/5'
                )
              }
            >
              <item.icon className="w-5 h-5" />
              {item.name}
              {item.badge && (
                <span className="ml-auto text-xs bg-orange-500/20 text-orange-400 px-2 py-0.5 rounded-full">
                  {item.badge}
                </span>
              )}
            </NavLink>
          ))}
        </div>

        {/* Landing Content Section */}
        <div className="pt-4 mt-4 border-t border-white/10">
          <button
            onClick={() => setLandingExpanded(!landingExpanded)}
            className="flex items-center justify-between w-full px-3 py-2 text-sm font-medium text-white/60 hover:text-white"
          >
            <span>Landing Content</span>
            <ChevronDownIcon
              className={cn('w-4 h-4 transition-transform', landingExpanded && 'rotate-180')}
            />
          </button>
          {landingExpanded && (
            <div className="mt-1 space-y-1">
              {landingContent.map((item) => (
                <NavLink
                  key={item.name}
                  to={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={({ isActive: active }) =>
                    cn(
                      'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ml-2',
                      active
                        ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                        : 'text-white/50 hover:text-white hover:bg-white/5'
                    )
                  }
                >
                  <item.icon className="w-4 h-4" />
                  {item.name}
                </NavLink>
              ))}
            </div>
          )}
        </div>

        {/* Settings */}
        <div className="pt-4 mt-4 border-t border-white/10">
          <NavLink
            to="/cms/settings"
            onClick={() => setSidebarOpen(false)}
            className={({ isActive: active }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                active
                  ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                  : 'text-white/60 hover:text-white hover:bg-white/5'
              )
            }
          >
            <Cog6ToothIcon className="w-5 h-5" />
            Settings
          </NavLink>
        </div>
      </nav>

      {/* User section */}
      <div className="p-4 border-t border-white/10">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center text-white font-medium">
            {user?.name?.charAt(0) || user?.email?.charAt(0) || 'A'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-white truncate">{user?.name || 'Admin'}</div>
            <div className="text-xs text-white/50 truncate">{user?.email}</div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/dashboard')}
            className="flex-1 border-white/10 text-white/60 hover:text-white hover:bg-white/5"
          >
            <HomeIcon className="w-4 h-4 mr-1" />
            Main App
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleLogout}
            className="border-white/10 text-white/60 hover:text-red-400 hover:border-red-500/30 hover:bg-red-500/10"
          >
            <ArrowLeftOnRectangleIcon className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-surface-primary">
      {/* Mobile sidebar */}
      <div
        className={cn(
          'fixed inset-0 z-50 lg:hidden transition-opacity',
          sidebarOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
      >
        <div className="absolute inset-0 bg-black/50" onClick={() => setSidebarOpen(false)} />
        <div
          className={cn(
            'absolute left-0 top-0 bottom-0 w-72 bg-surface-secondary border-r border-white/10 flex flex-col transition-transform',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          )}
        >
          <button
            onClick={() => setSidebarOpen(false)}
            className="absolute top-4 right-4 p-2 text-white/60 hover:text-white"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
          <NavContent />
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:w-72 lg:flex lg:flex-col bg-surface-secondary border-r border-white/10">
        <NavContent />
      </div>

      {/* Main content */}
      <div className="lg:pl-72">
        {/* Mobile header */}
        <header className="lg:hidden sticky top-0 z-40 flex items-center gap-4 px-4 py-3 bg-surface-secondary/80 backdrop-blur-xl border-b border-white/10">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 -ml-2 text-white/60 hover:text-white"
          >
            <Bars3Icon className="w-6 h-6" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center">
              <PencilSquareIcon className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-white">Stratum CMS</span>
          </div>
        </header>

        {/* Page content */}
        <main className="p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
