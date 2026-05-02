/**
 * Topbar — dashboard shell header.
 *
 * Layout (left → right):
 *   ⌕ Search input          (flex-1, max-w-md)        ThemeToggle  Profile/slot
 *
 * The search input is uncontrolled-friendly: caller passes `onSearch`
 * which fires on Enter (or debounced via `onChange` if they prefer).
 *
 * Profile slot is intentionally generic — the dashboard already has its
 * own profile dropdown in TenantLayout; we just expose a slot so callers
 * compose the existing dropdown without us re-implementing it.
 */

import {
  type FormEvent,
  type ReactNode,
  useState,
  useCallback,
} from 'react';
import { Search } from 'lucide-react';
import { ThemeToggle } from '../theme/ThemeToggle';
import { cn } from '@/lib/utils';

interface TopbarProps {
  /** Initial search value. */
  defaultSearch?: string;
  /** Fires on Enter or when the user clears via Escape. */
  onSearch?: (value: string) => void;
  /** Fires on every keystroke — useful for live filtering. */
  onSearchChange?: (value: string) => void;
  /** Search input placeholder. */
  searchPlaceholder?: string;
  /** Right-side slot for profile menu / notifications. */
  rightSlot?: ReactNode;
  /** Left-side slot — e.g. a breadcrumb or page title above the bar. */
  leftSlot?: ReactNode;
  /** Hide the theme toggle (tenant-only views). */
  hideThemeToggle?: boolean;
  className?: string;
}

export function Topbar({
  defaultSearch = '',
  onSearch,
  onSearchChange,
  searchPlaceholder = 'Search campaigns, audiences, signals…',
  rightSlot,
  leftSlot,
  hideThemeToggle = false,
  className,
}: TopbarProps) {
  const [value, setValue] = useState(defaultSearch);

  const handleSubmit = useCallback(
    (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      onSearch?.(value);
    },
    [onSearch, value]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const v = e.target.value;
      setValue(v);
      onSearchChange?.(v);
    },
    [onSearchChange]
  );

  return (
    <header
      className={cn(
        'flex items-center gap-4 h-14 px-5',
        'bg-card border-b border-border',
        className
      )}
      role="banner"
    >
      {leftSlot}

      <form
        role="search"
        onSubmit={handleSubmit}
        className="flex-1 flex items-center gap-2 max-w-md"
      >
        <label htmlFor="topbar-search" className="sr-only">
          Search
        </label>
        <div className="relative flex-1">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none"
            aria-hidden="true"
          />
          <input
            id="topbar-search"
            type="search"
            value={value}
            onChange={handleChange}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                setValue('');
                onSearchChange?.('');
                onSearch?.('');
              }
            }}
            placeholder={searchPlaceholder}
            className={cn(
              'w-full h-9 pl-9 pr-3 rounded-full',
              'bg-muted/40 border border-transparent text-body text-foreground',
              'placeholder:text-muted-foreground',
              'transition-colors duration-200',
              'focus:outline-none focus:bg-card focus:border-border',
              'focus-visible:ring-2 focus-visible:ring-primary/20'
            )}
          />
        </div>
      </form>

      <div className="flex items-center gap-3 ml-auto">
        {!hideThemeToggle && <ThemeToggle />}
        {rightSlot}
      </div>
    </header>
  );
}

export default Topbar;
