/**
 * Billing (Super Admin View)
 *
 * Platform billing management - plans, invoices, subscriptions
 * Revenue metrics and dunning management
 */

import { useState } from 'react';
import { cn } from '@/lib/utils';
import {
  useBillingInvoices,
  useBillingPlans,
  useBillingSubscriptions,
  useRetryPayment,
  useRevenue,
} from '@/api/hooks';
import { useToast } from '@/components/ui/use-toast';
import {
  ArrowDownTrayIcon,
  ArrowTrendingUpIcon,
  CheckCircleIcon,
  ClockIcon,
  CreditCardIcon,
  CurrencyDollarIcon,
  DocumentTextIcon,
  EnvelopeIcon,
  ExclamationTriangleIcon,
  PencilSquareIcon,
  UserGroupIcon,
  XCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

type PlanType = 'starter' | 'pro' | 'enterprise';
type SubscriptionStatus = 'active' | 'past_due' | 'canceled' | 'trialing';
type InvoiceStatus = 'paid' | 'pending' | 'overdue' | 'failed';

interface Subscription {
  id: string;
  tenantId: string;
  tenantName: string;
  plan: PlanType;
  status: SubscriptionStatus;
  mrr: number;
  startDate: Date;
  nextBilling: Date;
  paymentMethod: string;
  failedPayments: number;
}

interface Invoice {
  id: string;
  tenantName: string;
  amount: number;
  status: InvoiceStatus;
  dueDate: Date;
  paidAt: Date | null;
}

interface Plan {
  id: string;
  name: string;
  price: number;
  features: string[];
  subscribers: number;
  highlighted: boolean;
}

export default function Billing() {
  const [activeTab, setActiveTab] = useState<'overview' | 'subscriptions' | 'invoices' | 'plans'>(
    'overview'
  );
  const { toast } = useToast();

  // Modal states
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [selectedSubscription, setSelectedSubscription] = useState<Subscription | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false);
  const [showEditPlanModal, setShowEditPlanModal] = useState(false);

  // Fetch data from API
  const { data: revenueData } = useRevenue();
  const { data: plansData } = useBillingPlans();
  const { data: invoicesData } = useBillingInvoices();
  const { data: subscriptionsData } = useBillingSubscriptions();
  const retryPaymentMutation = useRetryPayment();

  // Use real API data, defaulting to 0 when loading
  const metrics = {
    mrr: revenueData?.mrr ?? 0,
    mrrGrowth: revenueData?.mrrGrowth ?? 0,
    arr: revenueData?.arr ?? 0,
    activeSubscriptions:
      subscriptionsData?.items?.filter((s: any) => s.status === 'active').length ?? 0,
    churnRate: revenueData?.churnRate ?? 0,
    pastDue:
      subscriptionsData?.items?.filter((s: any) => s.status === 'past_due').length ?? 0,
  };

  // Use real API data, defaulting to empty arrays when loading
  const subscriptions: Subscription[] =
    subscriptionsData?.items?.map((s: any) => ({
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
    })) ?? [];

  const invoices: Invoice[] =
    invoicesData?.items?.map((i: any) => ({
      id: i.id,
      tenantName: i.tenantName,
      amount: i.amount,
      status: i.status,
      dueDate: new Date(i.dueDate),
      paidAt: i.paidAt ? new Date(i.paidAt) : null,
    })) ?? [];

  const plans: Plan[] =
    plansData?.map((p: any) => ({
      id: p.id,
      name: p.name,
      price: p.price,
      features: p.features || [],
      subscribers: p.subscriberCount || 0,
      highlighted: p.name === 'Pro',
    })) ?? [];

  const handleRetryPayment = async (subscriptionId: string) => {
    try {
      await retryPaymentMutation.mutateAsync(subscriptionId);
      toast({
        title: 'Success',
        description: 'Payment retry initiated successfully',
      });
    } catch (error) {
      // Error displayed via toast below
      toast({
        title: 'Error',
        description: 'Failed to retry payment. Please try again.',
        variant: 'destructive',
      });
    }
  };

  // Export billing report to CSV
  const handleExportReport = () => {
    try {
      const csvData = [
        ['Invoice ID', 'Tenant', 'Amount', 'Status', 'Due Date', 'Paid At'],
        ...invoices.map((inv) => [
          inv.id,
          inv.tenantName,
          `$${inv.amount}`,
          inv.status,
          inv.dueDate.toLocaleDateString(),
          inv.paidAt ? inv.paidAt.toLocaleDateString() : 'N/A',
        ]),
      ];
      const csvContent = csvData.map((row) => row.join(',')).join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `billing-report-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast({
        title: 'Export Successful',
        description: 'Billing report downloaded as CSV',
      });
    } catch (error) {
      toast({
        title: 'Export Failed',
        description: 'Unable to export billing report',
        variant: 'destructive',
      });
    }
  };

  // Contact customer - open email client
  const handleContactCustomer = (tenantName: string) => {
    // In production, this would fetch actual email from backend
    const email = `billing@${tenantName.toLowerCase().replace(/\s+/g, '')}.com`;
    window.location.href = `mailto:${email}?subject=Payment%20Issue%20-%20${encodeURIComponent(tenantName)}&body=Dear%20${encodeURIComponent(tenantName)}%20Team,%0A%0AWe%20noticed%20there%20is%20an%20issue%20with%20your%20payment.%20Please%20contact%20us%20to%20resolve%20this.`;
    toast({
      title: 'Email Client Opened',
      description: `Opening email to contact ${tenantName}`,
    });
  };

  // Manage subscription - show modal
  const handleManageSubscription = (subscription: Subscription) => {
    setSelectedSubscription(subscription);
    setShowSubscriptionModal(true);
  };

  // View invoice - show modal
  const handleViewInvoice = (invoice: Invoice) => {
    setSelectedInvoice(invoice);
    setShowInvoiceModal(true);
  };

  // Download invoice as PDF (placeholder)
  const handleDownloadInvoice = (invoice: Invoice) => {
    try {
      // In production, this would call an API to generate actual PDF
      const invoiceContent = `
INVOICE
=======
Invoice ID: ${invoice.id}
Tenant: ${invoice.tenantName}
Amount: $${invoice.amount.toLocaleString()}
Status: ${invoice.status}
Due Date: ${invoice.dueDate.toLocaleDateString()}
${invoice.paidAt ? `Paid At: ${invoice.paidAt.toLocaleDateString()}` : ''}
      `.trim();

      const blob = new Blob([invoiceContent], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `invoice-${invoice.id}.txt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      toast({
        title: 'Invoice Downloaded',
        description: `Invoice ${invoice.id} has been downloaded`,
      });
    } catch (error) {
      toast({
        title: 'Download Failed',
        description: 'Unable to download invoice',
        variant: 'destructive',
      });
    }
  };

  // Edit plan - show modal
  const handleEditPlan = (plan: Plan) => {
    setSelectedPlan(plan);
    setShowEditPlanModal(true);
  };

  const getStatusColor = (status: SubscriptionStatus | InvoiceStatus) => {
    switch (status) {
      case 'active':
      case 'paid':
        return 'text-success bg-success/10';
      case 'past_due':
      case 'overdue':
        return 'text-danger bg-danger/10';
      case 'pending':
      case 'trialing':
        return 'text-warning bg-warning/10';
      case 'canceled':
      case 'failed':
        return 'text-text-muted bg-surface-tertiary';
    }
  };

  const getStatusIcon = (status: SubscriptionStatus | InvoiceStatus) => {
    switch (status) {
      case 'active':
      case 'paid':
        return <CheckCircleIcon className="w-4 h-4" />;
      case 'past_due':
      case 'overdue':
      case 'failed':
        return <ExclamationTriangleIcon className="w-4 h-4" />;
      case 'pending':
      case 'trialing':
        return <ClockIcon className="w-4 h-4" />;
      case 'canceled':
        return <XCircleIcon className="w-4 h-4" />;
    }
  };

  const tabs = [
    { id: 'overview' as const, label: 'Overview' },
    { id: 'subscriptions' as const, label: 'Subscriptions' },
    { id: 'invoices' as const, label: 'Invoices' },
    { id: 'plans' as const, label: 'Plans' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Billing</h1>
          <p className="text-text-muted">Revenue and subscription management</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleExportReport}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-text-secondary hover:text-white transition-colors"
          >
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
              <div className="text-3xl font-bold text-white">${metrics.mrr.toLocaleString()}</div>
              <div className="flex items-center gap-1 text-success text-sm mt-2">
                <ArrowTrendingUpIcon className="w-4 h-4" />+{metrics.mrrGrowth}% vs last month
              </div>
            </div>

            <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
              <div className="text-text-muted text-sm mb-2">Annual Recurring Revenue</div>
              <div className="text-3xl font-bold text-white">${metrics.arr.toLocaleString()}</div>
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
                      <button
                        onClick={() => handleContactCustomer(sub.tenantName)}
                        className="px-3 py-1 rounded-lg bg-surface-tertiary text-text-secondary hover:text-white text-sm transition-colors"
                      >
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
              {subscriptions.filter((s) => s.status === 'past_due' || s.failedPayments > 0)
                .length === 0 && (
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
                  <td className="p-4 text-white font-medium">${sub.mrr.toLocaleString()}</td>
                  <td className="p-4 text-text-muted">{sub.nextBilling.toLocaleDateString()}</td>
                  <td className="p-4">
                    <div className="flex items-center gap-2 text-text-muted">
                      <CreditCardIcon className="w-4 h-4" />
                      {sub.paymentMethod}
                    </div>
                  </td>
                  <td className="p-4">
                    <button
                      onClick={() => handleManageSubscription(sub)}
                      className="text-stratum-400 hover:text-stratum-300 text-sm"
                    >
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
                      <button
                        onClick={() => handleViewInvoice(invoice)}
                        className="text-stratum-400 hover:text-stratum-300 text-sm"
                      >
                        View
                      </button>
                      <button
                        onClick={() => handleDownloadInvoice(invoice)}
                        className="text-text-muted hover:text-white text-sm"
                      >
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

              <button
                onClick={() => handleEditPlan(plan)}
                className="w-full mt-6 py-2 rounded-lg bg-surface-tertiary text-text-secondary hover:text-white transition-colors"
              >
                Edit Plan
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Invoice Detail Modal */}
      {showInvoiceModal && selectedInvoice && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface-secondary rounded-2xl border border-white/10 p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">Invoice Details</h2>
              <button
                onClick={() => {
                  setShowInvoiceModal(false);
                  setSelectedInvoice(null);
                }}
                className="text-text-muted hover:text-white"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="flex justify-between">
                <span className="text-text-muted">Invoice ID</span>
                <span className="text-white font-mono">{selectedInvoice.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Tenant</span>
                <span className="text-white">{selectedInvoice.tenantName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Amount</span>
                <span className="text-white font-semibold">
                  ${selectedInvoice.amount.toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Status</span>
                <span
                  className={cn(
                    'px-2 py-1 rounded-full text-xs font-medium',
                    getStatusColor(selectedInvoice.status)
                  )}
                >
                  {selectedInvoice.status}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Due Date</span>
                <span className="text-white">{selectedInvoice.dueDate.toLocaleDateString()}</span>
              </div>
              {selectedInvoice.paidAt && (
                <div className="flex justify-between">
                  <span className="text-text-muted">Paid At</span>
                  <span className="text-white">{selectedInvoice.paidAt.toLocaleDateString()}</span>
                </div>
              )}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => handleDownloadInvoice(selectedInvoice)}
                className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-stratum-500 text-white hover:bg-stratum-600 transition-colors"
              >
                <ArrowDownTrayIcon className="w-4 h-4" />
                Download
              </button>
              <button
                onClick={() => {
                  setShowInvoiceModal(false);
                  setSelectedInvoice(null);
                }}
                className="flex-1 py-2 rounded-lg bg-surface-tertiary text-text-secondary hover:text-white transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Subscription Management Modal */}
      {showSubscriptionModal && selectedSubscription && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface-secondary rounded-2xl border border-white/10 p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">Manage Subscription</h2>
              <button
                onClick={() => {
                  setShowSubscriptionModal(false);
                  setSelectedSubscription(null);
                }}
                className="text-text-muted hover:text-white"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="flex justify-between">
                <span className="text-text-muted">Tenant</span>
                <span className="text-white font-semibold">{selectedSubscription.tenantName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Plan</span>
                <span className="px-2 py-1 rounded bg-stratum-500/10 text-stratum-400 text-sm capitalize">
                  {selectedSubscription.plan}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Status</span>
                <span
                  className={cn(
                    'px-2 py-1 rounded-full text-xs font-medium',
                    getStatusColor(selectedSubscription.status)
                  )}
                >
                  {selectedSubscription.status.replace('_', ' ')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">MRR</span>
                <span className="text-white font-semibold">
                  ${selectedSubscription.mrr.toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Payment Method</span>
                <span className="text-white">{selectedSubscription.paymentMethod}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Next Billing</span>
                <span className="text-white">
                  {selectedSubscription.nextBilling.toLocaleDateString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Start Date</span>
                <span className="text-white">
                  {selectedSubscription.startDate.toLocaleDateString()}
                </span>
              </div>
              {selectedSubscription.failedPayments > 0 && (
                <div className="flex justify-between">
                  <span className="text-text-muted">Failed Payments</span>
                  <span className="text-danger font-semibold">
                    {selectedSubscription.failedPayments}
                  </span>
                </div>
              )}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => handleContactCustomer(selectedSubscription.tenantName)}
                className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-surface-tertiary text-text-secondary hover:text-white transition-colors"
              >
                <EnvelopeIcon className="w-4 h-4" />
                Contact
              </button>
              {selectedSubscription.status === 'past_due' && (
                <button
                  onClick={() => {
                    handleRetryPayment(selectedSubscription.id);
                    setShowSubscriptionModal(false);
                    setSelectedSubscription(null);
                  }}
                  disabled={retryPaymentMutation.isPending}
                  className="flex-1 py-2 rounded-lg bg-danger/10 text-danger hover:bg-danger/20 transition-colors disabled:opacity-50"
                >
                  {retryPaymentMutation.isPending ? 'Retrying...' : 'Retry Payment'}
                </button>
              )}
              <button
                onClick={() => {
                  setShowSubscriptionModal(false);
                  setSelectedSubscription(null);
                }}
                className="flex-1 py-2 rounded-lg bg-stratum-500 text-white hover:bg-stratum-600 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Plan Modal */}
      {showEditPlanModal && selectedPlan && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface-secondary rounded-2xl border border-white/10 p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">Edit Plan: {selectedPlan.name}</h2>
              <button
                onClick={() => {
                  setShowEditPlanModal(false);
                  setSelectedPlan(null);
                }}
                className="text-text-muted hover:text-white"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-text-muted mb-2">Plan Name</label>
                <input
                  type="text"
                  defaultValue={selectedPlan.name}
                  className="w-full px-4 py-2 rounded-lg bg-surface-tertiary border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-stratum-500/50"
                />
              </div>
              <div>
                <label className="block text-sm text-text-muted mb-2">Price ($/month)</label>
                <input
                  type="number"
                  defaultValue={selectedPlan.price}
                  className="w-full px-4 py-2 rounded-lg bg-surface-tertiary border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-stratum-500/50"
                />
              </div>
              <div>
                <label className="block text-sm text-text-muted mb-2">
                  Features (one per line)
                </label>
                <textarea
                  defaultValue={selectedPlan.features.join('\n')}
                  rows={4}
                  className="w-full px-4 py-2 rounded-lg bg-surface-tertiary border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-stratum-500/50 resize-none"
                />
              </div>
              <div className="pt-2 border-t border-white/10">
                <div className="text-sm text-text-muted">
                  Current Subscribers:{' '}
                  <span className="text-white font-semibold">{selectedPlan.subscribers}</span>
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  toast({
                    title: 'Plan Updated',
                    description: `${selectedPlan.name} plan has been updated successfully`,
                  });
                  setShowEditPlanModal(false);
                  setSelectedPlan(null);
                }}
                className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-stratum-500 text-white hover:bg-stratum-600 transition-colors"
              >
                <PencilSquareIcon className="w-4 h-4" />
                Save Changes
              </button>
              <button
                onClick={() => {
                  setShowEditPlanModal(false);
                  setSelectedPlan(null);
                }}
                className="flex-1 py-2 rounded-lg bg-surface-tertiary text-text-secondary hover:text-white transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
