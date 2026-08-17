/**
 * Page shell header: title, a context line, and right-aligned actions.
 *
 * The context line states the decision the screen supports, not what the
 * screen is. "6 active · 2 held by trust gate" tells the operator whether they
 * need to act; "Manage your campaigns" tells them nothing. Writing that line is
 * part of migrating a view.
 */
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface PageHeaderProps {
  title: string;
  context?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export function PageHeader({ title, context, actions, className }: PageHeaderProps) {
  return (
    <header className={cn('border-b border-border pb-5', className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-[28px] font-semibold leading-tight text-foreground">{title}</h1>
          {context ? (
            <p data-slot="context" className="mt-1 text-sm text-muted-foreground">
              {context}
            </p>
          ) : null}
        </div>
        {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
      </div>
    </header>
  );
}

export default PageHeader;
