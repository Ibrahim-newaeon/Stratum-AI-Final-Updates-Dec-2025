/**
 * AI CTA Section - Final Call to Action
 * 2026 Design: Immersive gradient with floating elements
 */

import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import {
  ArrowRightIcon,
  ChartBarIcon,
  CpuChipIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';

const benefits = [
  { icon: SparklesIcon, text: '6 AI models included' },
  { icon: ShieldCheckIcon, text: 'Trust-gated safety' },
  { icon: CpuChipIcon, text: '<50ms predictions' },
  { icon: ChartBarIcon, text: '14-day free trial' },
];

export default function AICTA() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section className="relative py-32 overflow-hidden" style={{ background: '#000000' }}>
      {/* Background Effects */}
      <div className="absolute inset-0">
        {/* Floating orbs */}
        <motion.div
          animate={{
            y: [0, -20, 0],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute top-1/4 left-1/4 w-64 h-64 rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(10, 132, 255, 0.15), transparent 60%)' }}
        />
        <motion.div
          animate={{
            y: [0, 20, 0],
            opacity: [0.2, 0.4, 0.2],
          }}
          transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
          className="absolute bottom-1/4 right-1/4 w-80 h-80 rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(191, 90, 242, 0.1), transparent 60%)' }}
        />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center" ref={ref}>
        {/* Badge - Centered above hero */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="flex justify-center mb-8"
        >
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full"
            style={{
              background: 'rgba(10, 132, 255, 0.15)',
              border: '1px solid rgba(10, 132, 255, 0.3)',
            }}
          >
            <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: '#30D158' }} />
            <span className="text-sm font-medium" style={{ color: '#0A84FF' }}>Ready to transform your revenue operations?</span>
          </div>
        </motion.div>

        {/* Main Headline - Centered */}
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.1, duration: 0.6 }}
          className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-6 text-center"
        >
          <span className="text-white">Stop Guessing.</span>
          <br />
          <span style={{ color: '#0A84FF' }}>
            Start Predicting.
          </span>
        </motion.h2>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="text-lg max-w-2xl mx-auto mb-10 text-center"
          style={{ color: 'rgba(255, 255, 255, 0.5)' }}
        >
          Join 500+ revenue teams using Stratum AI to predict outcomes, automate safely, and scale
          with confidence.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12"
        >
          <a
            href="/signup"
            className="group inline-flex items-center gap-3 px-8 py-4 rounded-2xl text-base font-semibold text-white transition-all hover:scale-[1.02]"
            style={{
              background: '#0A84FF',
              boxShadow: '0 0 40px rgba(10, 132, 255, 0.3)',
            }}
          >
            <span>Start Your Free Trial</span>
            <ArrowRightIcon className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </a>

          <a
            href="/demo"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl text-base font-semibold text-white transition-all"
            style={{
              background: 'rgba(255, 255, 255, 0.03)',
              backdropFilter: 'blur(40px)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            Schedule a Demo
          </a>
        </motion.div>

        {/* Benefits Row */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.4, duration: 0.6 }}
          className="flex flex-wrap items-center justify-center gap-6"
        >
          {benefits.map((benefit) => (
            <div key={benefit.text} className="flex items-center gap-2 text-sm" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
              <benefit.icon className="w-4 h-4" style={{ color: '#0A84FF' }} />
              <span>{benefit.text}</span>
            </div>
          ))}
        </motion.div>

        {/* Trust Statement */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ delay: 0.6, duration: 0.6 }}
          className="mt-16 pt-8 border-t border-white/[0.05]"
        >
          <p className="text-sm text-gray-500">
            No credit card required. SOC 2 Type II compliant. Your data never trains our models.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
