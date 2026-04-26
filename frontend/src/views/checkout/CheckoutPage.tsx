import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Check, Loader2, ArrowLeft, Zap, Shield, Building2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCreateCheckout, usePaymentConfig } from '@/api/payments';

const TIER_DETAILS = {
  starter: {
    name: 'Starter',
    price: 499,
    icon: Zap,
    description: 'For growing agencies',
    features: [
      '5 ad accounts',
      '2 platforms (Meta + Google)',
      'Basic signal health',
      'Email alerts',
      '100K monthly ad spend limit',
      'Standard support',
    ],
  },
  professional: {
    name: 'Professional',
    price: 999,
    icon: Shield,
    description: 'For scaling teams',
    popular: true,
    features: [
      '15 ad accounts',
      '4 platforms (Meta, Google, TikTok, Snapchat)',
      'Advanced signal health + EMQ',
      'Autopilot enforcement',
      'CDP with audience sync',
      '500K monthly ad spend limit',
      'Priority support',
    ],
  },
  enterprise: {
    name: 'Enterprise',
    price: 2499,
    icon: Building2,
    description: 'For large organizations',
    features: [
      'Unlimited ad accounts',
      'All platforms + LinkedIn',
      'Full trust engine + ML predictions',
      'Custom autopilot rules',
      'Advanced CDP + identity graph',
      'Unlimited ad spend',
      'Dedicated support + SLA',
      'Custom integrations',
    ],
  },
};

export default function CheckoutPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preselected = searchParams.get('plan') as keyof typeof TIER_DETAILS | null;
  const [selectedTier, setSelectedTier] = useState<keyof typeof TIER_DETAILS>(preselected || 'professional');
  const checkout = useCreateCheckout();
  const { isLoading: configLoading } = usePaymentConfig();

  const handleCheckout = async () => {
    try {
      const result = await checkout.mutateAsync({
        tier: selectedTier,
        success_url: `${window.location.origin}/checkout/success?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${window.location.origin}/checkout/cancel`,
        trial_days: 14,
      });
      // Redirect to Stripe Checkout
      window.location.href = result.checkout_url;
    } catch (error) {

    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-5xl mx-auto px-4 py-12">
        {/* Back button */}
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-8"
          aria-label="Go back"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm">Back</span>
        </button>

        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold font-display text-foreground mb-2">
            Choose your plan
          </h1>
          <p className="text-muted-foreground">
            14-day free trial on all plans. No credit card required to start.
          </p>
        </div>

        {/* Plan Cards */}
        <div className="grid md:grid-cols-3 gap-6 mb-10">
          {(Object.entries(TIER_DETAILS) as [keyof typeof TIER_DETAILS, typeof TIER_DETAILS[keyof typeof TIER_DETAILS]][]).map(([key, tier]) => {
            const Icon = tier.icon;
            const isSelected = selectedTier === key;
            const isPopular = 'popular' in tier && tier.popular;

            return (
              <button
                key={key}
                onClick={() => setSelectedTier(key)}
                className={cn(
                  'relative text-left rounded-2xl p-6 border-2 transition-colors duration-200',
                  isSelected
                    ? 'border-primary bg-primary/5 ring-1 ring-primary/20'
                    : 'border-border hover:border-primary/30 bg-card',
                  isPopular && !isSelected && 'border-primary/20'
                )}
                aria-label={`Select ${tier.name} plan at $${tier.price} per month`}
                aria-pressed={isSelected}
              >
                {isPopular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-primary text-primary-foreground text-xs font-semibold rounded-full">
                    Most Popular
                  </div>
                )}

                <div className="flex items-center gap-3 mb-4">
                  <div className={cn(
                    'w-10 h-10 rounded-xl flex items-center justify-center',
                    isSelected ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
                  )}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="font-semibold text-foreground">{tier.name}</div>
                    <div className="text-xs text-muted-foreground">{tier.description}</div>
                  </div>
                </div>

                <div className="mb-5">
                  <span className="text-3xl font-bold font-display text-foreground">${tier.price}</span>
                  <span className="text-muted-foreground text-sm">/mo</span>
                </div>

                <ul className="space-y-2.5">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-sm">
                      <Check className={cn(
                        'w-4 h-4 mt-0.5 shrink-0',
                        isSelected ? 'text-primary' : 'text-muted-foreground'
                      )} />
                      <span className="text-foreground/80">{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* Selection indicator */}
                <div className={cn(
                  'absolute top-4 right-4 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors',
                  isSelected ? 'border-primary bg-primary' : 'border-muted-foreground/30'
                )}>
                  {isSelected && <Check className="w-3 h-3 text-primary-foreground" />}
                </div>
              </button>
            );
          })}
        </div>

        {/* Checkout Button */}
        <div className="flex flex-col items-center gap-4">
          <button
            onClick={handleCheckout}
            disabled={checkout.isPending || configLoading}
            className="inline-flex items-center justify-center px-8 py-3.5 bg-primary text-primary-foreground font-semibold rounded-xl hover:bg-primary/90 transition-colors disabled:opacity-50 text-base min-w-0 sm:min-w-[280px]"
          >
            {checkout.isPending ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Redirecting to checkout...
              </>
            ) : (
              `Start 14-day free trial — ${TIER_DETAILS[selectedTier].name}`
            )}
          </button>

          {checkout.isError && (
            <p className="text-sm text-destructive">
              Something went wrong. Please try again.
            </p>
          )}

          <p className="text-xs text-muted-foreground text-center max-w-md">
            You won't be charged during your 14-day trial. Cancel anytime before it ends.
            After the trial, you'll be billed ${TIER_DETAILS[selectedTier].price}/month.
          </p>
        </div>
      </div>
    </div>
  );
}
