import { useState } from 'react';
import { Link } from 'react-router-dom';

// Stratum Gold Dark theme
const theme = {
  gold: '#00c7be',
  goldLight: 'rgba(0, 199, 190, 0.15)',
  green: '#34c759', // Stratum Green
  bgBase: '#000000',
  bgCard: 'rgba(255, 255, 255, 0.03)',
  textPrimary: '#FFFFFF',
  textSecondary: 'rgba(255, 255, 255, 0.7)',
  textMuted: 'rgba(255, 255, 255, 0.5)',
  textTertiary: 'rgba(255, 255, 255, 0.4)',
  border: 'rgba(255, 255, 255, 0.08)',
};

export function Footer() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleNewsletterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    const urlParams = new URLSearchParams(window.location.search);

    try {
      const response = await fetch('/api/v1/landing-cms/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          source_page: 'footer_newsletter',
          language: 'en',
          utm_source: urlParams.get('utm_source'),
          utm_medium: urlParams.get('utm_medium'),
          utm_campaign: urlParams.get('utm_campaign'),
          landing_url: window.location.href,
          referrer_url: document.referrer,
        }),
      });

      const data = await response.json();
      if (data.success) {
        setMessage('Thank you for subscribing!');
        setEmail('');
      }
    } catch {
      setMessage('Thank you for your interest!');
      setEmail('');
    } finally {
      setIsSubmitting(false);
    }
  };
  const links = {
    Product: [
      { name: 'Features', href: '/features' },
      { name: 'Pricing', href: '/pricing' },
      { name: 'Integrations', href: '/integrations' },
      { name: 'API Docs', href: '/api-docs' },
    ],
    Solutions: [
      { name: 'CDP', href: '/solutions/cdp' },
      { name: 'Audience Sync', href: '/solutions/audience-sync' },
      { name: 'Predictions', href: '/solutions/predictions' },
      { name: 'Trust Engine', href: '/solutions/trust-engine' },
    ],
    Company: [
      { name: 'About', href: '/about' },
      { name: 'Careers', href: '/careers' },
      { name: 'Blog', href: '/blog' },
      { name: 'Contact', href: '/contact' },
    ],
    Legal: [
      { name: 'Privacy', href: '/privacy' },
      { name: 'Terms', href: '/terms' },
      { name: 'Security', href: '/security' },
      { name: 'DPA', href: '/dpa' },
    ],
  };

  return (
    <footer style={{ background: theme.bgBase, borderTop: `1px solid ${theme.border}` }}>
      <div className="max-w-7xl mx-auto px-6 py-16">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-8 mb-12">
          {/* Brand */}
          <div className="col-span-2">
            <Link to="/" className="flex items-center gap-3 mb-4">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: theme.gold }}
              >
                <span className="text-white font-bold text-lg">S</span>
              </div>
              <span
                className="text-xl font-semibold"
                style={{ color: theme.gold }}
              >
                Stratum AI
              </span>
            </Link>
            <p className="text-sm mb-4 max-w-xs" style={{ color: theme.textMuted }}>
              AI-Powered Revenue Operating System with Trust-Gated Autopilot.
            </p>

            {/* Address & Phone */}
            <div className="mb-4 text-sm" style={{ color: theme.textMuted }}>
              <p>Arizona, Phoenix: 14001 N 7th ST STE F111</p>
              <p className="mt-1">
                <a
                  href="tel:+14807440840"
                  className="transition-colors"
                  style={{ color: theme.textMuted }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = theme.gold)}
                  onMouseLeave={(e) => (e.currentTarget.style.color = theme.textMuted)}
                >
                  +1 (480) 744-0840
                </a>
              </p>
            </div>

            {/* Social links */}
            <div className="flex items-center gap-4">
              {/* Instagram */}
              <a
                href="https://instagram.com/stratumai"
                target="_blank"
                rel="noopener noreferrer"
                className="transition-colors"
                style={{ color: theme.textMuted }}
                onMouseEnter={(e) => (e.currentTarget.style.color = theme.gold)}
                onMouseLeave={(e) => (e.currentTarget.style.color = theme.textMuted)}
                aria-label="Follow us on Instagram"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
                </svg>
              </a>
              {/* TikTok */}
              <a
                href="https://tiktok.com/@stratumai"
                target="_blank"
                rel="noopener noreferrer"
                className="transition-colors"
                style={{ color: theme.textMuted }}
                onMouseEnter={(e) => (e.currentTarget.style.color = theme.gold)}
                onMouseLeave={(e) => (e.currentTarget.style.color = theme.textMuted)}
                aria-label="Follow us on TikTok"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-5.2 1.74 2.89 2.89 0 012.31-4.64 2.93 2.93 0 01.88.13V9.4a6.84 6.84 0 00-1-.05A6.33 6.33 0 005 20.1a6.34 6.34 0 0010.86-4.43v-7a8.16 8.16 0 004.77 1.52v-3.4a4.85 4.85 0 01-1-.1z" />
                </svg>
              </a>
              {/* YouTube */}
              <a
                href="https://youtube.com/@stratumai"
                target="_blank"
                rel="noopener noreferrer"
                className="transition-colors"
                style={{ color: theme.textMuted }}
                onMouseEnter={(e) => (e.currentTarget.style.color = theme.gold)}
                onMouseLeave={(e) => (e.currentTarget.style.color = theme.textMuted)}
                aria-label="Subscribe on YouTube"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                </svg>
              </a>
              {/* LinkedIn */}
              <a
                href="https://linkedin.com/company/stratumai"
                target="_blank"
                rel="noopener noreferrer"
                className="transition-colors"
                style={{ color: theme.textMuted }}
                onMouseEnter={(e) => (e.currentTarget.style.color = theme.gold)}
                onMouseLeave={(e) => (e.currentTarget.style.color = theme.textMuted)}
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
              {/* X (Twitter) */}
              <a
                href="https://x.com/stratumai"
                target="_blank"
                rel="noopener noreferrer"
                className="transition-colors"
                style={{ color: theme.textMuted }}
                onMouseEnter={(e) => (e.currentTarget.style.color = theme.gold)}
                onMouseLeave={(e) => (e.currentTarget.style.color = theme.textMuted)}
                aria-label="Follow us on X"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>
            </div>

            {/* Newsletter Signup */}
            <div className="mt-6">
              <p className="text-sm font-medium text-white mb-2">Get updates</p>
              <form onSubmit={handleNewsletterSubmit} className="flex gap-2">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Your email"
                  required
                  className="flex-1 px-3 py-2 text-sm rounded-xl text-white placeholder-white/40 focus:outline-none transition-colors"
                  style={{
                    background: theme.bgCard,
                    border: `1px solid ${theme.border}`,
                  }}
                />
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 text-sm rounded-xl text-white transition-colors disabled:opacity-50"
                  style={{ background: theme.gold }}
                >
                  {isSubmitting ? '...' : 'Subscribe'}
                </button>
              </form>
              {message && <p className="mt-2 text-xs" style={{ color: theme.green }}>{message}</p>}
            </div>
          </div>

          {/* Links */}
          {Object.entries(links).map(([category, items]) => (
            <div key={category}>
              <h4 className="text-sm text-white font-semibold mb-4">{category}</h4>
              <ul className="space-y-3">
                {items.map((item) => (
                  <li key={item.name}>
                    <Link
                      to={item.href}
                      className="text-sm transition-colors"
                      style={{ color: theme.textMuted }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = theme.gold)}
                      onMouseLeave={(e) => (e.currentTarget.style.color = theme.textMuted)}
                    >
                      {item.name}
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
          style={{ borderTop: `1px solid ${theme.border}` }}
        >
          <p className="text-xs" style={{ color: theme.textTertiary }}>
            &copy; {new Date().getFullYear()} Stratum AI. All rights reserved. Developed and
            Prepared by Al-Ai-ai
          </p>

          <div className="flex items-center gap-6">
            <span className="flex items-center gap-2 text-xs" style={{ color: theme.textTertiary }}>
              <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: theme.green }} />
              All systems operational
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
