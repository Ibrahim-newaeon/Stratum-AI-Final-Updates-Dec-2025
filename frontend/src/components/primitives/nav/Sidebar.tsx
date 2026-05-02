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
 * - Active item: ember accent line + brighter foreground.
 * - Keyboard: Tab through items; group headers toggle on Enter/Space.
 *
 * Routing-agnostic: caller passes `currentPath` (typically from
 * useLocation().pathname). Items render as plain <a> so the caller
 * can swap to Link/NavLink at the call site without a tighter coupling.
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
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface SidebarItem {
  label: string;
  href: string;
  /** Optional badge text (e.g. "3 holds"). */
  badge?: string;
  /** Optional decorative icon (lucide-react component). */
  icon?: ComponentType<{ className?: string }>;
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

function isGroupActive(group: SidebarGroup, currentPath: string): boolean {
  return group.items.some((item) => isItemActive(item.href, currentPath));
}

export function Sidebar({
  brand,
  groups,
  currentPath,
  footer,
  className,
  storageKey = DEFAULT_STORAGE_KEY,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(() =>
    readStoredCollapse(storageKey)
  );

  // Force-expand the group containing the active route on first paint
  // (only if user hasn't explicitly collapsed it before).
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
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = isItemActive(item.href, currentPath);
                return (
                  <li key={item.href}>
                    <Link
                      to={item.href}
                      aria-current={active ? 'page' : undefined}
                      className={cn(
                        'group flex items-center gap-3',
                        'px-3 py-2 rounded-lg text-body',
                        'transition-colors duration-150',
                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                        active
                          ? 'text-foreground bg-muted/50'
                          : 'text-muted-foreground hover:text-foreground hover:bg-muted/30'
                      )}
                    >
                      {/* Active indicator: ember vertical line on the left. */}
                      <span
                        aria-hidden="true"
                        className={cn(
                          'h-4 w-0.5 rounded-full -ml-3 mr-1',
                          active ? 'bg-primary' : 'bg-transparent'
                        )}
                      />
                      {Icon && (
                        <Icon
                          className={cn(
                            'w-4 h-4 flex-shrink-0',
                            active ? 'text-primary' : 'text-muted-foreground'
                          )}
                        />
                      )}
                      <span className="flex-1 truncate">{item.label}</span>
                      {item.badge && (
                        <span
                          className={cn(
                            'text-[10px] px-1.5 py-0.5 rounded-full',
                            'font-mono uppercase tracking-[0.06em]',
                            active ? 'bg-primary/15 text-primary' : 'bg-muted text-muted-foreground'
                          )}
                        >
                          {item.badge}
                        </span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      }),
    [groups, collapsed, currentPath, toggleGroup]
  );

  return (
    <aside
      className={cn('flex flex-col h-full w-60 bg-card border-r border-border', className)}
      aria-label="Primary navigation"
    >
      {brand && <div className="px-4 py-5 border-b border-border">{brand}</div>}
      <nav className="flex-1 overflow-y-auto px-2 py-4 scrollbar-thin">{renderedGroups}</nav>
      {footer && <div className="px-4 py-3 border-t border-border">{footer}</div>}
    </aside>
  );
}

export default Sidebar;
