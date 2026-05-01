/**
 * Card — base surface primitive.
 *
 * Variants:
 * - default   : surface bg, line border, no glow
 * - elevated  : surface-tier-2 bg, slight inner highlight
 * - glow      : default + ember radial bleed at the top edge (dark only)
 *
 * Composition contract:
 * - <Card>...</Card>
 * - <Card.Header />, <Card.Title />, <Card.Description />, <Card.Body />,
 *   <Card.Footer /> available via dot-notation for consistent spacing.
 *
 * Loading + empty are NOT props on Card itself — Card is a pure surface.
 * Components that compose Card (KPI, Chart, etc.) own those states.
 */

import { forwardRef, type HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

type CardVariant = 'default' | 'elevated' | 'glow';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  /** Shows a hover lift + ember-tinted border. */
  interactive?: boolean;
}

const VARIANT_CLASS: Record<CardVariant, string> = {
  default: 'bg-card',
  elevated: 'bg-surface-tier2',
  glow: 'bg-card',
};

const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  { variant = 'default', interactive = false, className, children, ...rest },
  ref
) {
  return (
    <div
      ref={ref}
      className={cn(
        'relative rounded-2xl border border-border',
        'transition-colors duration-200',
        VARIANT_CLASS[variant],
        interactive && 'hover:border-primary/30',
        className
      )}
      {...rest}
    >
      {variant === 'glow' && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 rounded-2xl overflow-hidden"
        >
          <div
            className="absolute inset-x-0 -top-12 h-32"
            style={{
              background:
                'radial-gradient(60% 60% at 50% 100%, hsl(var(--primary) / 0.18) 0%, hsl(var(--primary) / 0.04) 50%, transparent 75%)',
            }}
          />
        </div>
      )}
      <div className="relative">{children}</div>
    </div>
  );
});

const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(function CardHeader(
  { className, ...rest },
  ref
) {
  return (
    <div ref={ref} className={cn('flex flex-col gap-1.5 px-6 pt-6 pb-3', className)} {...rest} />
  );
});

const CardTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(
  function CardTitle({ className, ...rest }, ref) {
    return (
      <h3
        ref={ref}
        className={cn('text-h3 font-medium tracking-tight text-foreground', className)}
        {...rest}
      />
    );
  }
);

const CardDescription = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  function CardDescription({ className, ...rest }, ref) {
    return <p ref={ref} className={cn('text-body text-muted-foreground', className)} {...rest} />;
  }
);

const CardBody = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(function CardBody(
  { className, ...rest },
  ref
) {
  return <div ref={ref} className={cn('px-6 py-4', className)} {...rest} />;
});

const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(function CardFooter(
  { className, ...rest },
  ref
) {
  return (
    <div
      ref={ref}
      className={cn('flex items-center gap-3 px-6 pb-6 pt-3 border-t border-border', className)}
      {...rest}
    />
  );
});

type CardComponent = typeof Card & {
  Header: typeof CardHeader;
  Title: typeof CardTitle;
  Description: typeof CardDescription;
  Body: typeof CardBody;
  Footer: typeof CardFooter;
};

const CardWithSub = Card as CardComponent;
CardWithSub.Header = CardHeader;
CardWithSub.Title = CardTitle;
CardWithSub.Description = CardDescription;
CardWithSub.Body = CardBody;
CardWithSub.Footer = CardFooter;

export { CardWithSub as Card };
export type { CardProps, CardVariant };
