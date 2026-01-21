import { Link } from 'react-router-dom';

export function Footer() {
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
    <footer className="border-t border-white/5" style={{ background: '#030303' }}>
      <div className="max-w-7xl mx-auto px-6 py-16">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-8 mb-12">
          {/* Brand */}
          <div className="col-span-2">
            <Link to="/" className="flex items-center gap-3 mb-4">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{
                  background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 100%)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                }}
              >
                <span className="text-white font-bold text-lg">S</span>
              </div>
              <span className="text-xl text-white font-semibold">Stratum AI</span>
            </Link>
            <p className="text-sm mb-6 max-w-xs" style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
              AI-Powered Revenue Operating System with Trust-Gated Autopilot.
            </p>

            {/* Social links */}
            <div className="flex items-center gap-4">
              {/* X (Twitter) */}
              <a
                href="https://x.com/stratumai"
                target="_blank"
                rel="noopener noreferrer"
                className="transition-colors hover:opacity-80"
                style={{ color: 'rgba(255, 255, 255, 0.6)' }}
                aria-label="Follow us on X"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>
              {/* LinkedIn */}
              <a
                href="https://linkedin.com/company/stratumai"
                target="_blank"
                rel="noopener noreferrer"
                className="transition-colors hover:opacity-80"
                style={{ color: 'rgba(255, 255, 255, 0.6)' }}
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
          {Object.entries(links).map(([category, items]) => (
            <div key={category}>
              <h4 className="text-sm text-white font-semibold mb-4">{category}</h4>
              <ul className="space-y-3">
                {items.map((item) => (
                  <li key={item.name}>
                    <Link
                      to={item.href}
                      className="text-sm transition-colors hover:text-white"
                      style={{ color: 'rgba(255, 255, 255, 0.6)' }}
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
        <div className="pt-8 border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-xs" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
            &copy; {new Date().getFullYear()} Stratum AI. All rights reserved.
          </p>

          <div className="flex items-center gap-6">
            <span
              className="flex items-center gap-2 text-xs"
              style={{ color: 'rgba(255, 255, 255, 0.5)' }}
            >
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              All systems operational
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
