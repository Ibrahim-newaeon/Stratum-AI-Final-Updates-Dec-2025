/**
 * Billing (Super Admin View)
 *
 * Platform billing management - plans, invoices, subscriptions
 * Revenue metrics and dunning management
 */

import { useState } from 'react'
import { cn } from '@/lib/utils'
import {
  useRevenue,
  useBillingPlans,
  useBillingInvoices,
  useBillingSubscriptions,
  useRetryPayment,
} from '@/api/hooks'
import {
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  DocumentTextIcon,
  CreditCardIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline'

type PlanType = 'starter' | 'pro' | 'enterprise'
type SubscriptionStatus = 'active' | 'past_due' | 'canceled' | 'trialing'
type InvoiceStatus = 'paid' | 'pending' | 'overdue' | 'failed'

interface Subscription {
  id: string
  tenantId: string
  tenantName: string
  plan: PlanType
  status: SubscriptionStatus
  mrr: number
  startDate: Date
  nextBilling: Date
  paymentMethod: string
  failedPayments: number
}

interface Invoice {
  id: string
  tenantName: string
  amount: number
  status: InvoiceStatus
  dueDate: Date
  paidAt: Date | null
}

export default function Billing() {
  const [activeTab, setActiveTab] = useState<'overview' | 'subscriptions' | 'invoices' | 'plans'>('overview')

  // Fetch data from API
  const { data: revenueData, isLoading: revenueLoading } = useRevenue()
  const { data: plansData, isLoading: plansLoading } = useBillingPlans()
  const { data: invoicesData, isLoading: invoicesLoading } = useBillingInvoices()
  const { data: subscriptionsData, isLoading: subscriptionsLoading } = useBillingSubscriptions()
  const retryPaymentMutation = useRetryPayment()

  // Default mock data
  const mockMetrics = {
    mrr: 45890,
    mrrGrowth: 8.5,
    arr: 550680,
    activeSubscriptions: 89,
    churnRate: 2.3,
    pastDue: 4,
    totalRevenue: 1250000,
  }

  // Use API data or fallback to mock
  const metrics = {
    mrr: revenueData?.mrr ?? mockMetrics.mrr,
    mrrGrowth: revenueData?.mrrGrowth ?? mockMetrics.mrrGrowth,
    arr: revenueData?.arr ?? mockMetrics.arr,
    activeSubscriptions: subscriptionsData?.items?.filter(s => s.status === 'active').length ?? mockMetrics.activeSubscriptions,
    churnRate: revenueData?.churnRate ?? mockMetrics.churnRate,
    pastDue: subscriptionsData?.items?.filter(s => s.status === 'past_due').length ?? mockMetrics.pastDue,
    totalRevenue: mockMetrics.totalRevenue,
  }

  const mockSubscriptions: Subscription[] = [
    { id: 's1', tenantId: 't1', tenantName: 'Acme Corporation', plan: 'enterprise', status: 'active', mrr: 1999, startDate: new Date('2024-01-15'), nextBilling: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000), paymentMethod: 'Visa ****4242', failedPayments: 0 },
    { id: 's2', tenantId: 't2', tenantName: 'TechStart Inc', plan: 'pro', status: 'active', mrr: 499, startDate: new Date('2024-03-01'), nextBilling: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000), paymentMethod: 'Mastercard ****5555', failedPayments: 0 },
    { id: 's3', tenantId: 't3', tenantName: 'Fashion Forward', plan: 'pro', status: 'past_due', mrr: 499, startDate: new Date('2024-02-15'), nextBilling: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000), paymentMethod: 'Visa ****1234', failedPayments: 2 },
    { id: 's4', tenantId: 't4', tenantName: 'HealthPlus', plan: 'starter', status: 'trialing', mrr: 0, startDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), nextBilling: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), paymentMethod: 'Not set', failedPayments: 0 },
  ]

  const mockInvoices: Invoice[] = [
    { id: 'inv-001', tenantName: 'Acme Corporation', amount: 1999, status: 'paid', dueDate: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000), paidAt: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000) },
    { id: 'inv-002', tenantName: 'TechStart Inc', amount: 499, status: 'pending', dueDate: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000), paidAt: null },
    { id: 'inv-003', tenantName: 'Fashion Forward', amount: 499, status: 'overdue', dueDate: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000), paidAt: null },
  ]

  const mockPlans = [
    { id: 'starter', name: 'Starter', price: 99, features: ['2 platforms', '5 campaigns', 'Basic analytics', 'Email support'], subscribers: 23 },
    { id: 'pro', name: 'Pro', price: 499, features: ['5 platforms', 'Unlimited campaigns', 'Advanced analytics', 'Priority support', 'Autopilot'], subscribers: 52, highlighted: true },
    { id: 'enterprise', name: 'Enterprise', price: 1999, features: ['Unlimited platforms', 'Unlimited campaigns', 'Custom analytics', 'Dedicated support', 'Full Autopilot', 'SLA'], subscribers: 14 },
  ]

  // Use API data or fallback to mock
  const subscriptions: Subscription[] = subscriptionsData?.items?.map(s => ({
    id: s.id,
    tenantId: String(s.tenantId),
    tenantName: s.tenantName,
    plan: s.plan as PlanType,
    status: s.status,
    mrr: s.mrr,
    startDate: new Date(s.startDate),
    nextBilling: new Date(s.nextBillingDate),
    paymentMethod: s.paymentMethod,
    failedPayments: s.failedPayments,
  })) ?? mockSubscriptions

  const invoices: Invoice[] = invoicesData?.items?.map(i => ({
    id: i.id,
    tenantName: i.tenantName,
    amount: i.amount,
    status: i.status,
    dueDate: new Date(i.dueDate),
    paidAt: i.paidAt ? new Date(i.paidAt) : null,
  })) ?? mockInvoices

  const plans = plansData?.map(p => ({
    id: p.id,
    name: p.name,
    price: p.price,
    features: p.features,
    subscribers: p.subscriberCount,
    highlighted: p.name === 'Pro',
  })) ?? mockPlans

  const handleRetryPayment = async (subscriptionId: string) => {
    try {
      await retryPaymentMutation.mutateAsync(subscriptionId)
    } catch (error) {
      console.error('Failed to retry payment:', error)
    }
  }

  const getStatusColor = (status: SubscriptionStatus | InvoiceStatus) => {
    switch (status) {
      case 'active':
      case 'paid':
        return 'text-success bg-success/10'
      case 'past_due':
      case 'overdue':
        return 'text-danger bg-danger/10'
      case 'pending':
      case 'trialing':
        return 'text-warning bg-warning/10'
      case 'canceled':
      case 'failed':
        return 'text-text-muted bg-surface-tertiary'
    }
  }

  const getStatusIcon = (status: SubscriptionStatus | InvoiceStatus) => {
    switch (status) {
      case 'active':
      case 'paid':
        return <CheckCircleIcon className="w-4 h-4" />
      case 'past_due':
      case 'overdue':
      case 'failed':
        return <ExclamationTriangleIcon className="w-4 h-4" />
      case 'pending':
      case 'trialing':
        return <ClockIcon className="w-4 h-4" />
      case 'canceled':
        return <XCircleIcon className="w-4 h-4" />
    }
  }

  const tabs = [
    { id: 'overview' as const, label: 'Overview' },
    { id: 'subscriptions' as const, label: 'Subscriptions' },
    { id: 'invoices' as const, label: 'Invoices' },
    { id: 'plans' as const, label: 'Plans' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Billing</h1>
          <p className="text-text-muted">Revenue and subscription management</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-text-secondary hover:text-white transition-colors">
            <DocumentTextIcon className="w-4 h-4" />
            Export Report
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-white/10 pb-4">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'px-4 py-2 rounded-lg transition-colors',
              activeTab === tab.id
                ? 'bg-stratum-500/10 text-stratum-400'
                : 'text-text-muted hover:text-white hover:bg-white/5'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Revenue Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-gradient-to-br from-stratum-500/10 to-stratum-600/5 border border-stratum-500/20">
              <div className="flex items-center gap-2 text-text-muted text-sm mb-2">
                <CurrencyDollarIcon className="w-4 h-4" />
                Monthly Recurring Revenue
              </div>
              <div className="text-3xl font-bold text-white">
                ${metrics.mrr.toLocaleString()}
              </div>
              <div className="flex items-center gap-1 text-success text-sm mt-2">
                <ArrowTrendingUpIcon className="w-4 h-4" />
                +{metrics.mrrGrowth}% vs last month
              </div>
            </div>

            <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
              <div className="text-text-muted text-sm mb-2">Annual Recurring Revenue</div>
              <div className="text-3xl font-bold text-white">
                ${metrics.arr.toLocaleString()}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
              <div className="flex items-center gap-2 text-text-muted text-sm mb-2">
                <UserGroupIcon className="w-4 h-4" />
                Active Subscriptions
              </div>
              <div className="text-3xl font-bold text-white">{metrics.activeSubscriptions}</div>
            </div>

            <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
              <div className="text-text-muted text-sm mb-2">Churn Rate</div>
              <div className="text-3xl font-bold text-warning">{metrics.churnRate}%</div>
              <div className="flex items-center gap-1 text-danger text-sm mt-2">
                <ExclamationTriangleIcon className="w-4 h-4" />
                {metrics.pastDue} past due
              </div>
            </div>
          </div>

          {/* Plan Distribution */}
          <div className="rounded-2xl bg-surface-secondary border border-white/10 p-6">
            <h2 className="font-semibold text-white mb-4">Plan Distribution</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {plans.map((plan) => (
                <div
                  key={plan.id}
                  className={cn(
                    'p-4 rounded-xl border',
                    plan.highlighted
                      ? 'bg-stratum-500/10 border-stratum-500/30'
                      : 'bg-surface-tertiary border-white/5'
                  )}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-white">{plan.name}</span>
                    <span className="text-stratum-400">${plan.price}/mo</span>
                  </div>
                  <div className="text-3xl font-bold text-white">{plan.subscribers}</div>
                  <div className="text-sm text-text-muted">subscribers</div>
                  <div className="mt-2 text-sm text-text-muted">
                    ${(plan.price * plan.subscribers).toLocaleString()} MRR
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="rounded-2xl bg-surface-secondary border border-white/10 p-6">
            <h2 className="font-semibold text-white mb-4">Dunning Alerts</h2>
            <div className="space-y-3">
              {subscriptions
                .filter((s) => s.status === 'past_due' || s.failedPayments > 0)
                .map((sub) => (
                  <div
                    key={sub.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-danger/5 border border-danger/20"
                  >
                    <div className="flex items-center gap-3">
                      <ExclamationTriangleIcon className="w-5 h-5 text-danger" />
                      <div>
                        <div className="font-medium text-white">{sub.tenantName}</div>
                        <div className="text-sm text-text-muted">
                          {sub.failedPayments} failed payment(s) - {sub.paymentMethod}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button className="px-3 py-1 rounded-lg bg-surface-tertiary text-text-secondary hover:text-white text-sm transition-colors">
                        Contact
                      </button>
                      <button
                        onClick={() => handleRetryPayment(sub.id)}
                        disabled={retryPaymentMutation.isPending}
                        className="px-3 py-1 rounded-lg bg-danger/10 text-danger hover:bg-danger/20 text-sm transition-colors disabled:opacity-50"
                      >
                        {retryPaymentMutation.isPending ? 'Retrying...' : 'Retry Payment'}
                      </button>
                    </div>
                  </div>
                ))}
              {subscriptions.filter((s) => s.status === 'past_due' || s.failedPayments > 0).length === 0 && (
                <div className="flex items-center gap-2 text-success p-3">
                  <CheckCircleIcon className="w-5 h-5" />
                  No dunning alerts - all payments up to date
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Subscriptions Tab */}
      {activeTab === 'subscriptions' && (
        <div className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left p-4 text-text-muted font-medium">Tenant</th>
                <th className="text-left p-4 text-text-muted font-medium">Plan</th>
                <th className="text-left p-4 text-text-muted font-medium">Status</th>
                <th className="text-left p-4 text-text-muted font-medium">MRR</th>
                <th className="text-left p-4 text-text-muted font-medium">Next Billing</th>
                <th className="text-left p-4 text-text-muted font-medium">Payment Method</th>
                <th className="text-left p-4 text-text-muted font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {subscriptions.map((sub) => (
                <tr key={sub.id} className="hover:bg-white/5 transition-colors">
                  <td className="p-4">
                    <span className="font-medium text-white">{sub.tenantName}</span>
                  </td>
                  <td className="p-4">
                    <span className="px-2 py-1 rounded bg-stratum-500/10 text-stratum-400 text-sm capitalize">
                      {sub.plan}
                    </span>
                  </td>
                  <td className="p-4">
                    <span
                      className={cn(
                        'flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium w-fit',
                        getStatusColor(sub.status)
                      )}
                    >
                      {getStatusIcon(sub.status)}
                      {sub.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="p-4 text-white font-medium">
                    ${sub.mrr.toLocaleString()}
                  </td>
                  <td className="p-4 text-text-muted">
                    {sub.nextBilling.toLocaleDateString()}
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2 text-text-muted">
                      <CreditCardIcon className="w-4 h-4" />
                      {sub.paymentMethod}
                    </div>
                  </td>
                  <td className="p-4">
                    <button className="text-stratum-400 hover:text-stratum-300 text-sm">
                      Manage
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Invoices Tab */}
      {activeTab === 'invoices' && (
        <div className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left p-4 text-text-muted font-medium">Invoice ID</th>
                <th className="text-left p-4 text-text-muted font-medium">Tenant</th>
                <th className="text-left p-4 text-text-muted font-medium">Amount</th>
                <th className="text-left p-4 text-text-muted font-medium">Status</th>
                <th className="text-left p-4 text-text-muted font-medium">Due Date</th>
                <th className="text-left p-4 text-text-muted font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {invoices.map((invoice) => (
                <tr key={invoice.id} className="hover:bg-white/5 transition-colors">
                  <td className="p-4 font-mono text-stratum-400">{invoice.id}</td>
                  <td className="p-4 text-white">{invoice.tenantName}</td>
                  <td className="p-4 text-white font-medium">${invoice.amount.toLocaleString()}</td>
                  <td className="p-4">
                    <span
                      className={cn(
                        'flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium w-fit',
                        getStatusColor(invoice.status)
                      )}
                    >
                      {getStatusIcon(invoice.status)}
                      {invoice.status}
                    </span>
                  </td>
                  <td className="p-4 text-text-muted">{invoice.dueDate.toLocaleDateString()}</td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <button className="text-stratum-400 hover:text-stratum-300 text-sm">
                        View
                      </button>
                      <button className="text-text-muted hover:text-white text-sm">
                        Download
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Plans Tab */}
      {activeTab === 'plans' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={cn(
                'rounded-2xl border p-6',
                plan.highlighted
                  ? 'bg-gradient-to-br from-stratum-500/10 to-stratum-600/5 border-stratum-500/30'
                  : 'bg-surface-secondary border-white/10'
              )}
            >
              <h3 className="text-xl font-semibold text-white mb-2">{plan.name}</h3>
              <div className="flex items-baseline gap-1 mb-4">
                <span className="text-3xl font-bold text-white">${plan.price}</span>
                <span className="text-text-muted">/month</span>
              </div>

              <div className="py-4 border-t border-b border-white/10 mb-4">
                <div className="text-lg font-semibold text-white">{plan.subscribers}</div>
                <div className="text-sm text-text-muted">active subscribers</div>
              </div>

              <ul className="space-y-2">
                {plan.features.map((feature, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-text-secondary">
                    <CheckCircleIcon className="w-4 h-4 text-success" />
                    {feature}
                  </li>
                ))}
              </ul>

              <button className="w-full mt-6 py-2 rounded-lg bg-surface-tertiary text-text-secondary hover:text-white transition-colors">
                Edit Plan
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
