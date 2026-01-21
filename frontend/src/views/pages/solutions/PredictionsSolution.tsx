/**
 * Predictions Solution Page
 * ML-powered predictions and forecasting
 */

import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  SparklesIcon,
  ChartBarIcon,
  UserMinusIcon,
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  LightBulbIcon,
} from '@heroicons/react/24/outline';

const predictions = [
  {
    icon: UserMinusIcon,
    title: 'Churn Prediction',
    description:
      'Identify at-risk customers before they leave. Get actionable retention recommendations.',
    accuracy: '94%',
  },
  {
    icon: CurrencyDollarIcon,
    title: 'LTV Forecasting',
    description:
      'Predict customer lifetime value at acquisition. Optimize acquisition spend accordingly.',
    accuracy: '91%',
  },
  {
    icon: ArrowTrendingUpIcon,
    title: 'Revenue Forecasting',
    description:
      'Accurate revenue predictions based on historical patterns and market signals.',
    accuracy: '89%',
  },
  {
    icon: LightBulbIcon,
    title: 'Next-Best-Action',
    description:
      'AI-powered recommendations for the optimal next engagement for each customer.',
    accuracy: '87%',
  },
];

export default function PredictionsSolution() {
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
                  background: 'rgba(236, 72, 153, 0.1)',
                  border: '1px solid rgba(236, 72, 153, 0.3)',
                  color: '#ec4899',
                }}
              >
                <SparklesIcon className="w-4 h-4" />
                ML Predictions
              </div>
              <h1
                className="text-4xl md:text-5xl font-bold mb-6"
                style={{ fontFamily: "'Inter', sans-serif" }}
              >
                <span className="text-white">Predict the Future</span>
                <br />
                <span style={{ color: '#f97316' }}>Act Today</span>
              </h1>
              <p
                className="text-lg mb-8"
                style={{ color: 'rgba(255, 255, 255, 0.7)' }}
              >
                Machine learning models trained on your data deliver actionable predictions for
                churn, LTV, revenue, and optimal customer actions.
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
              {/* Prediction Preview */}
              <div className="space-y-4">
                <div
                  className="p-4 rounded-xl"
                  style={{
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.2)',
                  }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white">High Churn Risk</span>
                    <span className="text-sm font-bold" style={{ color: '#ef4444' }}>
                      847 customers
                    </span>
                  </div>
                  <div className="h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.1)' }}>
                    <div
                      className="h-full rounded-full"
                      style={{ width: '23%', background: '#ef4444' }}
                    />
                  </div>
                </div>
                <div
                  className="p-4 rounded-xl"
                  style={{
                    background: 'rgba(34, 197, 94, 0.1)',
                    border: '1px solid rgba(34, 197, 94, 0.2)',
                  }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white">High LTV Potential</span>
                    <span className="text-sm font-bold" style={{ color: '#22c55e' }}>
                      2,341 customers
                    </span>
                  </div>
                  <div className="h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.1)' }}>
                    <div
                      className="h-full rounded-full"
                      style={{ width: '67%', background: '#22c55e' }}
                    />
                  </div>
                </div>
                <div
                  className="p-4 rounded-xl"
                  style={{
                    background: 'rgba(59, 130, 246, 0.1)',
                    border: '1px solid rgba(59, 130, 246, 0.2)',
                  }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white">Next 30-Day Revenue</span>
                    <span className="text-sm font-bold" style={{ color: '#3b82f6' }}>
                      $847,200
                    </span>
                  </div>
                  <div className="h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.1)' }}>
                    <div
                      className="h-full rounded-full"
                      style={{ width: '85%', background: '#3b82f6' }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Prediction Types */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Prediction Models
            </h2>
            <p className="text-lg" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              Enterprise-grade ML models continuously trained on your data.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {predictions.map((pred) => (
              <div
                key={pred.title}
                className="p-6 rounded-2xl transition-all hover:scale-[1.02]"
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <div className="flex items-start gap-4">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{
                      background: 'rgba(236, 72, 153, 0.1)',
                      border: '1px solid rgba(236, 72, 153, 0.2)',
                    }}
                  >
                    <pred.icon className="w-6 h-6" style={{ color: '#ec4899' }} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-lg font-semibold text-white">{pred.title}</h3>
                      <span
                        className="text-sm font-bold px-2 py-1 rounded"
                        style={{
                          background: 'rgba(34, 197, 94, 0.1)',
                          color: '#22c55e',
                        }}
                      >
                        {pred.accuracy} accuracy
                      </span>
                    </div>
                    <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                      {pred.description}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-16">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {[
              { step: '1', title: 'Connect Data', desc: 'Link your customer and event data' },
              { step: '2', title: 'Train Models', desc: 'ML models learn from your patterns' },
              { step: '3', title: 'Get Predictions', desc: 'Real-time scores for every customer' },
              { step: '4', title: 'Take Action', desc: 'Automated workflows based on predictions' },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <div
                  className="w-14 h-14 rounded-xl flex items-center justify-center text-xl font-bold mx-auto mb-4"
                  style={{
                    background: 'linear-gradient(135deg, #ec4899 0%, #a855f7 100%)',
                    color: '#ffffff',
                  }}
                >
                  {item.step}
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{item.title}</h3>
                <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                  {item.desc}
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
            className="p-12 rounded-3xl"
            style={{
              background:
                'linear-gradient(135deg, rgba(236, 72, 153, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">
              Start Predicting Today
            </h2>
            <p className="text-lg mb-8" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              See predictions for your customers within 48 hours.
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
