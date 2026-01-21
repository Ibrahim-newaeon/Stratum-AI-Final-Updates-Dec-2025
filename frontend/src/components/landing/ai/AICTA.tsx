/**
 * AI CTA Section - Final Call to Action
 * 2026 Design: Immersive gradient with floating elements
 */

import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import {
  ArrowRightIcon,
  SparklesIcon,
  ShieldCheckIcon,
  CpuChipIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';

const benefits = [
  { icon: SparklesIcon, text: '6 AI models included' },
  { icon: ShieldCheckIcon, text: 'Trust-gated safety' },
  { icon: CpuChipIcon, text: '<50ms predictions' },
  { icon: ChartBarIcon, text: '14-day free trial' }
];

export default function AICTA() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section className="relative py-32 overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0">
        {/* Main gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-purple-500/10 via-transparent to-transparent" />

        {/* Floating orbs */}
        <motion.div
          animate={{
            y: [0, -20, 0],
            opacity: [0.3, 0.5, 0.3]
          }}
          transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute top-1/4 left-1/4 w-64 h-64 rounded-full bg-purple-500/20 blur-3xl"
        />
        <motion.div
          animate={{
            y: [0, 20, 0],
            opacity: [0.2, 0.4, 0.2]
          }}
          transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
          className="absolute bottom-1/4 right-1/4 w-80 h-80 rounded-full bg-cyan-500/15 blur-3xl"
        />
        <motion.div
          animate={{
            y: [0, -15, 0],
            opacity: [0.2, 0.3, 0.2]
          }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }}
          className="absolute top-1/2 right-1/3 w-48 h-48 rounded-full bg-orange-500/10 blur-3xl"
        />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center" ref={ref}>
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/[0.05] border border-white/10 mb-8"
        >
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-sm text-gray-300">Ready to transform your revenue operations?</span>
        </motion.div>

        {/* Main Headline */}
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.1, duration: 0.6 }}
          className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-6"
        >
          <span className="text-white">Stop Guessing.</span>
          <br />
          <span className="bg-gradient-to-r from-purple-400 via-cyan-400 to-orange-400 bg-clip-text text-transparent">
            Start Predicting.
          </span>
        </motion.h2>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="text-lg text-gray-400 max-w-2xl mx-auto mb-10"
        >
          Join 500+ revenue teams using Stratum AI to predict outcomes,
          automate safely, and scale with confidence.
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
            className="group relative inline-flex items-center gap-3 px-8 py-4 rounded-2xl text-base font-semibold overflow-hidden"
          >
            {/* Animated gradient */}
            <div className="absolute inset-0 bg-gradient-to-r from-purple-600 via-cyan-500 to-purple-600 bg-[length:200%_100%] animate-gradient-x" />
            {/* Shine effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
            <span className="relative text-white">Start Your Free Trial</span>
            <ArrowRightIcon className="relative w-5 h-5 text-white group-hover:translate-x-1 transition-transform" />
          </a>

          <a
            href="/demo"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl text-base font-semibold border border-white/10 hover:border-white/20 bg-white/[0.02] hover:bg-white/[0.05] text-white transition-all"
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
            <div key={benefit.text} className="flex items-center gap-2 text-sm text-gray-400">
              <benefit.icon className="w-4 h-4 text-purple-400" />
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
