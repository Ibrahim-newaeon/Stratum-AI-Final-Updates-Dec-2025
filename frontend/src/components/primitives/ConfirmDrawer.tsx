/**
 * ConfirmDrawer — preview-then-confirm gate for destructive actions.
 *
 * The bulk actions in the Overview ("Pause all", "Acknowledge all", etc.)
 * and per-row destructive CTAs ("Pause", "Hold") need a confirmation
 * gate that surfaces:
 *   • what the user is about to do (verb + scope)
 *   • the blast radius (preview rows / counts)
 *   • a clear cancel + confirm pair
 *
 * This is the figma-themed primitive for that gate. Built on Radix
 * Dialog so focus management, escape-to-close, and click-outside
 * behavior come for free.
 *
 * Variants:
 *   default      — primary (ember) confirm button
 *   destructive  — danger-tinted confirm + warning banner
 *   warning      — warning-tinted confirm
 *
 * Usage:
 *   <ConfirmDrawer
 *     open={open}
 *     onOpenChange={setOpen}
 *     title="Pause 14 campaigns"
 *     description="$48,200 of daily spend will stop within 60s."
 *     variant="destructive"
 *     confirmLabel="Pause campaigns"
 *     onConfirm={handle}
 *     loading={mutation.isPending}
 *   >
 *     <DataTable data={preview} … />
 *   </ConfirmDrawer>
 */

import * as React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { AlertTriangle, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export type ConfirmDrawerVariant = 'default' | 'destructive' | 'warning';

interface ConfirmDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  /** Renders inside the drawer above the action row — typically a preview table or list. */
  children?: React.ReactNode;
  variant?: ConfirmDrawerVariant;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void | Promise<void>;
  loading?: boolean;
  /** Disables confirm button (e.g. validation pending). */
  disabled?: boolean;
}

const VARIANT_CONFIRM: Record<ConfirmDrawerVariant, string> = {
  default: 'bg-primary text-primary-foreground hover:brightness-110',
  destructive: 'bg-danger text-white hover:brightness-110',
  warning: 'bg-warning text-zinc-950 hover:brightness-110',
};

const VARIANT_BANNER: Record<ConfirmDrawerVariant, string> = {
  default: 'border-primary/30 bg-primary/5 text-foreground',
  destructive: 'border-danger/40 bg-danger/8 text-foreground',
  warning: 'border-warning/40 bg-warning/8 text-foreground',
};

export function ConfirmDrawer({
  open,
  onOpenChange,
  title,
  description,
  children,
  variant = 'default',
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  loading = false,
  disabled = false,
}: ConfirmDrawerProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay
          className={cn(
            'fixed inset-0 z-50 bg-background/80 backdrop-blur-sm',
            'data-[state=open]:animate-in data-[state=closed]:animate-out',
            'data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0'
          )}
        />
        <Dialog.Content
          className={cn(
            'fixed top-[50%] left-[50%] z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2',
            'bg-card border border-border rounded-2xl shadow-elevated',
            'p-0 overflow-hidden',
            'data-[state=open]:animate-in data-[state=closed]:animate-out',
            'data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0',
            'data-[state=open]:zoom-in-95 data-[state=closed]:zoom-out-95'
          )}
        >
          {/* Header */}
          <div className="px-6 pt-6 pb-4">
            <div className="flex items-start gap-3">
              {variant !== 'default' && (
                <AlertTriangle
                  aria-hidden="true"
                  className={cn(
                    'w-5 h-5 mt-0.5 flex-shrink-0',
                    variant === 'destructive' ? 'text-danger' : 'text-warning'
                  )}
                />
              )}
              <div className="min-w-0 flex-1">
                <Dialog.Title className="text-h3 font-medium tracking-tight text-foreground">
                  {title}
                </Dialog.Title>
                {description && (
                  <Dialog.Description className="text-body text-muted-foreground mt-1.5">
                    {description}
                  </Dialog.Description>
                )}
              </div>
              <Dialog.Close
                className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </Dialog.Close>
            </div>

            {variant !== 'default' && (
              <div
                className={cn(
                  'mt-4 px-3 py-2 rounded-lg border text-meta',
                  VARIANT_BANNER[variant]
                )}
                role="alert"
              >
                {variant === 'destructive'
                  ? 'This action affects live campaigns and cannot be undone in-place.'
                  : 'Review the changes below before confirming.'}
              </div>
            )}
          </div>

          {/* Body — preview content */}
          {children && (
            <div className="px-6 pb-4 max-h-[50vh] overflow-y-auto scrollbar-thin">
              {children}
            </div>
          )}

          {/* Action row */}
          <div className="px-6 py-4 border-t border-border flex items-center justify-end gap-2">
            <Dialog.Close
              disabled={loading}
              className={cn(
                'inline-flex items-center justify-center rounded-full px-4 py-2 text-meta font-medium',
                'border border-border bg-card text-foreground',
                'hover:bg-muted transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            >
              {cancelLabel}
            </Dialog.Close>
            <button
              type="button"
              onClick={() => void onConfirm()}
              disabled={loading || disabled}
              className={cn(
                'inline-flex items-center justify-center rounded-full px-4 py-2 text-meta font-medium gap-2',
                'transition-all',
                VARIANT_CONFIRM[variant],
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card'
              )}
            >
              {loading && (
                <svg
                  className="animate-spin w-3.5 h-3.5"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
              )}
              {loading ? 'Working…' : confirmLabel}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export default ConfirmDrawer;
