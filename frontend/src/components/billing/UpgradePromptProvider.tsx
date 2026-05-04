/**
 * UpgradePromptProvider — surface the limit-triggered upgrade modal app-wide.
 *
 * The backend's limits service raises HTTP 402 (Payment Required) with a
 * structured payload when a tenant hits a tier ceiling — e.g., trying
 * to invite a 6th user on Starter (5 max). The axios interceptor in
 * api/client.ts dispatches a global `stratum:upgrade-required` event
 * with that payload; this provider listens for it and opens a
 * figma-themed upgrade drawer with a one-click Stripe-checkout CTA.
 *
 * Manual triggers via the `useUpgradePrompt()` hook are also supported
 * for outcome-based nudges (e.g., after a successful autopilot decision
 * surfaces a "see what Pro unlocks" prompt).
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import { Card } from '@/components/primitives/Card';
import { ConfirmDrawer } from '@/components/primitives/ConfirmDrawer';
import { useCreateCheckout } from '@/api/payments';
import { cn } from '@/lib/utils';

export type SuggestedTier = 'professional' | 'enterprise';

export interface UpgradeContext {
  /** Why the user hit this prompt. Free-form copy for the drawer body. */
  message: string;
  /** What the user was trying to do (e.g., "invite a 6th teammate"). */
  limitType?: string;
  currentTier?: string;
  suggestedTier?: SuggestedTier;
  /** When non-null, the drawer renders a small "X / Y" usage row. */
  current?: number;
  max?: number;
}

interface UpgradePromptContextValue {
  /** Open the prompt programmatically. */
  triggerUpgrade: (ctx: UpgradeContext) => void;
  /** Close without taking action. */
  dismiss: () => void;
}

const UpgradePromptContext = createContext<UpgradePromptContextValue | undefined>(undefined);

const TIER_PRICE: Record<SuggestedTier, { name: string; price: number }> = {
  professional: { name: 'Professional', price: 999 },
  enterprise: { name: 'Enterprise', price: 0 },
};

interface UpgradePromptProviderProps {
  children: ReactNode;
}

export function UpgradePromptProvider({ children }: UpgradePromptProviderProps) {
  const [ctx, setCtx] = useState<UpgradeContext | null>(null);
  const [redirectError, setRedirectError] = useState<string | null>(null);
  const checkout = useCreateCheckout();

  const triggerUpgrade = useCallback((c: UpgradeContext) => {
    setRedirectError(null);
    setCtx(c);
  }, []);

  const dismiss = useCallback(() => {
    setCtx(null);
    setRedirectError(null);
  }, []);

  // Listen for the global event the axios 402 interceptor dispatches.
  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<Record<string, unknown>>).detail ?? {};
      const suggested = (detail.suggested_tier as SuggestedTier) ?? 'professional';
      triggerUpgrade({
        message:
          (detail.message as string) ||
          `You've hit a ${detail.current_tier ?? 'Starter'} tier limit.`,
        limitType: detail.limit_type as string | undefined,
        currentTier: detail.current_tier as string | undefined,
        suggestedTier: suggested,
        current: detail.current as number | undefined,
        max: detail.max as number | undefined,
      });
    };
    window.addEventListener('stratum:upgrade-required', handler as EventListener);
    return () => window.removeEventListener('stratum:upgrade-required', handler as EventListener);
  }, [triggerUpgrade]);

  const handleConfirm = useCallback(async () => {
    if (!ctx?.suggestedTier) return;
    setRedirectError(null);

    if (ctx.suggestedTier === 'enterprise') {
      window.location.href = 'mailto:sales@stratumai.app?subject=Enterprise%20plan%20inquiry';
      dismiss();
      return;
    }

    try {
      const successUrl = `${window.location.origin}/dashboard/plans?status=success`;
      const cancelUrl = `${window.location.origin}/dashboard/plans?status=cancel`;
      const result = await checkout.mutateAsync({
        tier: ctx.suggestedTier,
        success_url: successUrl,
        cancel_url: cancelUrl,
      });
      window.location.href = result.checkout_url;
    } catch (err) {
      const msg =
        (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data
          ?.detail ??
        (err as { message?: string }).message ??
        'Failed to start checkout. Please try again.';
      setRedirectError(msg);
    }
  }, [ctx, checkout, dismiss]);

  const value = useMemo<UpgradePromptContextValue>(
    () => ({ triggerUpgrade, dismiss }),
    [triggerUpgrade, dismiss]
  );

  const open = ctx !== null;
  const tierMeta = ctx?.suggestedTier ? TIER_PRICE[ctx.suggestedTier] : null;

  return (
    <UpgradePromptContext.Provider value={value}>
      {children}
      <ConfirmDrawer
        open={open}
        onOpenChange={(o) => {
          if (!o) dismiss();
        }}
        title={tierMeta ? `Upgrade to ${tierMeta.name}` : 'Upgrade required'}
        description={ctx?.message ?? 'Upgrade your plan to continue.'}
        variant="default"
        confirmLabel={
          ctx?.suggestedTier === 'enterprise'
            ? 'Open email'
            : tierMeta
              ? `Continue to checkout`
              : 'Continue'
        }
        cancelLabel="Maybe later"
        onConfirm={handleConfirm}
        loading={checkout.isPending}
        disabled={!ctx?.suggestedTier}
      >
        {ctx && (
          <Card className="p-5 space-y-3">
            <div className="flex items-start gap-3">
              <Sparkles className="w-4 h-4 mt-0.5 flex-shrink-0 text-primary" aria-hidden="true" />
              <div className="flex-1 min-w-0">
                <p className="text-meta uppercase tracking-[0.06em] text-muted-foreground font-mono">
                  {ctx.currentTier ?? 'Current'} tier · {ctx.limitType ?? 'limit reached'}
                </p>
                {typeof ctx.current === 'number' && typeof ctx.max === 'number' && (
                  <p className="text-body text-foreground tabular-nums mt-1">
                    Using {ctx.current} of {ctx.max}.
                  </p>
                )}
              </div>
            </div>

            {tierMeta && (
              <>
                <div className="border-t border-border" />
                <div className="flex items-center justify-between">
                  <span className="text-meta uppercase tracking-[0.06em] text-muted-foreground font-mono">
                    Upgrade to
                  </span>
                  <span className="text-body font-medium text-foreground">{tierMeta.name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-meta uppercase tracking-[0.06em] text-muted-foreground font-mono">
                    Charge
                  </span>
                  <span
                    className={cn(
                      'text-body font-medium text-foreground tabular-nums',
                      tierMeta.price === 0 && 'text-muted-foreground'
                    )}
                  >
                    {tierMeta.price === 0
                      ? 'Custom'
                      : `$${tierMeta.price.toLocaleString()} / month`}
                  </span>
                </div>
              </>
            )}

            {checkout.isPending && (
              <div className="flex items-center gap-2 text-meta text-muted-foreground pt-1">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Connecting to Stripe…
              </div>
            )}

            {redirectError && (
              <div className="text-meta text-danger pt-1">
                <span className="font-medium">Couldn't start checkout.</span> {redirectError}
              </div>
            )}
          </Card>
        )}
      </ConfirmDrawer>
    </UpgradePromptContext.Provider>
  );
}

export function useUpgradePrompt(): UpgradePromptContextValue {
  const ctx = useContext(UpgradePromptContext);
  if (!ctx) {
    throw new Error('useUpgradePrompt must be used within UpgradePromptProvider');
  }
  return ctx;
}
