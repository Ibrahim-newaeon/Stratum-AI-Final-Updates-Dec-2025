'use client';

import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { ChevronRight, Home, MoreHorizontal } from 'lucide-react';

import { cn } from '@/lib/utils';

// Breadcrumb root
const Breadcrumb = React.forwardRef<
  HTMLElement,
  React.ComponentPropsWithoutRef<'nav'> & {
    separator?: React.ReactNode;
  }
>(({ ...props }, ref) => <nav ref={ref} aria-label="breadcrumb" {...props} />);
Breadcrumb.displayName = 'Breadcrumb';

// Breadcrumb list
const BreadcrumbList = React.forwardRef<HTMLOListElement, React.ComponentPropsWithoutRef<'ol'>>(
  ({ className, ...props }, ref) => (
    <ol
      ref={ref}
      className={cn(
        'flex flex-wrap items-center gap-1.5 break-words text-sm text-muted-foreground sm:gap-2.5',
        className
      )}
      {...props}
    />
  )
);
BreadcrumbList.displayName = 'BreadcrumbList';

// Breadcrumb item
const BreadcrumbItem = React.forwardRef<HTMLLIElement, React.ComponentPropsWithoutRef<'li'>>(
  ({ className, ...props }, ref) => (
    <li ref={ref} className={cn('inline-flex items-center gap-1.5', className)} {...props} />
  )
);
BreadcrumbItem.displayName = 'BreadcrumbItem';

// Breadcrumb link
const BreadcrumbLink = React.forwardRef<
  HTMLAnchorElement,
  React.ComponentPropsWithoutRef<'a'> & {
    asChild?: boolean;
  }
>(({ asChild, className, ...props }, ref) => {
  const Comp = asChild ? Slot : 'a';

  return (
    <Comp
      ref={ref}
      className={cn(
        'transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-sm',
        className
      )}
      {...props}
    />
  );
});
BreadcrumbLink.displayName = 'BreadcrumbLink';

// Breadcrumb page (current page - not a link)
const BreadcrumbPage = React.forwardRef<HTMLSpanElement, React.ComponentPropsWithoutRef<'span'>>(
  ({ className, ...props }, ref) => (
    <span
      ref={ref}
      role="link"
      aria-disabled="true"
      aria-current="page"
      className={cn('font-normal text-foreground', className)}
      {...props}
    />
  )
);
BreadcrumbPage.displayName = 'BreadcrumbPage';

// Breadcrumb separator
const BreadcrumbSeparator = ({ children, className, ...props }: React.ComponentProps<'li'>) => (
  <li
    role="presentation"
    aria-hidden="true"
    className={cn('[&>svg]:size-3.5', className)}
    {...props}
  >
    {children ?? <ChevronRight />}
  </li>
);
BreadcrumbSeparator.displayName = 'BreadcrumbSeparator';

// Breadcrumb ellipsis (for collapsed items)
const BreadcrumbEllipsis = ({ className, ...props }: React.ComponentProps<'span'>) => (
  <span
    role="presentation"
    aria-hidden="true"
    className={cn('flex h-9 w-9 items-center justify-center', className)}
    {...props}
  >
    <MoreHorizontal className="h-4 w-4" />
    <span className="sr-only">More</span>
  </span>
);
BreadcrumbEllipsis.displayName = 'BreadcrumbEllipsis';

// Home icon component for first breadcrumb
const BreadcrumbHome = React.forwardRef<
  HTMLAnchorElement,
  React.ComponentPropsWithoutRef<'a'> & {
    asChild?: boolean;
  }
>(({ asChild, className, ...props }, ref) => {
  const Comp = asChild ? Slot : 'a';

  return (
    <Comp
      ref={ref}
      className={cn(
        'flex items-center transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-sm',
        className
      )}
      aria-label="Home"
      {...props}
    >
      <Home className="h-4 w-4" />
    </Comp>
  );
});
BreadcrumbHome.displayName = 'BreadcrumbHome';

// Helper component for common breadcrumb patterns
export interface BreadcrumbItemData {
  label: string;
  href?: string;
  icon?: React.ReactNode;
}

export interface SimpleBreadcrumbProps extends React.ComponentPropsWithoutRef<'nav'> {
  items: BreadcrumbItemData[];
  separator?: React.ReactNode;
  showHome?: boolean;
  homeHref?: string;
  maxItems?: number;
}

const SimpleBreadcrumb = React.forwardRef<HTMLElement, SimpleBreadcrumbProps>(
  (
    { items, separator, showHome = false, homeHref = '/', maxItems = 0, className, ...props },
    ref
  ) => {
    // Collapse items if maxItems is set and we have more items
    let displayItems = items;
    let hasCollapsed = false;

    if (maxItems > 0 && items.length > maxItems) {
      // Keep first item, ellipsis, and last (maxItems - 1) items
      const firstItem = items[0];
      const lastItems = items.slice(-(maxItems - 1));
      displayItems = [firstItem, ...lastItems];
      hasCollapsed = true;
    }

    return (
      <Breadcrumb ref={ref} className={className} {...props}>
        <BreadcrumbList>
          {/* Home link */}
          {showHome && (
            <>
              <BreadcrumbItem>
                <BreadcrumbHome href={homeHref} />
              </BreadcrumbItem>
              <BreadcrumbSeparator>{separator}</BreadcrumbSeparator>
            </>
          )}

          {displayItems.map((item, index) => {
            const isLast = index === displayItems.length - 1;

            // Insert ellipsis after first item if collapsed
            const showEllipsis = hasCollapsed && index === 0;

            return (
              <React.Fragment key={item.label}>
                <BreadcrumbItem>
                  {item.icon && <span className="mr-1.5">{item.icon}</span>}
                  {isLast || !item.href ? (
                    <BreadcrumbPage>{item.label}</BreadcrumbPage>
                  ) : (
                    <BreadcrumbLink href={item.href}>{item.label}</BreadcrumbLink>
                  )}
                </BreadcrumbItem>

                {showEllipsis && (
                  <>
                    <BreadcrumbSeparator>{separator}</BreadcrumbSeparator>
                    <BreadcrumbItem>
                      <BreadcrumbEllipsis />
                    </BreadcrumbItem>
                  </>
                )}

                {!isLast && <BreadcrumbSeparator>{separator}</BreadcrumbSeparator>}
              </React.Fragment>
            );
          })}
        </BreadcrumbList>
      </Breadcrumb>
    );
  }
);
SimpleBreadcrumb.displayName = 'SimpleBreadcrumb';

export {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator,
  BreadcrumbEllipsis,
  BreadcrumbHome,
  SimpleBreadcrumb,
};
