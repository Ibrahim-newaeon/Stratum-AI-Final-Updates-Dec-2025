/**
 * Predictions Solution Page
 * ML-powered predictions and forecasting
 */

import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { usePageContent, type SolutionPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { SEO } from '@/components/common/SEO';
import {
  ArrowTrendingUpIcon,
  CurrencyDollarIcon,
  LightBulbIcon,
  SparklesIcon,
  UserMinusIcon,
} from '@heroicons/react/24/outline';

const fallbackHero = {
  badge: 'ML Predictions',
  title: 'Predict the Future',
  titleHighlight: 'Act Today',
  description:
    'Machine learning models trained on your data deliver actionable predictions for churn, LTV, revenue, and optimal customer actions.',
  ctaText: 'Start Free Trial',
  ctaLink: '/signup',
};

const fallbackSteps = [
  { step: 1, title: 'Connect Data', description: 'Link your customer and event data' },
  { step: 2, title: 'Train Models', description: 'ML models learn from your patterns' },
  { step: 3, title: 'Get Predictions', description: 'Real-time scores for every customer' },
  { step: 4, title: 'Take Action', description: 'Automated workflows based on predictions' },
];

const fallbackFeatures = [
  {
    icon: UserMinusIcon,
    iconName: 'UserMinusIcon',
    title: 'Churn Prediction',
    description:
      'Identify at-risk customers before they leave. Get actionable retention recommendations.',
    accuracy: '94%',
    color: 'var(--landing-accent-red)',
  },
  {
    icon: CurrencyDollarIcon,
    iconName: 'CurrencyDollarIcon',
    title: 'LTV Forecasting',
    description:
      'Predict customer lifetime value at acquisition. Optimize acquisition spend accordingly.',
    accuracy: '91%',
    color: 'var(--landing-accent-green)',
  },
  {
    icon: ArrowTrendingUpIcon,
    iconName: 'ArrowTrendingUpIcon',
    title: 'Revenue Forecasting',
    description: 'Accurate revenue predictions based on historical patterns and market signals.',
    accuracy: '89%',
    color: 'var(--landing-accent-blue)',
  },
  {
    icon: LightBulbIcon,
    iconName: 'LightBulbIcon',
    title: 'Next-Best-Action',
    description: 'AI-powered recommendations for the optimal next engagement for each customer.',
    accuracy: '87%',
    color: '#f97316',
  },
];

/** Map icon name strings from CMS to actual icon components */
const iconMap: Record<string, typeof UserMinusIcon> = {
  UserMinusIcon,
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  LightBulbIcon,
  SparklesIcon,
};

export default function PredictionsSolution() {
  const { page, content } = usePageContent<SolutionPageContent>('solutions-predictions');

  // SEO: override document title / meta description when CMS provides them
  useEffect(() => {
    if (page?.meta_title) document.title = page.meta_title;
    if (page?.meta_description) {
      document
        .querySelector('meta[name="description"]')
        ?.setAttribute('content', page.meta_description);
    }
  }, [page?.meta_title, page?.meta_description]);

  // CMS data with hardcoded fallback
  const hero = content?.hero ?? fallbackHero;
  const steps = content?.steps?.length ? content.steps : fallbackSteps;
  const predictions = content?.features?.length
    ? content.features.map((f, i) => ({
        ...f,
        icon: iconMap[f.iconName] ?? SparklesIcon,
        color: fallbackFeatures[i]?.color ?? '#a855f7',
        accuracy: fallbackFeatures[i]?.accuracy ?? '',
      }))
    : fallbackFeatures;

  return (
    <PageLayout>
      <SEO title="Predictive Analytics" description="ML-powered predictions for ROAS, churn risk, and budget optimization. Make data-driven decisions with confidence." url="https://stratum-ai.com/solutions/predictions" />
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <div
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
                style={{
                  background: 'rgba(255, 179, 71, 0.1)',
                  border: '1px solid rgba(255, 179, 71, 0.3)',
                  color: 'var(--landing-accent-warm)',
                }}
              >
                <SparklesIcon className="w-4 h-4" />
                {hero.badge}
              </div>
              <h1
                className="text-4xl md:text-5xl font-bold mb-6"
                style={{ fontFamily: "Geist, system-ui, sans-serif" }}
              >
                <span className="text-white">{hero.title}</span>
                <br />
                <span style={{ color: 'var(--landing-accent-coral)' }}>{hero.titleHighlight}</span>
              </h1>
              <p className="text-lg mb-8" style={{ color: 'var(--landing-text)' }}>
                {hero.description}
              </p>
              <Link
                to={hero.ctaLink}
                className="inline-flex px-8 py-4 rounded-full text-lg font-semibold text-white transition-opacity hover:opacity-90"
                style={{
                  background: 'var(--landing-accent-coral)',
                  boxShadow: '0 4px 20px rgba(255, 90, 31, 0.3)',
                }}
              >
                {hero.ctaText}
              </Link>
            </div>
            <div
              className="rounded-3xl p-8"
              style={{
                background: 'var(--landing-card)',
                border: '1px solid var(--landing-border)',
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
                    <span className="text-sm font-bold" style={{ color: 'var(--landing-accent-red)' }}>
                      847 customers
                    </span>
                  </div>
                  <div className="h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.1)' }}>
                    <div
                      className="h-full rounded-full"
                      style={{ width: '23%', background: 'var(--landing-accent-red)' }}
                    />
                  </div>
                </div>
                <div
                  className="p-4 rounded-xl"
                  style={{
                    background: 'rgba(52, 199, 89, 0.1)',
                    border: '1px solid rgba(52, 199, 89, 0.2)',
                  }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white">High LTV Potential</span>
                    <span className="text-sm font-bold" style={{ color: 'var(--landing-accent-green)' }}>
                      2,341 customers
                    </span>
                  </div>
                  <div className="h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.1)' }}>
                    <div
                      className="h-full rounded-full"
                      style={{ width: '67%', background: 'var(--landing-accent-green)' }}
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
                    <span className="text-sm font-bold" style={{ color: 'var(--landing-accent-blue)' }}>
                      $847,200
                    </span>
                  </div>
                  <div className="h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.1)' }}>
                    <div
                      className="h-full rounded-full"
                      style={{ width: '85%', background: 'var(--landing-accent-blue)' }}
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
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">Prediction Models</h2>
            <p className="text-lg" style={{ color: 'var(--landing-text)' }}>
              Enterprise-grade ML models continuously trained on your data.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {predictions.map((pred) => (
              <div
                key={pred.title}
                className="p-6 rounded-2xl transition-transform hover:scale-[1.02]"
                style={{
                  background: 'var(--landing-card)',
                  border: '1px solid var(--landing-border)',
                  borderLeft: `3px solid ${pred.color}`,
                }}
              >
                <div className="flex items-start gap-4">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{
                      background: `${pred.color}25`,
                      border: `1px solid ${pred.color}40`,
                    }}
                  >
                    <pred.icon className="w-6 h-6" style={{ color: pred.color }} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-lg font-semibold text-white">{pred.title}</h3>
                      <span
                        className="text-sm font-bold px-2 py-1 rounded"
                        style={{
                          background: 'rgba(52, 199, 89, 0.1)',
                          color: 'var(--landing-accent-green)',
                        }}
                      >
                        {pred.accuracy} accuracy
                      </span>
                    </div>
                    <p className="text-sm" style={{ color: 'var(--landing-text)' }}>
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
            {steps.map((item) => (
              <div key={item.step} className="text-center">
                <div
                  className="w-14 h-14 rounded-xl flex items-center justify-center text-xl font-bold mx-auto mb-4"
                  style={{
                    background: 'var(--landing-accent-coral)',
                    color: '#ffffff',
                  }}
                >
                  {item.step}
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{item.title}</h3>
                <p className="text-sm" style={{ color: 'var(--landing-text)' }}>
                  {item.description}
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
              background: 'var(--landing-card)',
              border: '1px solid var(--landing-border)',
            }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">Start Predicting Today</h2>
            <p className="text-lg mb-8" style={{ color: 'var(--landing-text)' }}>
              See predictions for your customers within 48 hours.
            </p>
            <Link
              to="/signup"
              className="inline-flex px-8 py-4 rounded-full text-lg font-semibold text-white transition-opacity hover:opacity-90"
              style={{
                background: 'var(--landing-accent-coral)',
                boxShadow: '0 4px 20px rgba(255, 90, 31, 0.3)',
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
