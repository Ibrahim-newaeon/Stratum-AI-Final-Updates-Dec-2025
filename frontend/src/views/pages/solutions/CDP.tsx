/**
 * CDP Solution Page
 * Customer Data Platform landing page
 */

import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  UserGroupIcon,
  ChartBarIcon,
  ArrowPathIcon,
  ShieldCheckIcon,
  CubeTransparentIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';

const features = [
  {
    icon: UserGroupIcon,
    title: '360° Customer Profiles',
    description:
      'Unified view from anonymous visitor to loyal customer. Real-time enrichment from every interaction.',
    color: '#a855f7',
  },
  {
    icon: CubeTransparentIcon,
    title: 'Identity Resolution',
    description:
      'Connect the dots across devices and channels. Visual identity graph shows every connection.',
    color: '#06b6d4',
  },
  {
    icon: ChartBarIcon,
    title: 'Smart Segmentation',
    description:
      'Build segments with behavioral rules, RFM scores, and lifecycle stages. Preview before you publish.',
    color: '#22c55e',
  },
  {
    icon: ArrowPathIcon,
    title: 'Multi-Platform Sync',
    description:
      'Push segments to Meta, Google, TikTok & Snapchat instantly. Auto-sync keeps your audiences fresh.',
    color: '#f97316',
  },
  {
    icon: SparklesIcon,
    title: 'Predictive Analytics',
    description:
      'Churn prediction, LTV forecasting, and next-best-action recommendations powered by ML.',
    color: '#ec4899',
  },
  {
    icon: ShieldCheckIcon,
    title: 'Privacy-First',
    description:
      'Consent management, GDPR/CCPA compliance, and hashed PII for secure platform sync.',
    color: '#3b82f6',
  },
];

export default function CDPSolution() {
  return (
    <PageLayout>
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <div
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
                style={{
                  background: 'rgba(168, 85, 247, 0.1)',
                  border: '1px solid rgba(168, 85, 247, 0.3)',
                  color: '#a855f7',
                }}
              >
                <UserGroupIcon className="w-4 h-4" />
                Customer Data Platform
              </div>
              <h1
                className="text-4xl md:text-5xl font-bold mb-6"
                style={{ fontFamily: "'Inter', sans-serif" }}
              >
                <span className="text-white">Turn Customer Data</span>
                <br />
                <span style={{ color: '#f97316' }}>Into Revenue</span>
              </h1>
              <p
                className="text-lg mb-8"
                style={{ color: 'rgba(255, 255, 255, 0.7)' }}
              >
                Unify customer profiles across every touchpoint. Build powerful segments and sync
                them to all your ad platforms instantly.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Link
                  to="/signup"
                  className="px-8 py-4 rounded-xl text-lg font-semibold text-white transition-all hover:opacity-90 text-center"
                  style={{
                    background: '#f97316',
                    boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
                  }}
                >
                  Start Free Trial
                </Link>
                <Link
                  to="/cdp-calculator"
                  className="px-8 py-4 rounded-xl text-lg font-semibold text-white transition-all hover:bg-white/10 text-center"
                  style={{
                    background: 'rgba(255, 255, 255, 0.06)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                  }}
                >
                  Calculate ROI
                </Link>
              </div>
            </div>
            <div
              className="rounded-3xl p-8"
              style={{
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
              }}
            >
              {/* Stats */}
              <div className="grid grid-cols-2 gap-6">
                {[
                  { value: '2.5M+', label: 'Profiles Unified' },
                  { value: '47%', label: 'Higher Match Rate' },
                  { value: '3.2x', label: 'ROAS Improvement' },
                  { value: '<100ms', label: 'Sync Latency' },
                ].map((stat) => (
                  <div key={stat.label} className="text-center">
                    <div className="text-3xl font-bold" style={{ color: '#f97316' }}>
                      {stat.value}
                    </div>
                    <div className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                      {stat.label}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Everything You Need in a CDP
            </h2>
            <p className="text-lg" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              From identity resolution to audience activation, all in one platform.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="p-6 rounded-2xl transition-all hover:scale-[1.02] backdrop-blur-xl"
                style={{
                  background: `${feature.color}15`,
                  border: `1px solid ${feature.color}30`,
                  boxShadow: `0 8px 32px ${feature.color}10`,
                }}
              >
                <feature.icon className="w-10 h-10 mb-4" style={{ color: feature.color }} />
                <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Comparison */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-12">
            How We Compare
          </h2>
          <div
            className="rounded-2xl overflow-hidden"
            style={{
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <th className="text-left p-4 text-white">Feature</th>
                  <th className="p-4 text-center" style={{ color: '#f97316' }}>
                    Stratum CDP
                  </th>
                  <th className="p-4 text-center" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                    Segment
                  </th>
                  <th className="p-4 text-center" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                    mParticle
                  </th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['Multi-platform sync', true, true, true],
                  ['Real-time segments', true, true, true],
                  ['Identity graph viz', true, false, false],
                  ['RFM analysis', true, false, false],
                  ['Trust-gated actions', true, false, false],
                  ['Anomaly detection', true, false, true],
                ].map(([feature, stratum, segment, mparticle]) => (
                  <tr
                    key={feature as string}
                    style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}
                  >
                    <td className="p-4 text-white">{feature}</td>
                    <td className="p-4 text-center">
                      {stratum ? (
                        <span style={{ color: '#22c55e' }}>✓</span>
                      ) : (
                        <span style={{ color: 'rgba(255, 255, 255, 0.3)' }}>—</span>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      {segment ? (
                        <span style={{ color: '#22c55e' }}>✓</span>
                      ) : (
                        <span style={{ color: 'rgba(255, 255, 255, 0.3)' }}>—</span>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      {mparticle ? (
                        <span style={{ color: '#22c55e' }}>✓</span>
                      ) : (
                        <span style={{ color: 'rgba(255, 255, 255, 0.3)' }}>—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div
            className="p-12 rounded-3xl"
            style={{
              background:
                'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">
              Ready to Unify Your Customer Data?
            </h2>
            <p className="text-lg mb-8" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              Start your free trial and see results in days, not months.
            </p>
            <Link
              to="/signup"
              className="inline-flex px-8 py-4 rounded-xl text-lg font-semibold text-white transition-all hover:opacity-90"
              style={{
                background: '#f97316',
                boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
              }}
            >
              Get Started Free
            </Link>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
