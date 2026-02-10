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
  const isRTL = currentLanguage === 'ar';

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
              <div
                className="w-10 h-10 rounded-2xl flex items-center justify-center transition-all duration-200 group-hover:scale-105"
                style={{
                  background: '#00c7be',
                  boxShadow: '0 0 30px rgba(0, 199, 190, 0.2)',
                }}
              >
                <span className="text-white font-bold text-lg">S</span>
              </div>
              <span
                className="text-xl font-bold"
                style={{ color: '#00c7be' }}
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
                className="cta-button px-5 py-2.5 rounded-2xl text-sm font-semibold text-white transition-all duration-200"
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
                  className="py-3 px-4 rounded-2xl text-sm font-semibold text-white text-center"
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

      {/* Spacer for fixed header */}
      <div className="h-20" />

      {/* Main Content */}
      <main className="flex-1 relative z-10">{children}</main>

      {/* Apple Glass Dark Footer */}
      <footer style={{ background: '#000000', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-8 mb-12">
            {/* Brand */}
            <div className="col-span-2">
              <Link to="/" className="flex items-center gap-3 mb-4">
                <div
                  className="w-10 h-10 rounded-2xl flex items-center justify-center"
                  style={{ background: '#00c7be' }}
                >
                  <span className="text-white font-bold text-lg">S</span>
                </div>
                <span
                  className="text-xl font-semibold"
                  style={{ color: '#00c7be' }}
                >
                  Stratum AI
                </span>
              </Link>
              <p className="text-sm mb-6 max-w-xs" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                AI-Powered Revenue Operating System with Trust-Gated Autopilot.
              </p>

              {/* Social links */}
              <div className="flex items-center gap-4">
                <a
                  href="https://x.com/stratumai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="transition-colors hover:text-[#00c7be]"
                  style={{ color: 'rgba(255, 255, 255, 0.5)' }}
                  aria-label="Follow us on X"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                  </svg>
                </a>
                <a
                  href="https://linkedin.com/company/stratumai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="transition-colors hover:text-[#00c7be]"
                  style={{ color: 'rgba(255, 255, 255, 0.5)' }}
                  aria-label="Follow us on LinkedIn"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path
                      fillRule="evenodd"
                      d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"
                      clipRule="evenodd"
                    />
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
      `}</style>
    </div>
  );
}
