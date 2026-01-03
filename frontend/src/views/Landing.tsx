import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Hero,
  Platforms,
  Features,
  HowItWorks,
  Pricing,
  CTA,
  Footer,
} from '../components/landing';

export default function Landing() {
  // Smooth scroll behavior for anchor links
  useEffect(() => {
    const handleAnchorClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const anchor = target.closest('a[href^="#"]');
      if (anchor) {
        e.preventDefault();
        const id = anchor.getAttribute('href')?.slice(1);
        if (id) {
          const element = document.getElementById(id);
          element?.scrollIntoView({ behavior: 'smooth' });
        }
      }
    };

    document.addEventListener('click', handleAnchorClick);
    return () => document.removeEventListener('click', handleAnchorClick);
  }, []);

  return (
    <div className="min-h-screen bg-surface-primary">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-surface-primary/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-stratum flex items-center justify-center">
                <span className="text-white font-bold text-body">S</span>
              </div>
              <span className="text-h3 text-white font-semibold hidden sm:block">
                Stratum AI
              </span>
            </Link>

            {/* Nav links */}
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-meta text-text-secondary hover:text-white transition-colors">
                Features
              </a>
              <a href="#how-it-works" className="text-meta text-text-secondary hover:text-white transition-colors">
                How it Works
              </a>
              <a href="#pricing" className="text-meta text-text-secondary hover:text-white transition-colors">
                Pricing
              </a>
            </div>

            {/* Auth buttons */}
            <div className="flex items-center gap-4">
              <Link
                to="/login"
                className="text-meta text-text-secondary hover:text-white transition-colors"
              >
                Sign in
              </Link>
              <Link
                to="/signup"
                className="px-4 py-2 rounded-lg bg-gradient-stratum text-white text-meta font-medium
                           hover:shadow-glow transition-all duration-base"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Page sections */}
      <main>
        <Hero />

        <Platforms />

        <section id="features">
          <Features />
        </section>

        <section id="how-it-works">
          <HowItWorks />
        </section>

        <section id="pricing">
          <Pricing />
        </section>

        <CTA />
      </main>

      <Footer />
    </div>
  );
}
