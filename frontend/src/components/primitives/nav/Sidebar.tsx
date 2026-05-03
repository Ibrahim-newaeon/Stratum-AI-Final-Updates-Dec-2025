/**
 * Sidebar — collapsible-group navigation for the dashboard shell.
 *
 * IA: 3 top-level groups (Operate / Intelligence / Account) with
 * existing routes nested. Honors the "max 3 sidebar items" brief
 * without deleting product surface.
 *
 * Behaviour:
 * - Group expanded state persisted in localStorage('stratum-sidebar-groups').
 * - Group containing the active route is force-expanded on first paint.
 * - Items can declare `children` for a 2nd-level sub-nav (e.g. CDP sub-pages);
 *   the parent auto-expands when any descendant route is active.
 * - Items can declare `visible: false` to hide based on caller-supplied role
 *   gating (filtered at config build time, not inside the primitive).
 * - Mobile drawer mode: when `mobileOpen` is provided the sidebar slides in
 *   from the left over a backdrop. Hidden offscreen otherwise.
 * - Active item: ember accent line + brighter foreground.
 * - Keyboard: Tab through items; group/sub-nav toggles fire on Enter/Space.
 */

import {
  type ComponentType,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface SidebarItem {
  label: string;
  href: string;
  /** Optional badge text (e.g. "3 holds"). */
  badge?: string;
  /** Optional decorative icon (lucide-react component). */
  icon?: ComponentType<{ className?: string }>;
  /** Optional 2nd-level sub-nav (e.g. CDP sub-pages). */
  children?: SidebarItem[];
}

export interface SidebarGroup {
  id: string;
  label: string;
  items: SidebarItem[];
}

interface SidebarProps {
  /** Top-level "brand" slot (logo / wordmark). */
  brand?: ReactNode;
  groups: SidebarGroup[];
  currentPath: string;
  /** Bottom slot (e.g. user mini-profile). */
  footer?: ReactNode;
  className?: string;
  /** Storage key override for group-collapse state. */
  storageKey?: string;
  /** Mobile drawer open state. When undefined, drawer behaviour is disabled. */
  mobileOpen?: boolean;
  /** Fired when the user dismisses the mobile drawer. */
  onMobileOpenChange?: (open: boolean) => void;
}

const DEFAULT_STORAGE_KEY = 'stratum-sidebar-groups';

function readStoredCollapse(key: string): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === 'object') return parsed as Record<string, boolean>;
  } catch {
    // ignore
  }
  return {};
}

function writeStoredCollapse(key: string, state: Record<string, boolean>): void {
  try {
    localStorage.setItem(key, JSON.stringify(state));
  } catch {
    // ignore
  }
}

function isItemActive(itemHref: string, currentPath: string): boolean {
  if (itemHref === currentPath) return true;
  // Treat /dashboard/foo as active for /dashboard/foo/bar (nested).
  if (itemHref !== '/' && currentPath.startsWith(itemHref + '/')) return true;
  return false;
}

function isItemOrChildActive(item: SidebarItem, currentPath: string): boolean {
  if (isItemActive(item.href, currentPath)) return true;
  return !!item.children?.some((c) => isItemActive(c.href, currentPath));
}

function isGroupActive(group: SidebarGroup, currentPath: string): boolean {
  return group.items.some((item) => isItemOrChildActive(item, currentPath));
}

export function Sidebar({
  brand,
  groups,
  currentPath,
  footer,
  className,
  storageKey = DEFAULT_STORAGE_KEY,
  mobileOpen,
  onMobileOpenChange,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(() =>
    readStoredCollapse(storageKey)
  );
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});

  // Force-expand the group + any item containing the active route on
  // first paint and on route changes (only if user hasn't explicitly
  // collapsed it before).
  useEffect(() => {
    setCollapsed((prev) => {
      const next = { ...prev };
      let changed = false;
      for (const g of groups) {
        if (isGroupActive(g, currentPath) && next[g.id] === true) {
          next[g.id] = false;
          changed = true;
        }
      }
      return changed ? next : prev;
    });
    setExpandedItems((prev) => {
      const next = { ...prev };
      let changed = false;
      for (const g of groups) {
        for (const item of g.items) {
          if (item.children?.length && isItemOrChildActive(item, currentPath) && !next[item.href]) {
            next[item.href] = true;
            changed = true;
          }
        }
      }
      return changed ? next : prev;
    });
  }, [currentPath, groups]);

  const toggleGroup = useCallback(
    (groupId: string) => {
      setCollapsed((prev) => {
        const next = { ...prev, [groupId]: !prev[groupId] };
        writeStoredCollapse(storageKey, next);
        return next;
      });
    },
    [storageKey]
  );

  const toggleItem = useCallback((href: string) => {
    setExpandedItems((prev) => ({ ...prev, [href]: !prev[href] }));
  }, []);

  const dismissMobile = useCallback(() => {
    onMobileOpenChange?.(false);
  }, [onMobileOpenChange]);

  const renderItem = useCallback(
    (item: SidebarItem, depth = 0): ReactNode => {
      const Icon = item.icon;
      const active = isItemActive(item.href, currentPath);
      const hasChildren = !!item.children?.length;
      const itemExpanded = expandedItems[item.href] ?? false;
      const parentActive = hasChildren && isItemOrChildActive(item, currentPath);

      const visualActive = depth === 0 ? active || parentActive : active;

      const linkClasses = cn(
        'group flex items-center gap-3',
        depth === 0 ? 'px-3 py-2' : 'px-3 py-1.5',
        'rounded-lg text-body',
        'transition-colors duration-150',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        visualActive
          ? 'text-foreground bg-muted/50'
          : 'text-muted-foreground hover:text-foreground hover:bg-muted/30'
      );

      const accentBar = (
        <span
          aria-hidden="true"
          className={cn(
            'h-4 w-0.5 rounded-full -ml-3 mr-1',
            visualActive ? 'bg-primary' : 'bg-transparent'
          )}
        />
      );

      const iconEl = Icon ? (
        <Icon
          className={cn(
            'flex-shrink-0',
            depth === 0 ? 'w-4 h-4' : 'w-3.5 h-3.5',
            visualActive ? 'text-primary' : 'text-muted-foreground'
          )}
        />
      ) : null;

      const badgeEl = item.badge ? (
        <span
          className={cn(
            'text-[10px] px-1.5 py-0.5 rounded-full',
            'font-mono uppercase tracking-[0.06em]',
            visualActive ? 'bg-primary/15 text-primary' : 'bg-muted text-muted-foreground'
          )}
        >
          {item.badge}
        </span>
      ) : null;

      if (hasChildren) {
        return (
          <li key={item.href}>
            <div className="flex items-center">
              <Link
                to={item.href}
                aria-current={active ? 'page' : undefined}
                onClick={dismissMobile}
                className={cn(linkClasses, 'flex-1')}
              >
                {accentBar}
                {iconEl}
                <span className="flex-1 truncate">{item.label}</span>
                {badgeEl}
              </Link>
              <button
                type="button"
                aria-expanded={itemExpanded}
                aria-controls={`sidebar-children-${item.href}`}
                aria-label={itemExpanded ? `Collapse ${item.label}` : `Expand ${item.label}`}
                onClick={() => toggleItem(item.href)}
                className={cn(
                  'p-2 rounded-lg text-muted-foreground hover:text-foreground transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                )}
              >
                <ChevronDown
                  className={cn(
                    'w-3.5 h-3.5 transition-transform duration-200',
                    !itemExpanded && '-rotate-90'
                  )}
                  aria-hidden="true"
                />
              </button>
            </div>
            <ul
              id={`sidebar-children-${item.href}`}
              hidden={!itemExpanded}
              className={cn(
                'mt-0.5 ml-4 space-y-0.5 border-l border-border pl-2',
                itemExpanded && 'animate-fade-in'
              )}
            >
              {item.children?.map((c) => renderItem(c, depth + 1))}
            </ul>
          </li>
        );
      }

      return (
        <li key={item.href}>
          <Link
            to={item.href}
            aria-current={active ? 'page' : undefined}
            onClick={dismissMobile}
            className={linkClasses}
          >
            {accentBar}
            {iconEl}
            <span className="flex-1 truncate">{item.label}</span>
            {badgeEl}
          </Link>
        </li>
      );
    },
    [currentPath, expandedItems, toggleItem, dismissMobile]
  );

  const renderedGroups = useMemo(
    () =>
      groups.map((group) => {
        const isCollapsed = !!collapsed[group.id];
        const sectionId = `sidebar-group-${group.id}`;
        return (
          <div key={group.id} className="mb-2">
            <button
              type="button"
              aria-expanded={!isCollapsed}
              aria-controls={sectionId}
              onClick={() => toggleGroup(group.id)}
              className={cn(
                'w-full flex items-center justify-between',
                'px-3 py-2 rounded-lg',
                'text-meta uppercase tracking-[0.06em] font-mono text-muted-foreground',
                'hover:text-foreground hover:bg-muted/40 transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            >
              <span>{group.label}</span>
              <ChevronDown
                className={cn(
                  'w-3.5 h-3.5 transition-transform duration-200',
                  isCollapsed && '-rotate-90'
                )}
                aria-hidden="true"
              />
            </button>
            <ul
              id={sectionId}
              hidden={isCollapsed}
              className={cn('mt-1 space-y-0.5', !isCollapsed && 'animate-fade-in')}
            >
              {group.items.map((item) => renderItem(item, 0))}
            </ul>
          </div>
        );
      }),
    [groups, collapsed, toggleGroup, renderItem]
  );

  const isMobileMode = typeof mobileOpen === 'boolean';

  const aside = (
    <aside
      className={cn(
        'flex flex-col h-full w-60 bg-card border-r border-border',
        isMobileMode &&
          cn(
            'fixed inset-y-0 left-0 z-50 transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]',
            'lg:static lg:translate-x-0',
            mobileOpen ? 'translate-x-0' : '-translate-x-full'
          ),
        className
      )}
      aria-label="Primary navigation"
    >
      {brand && (
        <div className="px-4 py-5 border-b border-border flex items-center justify-between">
          <div className="flex-1 min-w-0">{brand}</div>
          {isMobileMode && (
            <button
              type="button"
              onClick={dismissMobile}
              aria-label="Close navigation"
              className={cn(
                'lg:hidden p-1.5 rounded-md text-muted-foreground hover:text-foreground transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      )}
      <nav className="flex-1 overflow-y-auto px-2 py-4 scrollbar-thin">{renderedGroups}</nav>
      {footer && <div className="px-4 py-3 border-t border-border">{footer}</div>}
    </aside>
  );

  if (!isMobileMode) {
    return aside;
  }

  return (
    <>
      {/* Mobile backdrop. Hidden on lg+. */}
      <div
        aria-hidden="true"
        onClick={dismissMobile}
        className={cn(
          'fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity duration-200 lg:hidden',
          mobileOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
      />
      {aside}
    </>
  );
}

export default Sidebar;
