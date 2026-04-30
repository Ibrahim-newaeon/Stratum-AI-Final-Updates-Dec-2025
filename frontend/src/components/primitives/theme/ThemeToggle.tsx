/**
 * ThemeToggle — segmented sun / moon / system control.
 * Lives in the topbar. Keyboard-accessible, ARIA-labelled.
 */

import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme, type Theme } from './ThemeProvider';
import { cn } from '@/lib/utils';

interface Option {
  value: Theme;
  label: string;
  Icon: typeof Sun;
}

const OPTIONS: Option[] = [
  { value: 'light', label: 'Light theme', Icon: Sun },
  { value: 'dark', label: 'Dark theme', Icon: Moon },
  { value: 'system', label: 'System theme', Icon: Monitor },
];

interface ThemeToggleProps {
  className?: string;
}

export function ThemeToggle({ className }: ThemeToggleProps) {
  const { theme, setTheme } = useTheme();

  return (
    <div
      role="radiogroup"
      aria-label="Theme"
      className={cn(
        'inline-flex items-center gap-0.5 p-1 rounded-full',
        'bg-card border border-border',
        className
      )}
    >
      {OPTIONS.map(({ value, label, Icon }) => {
        const active = theme === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={active}
            aria-label={label}
            title={label}
            onClick={() => setTheme(value)}
            className={cn(
              'h-7 w-7 inline-flex items-center justify-center rounded-full',
              'transition-colors duration-200',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-card',
              active
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        );
      })}
    </div>
  );
}

export default ThemeToggle;
