/**
 * Competitive Battle Card Section
 * Sales enablement: Direct comparison vs competitors
 */

import { motion, useInView } from 'framer-motion';
import { useRef, useState } from 'react';
import {
  ArrowDownTrayIcon,
  CheckIcon,
  MinusIcon,
  SparklesIcon,
  TrophyIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

type FeatureStatus = 'yes' | 'no' | 'partial' | 'unique';

const competitors = [
  { id: 'stratum', name: 'Stratum AI', highlight: true },
  { id: 'segment', name: 'Segment' },
  { id: 'mparticle', name: 'mParticle' },
  { id: 'hightouch', name: 'Hightouch' },
  { id: 'hubspot', name: 'HubSpot' },
];

const featureCategories = [
  {
    name: 'AI & Predictions',
    icon: SparklesIcon,
    features: [
      {
        feature: 'Trust-Gated Execution',
        tooltip: 'Only execute when signal health passes safety thresholds',
        competitors: {
          stratum: 'unique',
          segment: 'no',
          mparticle: 'no',
          hightouch: 'no',
          hubspot: 'no',
        },
      },
      {
        feature: 'ROAS Prediction',
        tooltip: 'ML-powered return on ad spend forecasting',
        competitors: {
          stratum: 'yes',
          segment: 'no',
          mparticle: 'no',
          hightouch: 'no',
          hubspot: 'no',
        },
      },
      {
        feature: 'LTV Prediction',
        tooltip: 'Customer lifetime value forecasting',
        competitors: {
          stratum: 'yes',
          segment: 'no',
          mparticle: 'no',
          hightouch: 'no',
          hubspot: 'partial',
        },
      },
      {
        feature: 'Churn Prediction',
        tooltip: 'Identify at-risk customers before they leave',
        competitors: {
          stratum: 'yes',
          segment: 'no',
          mparticle: 'partial',
          hightouch: 'no',
          hubspot: 'partial',
        },
      },
      {
        feature: 'Creative Fatigue Detection',
        tooltip: 'Predict ad creative burnout before performance drops',
        competitors: {
          stratum: 'unique',
          segment: 'no',
          mparticle: 'no',
          hightouch: 'no',
          hubspot: 'no',
        },
      },
      {
        feature: 'Model Explainability (SHAP)',
        tooltip: 'See why AI made each recommendation',
        competitors: {
          stratum: 'yes',
          segment: 'no',
          mparticle: 'no',
          hightouch: 'no',
          hubspot: 'no',
        },
      },
    ],
  },
  {
    name: 'CDP & Data',
    icon: SparklesIcon,
    features: [
      {
        feature: 'Identity Resolution',
        competitors: {
          stratum: 'yes',
          segment: 'yes',
          mparticle: 'yes',
          hightouch: 'partial',
          hubspot: 'partial',
        },
      },
      {
        feature: 'Visual Identity Graph',
        tooltip: 'Interactive visualization of identity connections',
        competitors: {
          stratum: 'yes',
          segment: 'no',
          mparticle: 'no',
          hightouch: 'no',
          hubspot: 'no',
        },
      },
      {
        feature: 'RFM Segmentation (Built-in)',
        tooltip: '11 behavioral segments automatically classified',
        competitors: {
          stratum: 'yes',
          segment: 'no',
          mparticle: 'no',
          hightouch: 'no',
          hubspot: 'no',
        },
      },
      {
        feature: 'Real-time Event Processing',
        competitors: {
          stratum: 'yes',
          segment: 'yes',
          mparticle: 'yes',
          hightouch: 'partial',
          hubspot: 'partial',
        },
      },
      {
        feature: 'Anomaly Detection',
        competitors: {
          stratum: 'yes',
          segment: 'no',
          mparticle: 'yes',
          hightouch: 'no',
          hubspot: 'no',
        },
      },
    ],
  },
  {
    name: 'Audience Activation',
    icon: SparklesIcon,
    features: [
      {
        feature: 'Multi-Platform Sync (4+)',
        tooltip: 'Meta, Google, TikTok, Snapchat',
        competitors: {
          stratum: 'yes',
          segment: 'yes',
          mparticle: 'yes',
          hightouch: 'yes',
          hubspot: 'partial',
        },
      },
      {
        feature: 'Auto-Sync Scheduling',
        competitors: {
          stratum: 'yes',
          segment: 'yes',
          mparticle: 'yes',
          hightouch: 'yes',
          hubspot: 'partial',
        },
      },
      {
        feature: 'Match Rate Tracking',
        competitors: {
          stratum: 'yes',
          segment: 'partial',
          mparticle: 'yes',
          hightouch: 'partial',
          hubspot: 'no',
        },
      },
      {
        feature: 'Manual CSV/JSON Export',
        competitors: {
          stratum: 'yes',
          segment: 'yes',
          mparticle: 'yes',
          hightouch: 'yes',
          hubspot: 'yes',
        },
      },
    ],
  },
  {
    name: 'Analytics & Optimization',
    icon: SparklesIcon,
    features: [
      {
        feature: 'Signal Health Scoring',
        tooltip: 'Composite data quality score from 4 components',
        competitors: {
          stratum: 'unique',
          segment: 'no',
          mparticle: 'no',
          hightouch: 'no',
          hubspot: 'no',
        },
      },
      {
        feature: 'What-If Budget Simulator',
        competitors: {
          stratum: 'yes',
          segment: 'no',
          mparticle: 'no',
          hightouch: 'no',
          hubspot: 'no',
        },
      },
      {
        feature: 'A/B Testing Framework',
        competitors: {
          stratum: 'yes',
          segment: 'partial',
          mparticle: 'partial',
          hightouch: 'no',
          hubspot: 'yes',
        },
      },
      {
        feature: 'Power Analysis',
        competitors: {
          stratum: 'yes',
          segment: 'no',
          mparticle: 'no',
          hightouch: 'no',
          hubspot: 'no',
        },
      },
    ],
  },
];

const StatusIcon = ({ status }: { status: FeatureStatus }) => {
  switch (status) {
    case 'yes':
      return (
        <div
          className="flex items-center justify-center w-6 h-6 rounded-full"
          style={{ background: 'rgba(52, 199, 89, 0.2)' }}
        >
          <CheckIcon className="w-4 h-4" style={{ color: '#34c759' }} />
        </div>
      );
    case 'no':
      return (
        <div
          className="flex items-center justify-center w-6 h-6 rounded-full"
          style={{ background: 'rgba(239, 68, 68, 0.2)' }}
        >
          <XMarkIcon className="w-4 h-4" style={{ color: '#ef4444' }} />
        </div>
      );
    case 'partial':
      return (
        <div
          className="flex items-center justify-center w-6 h-6 rounded-full"
          style={{ background: 'rgba(255, 214, 10, 0.2)' }}
        >
          <MinusIcon className="w-4 h-4" style={{ color: '#FFD60A' }} />
        </div>
      );
    case 'unique':
      return (
        <div
          className="flex items-center justify-center w-6 h-6 rounded-full"
          style={{
            background: 'rgba(0, 199, 190, 0.2)',
            boxShadow: '0 0 0 2px rgba(0, 199, 190, 0.4)',
          }}
        >
          <SparklesIcon className="w-4 h-4" style={{ color: '#00c7be' }} />
        </div>
      );
  }
};

export default function BattleCard() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });
  const [expandedCategory, setExpandedCategory] = useState<string | null>('AI & Predictions');

  const handleDownload = () => {
    // In production, this would trigger a PDF download
    alert('Battle Card PDF download would trigger here');
  };

  return (
    <section id="compare" className="relative py-32 overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-orange-500/[0.02] to-transparent" />

      <div className="relative z-10 max-w-7xl mx-auto px-6" ref={ref}>
        {/* Section Header - Centered */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          {/* Badge - Centered above hero */}
          <div className="flex justify-center mb-8">
            <div
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full"
              style={{
                background: 'rgba(255, 159, 10, 0.15)',
                border: '1px solid rgba(255, 159, 10, 0.3)',
              }}
            >
              <TrophyIcon className="w-4 h-4" style={{ color: '#FF9F0A' }} />
              <span className="text-sm font-medium" style={{ color: '#FF9F0A' }}>
                Competitive Battle Card
              </span>
            </div>
          </div>

          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-6 text-center">
            <span className="text-white">See How We</span>
            <br />
            <span style={{ color: '#FF9F0A' }}>
              Stack Up
            </span>
          </h2>

          <p className="text-lg max-w-2xl mx-auto mb-8 text-center" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
            The only platform with Trust-Gated execution, built-in AI predictions, and visual
            identity resolution.
          </p>

          {/* Download Button */}
          <button
            onClick={handleDownload}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-white/[0.05] border border-white/10 hover:bg-white/10 transition-all text-sm font-medium text-white"
          >
            <ArrowDownTrayIcon className="w-4 h-4" />
            Download Sales Battle Card (PDF)
          </button>
        </motion.div>

        {/* Legend - Centered */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="flex flex-wrap items-center justify-center gap-6 mb-12 text-sm"
        >
          <div className="flex items-center gap-2">
            <StatusIcon status="unique" />
            <span style={{ color: 'rgba(255, 255, 255, 0.5)' }}>Unique to Stratum AI</span>
          </div>
          <div className="flex items-center gap-2">
            <StatusIcon status="yes" />
            <span style={{ color: 'rgba(255, 255, 255, 0.5)' }}>Full Support</span>
          </div>
          <div className="flex items-center gap-2">
            <StatusIcon status="partial" />
            <span style={{ color: 'rgba(255, 255, 255, 0.5)' }}>Partial/Limited</span>
          </div>
          <div className="flex items-center gap-2">
            <StatusIcon status="no" />
            <span style={{ color: 'rgba(255, 255, 255, 0.5)' }}>Not Available</span>
          </div>
        </motion.div>

        {/* Comparison Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="rounded-3xl border border-white/[0.05] bg-white/[0.02] backdrop-blur-xl overflow-hidden"
        >
          {/* Table Header */}
          <div className="grid grid-cols-6 gap-4 p-6 border-b border-white/[0.05] bg-white/[0.02]">
            <div className="text-sm font-medium text-gray-400">Feature</div>
            {competitors.map((comp) => (
              <div
                key={comp.id}
                className={`text-sm font-medium text-center ${
                  comp.highlight ? 'text-purple-400' : 'text-gray-400'
                }`}
              >
                {comp.name}
                {comp.highlight && <div className="text-xs text-purple-500 mt-1">You are here</div>}
              </div>
            ))}
          </div>

          {/* Feature Categories */}
          {featureCategories.map((category) => (
            <div key={category.name}>
              {/* Category Header */}
              <button
                onClick={() =>
                  setExpandedCategory(expandedCategory === category.name ? null : category.name)
                }
                className="w-full grid grid-cols-6 gap-4 p-4 border-b border-white/[0.05] bg-white/[0.03] hover:bg-white/[0.05] transition-colors"
              >
                <div className="col-span-6 flex items-center gap-2">
                  <motion.div
                    animate={{ rotate: expandedCategory === category.name ? 90 : 0 }}
                    className="text-gray-400"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </motion.div>
                  <span className="text-sm font-semibold text-white">{category.name}</span>
                  <span className="text-xs text-gray-500">
                    ({category.features.length} features)
                  </span>
                </div>
              </button>

              {/* Feature Rows */}
              <motion.div
                initial={false}
                animate={{
                  height: expandedCategory === category.name ? 'auto' : 0,
                  opacity: expandedCategory === category.name ? 1 : 0,
                }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                {category.features.map((row, index) => (
                  <div
                    key={row.feature}
                    className={`grid grid-cols-6 gap-4 p-4 items-center ${
                      index < category.features.length - 1 ? 'border-b border-white/[0.03]' : ''
                    } hover:bg-white/[0.02] transition-colors`}
                  >
                    <div className="group relative">
                      <span className="text-sm text-gray-300">{row.feature}</span>
                      {row.tooltip && (
                        <div className="absolute left-0 bottom-full mb-2 px-3 py-2 bg-gray-900 border border-white/10 rounded-lg text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                          {row.tooltip}
                        </div>
                      )}
                    </div>
                    <div className="flex justify-center">
                      <StatusIcon status={row.competitors.stratum as FeatureStatus} />
                    </div>
                    <div className="flex justify-center">
                      <StatusIcon status={row.competitors.segment as FeatureStatus} />
                    </div>
                    <div className="flex justify-center">
                      <StatusIcon status={row.competitors.mparticle as FeatureStatus} />
                    </div>
                    <div className="flex justify-center">
                      <StatusIcon status={row.competitors.hightouch as FeatureStatus} />
                    </div>
                    <div className="flex justify-center">
                      <StatusIcon status={row.competitors.hubspot as FeatureStatus} />
                    </div>
                  </div>
                ))}
              </motion.div>
            </div>
          ))}
        </motion.div>

        {/* Winning Message */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.5, duration: 0.6 }}
          className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          {[
            {
              title: '4 Unique Features',
              description:
                'Trust-Gated execution, creative fatigue detection, signal health scoring, and visual identity graph',
              color: 'from-purple-500 to-violet-500',
            },
            {
              title: '6 Built-in AI Models',
              description:
                'ROAS, LTV, Churn, Conversion, Creative Lifecycle, and ROAS Forecaster—all included',
              color: 'from-cyan-500 to-blue-500',
            },
            {
              title: 'All-in-One Platform',
              description:
                'CDP + Predictions + Activation in one system. No integrating 5 different tools',
              color: 'from-orange-500 to-amber-500',
            },
          ].map((item) => (
            <div
              key={item.title}
              className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]"
            >
              <div
                className={`inline-flex px-3 py-1 rounded-full bg-gradient-to-r ${item.color} bg-opacity-10 mb-4`}
              >
                <span
                  className={`text-xs font-medium bg-gradient-to-r ${item.color} bg-clip-text text-transparent`}
                >
                  {item.title}
                </span>
              </div>
              <p className="text-sm text-gray-400">{item.description}</p>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
