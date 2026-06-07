/**
 * Trust Engine Solution Page — landing-themed (ink + ember).
 * Trust-gated automation system.
 */

import { useEffect } from 'react';
import { usePageContent, type SolutionPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import {
  MktHero,
  MktSectionHeader,
  MktFeatureCard,
  MktCard,
} from '@/components/landing/marketing';
import { SEO } from '@/components/common/SEO';
import {
  BoltIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
  SignalIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

const fallbackHero = {
  badge: 'Trust Engine',
  title: 'Automation with',
  titleHighlight: 'built-in safety',
  description:
    'The Trust Engine ensures automations only execute when your data is healthy. No more blind optimization based on bad signals.',
  ctaText: 'Start Free Trial',
  ctaLink: '/signup',
};

const fallbackFeatures = [
  {
    iconName: 'XCircleIcon',
    title: 'Prevent Bad Decisions',
    description: 'Never optimize on corrupted data',
  },
  {
    iconName: 'CheckCircleIcon',
    title: 'Reduce Manual Oversight',
    description: 'Automated safety checks 24/7',
  },
  {
    iconName: 'ShieldCheckIcon',
    title: 'Audit Trail',
    description: 'Full logging of all gate decisions',
  },
  {
    iconName: 'BoltIcon',
    title: 'Customizable Thresholds',
    description: 'Set your own risk tolerance',
  },
];

const fallbackSteps = [
  { step: 1, title: 'Signal Health Check', description: 'Continuous monitoring of data quality' },
  { step: 2, title: 'Trust Gate', description: 'Pass / Hold / Block decision' },
  { step: 3, title: 'Automation Decision', description: 'Execute only when safe' },
];

const benefitIconMap: Record<string, typeof XCircleIcon> = {
  XCircleIcon,
  CheckCircleIcon,
  ShieldCheckIcon,
  BoltIcon,
};

/** Gate behavior cards keep genuine status semantics (success / warning / destructive). */
const gateBehaviors = [
  {
    status: 'HEALTHY',
    threshold: '≥70',
    action: 'EXECUTE',
    description: 'Automations run normally. Full autopilot mode enabled.',
    wrap: 'bg-success/10 border-success/20',
    accent: 'text-success',
  },
  {
    status: 'DEGRADED',
    threshold: '40-69',
    action: 'HOLD',
    description: 'Automations paused. Alert sent for review. Manual override available.',
    wrap: 'bg-warning/10 border-warning/20',
    accent: 'text-warning',
  },
  {
    status: 'UNHEALTHY',
    threshold: '<40',
    action: 'BLOCK',
    description: 'All automations blocked. Manual intervention required.',
    wrap: 'bg-destructive/10 border-destructive/20',
    accent: 'text-destructive',
  },
];

export default function TrustEngineSolution() {
  const { page, content } = usePageContent<SolutionPageContent>('solutions-trust-engine');

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
  const benefits = content?.features?.length ? content.features : fallbackFeatures;
  const steps = content?.steps?.length ? content.steps : fallbackSteps;

  return (
    <PageLayout>
      <SEO
        title="Trust Engine"
        description="Signal health monitoring and trust-gated automation. Ensure your automations only execute when data is reliable."
        url="https://stratum-ai.com/solutions/trust-engine"
      />

      <MktHero
        badge={hero.badge}
        badgeIcon={ShieldCheckIcon}
        title={hero.title}
        highlight={hero.titleHighlight}
        subtitle={hero.description}
        primary={{ label: hero.ctaText, href: hero.ctaLink }}
        secondary={{ label: 'See Signal Health', href: '/features' }}
      >
        <MktCard className="mt-16 max-w-xl mx-auto p-8">
          <div className="space-y-6">
            <div className="text-center">
              <SignalIcon className="w-12 h-12 mx-auto mb-2 text-success" />
              <div className="text-h3 text-foreground font-semibold">Signal Health</div>
              <div className="text-display-xs font-semibold mt-2 text-success">87</div>
            </div>
            <div className="flex items-center justify-center gap-4">
              <div className="text-center">
                <div className="w-16 h-16 rounded-xl bg-success/10 border border-success/20 flex items-center justify-center mx-auto mb-2">
                  <CheckCircleIcon className="w-8 h-8 text-success" />
                </div>
                <div className="text-micro uppercase text-muted-foreground">HEALTHY</div>
                <div className="text-micro text-muted-foreground">≥70</div>
              </div>
              <div className="text-center">
                <div className="w-16 h-16 rounded-xl bg-warning/10 border border-warning/20 flex items-center justify-center mx-auto mb-2">
                  <ExclamationTriangleIcon className="w-8 h-8 text-warning" />
                </div>
                <div className="text-micro uppercase text-muted-foreground">DEGRADED</div>
                <div className="text-micro text-muted-foreground">40-69</div>
              </div>
              <div className="text-center">
                <div className="w-16 h-16 rounded-xl bg-destructive/10 border border-destructive/20 flex items-center justify-center mx-auto mb-2">
                  <XCircleIcon className="w-8 h-8 text-destructive" />
                </div>
                <div className="text-micro uppercase text-muted-foreground">UNHEALTHY</div>
                <div className="text-micro text-muted-foreground">{'<40'}</div>
              </div>
            </div>
          </div>
        </MktCard>
      </MktHero>

      {/* How it works */}
      <section className="pb-12">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader
            eyebrow="How it works"
            title="How the Trust Engine"
            highlight="works"
          />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {steps.map((step, i) => (
              <MktCard key={step.step} delay={i * 0.06} className="p-8">
                <div className="w-11 h-11 rounded-full bg-secondary/10 border border-secondary/20 flex items-center justify-center mb-5">
                  <span className="text-h3 font-semibold text-secondary">{step.step}</span>
                </div>
                <h3 className="text-h3 text-foreground font-semibold mb-2">{step.title}</h3>
                <p className="text-body text-muted-foreground leading-relaxed">
                  {step.description}
                </p>
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      {/* Gate Behaviors */}
      <section className="py-24 lg:py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader eyebrow="Gate behaviors" title="What the" highlight="gate does" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {gateBehaviors.map((gate, i) => (
              <MktCard key={gate.status} delay={i * 0.05} className={`p-6 ${gate.wrap}`}>
                <div className="flex items-center justify-between mb-4">
                  <span className={`text-meta uppercase font-semibold ${gate.accent}`}>
                    {gate.status}
                  </span>
                  <span
                    className={`text-meta px-2 py-1 rounded bg-foreground/5 ${gate.accent}`}
                  >
                    {gate.threshold}
                  </span>
                </div>
                <div className="text-h2 text-foreground font-semibold mb-2">{gate.action}</div>
                <p className="text-body text-muted-foreground leading-relaxed">
                  {gate.description}
                </p>
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="py-24 lg:py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader
            eyebrow="Why it matters"
            title="Why trust-gated"
            highlight="automation?"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {benefits.map((benefit, i) => (
              <MktFeatureCard
                key={benefit.title}
                icon={benefitIconMap[benefit.iconName] ?? ShieldCheckIcon}
                title={benefit.title}
                description={benefit.description}
                delay={(i % 4) * 0.05}
              />
            ))}
          </div>
        </div>
      </section>

      <CTA />
    </PageLayout>
  );
}
