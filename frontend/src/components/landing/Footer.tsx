import { Link } from 'react-router-dom';
import { useLandingPages } from '@/api/landingCms';

export function Footer() {
  const { data: pagesData } = useLandingPages({ navigation_only: true });
  const cmsPages = pagesData?.pages || [];

  // Group CMS pages by category prefix (e.g. "product-features", "company-about")
  const productPages = cmsPages.filter((p) => p.slug.startsWith('product-') || p.slug === 'pricing' || p.slug === 'integrations');
  const resourcePages = cmsPages.filter((p) => p.slug.startsWith('resource-') || p.slug === 'docs' || p.slug === 'api');
  const companyPages = cmsPages.filter((p) => p.slug.startsWith('company-') || p.slug === 'blog' || p.slug === 'careers');
  const legalPages = cmsPages.filter((p) => p.slug.startsWith('legal-') || ['privacy', 'terms', 'security', 'gdpr'].includes(p.slug));

  const columns = [
    {
      title: 'Product',
      links: productPages.length > 0
        ? productPages.map((p) => ({ name: p.navigation_label || p.title, href: `/${p.slug}` }))
        : [
            { name: 'Features', href: '#product' },
            { name: 'Pricing', href: '/pricing' },
            { name: 'Integrations', href: '/integrations' },
            { name: 'Changelog', href: '/changelog' },
          ],
    },
    {
      title: 'Resources',
      links: resourcePages.length > 0
        ? resourcePages.map((p) => ({ name: p.navigation_label || p.title, href: `/${p.slug}` }))
        : [
            { name: 'Documentation', href: '/docs' },
            { name: 'API Reference', href: '/api' },
            { name: 'Help Center', href: '/help' },
            { name: 'Status', href: '/status' },
          ],
    },
    {
      title: 'Company',
      links: companyPages.length > 0
        ? companyPages.map((p) => ({ name: p.navigation_label || p.title, href: `/${p.slug}` }))
        : [
            { name: 'About', href: '/about' },
            { name: 'Blog', href: '/blog' },
            { name: 'Careers', href: '/careers' },
            { name: 'Contact', href: '/contact' },
          ],
    },
    {
      title: 'Legal',
      links: legalPages.length > 0
        ? legalPages.map((p) => ({ name: p.navigation_label || p.title, href: `/${p.slug}` }))
        : [
            { name: 'Privacy', href: '/privacy' },
            { name: 'Terms', href: '/terms' },
            { name: 'Security', href: '/security' },
            { name: 'GDPR', href: '/gdpr' },
          ],
    },
  ];

  return (
    <footer className="bg-[#05080F] border-t border-border">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-16">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-8 mb-12">
          {/* Brand */}
          <div className="col-span-2">
            <Link to="/" className="inline-flex items-center gap-2 mb-4">
              <img
                src="/images/stratum-logo.svg"
                alt="Stratum AI"
                className="h-7"
              />
            </Link>
            <p className="text-body text-text-muted mb-6 max-w-xs">
              Your AI Partner for Ad Growth. Unify, optimize, and scale with
              intelligence you can trust.
            </p>

            {/* Social links */}
            <div className="flex items-center gap-4">
              <a
                href="https://twitter.com/stratumai"
                aria-label="Twitter"
                className="text-text-muted hover:text-text-primary transition-colors duration-200"
              >
                <svg
                  className="w-5 h-5"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 001.27 5.477A4.072 4.072 0 012.8 9.713v.052a4.105 4.105 0 003.292 4.022 4.095 4.095 0 01-1.853.07 4.108 4.108 0 003.834 2.85A8.233 8.233 0 012 18.407a11.616 11.616 0 006.29 1.84" />
                </svg>
              </a>
              <a
                href="https://github.com/stratumai"
                aria-label="GitHub"
                className="text-text-muted hover:text-text-primary transition-colors duration-200"
              >
                <svg
                  className="w-5 h-5"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                    clipRule="evenodd"
                  />
                </svg>
              </a>
              <a
                href="https://linkedin.com/company/stratumai"
                aria-label="LinkedIn"
                className="text-text-muted hover:text-text-primary transition-colors duration-200"
              >
                <svg
                  className="w-5 h-5"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
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
          {columns.map((column) => (
            <div key={column.title}>
              <h4 className="text-meta text-text-primary font-semibold uppercase tracking-wider mb-4">
                {column.title}
              </h4>
              <ul className="space-y-3">
                {column.links.map((link) => (
                  <li key={link.name}>
                    <Link
                      to={link.href}
                      className="text-body text-text-muted hover:text-text-primary transition-colors duration-200"
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
        <div className="pt-8 border-t border-border flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-micro text-text-muted">
            &copy; {new Date().getFullYear()} Stratum AI. All rights reserved.
          </p>

          <div className="flex items-center gap-6">
            <span className="flex items-center gap-2 text-micro text-text-muted">
              <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
              All systems operational
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
