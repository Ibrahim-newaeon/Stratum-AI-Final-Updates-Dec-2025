/**
 * Predictions Solution Page — landing-themed (ink + ember).
 * ML-powered predictions and forecasting.
 */

import { useEffect } from 'react';
import { usePageContent, type SolutionPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import {
  MktHero,
  MktSectionHeader,
  MktCard,
} from '@/components/landing/marketing';
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
  title: 'Predict the future,',
  titleHighlight: 'act today',
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
  },
  {
    icon: CurrencyDollarIcon,
    iconName: 'CurrencyDollarIcon',
    title: 'LTV Forecasting',
    description:
      'Predict customer lifetime value at acquisition. Optimize acquisition spend accordingly.',
    accuracy: '91%',
  },
  {
    icon: ArrowTrendingUpIcon,
    iconName: 'ArrowTrendingUpIcon',
    title: 'Revenue Forecasting',
    description: 'Accurate revenue predictions based on historical patterns and market signals.',
    accuracy: '89%',
  },
  {
    icon: LightBulbIcon,
    iconName: 'LightBulbIcon',
    title: 'Next-Best-Action',
    description: 'AI-powered recommendations for the optimal next engagement for each customer.',
    accuracy: '87%',
  },
];

/** Predictions surfaced in the hero diagram, with genuine status semantics preserved. */
const heroPredictions = [
  {
    label: 'High Churn Risk',
    value: '847 customers',
    width: '23%',
    tone: 'destructive' as const,
  },
  {
    label: 'High LTV Potential',
    value: '2,341 customers',
    width: '67%',
    tone: 'success' as const,
  },
  {
    label: 'Next 30-Day Revenue',
    value: '$847,200',
    width: '85%',
    tone: 'accent' as const,
  },
];

const toneClasses: Record<
  'destructive' | 'success' | 'accent',
  { wrap: string; value: string; bar: string }
> = {
  destructive: {
    wrap: 'bg-destructive/10 border border-destructive/20',
    value: 'text-destructive',
    bar: 'bg-destructive',
  },
  success: {
    wrap: 'bg-success/10 border border-success/20',
    value: 'text-success',
    bar: 'bg-success',
  },
  accent: {
    wrap: 'bg-accent/10 border border-accent/20',
    value: 'text-accent',
    bar: 'bg-accent',
  },
};

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
        accuracy: fallbackFeatures[i]?.accuracy ?? '',
      }))
    : fallbackFeatures;

  return (
    <PageLayout>
      <SEO
        title="Predictive Analytics"
        description="ML-powered predictions for ROAS, churn risk, and budget optimization. Make data-driven decisions with confidence."
        url="https://stratum-ai.com/solutions/predictions"
      />

      <MktHero
        badge={hero.badge}
        badgeIcon={SparklesIcon}
        title={hero.title}
        highlight={hero.titleHighlight}
        subtitle={hero.description}
        primary={{ label: hero.ctaText, href: hero.ctaLink }}
        secondary={{ label: 'Explore the CDP', href: '/solutions/cdp' }}
      >
        <MktCard className="mt-16 max-w-xl mx-auto p-6 text-left">
          <div className="space-y-4">
            {heroPredictions.map((p) => {
              const tone = toneClasses[p.tone];
              return (
                <div key={p.label} className={`p-4 rounded-xl ${tone.wrap}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-meta uppercase text-muted-foreground">{p.label}</span>
                    <span className={`text-body font-semibold ${tone.value}`}>{p.value}</span>
                  </div>
                  <div className="h-2 rounded-full bg-foreground/10">
                    <div className={`h-full rounded-full ${tone.bar}`} style={{ width: p.width }} />
                  </div>
                </div>
              );
            })}
          </div>
        </MktCard>
      </MktHero>

      {/* Prediction Models */}
      <section className="pb-12">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader
            eyebrow="Prediction models"
            title="Enterprise-grade"
            highlight="ML models"
            subtitle="Enterprise-grade ML models continuously trained on your data."
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {predictions.map((pred, i) => (
              <MktCard key={pred.title} delay={(i % 2) * 0.05} className="p-6">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-xl bg-secondary/10 border border-secondary/20 flex items-center justify-center flex-shrink-0">
                    <pred.icon className="w-6 h-6 text-secondary" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between gap-3 mb-2">
                      <h3 className="text-h3 text-foreground font-semibold">{pred.title}</h3>
                      {pred.accuracy ? (
                        <span className="text-meta font-semibold px-2 py-1 rounded bg-success/10 text-success">
                          {pred.accuracy} accuracy
                        </span>
                      ) : null}
                    </div>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      {pred.description}
                    </p>
                  </div>
                </div>
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-24 lg:py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader eyebrow="How it works" title="From data to" highlight="decisions" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map((item, i) => (
              <MktCard key={item.step} delay={i * 0.05} className="p-8">
                <div className="w-11 h-11 rounded-full bg-secondary/10 border border-secondary/20 flex items-center justify-center mb-5">
                  <span className="text-h3 font-semibold text-secondary">{item.step}</span>
                </div>
                <h3 className="text-h3 text-foreground font-semibold mb-2">{item.title}</h3>
                <p className="text-body text-muted-foreground leading-relaxed">
                  {item.description}
                </p>
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      <CTA />
    </PageLayout>
  );
}
