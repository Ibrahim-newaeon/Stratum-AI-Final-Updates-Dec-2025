/**
 * Marketing primitives — shared building blocks for the public inner pages
 * (features, pricing, solutions, integrations, api-docs).
 *
 * Encodes the landing-page design language so every inner page matches the
 * home page exactly: ink + ember palette, semantic tokens, `text-display-*`
 * type scale, `text-gradient-primary` accents, restrained ember icon chips
 * (no rainbow), and `animate-enter` reveals.
 */

import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

type IconType = React.ComponentType<{ className?: string }>;
type CTALink = { label: string; href: string };

/** Ember pill used as an eyebrow above headings. */
export function MktBadge({ icon: Icon, children }: { icon?: IconType; children: ReactNode }) {
  return (
    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-secondary/10 border border-secondary/20 animate-enter">
      {Icon ? <Icon className="w-4 h-4 text-secondary" /> : null}
      <span className="text-meta uppercase text-secondary">{children}</span>
    </div>
  );
}

/** Primary (ember) call-to-action button. */
export function MktPrimaryButton({ label, href }: CTALink) {
  return (
    <Link
      to={href}
      className="group inline-flex items-center gap-2 px-7 py-3.5 rounded-full bg-stratum-500 text-primary-foreground font-semibold text-body hover:brightness-110 hover:shadow-glow transition-all duration-200"
    >
      {label}
      <ArrowRight className="w-5 h-5 transition-transform duration-200 group-hover:translate-x-1" />
    </Link>
  );
}

/** Secondary (outline) call-to-action button. */
export function MktSecondaryButton({ label, href }: CTALink) {
  return (
    <Link
      to={href}
      className="inline-flex items-center px-7 py-3.5 rounded-full bg-card border border-border text-foreground font-semibold text-body hover:bg-foreground/5 transition-colors duration-200"
    >
      {label}
    </Link>
  );
}

/** Page hero — badge + display heading + subtitle + CTAs, with an ember bleed. */
export function MktHero({
  badge,
  badgeIcon,
  title,
  highlight,
  subtitle,
  primary,
  secondary,
  children,
}: {
  badge?: string;
  badgeIcon?: IconType;
  title: string;
  highlight?: string;
  subtitle: string;
  primary?: CTALink;
  secondary?: CTALink;
  children?: ReactNode;
}) {
  return (
    <section className="relative overflow-hidden pt-16 pb-20 lg:pt-24 lg:pb-28">
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-[820px] h-[420px] rounded-full bg-primary/5 blur-3xl" />
      </div>
      <div className="relative max-w-4xl mx-auto px-6 text-center">
        {badge ? <MktBadge icon={badgeIcon}>{badge}</MktBadge> : null}
        <h1
          className="mt-6 text-display-sm md:text-display text-foreground animate-enter"
          style={{ animationDelay: '0.05s' }}
        >
          {title}
          {highlight ? (
            <>
              {' '}
              <span className="text-gradient-primary">{highlight}</span>
            </>
          ) : null}
        </h1>
        <p
          className="mt-6 text-body text-muted-foreground max-w-2xl mx-auto animate-enter"
          style={{ animationDelay: '0.15s' }}
        >
          {subtitle}
        </p>
        {(primary || secondary) && (
          <div
            className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 animate-enter"
            style={{ animationDelay: '0.25s' }}
          >
            {primary ? <MktPrimaryButton {...primary} /> : null}
            {secondary ? <MktSecondaryButton {...secondary} /> : null}
          </div>
        )}
        {children}
      </div>
    </section>
  );
}

/** Centered section header (eyebrow + display heading + subtitle). */
export function MktSectionHeader({
  eyebrow,
  title,
  highlight,
  subtitle,
}: {
  eyebrow?: string;
  title: string;
  highlight?: string;
  subtitle?: string;
}) {
  return (
    <div className="max-w-2xl mx-auto text-center mb-14">
      {eyebrow ? (
        <p className="text-meta uppercase text-secondary mb-3">{eyebrow}</p>
      ) : null}
      <h2 className="text-display-xs md:text-display-sm text-foreground">
        {title}
        {highlight ? (
          <>
            {' '}
            <span className="text-gradient-primary">{highlight}</span>
          </>
        ) : null}
      </h2>
      {subtitle ? (
        <p className="mt-4 text-body text-muted-foreground">{subtitle}</p>
      ) : null}
    </div>
  );
}

/** Surface card with hairline border + ember hover (matches landing cards). */
export function MktCard({
  className = '',
  delay,
  children,
}: {
  className?: string;
  delay?: number;
  children: ReactNode;
}) {
  return (
    <div
      className={`rounded-2xl bg-card border border-border transition-colors duration-200 hover:border-secondary/30 animate-enter ${className}`}
      style={delay ? { animationDelay: `${delay}s` } : undefined}
    >
      {children}
    </div>
  );
}

/** Feature card: ember icon chip + title + description. */
export function MktFeatureCard({
  icon: Icon,
  title,
  description,
  delay,
}: {
  icon?: IconType;
  title: string;
  description: string;
  delay?: number;
}) {
  return (
    <MktCard className="p-8 group" delay={delay}>
      {Icon ? (
        <div className="w-12 h-12 rounded-xl bg-secondary/10 border border-secondary/20 flex items-center justify-center mb-5">
          <Icon className="w-6 h-6 text-secondary" />
        </div>
      ) : null}
      <h3 className="text-h3 text-foreground font-semibold mb-2">{title}</h3>
      <p className="text-body text-muted-foreground leading-relaxed">{description}</p>
    </MktCard>
  );
}

/** A compact KPI/stat tile. */
export function MktStat({ value, label, delay }: { value: string; label: string; delay?: number }) {
  return (
    <MktCard className="p-6 text-center" delay={delay}>
      <p className="text-display-xs text-gradient-primary font-medium">{value}</p>
      <p className="mt-1 text-meta uppercase text-muted-foreground">{label}</p>
    </MktCard>
  );
}
