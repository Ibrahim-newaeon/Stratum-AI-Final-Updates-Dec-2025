/**
 * AI Features Section - Bento Grid Layout (2026 Design)
 * Showcases 6 AI models with interactive cards
 */

import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import {
  ArrowPathIcon,
  ArrowTrendingUpIcon,
  BeakerIcon,
  ChartBarIcon,
  ClockIcon,
  CubeTransparentIcon,
  CurrencyDollarIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  LightBulbIcon,
  SparklesIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';

const aiModels = [
  {
    id: 'roas',
    title: 'ROAS Predictor',
    subtitle: 'Know ROI Before You Spend',
    description:
      'ML-powered predictions for Meta, Google, TikTok & Snapchat campaigns with platform-specific baselines.',
    icon: CurrencyDollarIcon,
    gradient: 'from-green-500 to-emerald-500',
    bgGradient: 'from-green-500/10 to-emerald-500/5',
    stats: { accuracy: '94%', latency: '23ms' },
    size: 'large',
  },
  {
    id: 'ltv',
    title: 'LTV Predictor',
    subtitle: 'Target High-Value Customers',
    description: '30/90/180/365-day + lifetime value predictions with customer segmentation.',
    icon: UserGroupIcon,
    gradient: 'from-purple-500 to-violet-500',
    bgGradient: 'from-purple-500/10 to-violet-500/5',
    stats: { segments: '5', timeframes: '4' },
    size: 'medium',
  },
  {
    id: 'churn',
    title: 'Churn Predictor',
    subtitle: 'Retain Revenue at Risk',
    description: 'Identify at-risk customers with contributing factors and recommended actions.',
    icon: ExclamationTriangleIcon,
    gradient: 'from-red-500 to-orange-500',
    bgGradient: 'from-red-500/10 to-orange-500/5',
    stats: { rocAuc: '0.89', precision: '87%' },
    size: 'medium',
  },
  {
    id: 'conversion',
    title: 'Conversion Predictor',
    subtitle: 'Prioritize High-Intent Audiences',
    description: 'Predict conversion likelihood per campaign with platform-specific baselines.',
    icon: ArrowTrendingUpIcon,
    gradient: 'from-cyan-500 to-blue-500',
    bgGradient: 'from-cyan-500/10 to-blue-500/5',
    stats: { accuracy: '91%', features: '12' },
    size: 'medium',
  },
  {
    id: 'creative',
    title: 'Creative Lifecycle',
    subtitle: 'Refresh Before Performance Drops',
    description:
      'Predicts creative fatigue with lifecycle phases: Learning → Growth → Maturity → Decline.',
    icon: SparklesIcon,
    gradient: 'from-orange-500 to-amber-500',
    bgGradient: 'from-orange-500/10 to-amber-500/5',
    stats: { phases: '5', urgencyLevels: '5' },
    size: 'large',
  },
  {
    id: 'forecaster',
    title: 'ROAS Forecaster',
    subtitle: 'Plan Budget Cycles',
    description:
      'Time-series revenue forecasting with confidence intervals and baseline calculations.',
    icon: ChartBarIcon,
    gradient: 'from-indigo-500 to-purple-500',
    bgGradient: 'from-indigo-500/10 to-purple-500/5',
    stats: { granularity: '3', horizon: '90d' },
    size: 'medium',
  },
];

const additionalFeatures = [
  {
    icon: BeakerIcon,
    title: 'A/B Testing Framework',
    description: 'Champion/challenger model testing with auto-promotion',
  },
  {
    icon: EyeIcon,
    title: 'SHAP Explainability',
    description: 'See why AI made each recommendation',
  },
  {
    icon: CubeTransparentIcon,
    title: 'What-If Simulator',
    description: 'Test budget scenarios before committing',
  },
  {
    icon: ArrowPathIcon,
    title: 'RFM Segmentation',
    description: '11 behavioral segments automatically classified',
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] },
  },
};

export default function AIFeatures() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section id="features" className="relative py-32 overflow-hidden">
      {/* Background accent */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[600px] rounded-full blur-3xl" style={{ background: 'radial-gradient(circle, rgba(10, 132, 255, 0.08), transparent 60%)' }} />

      <div className="relative z-10 max-w-7xl mx-auto px-6" ref={ref}>
        {/* Section Header - Centered */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          {/* Badge - Centered above hero */}
          <div className="flex justify-center mb-8">
            <div
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full"
              style={{
                background: 'rgba(10, 132, 255, 0.15)',
                border: '1px solid rgba(10, 132, 255, 0.3)',
              }}
            >
              <SparklesIcon className="w-4 h-4" style={{ color: '#0A84FF' }} />
              <span className="text-sm font-medium" style={{ color: '#0A84FF' }}>6 AI Models Built-In</span>
            </div>
          </div>

          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-6 text-center">
            <span className="text-white">Predictive Intelligence</span>
            <br />
            <span style={{ color: '#0A84FF' }}>
              Not Just Analytics
            </span>
          </h2>

          <p className="text-lg max-w-2xl mx-auto text-center" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
            Every model is trained on YOUR data. No generic predictions—tailored insights for your
            unique business patterns.
          </p>
        </motion.div>

        {/* Bento Grid - AI Models */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-16"
        >
          {aiModels.map((model, index) => (
            <motion.div
              key={model.id}
              variants={itemVariants}
              className={`group relative rounded-3xl bg-gradient-to-b ${model.bgGradient} border border-white/[0.05] hover:border-white/10 backdrop-blur-sm overflow-hidden transition-all duration-500 hover:scale-[1.02] ${
                model.size === 'large' ? 'md:col-span-2 lg:col-span-1' : ''
              }`}
            >
              {/* Gradient accent line */}
              <div
                className={`absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r ${model.gradient} opacity-60`}
              />

              <div className="p-8">
                {/* Icon */}
                <div
                  className={`inline-flex p-3 rounded-2xl bg-gradient-to-br ${model.gradient} mb-6`}
                >
                  <model.icon className="w-6 h-6 text-white" />
                </div>

                {/* Title & Subtitle */}
                <h3 className="text-xl font-semibold text-white mb-1">{model.title}</h3>
                <p
                  className={`text-sm font-medium bg-gradient-to-r ${model.gradient} bg-clip-text text-transparent mb-3`}
                >
                  {model.subtitle}
                </p>

                {/* Description */}
                <p className="text-gray-400 text-sm leading-relaxed mb-6">{model.description}</p>

                {/* Stats */}
                <div className="flex items-center gap-4">
                  {Object.entries(model.stats).map(([key, value]) => (
                    <div key={key} className="flex items-center gap-2">
                      <div className="text-lg font-bold text-white">{value}</div>
                      <div className="text-xs text-gray-500 uppercase">{key}</div>
                    </div>
                  ))}
                </div>

                {/* Hover glow effect */}
                <div
                  className={`absolute inset-0 bg-gradient-to-r ${model.gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-500 pointer-events-none`}
                />
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Additional AI Features */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.4, duration: 0.6 }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        >
          {additionalFeatures.map((feature) => (
            <div
              key={feature.title}
              className="group relative p-6 rounded-2xl transition-all"
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid rgba(255, 255, 255, 0.05)',
              }}
            >
              <feature.icon className="w-5 h-5 mb-3 transition-colors" style={{ color: 'rgba(255, 255, 255, 0.5)' }} />
              <h4 className="text-sm font-medium text-white mb-1">{feature.title}</h4>
              <p className="text-xs text-gray-500">{feature.description}</p>
            </div>
          ))}
        </motion.div>

        {/* AI Infrastructure Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.6, duration: 0.6 }}
          className="mt-16 flex flex-wrap items-center justify-center gap-6 text-sm text-gray-500"
        >
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span>Hybrid Inference (Local + Cloud)</span>
          </div>
          <div className="flex items-center gap-2">
            <ClockIcon className="w-4 h-4" />
            <span>&lt;50ms average latency</span>
          </div>
          <div className="flex items-center gap-2">
            <span>Powered by</span>
            <span className="font-medium text-gray-400">scikit-learn + Vertex AI</span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
