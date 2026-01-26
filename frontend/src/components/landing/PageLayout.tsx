/**
 * PageLayout Component
 * Shared layout for all public-facing pages with header and footer
 * Theme: Vibe.co Clean Light Design
 */

import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline';
import { Footer } from './Footer';

interface PageLayoutProps {
  children: React.ReactNode;
}

const navLinks = [
  { name: 'Features', href: '/features' },
  { name: 'Pricing', href: '/pricing' },
  { name: 'Solutions', href: '/solutions/cdp' },
  { name: 'Resources', href: '/resources' },
  { name: 'Docs', href: '/docs' },
  { name: 'Company', href: '/about' },
];

export function PageLayout({ children }: PageLayoutProps) {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const isActiveLink = (href: string) => {
    if (href === '/solutions/cdp') {
      return location.pathname.startsWith('/solutions');
    }
    return location.pathname === href || location.pathname.startsWith(href + '/');
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#FFFFFF' }}>
      {/* Vibe.co Clean Light Header */}
      <header
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-200 ${
          isScrolled ? 'py-3' : 'py-4'
        }`}
        style={{
          background: '#FFFFFF',
          borderBottom: isScrolled ? '1px solid #E5E7EB' : '1px solid transparent',
          boxShadow: isScrolled ? '0 1px 3px rgba(0, 0, 0, 0.08)' : 'none',
        }}
      >
        <div className="max-w-[1400px] mx-auto px-6 lg:px-8">
          <nav className="flex items-center justify-between">
            {/* Vibe Logo - Indigo Gradient */}
            <Link to="/" className="flex items-center gap-3 group">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 group-hover:scale-105 group-hover:shadow-[0_4px_14px_rgba(79,70,229,0.4)]"
                style={{
                  background: 'linear-gradient(135deg, #3730A3 0%, #4F46E5 100%)',
                }}
              >
                <span className="text-white font-bold text-lg">S</span>
              </div>
              <span
                className="text-xl font-bold"
                style={{
                  background: 'linear-gradient(135deg, #3730A3 0%, #4F46E5 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                Stratum AI
              </span>
            </Link>

            {/* Desktop Navigation Links */}
            <div className="hidden lg:flex items-center gap-9">
              {navLinks.map((link) => (
                <Link
                  key={link.name}
                  to={link.href}
                  className={`nav-link relative text-sm font-medium py-2 transition-colors ${
                    isActiveLink(link.href) ? 'font-semibold' : ''
                  }`}
                  style={{
                    color: isActiveLink(link.href) ? '#000000' : '#6B7280',
                    letterSpacing: '0.01em',
                  }}
                >
                  {link.name}
                  <span
                    className={`nav-link-underline absolute bottom-0 left-0 h-0.5 rounded-full transition-all duration-200 ${
                      isActiveLink(link.href) ? 'w-full' : 'w-0'
                    }`}
                    style={{
                      background: 'linear-gradient(135deg, #3730A3 0%, #4F46E5 100%)',
                    }}
                  />
                </Link>
              ))}
            </div>

            {/* Vibe CTA Buttons */}
            <div className="hidden lg:flex items-center gap-4">
              <Link
                to="/login"
                className="text-sm font-medium py-2 px-4 transition-all duration-200 hover:text-black"
                style={{ color: '#374151' }}
              >
                Sign In
              </Link>
              <Link
                to="/signup"
                className="cta-button px-5 py-2.5 rounded-lg text-sm font-semibold text-white transition-all duration-200"
                style={{
                  background: 'linear-gradient(135deg, #3730A3 0%, #4F46E5 100%)',
                  boxShadow: '0 4px 14px rgba(79, 70, 229, 0.4)',
                }}
              >
                Get Started
              </Link>
            </div>

            {/* Mobile Menu Button */}
            <button
              className="lg:hidden p-2 rounded-lg transition-all duration-200"
              style={{
                background: '#F3F4F6',
                border: '1px solid #E5E7EB',
              }}
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              aria-label="Toggle mobile menu"
            >
              {isMobileMenuOpen ? (
                <XMarkIcon className="w-6 h-6 text-gray-700" />
              ) : (
                <Bars3Icon className="w-6 h-6 text-gray-700" />
              )}
            </button>
          </nav>

          {/* Mobile Menu - Light Theme */}
          {isMobileMenuOpen && (
            <div
              className="lg:hidden mt-4 py-4 rounded-2xl"
              style={{
                background: '#FFFFFF',
                border: '1px solid #E5E7EB',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
            >
              <div className="flex flex-col gap-2 px-4">
                {navLinks.map((link) => (
                  <Link
                    key={link.name}
                    to={link.href}
                    className="py-3 px-4 rounded-lg text-sm font-medium transition-colors"
                    style={{
                      color: isActiveLink(link.href) ? '#000000' : '#6B7280',
                      background: isActiveLink(link.href) ? '#F3F4F6' : 'transparent',
                    }}
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    {link.name}
                  </Link>
                ))}
                <hr className="border-gray-200 my-2" />
                <Link
                  to="/login"
                  className="py-3 px-4 rounded-lg text-sm font-medium"
                  style={{ color: '#374151' }}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Sign In
                </Link>
                <Link
                  to="/signup"
                  className="py-3 px-4 rounded-lg text-sm font-semibold text-white text-center"
                  style={{
                    background: 'linear-gradient(135deg, #3730A3 0%, #4F46E5 100%)',
                  }}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Get Started
                </Link>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Spacer for fixed header */}
      <div className="h-20" />

      {/* Main Content */}
      <main className="flex-1 relative z-10">{children}</main>

      {/* Footer */}
      <Footer />

      {/* Vibe.co Light Theme CSS */}
      <style>{`
        .nav-link:hover {
          color: #000000 !important;
        }

        .nav-link:hover .nav-link-underline {
          width: 100%;
        }

        .cta-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 24px rgba(79, 70, 229, 0.5) !important;
        }
      `}</style>
    </div>
  );
}
