/**
 * Trust Engine Solution Page
 * Trust-gated automation system
 */

import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  ShieldCheckIcon,
  SignalIcon,
  BoltIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

export default function TrustEngineSolution() {
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
                  background: 'rgba(34, 197, 94, 0.1)',
                  border: '1px solid rgba(34, 197, 94, 0.3)',
                  color: '#22c55e',
                }}
              >
                <ShieldCheckIcon className="w-4 h-4" />
                Trust Engine
              </div>
              <h1
                className="text-4xl md:text-5xl font-bold mb-6"
                style={{ fontFamily: "'Inter', sans-serif" }}
              >
                <span className="text-white">Automation with</span>
                <br />
                <span style={{ color: '#f97316' }}>Built-In Safety</span>
              </h1>
              <p
                className="text-lg mb-8"
                style={{ color: 'rgba(255, 255, 255, 0.7)' }}
              >
                The Trust Engine ensures automations only execute when your data is healthy. No more
                blind optimization based on bad signals.
              </p>
              <Link
                to="/signup"
                className="inline-flex px-8 py-4 rounded-xl text-lg font-semibold text-white transition-all hover:opacity-90"
                style={{
                  background: '#f97316',
                  boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
                }}
              >
                Start Free Trial
              </Link>
            </div>
            <div
              className="rounded-3xl p-8"
              style={{
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
              }}
            >
              {/* Trust Gate Visualization */}
              <div className="space-y-6">
                <div className="text-center">
                  <SignalIcon className="w-12 h-12 mx-auto mb-2" style={{ color: '#22c55e' }} />
                  <div className="text-3xl font-bold text-white">Signal Health</div>
                  <div className="text-5xl font-bold mt-2" style={{ color: '#22c55e' }}>
                    87
                  </div>
                </div>
                <div className="flex items-center justify-center gap-4">
                  <div className="text-center">
                    <div
                      className="w-16 h-16 rounded-xl flex items-center justify-center mx-auto mb-2"
                      style={{
                        background: 'rgba(34, 197, 94, 0.1)',
                        border: '1px solid rgba(34, 197, 94, 0.3)',
                      }}
                    >
                      <CheckCircleIcon className="w-8 h-8" style={{ color: '#22c55e' }} />
                    </div>
                    <div className="text-xs" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                      HEALTHY
                    </div>
                    <div className="text-xs" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                      ≥70
                    </div>
                  </div>
                  <div className="text-center">
                    <div
                      className="w-16 h-16 rounded-xl flex items-center justify-center mx-auto mb-2"
                      style={{
                        background: 'rgba(234, 179, 8, 0.1)',
                        border: '1px solid rgba(234, 179, 8, 0.3)',
                      }}
                    >
                      <ExclamationTriangleIcon className="w-8 h-8" style={{ color: '#eab308' }} />
                    </div>
                    <div className="text-xs" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                      DEGRADED
                    </div>
                    <div className="text-xs" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                      40-69
                    </div>
                  </div>
                  <div className="text-center">
                    <div
                      className="w-16 h-16 rounded-xl flex items-center justify-center mx-auto mb-2"
                      style={{
                        background: 'rgba(239, 68, 68, 0.1)',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                      }}
                    >
                      <XCircleIcon className="w-8 h-8" style={{ color: '#ef4444' }} />
                    </div>
                    <div className="text-xs" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                      UNHEALTHY
                    </div>
                    <div className="text-xs" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                      {'<40'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-16">
            How the Trust Engine Works
          </h2>
          <div
            className="rounded-3xl p-8"
            style={{
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8 items-center">
              <div className="text-center">
                <SignalIcon className="w-12 h-12 mx-auto mb-3" style={{ color: '#a855f7' }} />
                <h3 className="font-semibold text-white">Signal Health Check</h3>
                <p className="text-sm mt-2" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                  Continuous monitoring of data quality
                </p>
              </div>
              <div className="hidden md:block text-center">
                <div className="text-4xl" style={{ color: 'rgba(255, 255, 255, 0.3)' }}>
                  →
                </div>
              </div>
              <div className="text-center">
                <ShieldCheckIcon className="w-12 h-12 mx-auto mb-3" style={{ color: '#06b6d4' }} />
                <h3 className="font-semibold text-white">Trust Gate</h3>
                <p className="text-sm mt-2" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                  Pass / Hold / Block decision
                </p>
              </div>
              <div className="hidden md:block text-center">
                <div className="text-4xl" style={{ color: 'rgba(255, 255, 255, 0.3)' }}>
                  →
                </div>
              </div>
              <div className="text-center">
                <BoltIcon className="w-12 h-12 mx-auto mb-3" style={{ color: '#f97316' }} />
                <h3 className="font-semibold text-white">Automation Decision</h3>
                <p className="text-sm mt-2" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                  Execute only when safe
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Gate Behaviors */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-16">
            Gate Behaviors
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                status: 'HEALTHY',
                threshold: '≥70',
                action: 'EXECUTE',
                description: 'Automations run normally. Full autopilot mode enabled.',
                color: '#22c55e',
                bg: 'rgba(34, 197, 94, 0.1)',
                border: 'rgba(34, 197, 94, 0.3)',
              },
              {
                status: 'DEGRADED',
                threshold: '40-69',
                action: 'HOLD',
                description: 'Automations paused. Alert sent for review. Manual override available.',
                color: '#eab308',
                bg: 'rgba(234, 179, 8, 0.1)',
                border: 'rgba(234, 179, 8, 0.3)',
              },
              {
                status: 'UNHEALTHY',
                threshold: '<40',
                action: 'BLOCK',
                description: 'All automations blocked. Manual intervention required.',
                color: '#ef4444',
                bg: 'rgba(239, 68, 68, 0.1)',
                border: 'rgba(239, 68, 68, 0.3)',
              },
            ].map((gate) => (
              <div
                key={gate.status}
                className="p-6 rounded-2xl"
                style={{
                  background: gate.bg,
                  border: `1px solid ${gate.border}`,
                }}
              >
                <div className="flex items-center justify-between mb-4">
                  <span className="font-bold" style={{ color: gate.color }}>
                    {gate.status}
                  </span>
                  <span
                    className="text-sm px-2 py-1 rounded"
                    style={{ background: 'rgba(0,0,0,0.2)', color: gate.color }}
                  >
                    {gate.threshold}
                  </span>
                </div>
                <div className="text-2xl font-bold text-white mb-2">{gate.action}</div>
                <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
                  {gate.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">Why Trust-Gated Automation?</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { title: 'Prevent Bad Decisions', desc: 'Never optimize on corrupted data', color: '#ef4444' },
              { title: 'Reduce Manual Oversight', desc: 'Automated safety checks 24/7', color: '#22c55e' },
              { title: 'Audit Trail', desc: 'Full logging of all gate decisions', color: '#a855f7' },
              { title: 'Customizable Thresholds', desc: 'Set your own risk tolerance', color: '#06b6d4' },
            ].map((benefit) => (
              <div
                key={benefit.title}
                className="p-6 rounded-2xl text-center backdrop-blur-xl transition-all hover:scale-[1.02]"
                style={{
                  background: `${benefit.color}15`,
                  border: `1px solid ${benefit.color}30`,
                  boxShadow: `0 8px 32px ${benefit.color}10`,
                }}
              >
                <h3 className="font-semibold text-white mb-2">{benefit.title}</h3>
                <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                  {benefit.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div
            className="p-12 rounded-3xl backdrop-blur-xl"
            style={{
              background:
                'linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(6, 182, 212, 0.15) 100%)',
              border: '1px solid rgba(34, 197, 94, 0.3)',
              boxShadow: '0 8px 32px rgba(34, 197, 94, 0.15), 0 8px 32px rgba(6, 182, 212, 0.15)',
            }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">
              Automate with Confidence
            </h2>
            <p className="text-lg mb-8" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              Let the Trust Engine handle the safety checks while you focus on growth.
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
