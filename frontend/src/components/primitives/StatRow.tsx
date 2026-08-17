/**
 * Inline stat strip — deliberately NOT cards.
 *
 * Four bordered cards atop every list screen is what makes a dashboard read as
 * crowded, and it dilutes Card variant="glow", which the theme reserves for
 * emphasis on the home view. Weight here comes from typography: mono figures
 * with tabular numerals, mono uppercase labels, hairline dividers.
 */
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface StatRowItem {
  label: string;
  value: ReactNode;
}

interface StatRowProps {
  items: StatRowItem[];
  className?: string;
}

export function StatRow({ items, className }: StatRowProps) {
  if (items.length === 0) return null;

  return (
    <dl className={cn('flex flex-wrap items-stretch border-b border-border', className)}>
      {items.map((item) => (
        <div
          key={item.label}
          className="flex min-w-[9rem] flex-col gap-1 border-r border-border py-4 pr-8 last:border-r-0 [&:not(:first-child)]:pl-8"
        >
          <dt className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {item.label}
          </dt>
          <dd data-slot="stat-value" className="font-mono text-xl tabular-nums text-foreground">
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export default StatRow;
