import { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { Hero } from '../components/landing/Hero';
import { Features } from '../components/landing/Features';
import { CTA } from '../components/landing/CTA';
import { Footer } from '../components/landing/Footer';
import { useLandingPages } from '@/api/landingCms';

export default function Landing() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const { data: pagesData } = useLandingPages({ navigation_only: true });

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = useMemo(() => {
    const cmsPages = pagesData?.pages || [];
    if (cmsPages.length > 0) {
      return cmsPages
        .filter((p) => p.show_in_navigation)
        .sort((a, b) => a.navigation_order - b.navigation_order)
        .map((p) => ({
          name: p.navigation_label || p.title,
          href: `/${p.slug}`,
        }));
    }
    return [
      { name: 'Product', href: '#product' },
      { name: 'Solutions', href: '#solutions' },
      { name: 'Pricing', href: '/pricing' },
      { name: 'Docs', href: '/docs' },
    ];
  }, [pagesData]);

  return (
    <div className="min-h-screen bg-background font-sans">
      {/* Navigation */}
      <header
        className={`fixed top-0 left-0 right-0 z-50 transition-colors duration-200 ${
          isScrolled
            ? 'bg-background/95 backdrop-blur-md border-b border-border'
            : 'bg-transparent'
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <nav className="flex items-center justify-between h-16 lg:h-20">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3">
              <img
                src="/images/stratum-logo.svg"
                alt="Stratum AI"
                className="h-7"
              />
            </Link>

            {/* Desktop Links */}
            <div className="hidden lg:flex items-center gap-8">
              {navLinks.map((link) => (
                <a
                  key={link.name}
                  href={link.href}
                  className="text-sm font-medium text-text-secondary hover:text-text-primary transition-colors duration-200"
                >
                  {link.name}
                </a>
              ))}
            </div>

            {/* CTA */}
            <div className="hidden lg:flex items-center gap-4">
              <Link
                to="/login"
                className="text-sm font-medium text-text-secondary hover:text-text-primary transition-colors duration-200"
              >
                Sign In
              </Link>
              <Link
                to="/signup"
                className="inline-flex items-center px-5 py-2.5 rounded-lg bg-stratum-500 text-primary-foreground text-sm font-semibold hover:brightness-110 transition-opacity duration-200"
              >
                Start Partnering
              </Link>
            </div>

            {/* Mobile Menu Button */}
            <button
              className="lg:hidden p-2 rounded-lg bg-card border border-border text-text-primary"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              aria-label="Toggle menu"
            >
              {isMobileMenuOpen ? (
                <X className="w-5 h-5" />
              ) : (
                <Menu className="w-5 h-5" />
              )}
            </button>
          </nav>

          {/* Mobile Menu */}
          {isMobileMenuOpen && (
            <div className="lg:hidden py-4 px-2 rounded-2xl bg-card border border-border mt-2 mb-4 animate-scale-in">
              <div className="flex flex-col gap-1">
                {navLinks.map((link) => (
                  <a
                    key={link.name}
                    href={link.href}
                    className="py-3 px-4 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-white/5 transition-colors duration-200"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    {link.name}
                  </a>
                ))}
                <hr className="my-2 border-border" />
                <Link
                  to="/login"
                  className="py-3 px-4 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary transition-colors duration-200"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Sign In
                </Link>
                <Link
                  to="/signup"
                  className="py-3 px-4 rounded-lg text-sm font-semibold text-primary-foreground bg-stratum-500 text-center hover:brightness-110 transition-opacity duration-200"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Start Partnering
                </Link>
              </div>
            </div>
          )}
        </div>
      </header>

      <main>
        <Hero />

        {/* Trust Bar */}
        <section className="py-12 border-y border-border bg-card/30">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <p className="text-center text-sm text-text-muted mb-8 tracking-wide uppercase">
              Trusted by growth teams at
            </p>
            <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-4">
              {[
                'Nexus Digital',
                'Vertex Commerce',
                'Aurora Brands',
                'Horizon Media',
                'Catalyst Labs',
              ].map((name) => (
                <span
                  key={name}
                  className="text-lg font-semibold text-text-muted/60 tracking-tight"
                >
                  {name}
                </span>
              ))}
            </div>
          </div>
        </section>

        <Features />

        {/* Social Proof */}
        <section id="solutions" className="py-24 lg:py-32 bg-card/20">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-display-sm text-text-primary mb-4">
                Trusted by teams who{' '}
                <span className="text-gradient-primary">demand more</span>
              </h2>
              <p className="text-body text-text-secondary max-w-2xl mx-auto">
                Partnering with growth teams to unlock unprecedented
                performance.
              </p>
            </div>
            <div className="grid md:grid-cols-3 gap-8">
              {[
                {
                  quote:
                    "Stratum AI doesn't just report data — it partners with us to make decisions. Our ROAS improved 34% in the first quarter.",
                  name: 'Sarah Chen',
                  title: 'VP of Growth, Nexus Digital',
                },
                {
                  quote:
                    'Finally, an AI that understands context. It feels like having a senior strategist who never sleeps.',
                  name: 'Marcus Webb',
                  title: 'Head of Performance, Vertex Commerce',
                },
                {
                  quote:
                    'The trust layer changed everything. We automate with confidence because we know the data is reliable.',
                  name: 'Elena Rodriguez',
                  title: 'CMO, Aurora Brands',
                },
              ].map((testimonial, i) => (
                <div
                  key={i}
                  className="p-8 rounded-2xl bg-card border border-border animate-enter"
                  style={{ animationDelay: `${i * 0.1}s` }}
                >
                  <div className="flex gap-1 mb-6">
                    {[...Array(5)].map((_, j) => (
                      <svg
                        key={j}
                        className="w-4 h-4 text-stratum-400"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                    ))}
                  </div>
                  <p className="text-body text-text-primary mb-6 leading-relaxed">
                    &ldquo;{testimonial.quote}&rdquo;
                  </p>
                  <div>
                    <p className="text-sm font-semibold text-text-primary">
                      {testimonial.name}
                    </p>
                    <p className="text-meta text-text-muted">
                      {testimonial.title}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <CTA />
      </main>

      <Footer />
    </div>
  );
}
