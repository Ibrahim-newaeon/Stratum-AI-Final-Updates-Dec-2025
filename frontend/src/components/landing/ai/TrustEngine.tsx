/**
 * Trust Engine Visualization - Interactive Flow Diagram
 * The core differentiator: Trust-Gated Autopilot
 */

import { motion, useInView } from 'framer-motion';
import { useRef, useState } from 'react';
import {
  ArrowRightIcon,
  BoltIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  ShieldCheckIcon,
  SignalIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

type SignalStatus = 'healthy' | 'degraded' | 'unhealthy';

interface SignalState {
  status: SignalStatus;
  score: number;
  decision: string;
  action: string;
  color: string;
  icon: typeof CheckCircleIcon;
}

const signalStates: Record<SignalStatus, SignalState> = {
  healthy: {
    status: 'healthy',
    score: 87,
    decision: 'PASS',
    action: 'AUTOPILOT EXECUTE',
    color: 'green',
    icon: CheckCircleIcon,
  },
  degraded: {
    status: 'degraded',
    score: 52,
    decision: 'HOLD',
    action: 'ALERT ONLY',
    color: 'yellow',
    icon: ExclamationTriangleIcon,
  },
  unhealthy: {
    status: 'unhealthy',
    score: 28,
    decision: 'BLOCK',
    action: 'MANUAL REQUIRED',
    color: 'red',
    icon: XCircleIcon,
  },
};

const healthComponents = [
  { name: 'EMQ Score', weight: '40%', description: 'Event Match Quality from ad platforms' },
  { name: 'Freshness', weight: '25%', description: 'Data recency and completeness' },
  { name: 'Variance', weight: '20%', description: 'Metric consistency over time' },
  { name: 'Anomalies', weight: '15%', description: 'Unusual pattern detection' },
];

export default function TrustEngine() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });
  const [activeState, setActiveState] = useState<SignalStatus>('healthy');
  const current = signalStates[activeState];

  const getColorClasses = (color: string) => ({
    bg: color === 'green' ? 'bg-green-500' : color === 'yellow' ? 'bg-yellow-500' : 'bg-red-500',
    bgLight:
      color === 'green'
        ? 'bg-green-500/10'
        : color === 'yellow'
          ? 'bg-yellow-500/10'
          : 'bg-red-500/10',
    border:
      color === 'green'
        ? 'border-green-500/30'
        : color === 'yellow'
          ? 'border-yellow-500/30'
          : 'border-red-500/30',
    text:
      color === 'green'
        ? 'text-green-400'
        : color === 'yellow'
          ? 'text-yellow-400'
          : 'text-red-400',
    gradient:
      color === 'green'
        ? 'from-green-500 to-emerald-500'
        : color === 'yellow'
          ? 'from-yellow-500 to-amber-500'
          : 'from-red-500 to-rose-500',
  });

  const colors = getColorClasses(current.color);

  return (
    <section className="relative py-32 overflow-hidden bg-gradient-to-b from-transparent via-purple-500/[0.02] to-transparent">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-[0.02]">
        <svg className="w-full h-full">
          <pattern id="trust-pattern" width="60" height="60" patternUnits="userSpaceOnUse">
            <path
              d="M30 0v60M0 30h60"
              stroke="currentColor"
              strokeWidth="0.5"
              fill="none"
              className="text-white"
            />
          </pattern>
          <rect width="100%" height="100%" fill="url(#trust-pattern)" />
        </svg>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6" ref={ref}>
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
            <span className="text-white">Trust-Gated</span>
            <br />
            <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              Autopilot
            </span>
          </h2>

          <p className="text-lg text-gray-400 max-w-2xl mx-auto">
            The only platform that{' '}
            <span className="text-white font-medium">refuses to execute bad recommendations</span>.
            Signal health is verified before every automated action.
          </p>
        </motion.div>

        {/* Interactive Flow Diagram */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.2, duration: 0.8 }}
          className="relative"
        >
          {/* State Selector */}
          <div className="flex justify-center gap-4 mb-12">
            {(Object.keys(signalStates) as SignalStatus[]).map((state) => {
              const stateData = signalStates[state];
              const stateColors = getColorClasses(stateData.color);
              const isActive = activeState === state;

              return (
                <button
                  key={state}
                  onClick={() => setActiveState(state)}
                  className={`relative px-6 py-3 rounded-xl font-medium text-sm transition-all ${
                    isActive
                      ? `${stateColors.bgLight} ${stateColors.border} border-2 ${stateColors.text}`
                      : 'bg-white/[0.02] border border-white/[0.05] text-gray-400 hover:bg-white/[0.05]'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-2 h-2 rounded-full ${isActive ? stateColors.bg : 'bg-gray-600'}`}
                    />
                    <span className="capitalize">{state}</span>
                    <span className="text-xs opacity-60">({stateData.score})</span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Flow Visualization */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 items-center">
            {/* Step 1: Signal Sources */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
              className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-xl bg-blue-500/10">
                  <SignalIcon className="w-5 h-5 text-blue-400" />
                </div>
                <span className="text-sm font-medium text-white">Signal Sources</span>
              </div>
              <div className="space-y-2 text-xs text-gray-500">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                  <span>Meta Ads API</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                  <span>Google Ads API</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
                  <span>TikTok Ads API</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
                  <span>Snapchat Ads API</span>
                </div>
              </div>
            </motion.div>

            {/* Arrow */}
            <div className="hidden lg:flex items-center justify-center">
              <ArrowRightIcon className="w-6 h-6 text-gray-600" />
            </div>

            {/* Step 2: Health Calculator */}
            <motion.div
              key={activeState}
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.4 }}
              className={`p-6 rounded-2xl ${colors.bgLight} border ${colors.border}`}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className={`p-2 rounded-xl bg-gradient-to-br ${colors.gradient}`}>
                  <current.icon className="w-5 h-5 text-white" />
                </div>
                <span className="text-sm font-medium text-white">Signal Health</span>
              </div>

              {/* Score Display */}
              <div className="text-center mb-4">
                <div className={`text-5xl font-bold ${colors.text}`}>{current.score}</div>
                <div className="text-xs text-gray-500 uppercase mt-1">{current.status}</div>
              </div>

              {/* Health Bar */}
              <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                <motion.div
                  className={`h-full rounded-full bg-gradient-to-r ${colors.gradient}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${current.score}%` }}
                  transition={{ duration: 0.6, ease: 'easeOut' }}
                />
              </div>
            </motion.div>

            {/* Arrow */}
            <div className="hidden lg:flex items-center justify-center">
              <ArrowRightIcon className="w-6 h-6 text-gray-600" />
            </div>

            {/* Step 3: Trust Gate Decision */}
            <motion.div
              key={`decision-${activeState}`}
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.4, delay: 0.1 }}
              className={`p-6 rounded-2xl bg-gradient-to-br ${colors.bgLight} border ${colors.border}`}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-xl bg-purple-500/10">
                  <ShieldCheckIcon className="w-5 h-5 text-purple-400" />
                </div>
                <span className="text-sm font-medium text-white">Trust Gate</span>
              </div>

              <div className="text-center">
                <div
                  className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg ${colors.bgLight} ${colors.border} border mb-3`}
                >
                  <current.icon className={`w-4 h-4 ${colors.text}`} />
                  <span className={`font-bold ${colors.text}`}>{current.decision}</span>
                </div>
                <div className="text-sm text-gray-400">{current.action}</div>
              </div>
            </motion.div>
          </div>

          {/* Health Components Breakdown */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.5, duration: 0.6 }}
            className="mt-16 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
          >
            {healthComponents.map((component, index) => (
              <div
                key={component.name}
                className="group relative p-5 rounded-xl bg-white/[0.02] border border-white/[0.05] hover:border-white/10 transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-white">{component.name}</span>
                  <span className="text-xs font-bold text-purple-400">{component.weight}</span>
                </div>
                <p className="text-xs text-gray-500">{component.description}</p>
              </div>
            ))}
          </motion.div>

          {/* Key Insight */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.7, duration: 0.6 }}
            className="mt-12 flex justify-center"
          >
            <div className="inline-flex items-start gap-3 px-6 py-4 rounded-2xl bg-gradient-to-r from-purple-500/10 to-cyan-500/10 border border-purple-500/20 max-w-2xl">
              <InformationCircleIcon className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-gray-300">
                  <span className="font-medium text-white">
                    Never auto-execute when signal_health &lt; 70.
                  </span>{' '}
                  This is the safety guarantee that no other platform provides. Your automation only
                  runs when data quality is verified.
                </p>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
