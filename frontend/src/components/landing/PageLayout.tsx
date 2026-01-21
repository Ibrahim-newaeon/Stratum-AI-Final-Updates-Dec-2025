/**
 * PageLayout Component
 * Shared layout for all public-facing pages with header and footer
 * Theme: 2026 Pure Black Theme
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
  { name: 'Integrations', href: '/integrations' },
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
    <div className="min-h-screen flex flex-col" style={{ background: '#030303' }}>
      {/* Animated Background Orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
      </div>

      {/* Header / Navigation */}
      <header
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          isScrolled ? 'py-3' : 'py-4'
        }`}
        style={{
          background: isScrolled ? 'rgba(3, 3, 3, 0.95)' : 'rgba(3, 3, 3, 0.8)',
          backdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: isScrolled ? '0 4px 30px rgba(0, 0, 0, 0.6)' : 'none',
        }}
      >
        <div className="max-w-[1400px] mx-auto px-6 lg:px-8">
          <nav className="flex items-center justify-between">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 group">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center transition-transform group-hover:scale-105"
                style={{
                  background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 100%)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                }}
              >
                <span className="text-white font-bold text-lg">S</span>
              </div>
              <span
                className="text-xl font-bold animate-[logoShine_3s_ease-in-out_infinite]"
                style={{
                  background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 50%, #f97316 100%)',
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
                    isActiveLink(link.href) ? 'text-white font-semibold' : ''
                  }`}
                  style={{
                    color: isActiveLink(link.href) ? '#ffffff' : 'rgba(255, 255, 255, 0.75)',
                    letterSpacing: '0.01em',
                  }}
                >
                  {link.name}
                  <span
                    className={`nav-link-underline absolute bottom-0 left-0 h-0.5 rounded-full transition-all duration-300 ${
                      isActiveLink(link.href) ? 'w-full' : 'w-0'
                    }`}
                    style={{
                      background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 50%, #f97316 100%)',
                    }}
                  />
                </Link>
              ))}
            </div>

            {/* CTA Buttons */}
            <div className="hidden lg:flex items-center gap-4">
              <Link
                to="/login"
                className="text-sm font-medium py-2 px-4 transition-colors hover:text-white"
                style={{ color: 'rgba(255, 255, 255, 0.75)' }}
              >
                Sign In
              </Link>
              <Link
                to="/signup"
                className="cta-button px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all"
                style={{
                  background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
                  boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
                }}
              >
                Get Started
              </Link>
            </div>

            {/* Mobile Menu Button */}
            <button
              className="lg:hidden p-2 rounded-lg transition-colors"
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
              }}
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              aria-label="Toggle mobile menu"
            >
              {isMobileMenuOpen ? (
                <XMarkIcon className="w-6 h-6 text-white" />
              ) : (
                <Bars3Icon className="w-6 h-6 text-white" />
              )}
            </button>
          </nav>

          {/* Mobile Menu */}
          {isMobileMenuOpen && (
            <div
              className="lg:hidden mt-4 py-4 rounded-2xl"
              style={{
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
              }}
            >
              <div className="flex flex-col gap-2 px-4">
                {navLinks.map((link) => (
                  <Link
                    key={link.name}
                    to={link.href}
                    className="py-3 px-4 rounded-lg text-sm font-medium transition-colors"
                    style={{
                      color: isActiveLink(link.href) ? '#ffffff' : 'rgba(255, 255, 255, 0.75)',
                      background: isActiveLink(link.href) ? 'rgba(255, 255, 255, 0.06)' : 'transparent',
                    }}
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    {link.name}
                  </Link>
                ))}
                <hr className="border-white/10 my-2" />
                <Link
                  to="/login"
                  className="py-3 px-4 rounded-lg text-sm font-medium text-white/75"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Sign In
                </Link>
                <Link
                  to="/signup"
                  className="py-3 px-4 rounded-xl text-sm font-semibold text-white text-center"
                  style={{
                    background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
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

      {/* CSS for animations */}
      <style>{`
        @keyframes orbFloat {
          0%, 100% { transform: translate(0, 0) scale(1); }
          25% { transform: translate(50px, -50px) scale(1.1); }
          50% { transform: translate(-30px, 30px) scale(0.95); }
          75% { transform: translate(30px, 50px) scale(1.05); }
        }

        @keyframes logoShine {
          0%, 100% { filter: brightness(1); }
          50% { filter: brightness(1.2); }
        }

        .orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(80px);
          opacity: 0.4;
          animation: orbFloat 15s ease-in-out infinite;
        }

        .orb-1 {
          width: 600px;
          height: 600px;
          background: rgba(168, 85, 247, 0.25);
          top: -200px;
          left: -200px;
          animation-delay: 0s;
        }

        .orb-2 {
          width: 500px;
          height: 500px;
          background: rgba(6, 182, 212, 0.25);
          bottom: -150px;
          right: -150px;
          animation-delay: -5s;
        }

        .orb-3 {
          width: 400px;
          height: 400px;
          background: rgba(249, 115, 22, 0.18);
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          animation-delay: -10s;
        }

        .nav-link:hover {
          color: #ffffff !important;
        }

        .nav-link:hover .nav-link-underline {
          width: 100%;
        }

        .cta-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 30px rgba(249, 115, 22, 0.5) !important;
        }
      `}</style>
    </div>
  );
}
