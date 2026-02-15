/**
 * AI Landing Page - Stratum AI Revenue Operating System
 * 2026 Design Standards: Glass morphism, mesh gradients, micro-interactions
 * Sections: Hero, AI Features, Battle Card, Pricing, Trust Engine, CTA
 */

import { lazy, Suspense } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';

// Lazy load sections for performance
const AIHero = lazy(() => import('../components/landing/ai/AIHero'));
const AIFeatures = lazy(() => import('../components/landing/ai/AIFeatures'));
const TrustEngine = lazy(() => import('../components/landing/ai/TrustEngine'));
const BattleCard = lazy(() => import('../components/landing/ai/BattleCard'));
const AIPricing = lazy(() => import('../components/landing/ai/AIPricing'));
const AITestimonials = lazy(() => import('../components/landing/ai/AITestimonials'));
const AICTA = lazy(() => import('../components/landing/ai/AICTA'));
const AIFooter = lazy(() => import('../components/landing/ai/AIFooter'));

// Loading skeleton with 2026 shimmer effect
const SectionSkeleton = () => (
  <div className="min-h-[60vh] flex items-center justify-center">
    <div className="relative w-16 h-16">
      <div className="absolute inset-0 rounded-full bg-gradient-to-r from-purple-500 via-cyan-500 to-orange-500 animate-spin opacity-20 blur-xl" />
      <div className="absolute inset-2 rounded-full bg-surface-primary" />
      <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-purple-500 animate-spin" />
    </div>
  </div>
);

export default function AILanding() {
  const { scrollYProgress } = useScroll();
  const backgroundY = useTransform(scrollYProgress, [0, 1], ['0%', '100%']);

  return (
    <div className="relative min-h-screen bg-[#030303] text-white overflow-x-hidden" style={{ scrollBehavior: 'smooth' }}>
      {/* Ambient Background - 2026 Mesh Gradient */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        {/* Primary mesh gradient */}
        <motion.div
          className="absolute top-0 left-1/4 w-[800px] h-[800px] rounded-full"
          style={{
            background: 'radial-gradient(circle, rgba(139, 92, 246, 0.15) 0%, transparent 70%)',
            filter: 'blur(100px)',
            y: backgroundY,
          }}
        />
        <motion.div
          className="absolute top-1/3 right-0 w-[600px] h-[600px] rounded-full"
          style={{
            background: 'radial-gradient(circle, rgba(6, 182, 212, 0.12) 0%, transparent 70%)',
            filter: 'blur(80px)',
          }}
        />
        <motion.div
          className="absolute bottom-0 left-0 w-[700px] h-[700px] rounded-full"
          style={{
            background: 'radial-gradient(circle, rgba(249, 115, 22, 0.1) 0%, transparent 70%)',
            filter: 'blur(90px)',
          }}
        />

        {/* Subtle grid overlay */}
        <div
          className="absolute inset-0 opacity-[0.015]"
          style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
            `,
            backgroundSize: '64px 64px',
          }}
        />

        {/* Noise texture for depth */}
        <div
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
          }}
        />
      </div>

      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50">
        <div className="mx-auto max-w-7xl px-6 py-4">
          <div className="flex items-center justify-between backdrop-blur-xl bg-white/[0.02] border border-white/[0.05] rounded-2xl px-6 py-3">
            {/* Logo */}
            <a href="/" className="flex items-center gap-3 group">
              <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 via-cyan-500 to-orange-500 p-[1px]">
                <div className="absolute inset-[1px] rounded-xl bg-[#030303] flex items-center justify-center">
                  <span className="text-lg font-bold bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent">
                    S
                  </span>
                </div>
              </div>
              <span className="text-xl font-semibold tracking-tight">Stratum AI</span>
            </a>

            {/* Nav Links */}
            <div className="hidden md:flex items-center gap-8">
              <a
                href="#features"
                className="text-sm text-gray-400 hover:text-white transition-colors"
              >
                Features
              </a>
              <a
                href="#compare"
                className="text-sm text-gray-400 hover:text-white transition-colors"
              >
                Compare
              </a>
              <a
                href="#pricing"
                className="text-sm text-gray-400 hover:text-white transition-colors"
              >
                Pricing
              </a>
              <a href="/docs" className="text-sm text-gray-400 hover:text-white transition-colors">
                Docs
              </a>
            </div>

            {/* CTA Buttons */}
            <div className="flex items-center gap-3">
              <a
                href="/login"
                className="hidden sm:block text-sm text-gray-300 hover:text-white px-4 py-2 transition-colors"
              >
                Sign In
              </a>
              <a
                href="/signup"
                className="relative group px-5 py-2.5 rounded-xl text-sm font-medium overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-purple-500 via-cyan-500 to-purple-500 bg-[length:200%_100%] group-hover:animate-gradient-x" />
                <span className="relative text-white">Start Free Trial</span>
              </a>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="relative z-10">
        <Suspense fallback={<SectionSkeleton />}>
          <AIHero />
        </Suspense>

        <Suspense fallback={<SectionSkeleton />}>
          <AIFeatures />
        </Suspense>

        <Suspense fallback={<SectionSkeleton />}>
          <TrustEngine />
        </Suspense>

        <Suspense fallback={<SectionSkeleton />}>
          <BattleCard />
        </Suspense>

        <Suspense fallback={<SectionSkeleton />}>
          <AIPricing />
        </Suspense>

        <Suspense fallback={<SectionSkeleton />}>
          <AITestimonials />
        </Suspense>

        <Suspense fallback={<SectionSkeleton />}>
          <AICTA />
        </Suspense>
      </main>

      <Suspense fallback={<div className="h-48 bg-surface-primary" />}>
        <AIFooter />
      </Suspense>
    </div>
  );
}
