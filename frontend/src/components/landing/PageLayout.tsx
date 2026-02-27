/**
 * PageLayout Component
 * Shared layout for all public-facing pages with header and footer
 * Theme: Apple Glass Dark (#000000 + frosted glass)
 */

import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Bars3Icon, GlobeAltIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { useTranslation } from 'react-i18next';

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
  const [isLangMenuOpen, setIsLangMenuOpen] = useState(false);
  const location = useLocation();
  const { i18n } = useTranslation();

  const currentLanguage = i18n.language || 'en';

  const toggleLanguage = (lang: string) => {
    i18n.changeLanguage(lang);
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = lang;
    setIsLangMenuOpen(false);
  };

  // Set initial direction based on language
  useEffect(() => {
    document.documentElement.dir = currentLanguage === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = currentLanguage;
  }, [currentLanguage]);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Close language menu on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.lang-toggle')) {
        setIsLangMenuOpen(false);
      }
    };
    if (isLangMenuOpen) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [isLangMenuOpen]);

  const isActiveLink = (href: string) => {
    if (href === '/solutions/cdp') {
      return location.pathname.startsWith('/solutions');
    }
    return location.pathname === href || location.pathname.startsWith(href + '/');
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#000000' }}>
      {/* Ambient orbs background */}
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          background: `
            radial-gradient(ellipse 40% 40% at 20% 30%, rgba(0, 199, 190, 0.08), transparent),
            radial-gradient(ellipse 30% 30% at 80% 70%, rgba(139, 92, 246, 0.06), transparent),
            radial-gradient(ellipse 35% 35% at 60% 20%, rgba(20, 240, 198, 0.05), transparent)
          `,
        }}
      />
      {/* Apple Glass Dark Header */}
      <header
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-200 ${
          isScrolled ? 'py-3' : 'py-4'
        }`}
        style={{
          background: isScrolled ? 'rgba(0, 0, 0, 0.8)' : 'rgba(0, 0, 0, 0.5)',
          backdropFilter: 'blur(40px)',
          WebkitBackdropFilter: 'blur(40px)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        <div className="max-w-[1400px] mx-auto px-6 lg:px-8">
          <nav className="flex items-center justify-between">
            {/* Logo - Stratum Gold */}
            <Link to="/" className="flex items-center gap-3 group">
              <img src="/images/stratum-logo.svg" alt="Stratum AI" className="h-8" style={{ filter: 'invert(1) brightness(2)' }} />
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
                    color: isActiveLink(link.href) ? '#ffffff' : 'rgba(255, 255, 255, 0.6)',
                    letterSpacing: '0.01em',
                  }}
                >
                  {link.name}
                  <span
                    className={`nav-link-underline absolute bottom-0 left-0 h-0.5 rounded-full transition-all duration-200 ${
                      isActiveLink(link.href) ? 'w-full' : 'w-0'
                    }`}
                    style={{ background: '#00c7be' }}
                  />
                </Link>
              ))}
            </div>

            {/* CTA Buttons */}
            <div className="hidden lg:flex items-center gap-4">
              {/* Language Toggle */}
              <div className="relative lang-toggle">
                <button
                  onClick={() => setIsLangMenuOpen(!isLangMenuOpen)}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 hover:bg-white/5"
                  style={{ color: 'rgba(255, 255, 255, 0.6)' }}
                  aria-label="Change language"
                >
                  <GlobeAltIcon className="w-4 h-4" />
                  <span className="uppercase">{currentLanguage}</span>
                </button>
                {isLangMenuOpen && (
                  <div
                    className="absolute top-full mt-2 right-0 py-2 rounded-xl min-w-[120px] z-50"
                    style={{
                      background: 'rgba(10, 10, 10, 0.98)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      boxShadow: '0 10px 40px rgba(0, 0, 0, 0.5)',
                    }}
                  >
                    <button
                      onClick={() => toggleLanguage('en')}
                      className={`w-full px-4 py-2 text-sm text-left transition-colors hover:bg-white/5 flex items-center justify-between ${
                        currentLanguage === 'en' ? 'text-white' : ''
                      }`}
                      style={{
                        color: currentLanguage === 'en' ? '#ffffff' : 'rgba(255, 255, 255, 0.6)',
                      }}
                    >
                      <span>English</span>
                      {currentLanguage === 'en' && (
                        <span className="w-2 h-2 rounded-full bg-green-500" />
                      )}
                    </button>
                    <button
                      onClick={() => toggleLanguage('ar')}
                      className={`w-full px-4 py-2 text-sm text-left transition-colors hover:bg-white/5 flex items-center justify-between ${
                        currentLanguage === 'ar' ? 'text-white' : ''
                      }`}
                      style={{
                        color: currentLanguage === 'ar' ? '#ffffff' : 'rgba(255, 255, 255, 0.6)',
                      }}
                    >
                      <span>العربية</span>
                      {currentLanguage === 'ar' && (
                        <span className="w-2 h-2 rounded-full bg-green-500" />
                      )}
                    </button>
                  </div>
                )}
              </div>

              <Link
                to="/login"
                className="text-sm font-medium py-2 px-4 transition-all duration-200 hover:text-white"
                style={{ color: 'rgba(255, 255, 255, 0.6)' }}
              >
                Sign In
              </Link>
              <Link
                to="/signup"
                className="cta-button px-5 py-2.5 rounded-lg text-sm font-semibold text-white transition-all duration-200 hover:brightness-110"
                style={{
                  background: '#00c7be',
                  boxShadow: '0 0 30px rgba(0, 199, 190, 0.2)',
                }}
              >
                Start Free Trial
              </Link>
            </div>

            {/* Mobile Menu Button */}
            <button
              className="lg:hidden p-2 rounded-lg transition-all duration-200"
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
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

          {/* Mobile Menu - Apple Glass Dark */}
          {isMobileMenuOpen && (
            <div
              className="lg:hidden mt-4 py-4 rounded-3xl"
              style={{
                background: 'rgba(255, 255, 255, 0.03)',
                backdropFilter: 'blur(40px)',
                WebkitBackdropFilter: 'blur(40px)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                boxShadow: '0 25px 50px rgba(0, 0, 0, 0.4)',
              }}
            >
              <div className="flex flex-col gap-2 px-4">
                {navLinks.map((link) => (
                  <Link
                    key={link.name}
                    to={link.href}
                    className="py-3 px-4 rounded-lg text-sm font-medium transition-colors"
                    style={{
                      color: isActiveLink(link.href) ? '#ffffff' : 'rgba(255, 255, 255, 0.6)',
                      background: isActiveLink(link.href)
                        ? 'rgba(255, 255, 255, 0.05)'
                        : 'transparent',
                    }}
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    {link.name}
                  </Link>
                ))}
                <hr style={{ borderColor: 'rgba(255, 255, 255, 0.1)' }} className="my-2" />

                {/* Mobile Language Toggle */}
                <div className="px-4 py-2">
                  <p className="text-xs mb-2" style={{ color: 'rgba(255, 255, 255, 0.4)' }}>
                    Language
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => toggleLanguage('en')}
                      className={`flex-1 py-2 px-4 rounded-xl text-sm font-medium transition-colors ${
                        currentLanguage === 'en' ? 'text-white' : ''
                      }`}
                      style={{
                        background:
                          currentLanguage === 'en'
                            ? 'rgba(0, 199, 190, 0.15)'
                            : 'rgba(255, 255, 255, 0.03)',
                        border:
                          currentLanguage === 'en'
                            ? '1px solid rgba(0, 199, 190, 0.3)'
                            : '1px solid rgba(255, 255, 255, 0.08)',
                        color: currentLanguage === 'en' ? '#ffffff' : 'rgba(255, 255, 255, 0.6)',
                      }}
                    >
                      English
                    </button>
                    <button
                      onClick={() => toggleLanguage('ar')}
                      className={`flex-1 py-2 px-4 rounded-xl text-sm font-medium transition-colors ${
                        currentLanguage === 'ar' ? 'text-white' : ''
                      }`}
                      style={{
                        background:
                          currentLanguage === 'ar'
                            ? 'rgba(0, 199, 190, 0.15)'
                            : 'rgba(255, 255, 255, 0.03)',
                        border:
                          currentLanguage === 'ar'
                            ? '1px solid rgba(0, 199, 190, 0.3)'
                            : '1px solid rgba(255, 255, 255, 0.08)',
                        color: currentLanguage === 'ar' ? '#ffffff' : 'rgba(255, 255, 255, 0.6)',
                      }}
                    >
                      العربية
                    </button>
                  </div>
                </div>

                <hr style={{ borderColor: 'rgba(255, 255, 255, 0.1)' }} className="my-2" />
                <Link
                  to="/login"
                  className="py-3 px-4 rounded-lg text-sm font-medium"
                  style={{ color: 'rgba(255, 255, 255, 0.6)' }}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Sign In
                </Link>
                <Link
                  to="/signup"
                  className="py-3 px-4 rounded-lg text-sm font-semibold text-white text-center hover:brightness-110 transition-all"
                  style={{ background: '#00c7be' }}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Start Free Trial
                </Link>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* BUG-018: Spacer for fixed header — ensures content is not hidden behind the sticky nav */}
      <div className="h-[72px] lg:h-20" />

      {/* Main Content */}
      <main className="flex-1 relative z-10">{children}</main>

      {/* Apple Glass Dark Footer */}
      <footer style={{ background: '#000000', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-8 mb-12">
            {/* Brand */}
            <div className="col-span-2">
              <Link to="/" className="flex items-center gap-3 mb-4">
                <img src="/images/stratum-logo.svg" alt="Stratum AI" className="h-7" style={{ filter: 'invert(1) brightness(2)' }} />
              </Link>
              <p className="text-sm mb-6 max-w-xs" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                AI-Powered Revenue Operating System with Trust-Gated Autopilot.
              </p>

              {/* Social links */}
              <div className="flex items-center gap-4">
                <a
                  href="https://linkedin.com/company/stratumhq"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="transition-colors hover:text-[#00c7be]"
                  style={{ color: 'rgba(255, 255, 255, 0.5)' }}
                  aria-label="Follow us on LinkedIn"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                  </svg>
                </a>
                <a
                  href="https://instagram.com/stratumhq"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="transition-colors hover:text-[#00c7be]"
                  style={{ color: 'rgba(255, 255, 255, 0.5)' }}
                  aria-label="Follow us on Instagram"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z" />
                  </svg>
                </a>
              </div>
            </div>

            {/* Links */}
            {[
              {
                title: 'Product',
                links: [
                  { name: 'Features', href: '/features' },
                  { name: 'Pricing', href: '/pricing' },
                  { name: 'Integrations', href: '/integrations' },
                  { name: 'API Docs', href: '/api-docs' },
                ],
              },
              {
                title: 'Solutions',
                links: [
                  { name: 'CDP', href: '/solutions/cdp' },
                  { name: 'Audience Sync', href: '/solutions/audience-sync' },
                  { name: 'Predictions', href: '/solutions/predictions' },
                  { name: 'Trust Engine', href: '/solutions/trust-engine' },
                ],
              },
              {
                title: 'Company',
                links: [
                  { name: 'About', href: '/about' },
                  { name: 'Careers', href: '/careers' },
                  { name: 'Blog', href: '/blog' },
                  { name: 'Contact', href: '/contact' },
                ],
              },
              {
                title: 'Legal',
                links: [
                  { name: 'Privacy', href: '/privacy' },
                  { name: 'Terms', href: '/terms' },
                  { name: 'Security', href: '/security' },
                  { name: 'DPA', href: '/dpa' },
                ],
              },
            ].map((section) => (
              <div key={section.title}>
                <h4 className="text-sm text-white font-semibold mb-4">{section.title}</h4>
                <ul className="space-y-3">
                  {section.links.map((link) => (
                    <li key={link.name}>
                      <Link
                        to={link.href}
                        className="text-sm transition-colors hover:text-[#00c7be]"
                        style={{ color: 'rgba(255, 255, 255, 0.5)' }}
                      >
                        {link.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {/* Bottom bar */}
          <div
            className="pt-8 flex flex-col md:flex-row items-center justify-between gap-4"
            style={{ borderTop: '1px solid rgba(255, 255, 255, 0.05)' }}
          >
            <p className="text-xs" style={{ color: 'rgba(255, 255, 255, 0.4)' }}>
              &copy; {new Date().getFullYear()} Stratum AI. All rights reserved.
            </p>

            <div className="flex items-center gap-6">
              <span
                className="flex items-center gap-2 text-xs"
                style={{ color: 'rgba(255, 255, 255, 0.4)' }}
              >
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                All systems operational
              </span>
            </div>
          </div>
        </div>
      </footer>

      {/* Stratum Gold Dark CSS */}
      <style>{`
        .nav-link:hover {
          color: #ffffff !important;
        }

        .nav-link:hover .nav-link-underline {
          width: 100%;
        }

        .cta-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 0 40px rgba(0, 199, 190, 0.3) !important;
        }

        /* BUG-018: Anchor sections offset by header height so they don't hide behind nav */
        [id] {
          scroll-margin-top: 5rem;
        }
      `}</style>
    </div>
  );
}
