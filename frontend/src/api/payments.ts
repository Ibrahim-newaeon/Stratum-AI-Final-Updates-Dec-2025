import { apiClient } from './client';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Types
interface CheckoutRequest {
  tier: 'starter' | 'professional' | 'enterprise';
  success_url: string;
  cancel_url: string;
  trial_days?: number;
}

interface CheckoutResponse {
  checkout_url: string;
  session_id: string;
  expires_at: string;
}

interface SubscriptionResponse {
  id: string;
  status: string;
  tier: string;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  trial_end: string | null;
}

interface BillingOverview {
  stripe_configured: boolean;
  has_customer: boolean;
  customer_id: string | null;
  subscription: {
    has_subscription: boolean;
    subscription_id: string | null;
    status: string | null;
    tier: string | null;
    current_period_start: string | null;
    current_period_end: string | null;
    cancel_at_period_end: boolean;
    trial_end: string | null;
  };
  upcoming_invoice: {
    amount_due: number;
    currency: string;
    next_payment_date: string;
  } | null;
  payment_methods: PaymentMethod[];
  available_tiers: TierInfo[];
}

interface PaymentMethod {
  id: string;
  type: string;
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  is_default: boolean;
}

interface Invoice {
  id: string;
  status: string;
  amount_due: number;
  amount_paid: number;
  currency: string;
  created: string;
  hosted_invoice_url: string | null;
  invoice_pdf: string | null;
}

interface TierInfo {
  tier: string;
  name: string;
  price: number;
  features: string[];
}

interface PaymentConfig {
  stripe_configured: boolean;
  publishable_key: string;
  tiers: TierInfo[];
}

interface UpgradeRequest {
  new_tier: string;
  prorate?: boolean;
}

// API functions
const paymentsApi = {
  getConfig: () => apiClient.get<PaymentConfig>('/payments/config').then(r => r.data),
  getOverview: () => apiClient.get<BillingOverview>('/payments/overview').then(r => r.data),
  getSubscription: () => apiClient.get<SubscriptionResponse>('/payments/subscription').then(r => r.data),
  getInvoices: () => apiClient.get<Invoice[]>('/payments/invoices').then(r => r.data),
  getPaymentMethods: () => apiClient.get<PaymentMethod[]>('/payments/payment-methods').then(r => r.data),
  createCheckout: (data: CheckoutRequest) => apiClient.post<CheckoutResponse>('/payments/checkout', data).then(r => r.data),
  createPortal: () => apiClient.post<{ portal_url: string }>('/payments/portal', { return_url: window.location.origin + '/settings' }).then(r => r.data),
  upgradeSubscription: (data: UpgradeRequest) => apiClient.post<SubscriptionResponse>('/payments/subscription/upgrade', data).then(r => r.data),
  cancelSubscription: () => apiClient.post('/payments/subscription/cancel').then(r => r.data),
  reactivateSubscription: () => apiClient.post('/payments/subscription/reactivate').then(r => r.data),
};

// Query hooks
export function usePaymentConfig() {
  return useQuery({
    queryKey: ['payments', 'config'],
    queryFn: paymentsApi.getConfig,
    staleTime: 5 * 60 * 1000,
  });
}

export function useBillingOverview() {
  return useQuery({
    queryKey: ['payments', 'overview'],
    queryFn: paymentsApi.getOverview,
  });
}

export function useSubscription() {
  return useQuery({
    queryKey: ['payments', 'subscription'],
    queryFn: paymentsApi.getSubscription,
    retry: false,
  });
}

export function useInvoices() {
  return useQuery({
    queryKey: ['payments', 'invoices'],
    queryFn: paymentsApi.getInvoices,
  });
}

export function usePaymentMethods() {
  return useQuery({
    queryKey: ['payments', 'payment-methods'],
    queryFn: paymentsApi.getPaymentMethods,
  });
}

// Mutation hooks
export function useCreateCheckout() {
  return useMutation({
    mutationFn: paymentsApi.createCheckout,
  });
}

export function useCreatePortal() {
  return useMutation({
    mutationFn: paymentsApi.createPortal,
  });
}

export function useUpgradeSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: paymentsApi.upgradeSubscription,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payments'] });
    },
  });
}

export function useCancelSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: paymentsApi.cancelSubscription,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payments'] });
    },
  });
}

export function useReactivateSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: paymentsApi.reactivateSubscription,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payments'] });
    },
  });
}

// Re-export types
export type {
  CheckoutRequest,
  CheckoutResponse,
  SubscriptionResponse,
  BillingOverview,
  PaymentMethod,
  Invoice,
  TierInfo,
  PaymentConfig,
  UpgradeRequest,
};
