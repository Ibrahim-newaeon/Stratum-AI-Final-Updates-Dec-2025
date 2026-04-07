/**
 * Onboarding Wizard
 *
 * 5-step wizard that guides new users through platform setup:
 * 1. Business Profile - Industry, spend, team size
 * 2. Platform Selection - Which ad platforms to connect
 * 3. Goals Setup - KPIs, targets, currency
 * 4. Automation Preferences - Manual/assisted/autopilot
 * 5. Trust Gate Configuration - Safety thresholds
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart3,
  Bell,
  Building2,
  Check,
  ChevronLeft,
  ChevronRight,
  DollarSign,
  Globe,
  Link2,
  Loader2,
  Shield,
  SkipForward,
  Target,
  Users,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  type AdPlatform,
  type AutomationMode,
  type Industry,
  type MonthlyAdSpend,
  type OnboardingStep,
  type PrimaryKPI,
  type TeamSize,
  useOnboardingStatus,
  useSkipOnboarding,
  useSubmitAutomationPreferences,
  useSubmitBusinessProfile,
  useSubmitGoalsSetup,
  useSubmitPlatformSelection,
  useSubmitTrustGateConfig,
} from '@/api/onboarding';
import { useToast } from '@/components/ui/use-toast';

// Step configuration
const STEPS: {
  id: OnboardingStep;
  title: string;
  description: string;
  icon: typeof Building2;
}[] = [
  {
    id: 'business_profile',
    title: 'Business Profile',
    description: 'Tell us about your business',
    icon: Building2,
  },
  {
    id: 'platform_selection',
    title: 'Ad Platforms',
    description: 'Select platforms to connect',
    icon: Link2,
  },
  {
    id: 'goals_setup',
    title: 'Goals & Targets',
    description: 'Set your KPIs and targets',
    icon: Target,
  },
  {
    id: 'automation_preferences',
    title: 'Automation',
    description: 'Choose your automation level',
    icon: Zap,
  },
  {
    id: 'trust_gate_config',
    title: 'Trust Gate',
    description: 'Configure safety thresholds',
    icon: Shield,
  },
];

// Options data
const INDUSTRIES: { value: Industry; label: string }[] = [
  { value: 'ecommerce', label: 'E-commerce' },
  { value: 'saas', label: 'SaaS' },
  { value: 'lead_gen', label: 'Lead Generation' },
  { value: 'mobile_app', label: 'Mobile App' },
  { value: 'gaming', label: 'Gaming' },
  { value: 'finance', label: 'Finance' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'education', label: 'Education' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'travel', label: 'Travel' },
  { value: 'food_beverage', label: 'Food & Beverage' },
  { value: 'retail', label: 'Retail' },
  { value: 'automotive', label: 'Automotive' },
  { value: 'entertainment', label: 'Entertainment' },
  { value: 'other', label: 'Other' },
];

const AD_SPEND_RANGES: { value: MonthlyAdSpend; label: string }[] = [
  { value: 'under_10k', label: 'Under $10K' },
  { value: '10k_50k', label: '$10K - $50K' },
  { value: '50k_100k', label: '$50K - $100K' },
  { value: '100k_500k', label: '$100K - $500K' },
  { value: '500k_1m', label: '$500K - $1M' },
  { value: 'over_1m', label: 'Over $1M' },
];

const TEAM_SIZES: { value: TeamSize; label: string }[] = [
  { value: 'solo', label: 'Solo' },
  { value: '2_5', label: '2-5 people' },
  { value: '6_15', label: '6-15 people' },
  { value: '16_50', label: '16-50 people' },
  { value: '50_plus', label: '50+ people' },
];

const PLATFORMS: { value: AdPlatform; label: string; color: string }[] = [
  { value: 'meta', label: 'Meta (Facebook/Instagram)', color: 'bg-blue-500' },
  { value: 'google', label: 'Google Ads', color: 'bg-red-500' },
  { value: 'tiktok', label: 'TikTok Ads', color: 'bg-black' },
  { value: 'snapchat', label: 'Snapchat Ads', color: 'bg-yellow-400' },
];

const KPIS: { value: PrimaryKPI; label: string; description: string }[] = [
  { value: 'roas', label: 'ROAS', description: 'Return on Ad Spend' },
  { value: 'cpa', label: 'CPA', description: 'Cost per Acquisition' },
  { value: 'cpl', label: 'CPL', description: 'Cost per Lead' },
  { value: 'revenue', label: 'Revenue', description: 'Total Revenue' },
  { value: 'conversions', label: 'Conversions', description: 'Total Conversions' },
  { value: 'leads', label: 'Leads', description: 'Total Leads' },
  { value: 'app_installs', label: 'App Installs', description: 'Mobile App Installs' },
  { value: 'brand_awareness', label: 'Brand Awareness', description: 'Reach & Impressions' },
];

const AUTOMATION_MODES: {
  value: AutomationMode;
  label: string;
  description: string;
  icon: typeof Zap;
}[] = [
  {
    value: 'manual',
    label: 'Manual',
    description: 'All changes require your approval. Full control over every action.',
    icon: Users,
  },
  {
    value: 'assisted',
    label: 'Assisted',
    description: 'AI recommends actions, you review and approve before execution.',
    icon: BarChart3,
  },
  {
    value: 'autopilot',
    label: 'Autopilot',
    description: 'AI automatically executes when trust gate passes. Hands-free optimization.',
    icon: Zap,
  },
];

export default function Onboarding() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { data: status, isLoading: statusLoading } = useOnboardingStatus();

  // Form state
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState({
    // Step 1: Business Profile
    industry: '' as Industry | '',
    industryOther: '',
    monthlyAdSpend: '' as MonthlyAdSpend | '',
    teamSize: '' as TeamSize | '',
    companyWebsite: '',
    targetMarkets: [] as string[],
    // Step 2: Platform Selection
    platforms: [] as AdPlatform[],
    // Step 3: Goals Setup
    primaryKpi: '' as PrimaryKPI | '',
    targetRoas: '',
    targetCpa: '',
    monthlyBudget: '',
    currency: 'USD',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    // Step 4: Automation Preferences
    automationMode: 'assisted' as AutomationMode,
    autoPauseEnabled: true,
    autoScaleEnabled: false,
    notificationEmail: true,
    notificationSlack: false,
    notificationWhatsapp: false,
    // Step 5: Trust Gate Config
    trustThresholdAutopilot: 70,
    trustThresholdAlert: 40,
    requireApprovalAbove: '',
    maxDailyActions: 10,
  });

  // Mutations
  const submitBusinessProfile = useSubmitBusinessProfile();
  const submitPlatformSelection = useSubmitPlatformSelection();
  const submitGoalsSetup = useSubmitGoalsSetup();
  const submitAutomationPreferences = useSubmitAutomationPreferences();
  const submitTrustGateConfig = useSubmitTrustGateConfig();
  const skipOnboarding = useSkipOnboarding();

  // Set current step based on status
  useEffect(() => {
    if (status) {
      const stepIndex = STEPS.findIndex((s) => s.id === status.current_step);
      if (stepIndex !== -1) {
        setCurrentStep(stepIndex);
      }
    }
  }, [status]);

  const isSubmitting =
    submitBusinessProfile.isPending ||
    submitPlatformSelection.isPending ||
    submitGoalsSetup.isPending ||
    submitAutomationPreferences.isPending ||
    submitTrustGateConfig.isPending ||
    skipOnboarding.isPending;

  // Handle step submission
  const handleNext = async () => {
    const step = STEPS[currentStep];

    try {
      switch (step.id) {
        case 'business_profile':
          if (!formData.industry || !formData.monthlyAdSpend || !formData.teamSize) {
            toast({
              title: 'Missing Information',
              description: 'Please fill in all required fields.',
              variant: 'destructive',
            });
            return;
          }
          await submitBusinessProfile.mutateAsync({
            industry: formData.industry,
            industry_other: formData.industry === 'other' ? formData.industryOther : undefined,
            monthly_ad_spend: formData.monthlyAdSpend,
            team_size: formData.teamSize,
            company_website: formData.companyWebsite || undefined,
            target_markets: formData.targetMarkets.length > 0 ? formData.targetMarkets : undefined,
          });
          break;

        case 'platform_selection':
          if (formData.platforms.length === 0) {
            toast({
              title: 'Select Platforms',
              description: 'Please select at least one ad platform.',
              variant: 'destructive',
            });
            return;
          }
          await submitPlatformSelection.mutateAsync({
            platforms: formData.platforms,
          });
          break;

        case 'goals_setup':
          if (!formData.primaryKpi) {
            toast({
              title: 'Select KPI',
              description: 'Please select your primary KPI.',
              variant: 'destructive',
            });
            return;
          }
          await submitGoalsSetup.mutateAsync({
            primary_kpi: formData.primaryKpi,
            target_roas: formData.targetRoas ? parseFloat(formData.targetRoas) : undefined,
            target_cpa: formData.targetCpa ? parseFloat(formData.targetCpa) : undefined,
            monthly_budget: formData.monthlyBudget ? parseFloat(formData.monthlyBudget) : undefined,
            currency: formData.currency,
            timezone: formData.timezone,
          });
          break;

        case 'automation_preferences':
          await submitAutomationPreferences.mutateAsync({
            automation_mode: formData.automationMode,
            auto_pause_enabled: formData.autoPauseEnabled,
            auto_scale_enabled: formData.autoScaleEnabled,
            notification_email: formData.notificationEmail,
            notification_slack: formData.notificationSlack,
            notification_whatsapp: formData.notificationWhatsapp,
          });
          break;

        case 'trust_gate_config':
          await submitTrustGateConfig.mutateAsync({
            trust_threshold_autopilot: formData.trustThresholdAutopilot,
            trust_threshold_alert: formData.trustThresholdAlert,
            require_approval_above: formData.requireApprovalAbove
              ? parseInt(formData.requireApprovalAbove)
              : undefined,
            max_daily_actions: formData.maxDailyActions,
          });
          // Final step - redirect to dashboard
          toast({
            title: 'Setup Complete!',
            description: 'Your account is ready. Redirecting to dashboard...',
          });
          setTimeout(() => {
            navigate('/dashboard/overview');
          }, 1500);
          return;
      }

      // Move to next step
      setCurrentStep((prev) => Math.min(prev + 1, STEPS.length - 1));
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleBack = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  };

  const handleSkip = async () => {
    try {
      await skipOnboarding.mutateAsync();
    } catch {
      // Backend skip may fail — that's OK, proceed anyway
    }
    // Persist skip client-side so OnboardingGuard won't redirect back
    localStorage.setItem('stratum_onboarding_skipped', 'true');
    toast({
      title: 'Onboarding Skipped',
      description: 'You can complete setup later from Settings.',
    });
    navigate('/dashboard/overview');
  };

  const togglePlatform = (platform: AdPlatform) => {
    setFormData((prev) => ({
      ...prev,
      platforms: prev.platforms.includes(platform)
        ? prev.platforms.filter((p) => p !== platform)
        : [...prev.platforms, platform],
    }));
  };

  if (statusLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const step = STEPS[currentStep];
  const StepIcon = step.icon;

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/30">
      <div className="container max-w-4xl mx-auto py-12 px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="h-10 w-10 rounded-xl bg-gradient-stratum flex items-center justify-center shadow-glow">
              <span className="text-white font-bold text-xl">S</span>
            </div>
            <span className="text-2xl font-bold">Stratum AI</span>
          </div>
          <h1 className="text-3xl font-bold mb-2">Let's set up your account</h1>
          <p className="text-muted-foreground">
            Complete these steps to get the most out of Stratum AI
          </p>
        </div>

        {/* Welcome Banner - shown on first step */}
        {currentStep === 0 && (
          <div className="mb-8 p-5 rounded-2xl border border-primary/20 bg-primary/5 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                <Zap className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="font-semibold text-sm">Welcome to Stratum AI!</p>
                <p className="text-sm text-muted-foreground">
                  Customize your workspace in a few steps, or jump straight into the dashboard.
                  You can always configure these settings later.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleSkip}
              disabled={isSubmitting}
              className={cn(
                'flex-shrink-0 px-5 py-2.5 rounded-xl font-medium text-sm transition-all',
                'border-2 border-primary/30 text-primary hover:bg-primary/10 hover:border-primary/50',
                'flex items-center gap-2',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              <SkipForward className="w-4 h-4" />
              Skip & Go to Dashboard
            </button>
          </div>
        )}

        {/* Progress Steps - Onboarding Stepper */}
        <div className="onboarding-stepper mb-12">
          {/* Left side - Icon + Title + Progress */}
          <div className="onboarding-header">
            <div className="onboarding-icon">
              <Zap />
            </div>
            <div>
              <div className="onboarding-title">Getting Started</div>
              <span className="onboarding-progress">{currentStep}/{STEPS.length}</span>
            </div>
          </div>

          {/* Right side - Step tabs */}
          <div className="onboarding-steps">
            {STEPS.map((s, index) => {
              const Icon = s.icon;
              const isCompleted = index < currentStep;
              const isCurrent = index === currentStep;
              const isLocked = index > currentStep;

              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => isCompleted && setCurrentStep(index)}
                  className={cn(
                    'onboarding-step',
                    isCompleted && 'completed',
                    isCurrent && 'active',
                    isLocked && 'locked'
                  )}
                  disabled={isLocked}
                >
                  {isCompleted ? <Check className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                  <span className="hidden sm:inline">{s.title}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Step Content Card */}
        <div className="metric-card premium p-8 rounded-2xl">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <StepIcon className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-semibold">{step.title}</h2>
              <p className="text-sm text-muted-foreground">{step.description}</p>
            </div>
          </div>

          {/* Step Forms */}
          <div className="space-y-6">
            {/* Step 1: Business Profile */}
            {step.id === 'business_profile' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Industry <span className="text-destructive">*</span>
                  </label>
                  <select
                    value={formData.industry}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, industry: e.target.value as Industry }))
                    }
                    className="w-full px-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  >
                    <option value="">Select your industry</option>
                    {INDUSTRIES.map((i) => (
                      <option key={i.value} value={i.value}>
                        {i.label}
                      </option>
                    ))}
                  </select>
                </div>

                {formData.industry === 'other' && (
                  <div>
                    <label className="block text-sm font-medium mb-2">Specify Industry</label>
                    <input
                      type="text"
                      value={formData.industryOther}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, industryOther: e.target.value }))
                      }
                      className="w-full px-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                      placeholder="Enter your industry"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Monthly Ad Spend <span className="text-destructive">*</span>
                  </label>
                  <select
                    value={formData.monthlyAdSpend}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        monthlyAdSpend: e.target.value as MonthlyAdSpend,
                      }))
                    }
                    className="w-full px-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  >
                    <option value="">Select your monthly spend</option>
                    {AD_SPEND_RANGES.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Marketing Team Size <span className="text-destructive">*</span>
                  </label>
                  <select
                    value={formData.teamSize}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, teamSize: e.target.value as TeamSize }))
                    }
                    className="w-full px-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  >
                    <option value="">Select team size</option>
                    {TEAM_SIZES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Company Website</label>
                  <div className="relative">
                    <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                    <input
                      type="url"
                      value={formData.companyWebsite}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, companyWebsite: e.target.value }))
                      }
                      className="w-full pl-10 pr-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                      placeholder="https://yourcompany.com"
                    />
                  </div>
                </div>
              </>
            )}

            {/* Step 2: Platform Selection */}
            {step.id === 'platform_selection' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {PLATFORMS.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => togglePlatform(p.value)}
                    className={cn(
                      'p-4 rounded-xl border-2 text-left transition-all',
                      formData.platforms.includes(p.value)
                        ? 'border-primary bg-primary/5'
                        : 'border-muted hover:border-muted-foreground/50'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          'w-10 h-10 rounded-lg flex items-center justify-center text-white',
                          p.color
                        )}
                      >
                        {p.value[0].toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium">{p.label}</p>
                        <p className="text-sm text-muted-foreground">
                          {formData.platforms.includes(p.value) ? 'Selected' : 'Click to select'}
                        </p>
                      </div>
                      {formData.platforms.includes(p.value) && (
                        <Check className="w-5 h-5 text-primary ml-auto" />
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}

            {/* Step 3: Goals Setup */}
            {step.id === 'goals_setup' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-3">
                    Primary KPI <span className="text-destructive">*</span>
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {KPIS.map((kpi) => (
                      <button
                        key={kpi.value}
                        type="button"
                        onClick={() => setFormData((prev) => ({ ...prev, primaryKpi: kpi.value }))}
                        className={cn(
                          'p-3 rounded-lg border text-center transition-all',
                          formData.primaryKpi === kpi.value
                            ? 'border-primary bg-primary/5'
                            : 'border-muted hover:border-muted-foreground/50'
                        )}
                      >
                        <p className="font-medium">{kpi.label}</p>
                        <p className="text-xs text-muted-foreground">{kpi.description}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {(formData.primaryKpi === 'roas' || formData.primaryKpi === 'revenue') && (
                  <div>
                    <label className="block text-sm font-medium mb-2">Target ROAS</label>
                    <div className="relative">
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        value={formData.targetRoas}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, targetRoas: e.target.value }))
                        }
                        className="w-full px-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                        placeholder="e.g., 3.5"
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground">
                        x
                      </span>
                    </div>
                  </div>
                )}

                {(formData.primaryKpi === 'cpa' || formData.primaryKpi === 'cpl') && (
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Target {formData.primaryKpi.toUpperCase()}
                    </label>
                    <div className="relative">
                      <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={formData.targetCpa}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, targetCpa: e.target.value }))
                        }
                        className="w-full pl-10 pr-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                        placeholder="e.g., 25.00"
                      />
                    </div>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium mb-2">Monthly Budget</label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                    <input
                      type="number"
                      step="100"
                      min="0"
                      value={formData.monthlyBudget}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, monthlyBudget: e.target.value }))
                      }
                      className="w-full pl-10 pr-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                      placeholder="e.g., 50000"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Currency</label>
                    <select
                      value={formData.currency}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, currency: e.target.value }))
                      }
                      className="w-full px-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                    >
                      <option value="USD">USD</option>
                      <option value="EUR">EUR</option>
                      <option value="GBP">GBP</option>
                      <option value="AED">AED</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Timezone</label>
                    <input
                      type="text"
                      value={formData.timezone}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, timezone: e.target.value }))
                      }
                      className="w-full px-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                    />
                  </div>
                </div>
              </>
            )}

            {/* Step 4: Automation Preferences */}
            {step.id === 'automation_preferences' && (
              <>
                <div className="space-y-4">
                  {AUTOMATION_MODES.map((mode) => {
                    const ModeIcon = mode.icon;
                    return (
                      <button
                        key={mode.value}
                        type="button"
                        onClick={() =>
                          setFormData((prev) => ({ ...prev, automationMode: mode.value }))
                        }
                        className={cn(
                          'w-full p-4 rounded-xl border-2 text-left transition-all',
                          formData.automationMode === mode.value
                            ? 'border-primary bg-primary/5'
                            : 'border-muted hover:border-muted-foreground/50'
                        )}
                      >
                        <div className="flex items-start gap-4">
                          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                            <ModeIcon className="w-5 h-5 text-primary" />
                          </div>
                          <div className="flex-1">
                            <p className="font-medium">{mode.label}</p>
                            <p className="text-sm text-muted-foreground">{mode.description}</p>
                          </div>
                          {formData.automationMode === mode.value && (
                            <Check className="w-5 h-5 text-primary" />
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div className="pt-6 border-t space-y-4">
                  <h3 className="font-medium flex items-center gap-2">
                    <Bell className="w-4 h-4" /> Notifications
                  </h3>
                  <div className="space-y-3">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.notificationEmail}
                        onChange={(e) =>
                          setFormData((prev) => ({
                            ...prev,
                            notificationEmail: e.target.checked,
                          }))
                        }
                        className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                      />
                      <span className="text-sm">Email notifications</span>
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.notificationSlack}
                        onChange={(e) =>
                          setFormData((prev) => ({
                            ...prev,
                            notificationSlack: e.target.checked,
                          }))
                        }
                        className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                      />
                      <span className="text-sm">Slack notifications</span>
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.notificationWhatsapp}
                        onChange={(e) =>
                          setFormData((prev) => ({
                            ...prev,
                            notificationWhatsapp: e.target.checked,
                          }))
                        }
                        className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                      />
                      <span className="text-sm">WhatsApp notifications</span>
                    </label>
                  </div>
                </div>
              </>
            )}

            {/* Step 5: Trust Gate Configuration */}
            {step.id === 'trust_gate_config' && (
              <>
                <div className="p-4 rounded-lg bg-primary/5 border border-primary/20 mb-6">
                  <div className="flex items-start gap-3">
                    <Shield className="w-5 h-5 text-primary mt-0.5" />
                    <div>
                      <p className="font-medium text-sm">Trust Gate Protection</p>
                      <p className="text-sm text-muted-foreground">
                        The Trust Gate ensures automation only executes when your data quality is
                        high enough. This protects you from making decisions based on unreliable
                        data.
                      </p>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Autopilot Threshold
                    <span className="text-muted-foreground ml-2">
                      (Score required for auto-execution)
                    </span>
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="50"
                      max="100"
                      value={formData.trustThresholdAutopilot}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          trustThresholdAutopilot: parseInt(e.target.value),
                        }))
                      }
                      className="flex-1"
                    />
                    <span className="w-12 text-center font-medium">
                      {formData.trustThresholdAutopilot}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Higher = safer but less automation. Recommended: 70
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Alert Threshold
                    <span className="text-muted-foreground ml-2">(Score to trigger warnings)</span>
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="20"
                      max="70"
                      value={formData.trustThresholdAlert}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          trustThresholdAlert: parseInt(e.target.value),
                        }))
                      }
                      className="flex-1"
                    />
                    <span className="w-12 text-center font-medium">
                      {formData.trustThresholdAlert}
                    </span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Require Approval Above (Budget)
                  </label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                    <input
                      type="number"
                      step="100"
                      min="0"
                      value={formData.requireApprovalAbove}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          requireApprovalAbove: e.target.value,
                        }))
                      }
                      className="w-full pl-10 pr-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                      placeholder="Leave empty for no limit"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Budget changes above this amount will always require approval
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Max Daily Auto-Actions</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={formData.maxDailyActions}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        maxDailyActions: parseInt(e.target.value) || 10,
                      }))
                    }
                    className="w-full px-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Maximum automatic actions allowed per day
                  </p>
                </div>
              </>
            )}
          </div>

          {/* Navigation Buttons */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t">
            <button
              type="button"
              onClick={handleSkip}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg border border-muted-foreground/20 text-sm font-medium text-muted-foreground hover:text-foreground hover:border-muted-foreground/40 hover:bg-muted/50 transition-all flex items-center gap-2 disabled:opacity-50"
            >
              <SkipForward className="w-4 h-4" />
              Skip setup
            </button>

            <div className="flex items-center gap-3">
              {currentStep > 0 && (
                <button
                  type="button"
                  onClick={handleBack}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors flex items-center gap-2"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Back
                </button>
              )}
              <button
                type="button"
                onClick={handleNext}
                disabled={isSubmitting}
                className={cn(
                  'px-6 py-2 rounded-lg font-medium text-white bg-gradient-stratum shadow-glow transition-all',
                  'hover:shadow-glow-lg hover:scale-[1.02]',
                  'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100',
                  'flex items-center gap-2'
                )}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : currentStep === STEPS.length - 1 ? (
                  <>
                    Complete Setup
                    <Check className="w-4 h-4" />
                  </>
                ) : (
                  <>
                    Continue
                    <ChevronRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground mt-8">
          You can always change these settings later from your account settings.
        </p>
      </div>
    </div>
  );
}
