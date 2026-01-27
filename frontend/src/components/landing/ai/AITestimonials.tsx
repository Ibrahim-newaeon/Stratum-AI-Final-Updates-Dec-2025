/**
 * AI Testimonials Section - Social Proof
 * 2026 Design: Floating cards with gradient borders
 */

import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { StarIcon } from '@heroicons/react/24/solid';

const testimonials = [
  {
    quote:
      "Trust-Gated Autopilot is a game-changer. We've eliminated bad automation decisions completely. Our team finally sleeps at night knowing the AI won't act on degraded data.",
    author: 'Sarah Chen',
    role: 'VP of Growth',
    company: 'TechScale Inc.',
    avatar: 'SC',
    metric: '+47% ROAS',
    color: 'from-purple-500 to-violet-500',
  },
  {
    quote:
      'The creative fatigue prediction alone saved us $200K in wasted ad spend last quarter. We refresh creatives before they burn out, not after.',
    author: 'Marcus Johnson',
    role: 'Performance Marketing Lead',
    company: 'E-Commerce Giant',
    avatar: 'MJ',
    metric: '-34% CPA',
    color: 'from-cyan-500 to-blue-500',
  },
  {
    quote:
      "Finally, a CDP that doesn't just collect data but actually tells you what to do with it. The LTV predictions are scary accurate—we now focus on the right customers.",
    author: 'Emily Rodriguez',
    role: 'Director of CRM',
    company: 'Subscription Box Co.',
    avatar: 'ER',
    metric: '+62% LTV',
    color: 'from-orange-500 to-amber-500',
  },
  {
    quote:
      'We replaced Segment + Looker + a custom ML pipeline with Stratum. One platform, 6 AI models built-in. Implementation took 2 days.',
    author: 'David Kim',
    role: 'CTO',
    company: 'Growth Startup',
    avatar: 'DK',
    metric: '10x faster',
    color: 'from-green-500 to-emerald-500',
  },
];

const logos = [
  { name: 'Meta', svg: 'M' },
  { name: 'Google', svg: 'G' },
  { name: 'TikTok', svg: 'T' },
  { name: 'Snapchat', svg: 'S' },
  { name: 'HubSpot', svg: 'H' },
  { name: 'Salesforce', svg: 'SF' },
];

export default function AITestimonials() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section className="relative py-32 overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-cyan-500/[0.02] to-transparent" />

      <div className="relative z-10 max-w-7xl mx-auto px-6" ref={ref}>
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl sm:text-5xl font-bold tracking-tight mb-6">
            <span className="text-white">Trusted by</span>{' '}
            <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              Revenue Teams
            </span>
          </h2>

          <p className="text-lg text-gray-400 max-w-2xl mx-auto">
            See what growth and marketing leaders say about switching to AI-powered revenue
            operations.
          </p>
        </motion.div>

        {/* Testimonials Grid */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-16"
        >
          {testimonials.map((testimonial, index) => (
            <motion.div
              key={testimonial.author}
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.1 * index, duration: 0.6 }}
              className="group relative"
            >
              {/* Gradient border effect */}
              <div
                className={`absolute -inset-[1px] rounded-3xl bg-gradient-to-r ${testimonial.color} opacity-0 group-hover:opacity-20 blur-sm transition-opacity duration-500`}
              />

              <div className="relative p-8 rounded-3xl bg-white/[0.02] border border-white/[0.05] hover:border-white/10 transition-all">
                {/* Stars */}
                <div className="flex gap-1 mb-4">
                  {[...Array(5)].map((_, i) => (
                    <StarIcon key={i} className="w-4 h-4 text-yellow-500" />
                  ))}
                </div>

                {/* Quote */}
                <blockquote className="text-gray-300 text-lg leading-relaxed mb-6">
                  "{testimonial.quote}"
                </blockquote>

                {/* Author */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div
                      className={`w-12 h-12 rounded-full bg-gradient-to-br ${testimonial.color} flex items-center justify-center text-white font-semibold`}
                    >
                      {testimonial.avatar}
                    </div>
                    <div>
                      <div className="font-medium text-white">{testimonial.author}</div>
                      <div className="text-sm text-gray-500">
                        {testimonial.role}, {testimonial.company}
                      </div>
                    </div>
                  </div>

                  {/* Metric Badge */}
                  <div
                    className={`px-4 py-2 rounded-full bg-gradient-to-r ${testimonial.color} bg-opacity-10`}
                  >
                    <span
                      className={`text-sm font-bold bg-gradient-to-r ${testimonial.color} bg-clip-text text-transparent`}
                    >
                      {testimonial.metric}
                    </span>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Integration Logos */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.4, duration: 0.6 }}
          className="text-center"
        >
          <p className="text-sm text-gray-500 mb-8">
            Integrates with the platforms you already use
          </p>

          <div className="flex flex-wrap items-center justify-center gap-8">
            {logos.map((logo) => (
              <div
                key={logo.name}
                className="w-16 h-16 rounded-2xl bg-white/[0.02] border border-white/[0.05] flex items-center justify-center text-gray-500 hover:text-white hover:border-white/10 transition-all"
              >
                <span className="text-lg font-bold">{logo.svg}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Stats Bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.6, duration: 0.6 }}
          className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-6"
        >
          {[
            { value: '500+', label: 'Companies' },
            { value: '$2.4B+', label: 'Revenue Optimized' },
            { value: '99.7%', label: 'Uptime SLA' },
            { value: '4.9/5', label: 'Customer Rating' },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent mb-1">
                {stat.value}
              </div>
              <div className="text-sm text-gray-500">{stat.label}</div>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
