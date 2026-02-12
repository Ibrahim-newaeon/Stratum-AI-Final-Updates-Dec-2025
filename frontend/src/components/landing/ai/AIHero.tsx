/**
 * AI Hero Section - 2026 Design
 * Features: Animated mesh background, 3D card effects, AI-first messaging
 */

import { motion } from 'framer-motion';
import {
  ArrowRightIcon,
  BoltIcon,
  ChartBarIcon,
  CpuChipIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';

const stats = [
  { value: '6', label: 'AI Models', sublabel: 'Built-in' },
  { value: '99.7%', label: 'Uptime', sublabel: 'SLA' },
  { value: '<50ms', label: 'Predictions', sublabel: 'Latency' },
  { value: '4', label: 'Ad Platforms', sublabel: 'Synced' },
];

const trustBadges = [
  { icon: ShieldCheckIcon, text: 'SOC 2 Type II', color: 'from-green-500 to-emerald-500' },
  { icon: CpuChipIcon, text: 'GDPR Compliant', color: 'from-blue-500 to-cyan-500' },
  { icon: BoltIcon, text: 'Real-time Sync', color: 'from-orange-500 to-amber-500' },
];

const fadeUpVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: i * 0.1,
      duration: 0.6,
      ease: [0.16, 1, 0.3, 1],
    },
  }),
};

export default function AIHero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center pt-32 pb-20 overflow-hidden">
      {/* Animated AI Neural Network Background */}
      <div className="absolute inset-0 overflow-hidden">
        <svg className="absolute w-full h-full opacity-[0.03]" viewBox="0 0 1000 1000">
          <defs>
            <pattern id="neural-grid" width="50" height="50" patternUnits="userSpaceOnUse">
              <circle cx="25" cy="25" r="1" fill="currentColor" className="text-purple-500" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#neural-grid)" />
          {/* Animated connection lines */}
          {[...Array(8)].map((_, i) => (
            <motion.line
              key={i}
              x1={100 + i * 100}
              y1={200 + (i % 3) * 150}
              x2={200 + i * 100}
              y2={350 + (i % 2) * 100}
              stroke="url(#line-gradient)"
              strokeWidth="0.5"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 0.3 }}
              transition={{ duration: 2, delay: i * 0.2, repeat: Infinity, repeatType: 'reverse' }}
            />
          ))}
          <defs>
            <linearGradient id="line-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#a855f7" />
              <stop offset="100%" stopColor="#06b6d4" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6">
        <div className="text-center">
          {/* AI Badge - Centered */}
          <motion.div
            custom={0}
            initial="hidden"
            animate="visible"
            variants={fadeUpVariants}
            className="flex justify-center mb-8"
          >
            <div
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full"
              style={{
                background: 'rgba(0, 199, 190, 0.15)',
                border: '1px solid rgba(0, 199, 190, 0.3)',
              }}
            >
              <SparklesIcon className="w-4 h-4" style={{ color: '#00c7be' }} />
              <span className="text-sm font-medium" style={{ color: '#00c7be' }}>
                6 AI Models Built-In
              </span>
              <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: '#34c759' }} />
            </div>
          </motion.div>

          {/* Main Headline - Centered */}
          <motion.h1
            custom={1}
            initial="hidden"
            animate="visible"
            variants={fadeUpVariants}
            className="text-5xl sm:text-6xl lg:text-7xl xl:text-8xl font-bold tracking-tight leading-[1.1] mb-6 text-center"
          >
            <span className="text-white">The Only AI That</span>
            <br />
            <span className="relative inline-block">
              <span style={{ color: '#00c7be' }}>
                Thinks Before It Acts
              </span>
              {/* Animated underline */}
              <motion.div
                className="absolute -bottom-2 left-0 right-0 h-1 rounded-full"
                style={{ background: '#00c7be' }}
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ delay: 0.8, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
              />
            </span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            custom={2}
            initial="hidden"
            animate="visible"
            variants={fadeUpVariants}
            className="text-lg sm:text-xl text-gray-400 max-w-3xl mx-auto mb-10 leading-relaxed"
          >
            Trust-Gated Autopilot executes revenue operations{' '}
            <span className="text-white font-medium">
              only when AI confirms data quality meets safety thresholds
            </span>
            . Predict ROAS, prevent churn, and sync audiences across 4 platforms—automatically.
          </motion.p>

          {/* CTA Buttons - Centered */}
          <motion.div
            custom={3}
            initial="hidden"
            animate="visible"
            variants={fadeUpVariants}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16"
          >
            <a
              href="/signup"
              className="group inline-flex items-center gap-2 px-8 py-4 rounded-lg text-base font-semibold text-white transition-all hover:scale-[1.02] hover:brightness-110"
              style={{
                background: '#00c7be',
                boxShadow: '0 0 40px rgba(0, 199, 190, 0.3)',
              }}
            >
              <span>Start Free Trial</span>
              <ArrowRightIcon className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </a>

            <a
              href="#demo"
              className="group inline-flex items-center gap-2 px-8 py-4 rounded-lg text-base font-semibold text-white transition-all hover:bg-white/10"
              style={{
                background: 'rgba(255, 255, 255, 0.03)',
                backdropFilter: 'blur(40px)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
              }}
            >
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center"
                style={{ background: 'rgba(0, 199, 190, 0.15)' }}
              >
                <div className="w-0 h-0 border-l-[8px] border-l-white border-y-[5px] border-y-transparent ml-1" />
              </div>
              <span>Watch Demo</span>
            </a>
          </motion.div>

          {/* Stats Grid */}
          <motion.div
            custom={4}
            initial="hidden"
            animate="visible"
            variants={fadeUpVariants}
            className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-16 max-w-4xl mx-auto"
          >
            {stats.map((stat) => (
              <div
                key={stat.label}
                className="group relative p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:border-white/10 backdrop-blur-sm transition-all hover:bg-white/[0.04]"
              >
                <div className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent mb-1">
                  {stat.value}
                </div>
                <div className="text-sm text-gray-400">{stat.label}</div>
                <div className="text-xs text-gray-500">{stat.sublabel}</div>
              </div>
            ))}
          </motion.div>

          {/* Trust Badges */}
          <motion.div
            custom={5}
            initial="hidden"
            animate="visible"
            variants={fadeUpVariants}
            className="flex flex-wrap items-center justify-center gap-4"
          >
            {trustBadges.map((badge) => (
              <div
                key={badge.text}
                className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/[0.02] border border-white/[0.05]"
              >
                <badge.icon
                  className={`w-4 h-4 bg-gradient-to-r ${badge.color} bg-clip-text text-transparent`}
                  style={{ stroke: 'url(#badge-gradient)' }}
                />
                <span className="text-sm text-gray-400">{badge.text}</span>
              </div>
            ))}
          </motion.div>
        </div>

        {/* Dashboard Preview - 3D Card Effect */}
        <motion.div
          initial={{ opacity: 0, y: 60, rotateX: 10 }}
          animate={{ opacity: 1, y: 0, rotateX: 0 }}
          transition={{ delay: 0.6, duration: 1, ease: [0.16, 1, 0.3, 1] }}
          className="relative mt-20 perspective-1000"
        >
          {/* Glow effect behind card */}
          <div className="absolute inset-0 bg-gradient-to-r from-purple-500/20 via-cyan-500/20 to-orange-500/20 blur-3xl -z-10 scale-95" />

          {/* Dashboard Card */}
          <div className="relative rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.05] to-transparent backdrop-blur-xl overflow-hidden">
            {/* Window Controls */}
            <div className="flex items-center gap-2 px-6 py-4 border-b border-white/[0.05]">
              <div className="w-3 h-3 rounded-full bg-red-500/80" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
              <div className="w-3 h-3 rounded-full bg-green-500/80" />
              <div className="flex-1 text-center text-sm text-gray-500">Stratum AI Dashboard</div>
            </div>

            {/* Dashboard Content Mock */}
            <div className="p-8 grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Signal Health Card */}
              <div className="col-span-1 p-6 rounded-2xl bg-white/[0.03] border border-white/[0.05]">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm text-gray-400">Signal Health</span>
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-xs text-green-400">HEALTHY</span>
                  </div>
                </div>
                <div className="text-4xl font-bold text-white mb-2">87</div>
                <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: '87%' }}
                    transition={{ delay: 1.2, duration: 1, ease: 'easeOut' }}
                  />
                </div>
              </div>

              {/* ROAS Prediction Card */}
              <div className="col-span-1 p-6 rounded-2xl bg-white/[0.03] border border-white/[0.05]">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm text-gray-400">Predicted ROAS</span>
                  <ChartBarIcon className="w-4 h-4 text-purple-400" />
                </div>
                <div className="text-4xl font-bold text-white mb-2">3.2x</div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-green-400">+12%</span>
                  <span className="text-xs text-gray-500">vs last week</span>
                </div>
              </div>

              {/* Trust Gate Card */}
              <div className="col-span-1 p-6 rounded-2xl bg-gradient-to-br from-purple-500/10 to-cyan-500/10 border border-purple-500/20">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm text-gray-400">Trust Gate</span>
                  <ShieldCheckIcon className="w-4 h-4 text-cyan-400" />
                </div>
                <div className="text-2xl font-bold text-white mb-2">AUTOPILOT</div>
                <div className="text-sm text-cyan-400">✓ All checks passed</div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Scroll Indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
      >
        <div className="flex flex-col items-center gap-2 text-gray-500">
          <span className="text-xs uppercase tracking-widest">Scroll to explore</span>
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="w-6 h-10 rounded-full border border-white/20 flex items-start justify-center p-2"
          >
            <div className="w-1 h-2 rounded-full bg-white/40" />
          </motion.div>
        </div>
      </motion.div>
    </section>
  );
}
