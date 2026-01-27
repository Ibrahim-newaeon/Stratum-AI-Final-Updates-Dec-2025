/**
 * Campaign Creation Modal
 * Multi-step wizard for creating campaigns across all platforms
 */

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertCircle,
  Bookmark,
  Check,
  ChevronLeft,
  ChevronRight,
  DollarSign,
  Loader2,
  RefreshCw,
  Settings,
  UserPlus,
  Users,
  UsersRound,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Platform, useAdAccounts } from '@/api/campaignBuilder';
import { useAuth } from '@/contexts/AuthContext';

interface CampaignCreateModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: (campaign: any) => void;
}

// Platform configurations
const PLATFORMS = [
  {
    id: 'meta',
    name: 'Meta',
    description: 'Facebook & Instagram Ads',
    color: 'bg-blue-600',
    objectives: ['AWARENESS', 'TRAFFIC', 'ENGAGEMENT', 'LEADS', 'APP_PROMOTION', 'SALES'],
  },
  {
    id: 'google',
    name: 'Google',
    description: 'Search, Display & YouTube',
    color: 'bg-red-500',
    objectives: ['SEARCH', 'DISPLAY', 'VIDEO', 'SHOPPING', 'PERFORMANCE_MAX', 'DISCOVERY'],
  },
  {
    id: 'tiktok',
    name: 'TikTok',
    description: 'TikTok For Business',
    color: 'bg-black',
    objectives: [
      'REACH',
      'TRAFFIC',
      'VIDEO_VIEWS',
      'COMMUNITY_INTERACTION',
      'CONVERSIONS',
      'APP_PROMOTION',
    ],
  },
  {
    id: 'snapchat',
    name: 'Snapchat',
    description: 'Snapchat Ads Manager',
    color: 'bg-yellow-400',
    objectives: ['AWARENESS', 'CONSIDERATION', 'CONVERSIONS', 'CATALOG_SALES'],
  },
];

// Audience types for when API is available
interface CustomAudience {
  id: string;
  name: string;
  size: number;
}

interface LookalikeAudience {
  id: string;
  name: string;
  size: number;
  source: string;
}

interface SavedAudience {
  id: string;
  name: string;
  description: string;
}

interface PlatformAudiences {
  custom: CustomAudience[];
  lookalike: LookalikeAudience[];
  saved: SavedAudience[];
}

const STEPS = ['platform', 'basics', 'budget', 'targeting'] as const;
type Step = (typeof STEPS)[number];

interface FormData {
  // Platform
  platform: string;
  // Basics
  name: string;
  objective: string;
  external_id: string;
  account_id: string;
  status: string;
  // Budget
  daily_budget: string;
  lifetime_budget: string;
  currency: string;
  start_date: string;
  end_date: string;
  // Targeting
  targeting_age_min: string;
  targeting_age_max: string;
  targeting_genders: string[];
  targeting_locations: string;
  targeting_interests: string;
  // Audiences
  custom_audiences: string[];
  lookalike_audiences: string[];
  saved_audiences: string[];
}

const initialFormData: FormData = {
  platform: '',
  name: '',
  objective: '',
  external_id: '',
  account_id: '',
  status: 'draft',
  daily_budget: '',
  lifetime_budget: '',
  currency: 'USD',
  start_date: '',
  end_date: '',
  targeting_age_min: '18',
  targeting_age_max: '65',
  targeting_genders: [],
  targeting_locations: '',
  targeting_interests: '',
  custom_audiences: [],
  lookalike_audiences: [],
  saved_audiences: [],
};

export function CampaignCreateModal({ open, onClose, onSuccess }: CampaignCreateModalProps) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [currentStep, setCurrentStep] = useState<Step>('platform');
  const [formData, setFormData] = useState<FormData>(initialFormData);
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [audienceTab, setAudienceTab] = useState<'custom' | 'lookalike' | 'saved'>('custom');
  const [platformAudiences, setPlatformAudiences] = useState<PlatformAudiences | null>(null);

  const tenantId = user?.tenant_id || 0;
  const currentStepIndex = STEPS.indexOf(currentStep);
  const selectedPlatform = PLATFORMS.find((p) => p.id === formData.platform);

  // Fetch ad accounts from real API
  const {
    data: adAccounts = [],
    isLoading: isLoadingAccounts,
    refetch: _refetchAccounts,
  } = useAdAccounts(
    tenantId,
    formData.platform as Platform,
    true // enabled only
  );

  // Auto-select first account when accounts load
  useEffect(() => {
    if (adAccounts.length > 0 && !formData.account_id) {
      setFormData((prev) => ({
        ...prev,
        account_id: adAccounts[0].platform_account_id,
        currency: adAccounts[0].currency,
      }));
    }
  }, [adAccounts, formData.account_id]);

  // Reset account selection when platform changes
  useEffect(() => {
    if (formData.platform) {
      setFormData((prev) => ({
        ...prev,
        account_id: '',
        currency: 'USD',
      }));
      // Audiences would be fetched from API when endpoint is available
      setPlatformAudiences(null);
    }
  }, [formData.platform]);

  const updateFormData = (field: keyof FormData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const handleAccountChange = (accountId: string) => {
    const account = adAccounts.find((a) => a.platform_account_id === accountId);
    if (account) {
      setFormData((prev) => ({
        ...prev,
        account_id: accountId,
        currency: account.currency,
      }));
    }
  };

  const toggleAudience = (
    type: 'custom_audiences' | 'lookalike_audiences' | 'saved_audiences',
    audienceId: string
  ) => {
    setFormData((prev) => {
      const current = prev[type];
      if (current.includes(audienceId)) {
        return { ...prev, [type]: current.filter((id) => id !== audienceId) };
      }
      return { ...prev, [type]: [...current, audienceId] };
    });
  };

  const validateStep = (step: Step): boolean => {
    const newErrors: Partial<Record<keyof FormData, string>> = {};

    switch (step) {
      case 'platform':
        if (!formData.platform) {
          newErrors.platform = t('campaigns.create.errors.platformRequired');
        }
        break;
      case 'basics':
        if (!formData.name.trim()) {
          newErrors.name = t('campaigns.create.errors.nameRequired');
        }
        if (!formData.objective) {
          newErrors.objective = t('campaigns.create.errors.objectiveRequired');
        }
        if (!formData.account_id) {
          newErrors.account_id = t('campaigns.create.errors.accountRequired');
        }
        break;
      case 'budget':
        if (!formData.daily_budget && !formData.lifetime_budget) {
          newErrors.daily_budget = t('campaigns.create.errors.budgetRequired');
        }
        if (formData.start_date && formData.end_date && formData.end_date < formData.start_date) {
          newErrors.end_date = t('campaigns.create.errors.endDateInvalid');
        }
        break;
      case 'targeting':
        const minAge = parseInt(formData.targeting_age_min);
        const maxAge = parseInt(formData.targeting_age_max);
        if (minAge < 13 || minAge > 100) {
          newErrors.targeting_age_min = t('campaigns.create.errors.ageInvalid');
        }
        if (maxAge < 13 || maxAge > 100) {
          newErrors.targeting_age_max = t('campaigns.create.errors.ageInvalid');
        }
        if (minAge > maxAge) {
          newErrors.targeting_age_max = t('campaigns.create.errors.ageRangeInvalid');
        }
        break;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      const nextIndex = currentStepIndex + 1;
      if (nextIndex < STEPS.length) {
        setCurrentStep(STEPS[nextIndex]);
      }
    }
  };

  const handleBack = () => {
    const prevIndex = currentStepIndex - 1;
    if (prevIndex >= 0) {
      setCurrentStep(STEPS[prevIndex]);
    }
  };

  const handleSubmit = async () => {
    if (!validateStep('targeting')) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const external_id =
        formData.external_id || `stratum_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      const payload = {
        name: formData.name,
        platform: formData.platform,
        status: formData.status,
        objective: formData.objective,
        external_id,
        account_id: formData.account_id,
        daily_budget_cents: formData.daily_budget
          ? Math.round(parseFloat(formData.daily_budget) * 100)
          : null,
        lifetime_budget_cents: formData.lifetime_budget
          ? Math.round(parseFloat(formData.lifetime_budget) * 100)
          : null,
        currency: formData.currency,
        start_date: formData.start_date || null,
        end_date: formData.end_date || null,
        targeting_age_min: parseInt(formData.targeting_age_min) || 18,
        targeting_age_max: parseInt(formData.targeting_age_max) || 65,
        targeting_genders:
          formData.targeting_genders.length > 0 ? formData.targeting_genders : null,
        targeting_locations: formData.targeting_locations
          ? formData.targeting_locations.split(',').map((l) => ({ name: l.trim() }))
          : null,
        targeting_interests: formData.targeting_interests
          ? formData.targeting_interests.split(',').map((i) => i.trim())
          : null,
        custom_audiences: formData.custom_audiences.length > 0 ? formData.custom_audiences : null,
        lookalike_audiences:
          formData.lookalike_audiences.length > 0 ? formData.lookalike_audiences : null,
        saved_audiences: formData.saved_audiences.length > 0 ? formData.saved_audiences : null,
      };

      const response = await fetch('/api/v1/campaigns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (data.success) {
        onSuccess?.(data.data);
        handleClose();
      } else {
        setSubmitError(data.message || t('campaigns.create.errors.submitFailed'));
      }
    } catch (err) {
      setSubmitError(t('campaigns.create.errors.submitFailed'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setFormData(initialFormData);
    setCurrentStep('platform');
    setErrors({});
    setSubmitError(null);
    setPlatformAudiences(null);
    onClose();
  };

  const formatAudienceSize = (size: number) => {
    if (size >= 1000000) return `${(size / 1000000).toFixed(1)}M`;
    if (size >= 1000) return `${(size / 1000).toFixed(0)}K`;
    return size.toString();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={handleClose} />

      {/* Modal */}
      <div className="relative w-full max-w-5xl max-h-[90vh] overflow-hidden rounded-2xl bg-card border shadow-xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-xl font-bold text-foreground">{t('campaigns.create.title')}</h2>
            <p className="text-sm text-muted-foreground mt-1">{t('campaigns.create.subtitle')}</p>
          </div>
          <button onClick={handleClose} className="p-2 rounded-lg hover:bg-muted transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step Indicator */}
        <div className="px-6 py-4 border-b bg-muted/30">
          <div className="flex items-center justify-between">
            {STEPS.map((step, index) => (
              <div key={step} className="flex items-center">
                <div
                  className={cn(
                    'flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium transition-all',
                    index < currentStepIndex
                      ? 'bg-green-500 text-white'
                      : index === currentStepIndex
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground'
                  )}
                >
                  {index < currentStepIndex ? <Check className="w-4 h-4" /> : index + 1}
                </div>
                <span
                  className={cn(
                    'ml-2 text-sm font-medium hidden sm:block',
                    index === currentStepIndex ? 'text-foreground' : 'text-muted-foreground'
                  )}
                >
                  {t(`campaigns.create.steps.${step}`)}
                </span>
                {index < STEPS.length - 1 && (
                  <div
                    className={cn(
                      'w-12 h-0.5 mx-4 transition-colors',
                      index < currentStepIndex ? 'bg-green-500' : 'bg-muted'
                    )}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-8 overflow-y-auto max-h-[60vh]">
          {/* Platform Selection Step */}
          {currentStep === 'platform' && (
            <div className="space-y-6">
              <p className="text-muted-foreground text-lg">
                {t('campaigns.create.selectPlatform')}
              </p>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {PLATFORMS.map((platform) => (
                  <button
                    key={platform.id}
                    onClick={() => updateFormData('platform', platform.id)}
                    className={cn(
                      'flex flex-col items-center gap-4 p-6 rounded-xl border-2 transition-all text-center relative',
                      formData.platform === platform.id
                        ? 'border-primary bg-primary/5'
                        : 'border-transparent bg-muted/50 hover:bg-muted'
                    )}
                  >
                    {formData.platform === platform.id && (
                      <Check className="w-5 h-5 text-primary absolute top-3 right-3" />
                    )}
                    <div
                      className={cn(
                        'w-16 h-16 rounded-xl flex items-center justify-center text-white font-bold text-2xl',
                        platform.color
                      )}
                    >
                      {platform.name.charAt(0)}
                    </div>
                    <div>
                      <h3 className="font-semibold text-foreground text-lg">{platform.name}</h3>
                      <p className="text-sm text-muted-foreground">{platform.description}</p>
                    </div>
                  </button>
                ))}
              </div>
              {errors.platform && (
                <p className="text-sm text-red-500 flex items-center gap-1">
                  <AlertCircle className="w-4 h-4" />
                  {errors.platform}
                </p>
              )}
            </div>
          )}

          {/* Basics Step */}
          {currentStep === 'basics' && (
            <div className="space-y-5">
              {/* Campaign Name */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('campaigns.create.campaignName')} *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => updateFormData('name', e.target.value)}
                  placeholder={t('campaigns.create.campaignNamePlaceholder')}
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary',
                    errors.name && 'border-red-500'
                  )}
                />
                {errors.name && <p className="mt-1 text-sm text-red-500">{errors.name}</p>}
              </div>

              {/* Objective */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('campaigns.create.objective')} *
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {selectedPlatform?.objectives.map((obj) => (
                    <button
                      key={obj}
                      onClick={() => updateFormData('objective', obj)}
                      className={cn(
                        'px-3 py-2 rounded-lg text-sm font-medium border transition-all',
                        formData.objective === obj
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-transparent bg-muted hover:bg-muted/80 text-foreground'
                      )}
                    >
                      {t(
                        `campaigns.create.objectives.${obj.toLowerCase()}`,
                        obj.replace(/_/g, ' ')
                      )}
                    </button>
                  ))}
                </div>
                {errors.objective && (
                  <p className="mt-1 text-sm text-red-500">{errors.objective}</p>
                )}
              </div>

              {/* Ad Account Dropdown */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('campaigns.create.accountId')} *
                </label>
                {isLoadingAccounts ? (
                  <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg border bg-muted">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span className="text-sm text-muted-foreground">Loading accounts...</span>
                  </div>
                ) : adAccounts.length === 0 ? (
                  <div className="flex items-center justify-between p-4 rounded-lg border border-dashed bg-muted/30">
                    <div className="flex items-center gap-3">
                      <Settings className="w-5 h-5 text-muted-foreground" />
                      <div>
                        <p className="text-sm font-medium text-foreground">
                          No ad accounts connected
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Connect your {selectedPlatform?.name} account in Settings → Integrations
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <select
                    value={formData.account_id}
                    onChange={(e) => handleAccountChange(e.target.value)}
                    className={cn(
                      'w-full px-4 py-2.5 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary',
                      errors.account_id && 'border-red-500'
                    )}
                  >
                    <option value="">Select an ad account</option>
                    {adAccounts.map((account) => (
                      <option key={account.id} value={account.platform_account_id}>
                        {account.name} ({account.platform_account_id}) - {account.currency}
                      </option>
                    ))}
                  </select>
                )}
                {errors.account_id && (
                  <p className="mt-1 text-sm text-red-500">{errors.account_id}</p>
                )}
              </div>

              {/* Status */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('campaigns.create.initialStatus')}
                </label>
                <div className="flex gap-3">
                  {['draft', 'active', 'paused'].map((status) => (
                    <button
                      key={status}
                      onClick={() => updateFormData('status', status)}
                      className={cn(
                        'px-4 py-2 rounded-lg text-sm font-medium border transition-all',
                        formData.status === status
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-transparent bg-muted hover:bg-muted/80 text-foreground'
                      )}
                    >
                      {t(`campaigns.status.${status}`)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Budget Step */}
          {currentStep === 'budget' && (
            <div className="space-y-5">
              <div className="flex items-center gap-3 p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                <DollarSign className="w-5 h-5 text-blue-500" />
                <p className="text-sm text-blue-600 dark:text-blue-400">
                  {t('campaigns.create.budgetInfo')}
                </p>
              </div>

              {/* Currency (Auto-set based on account) */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('campaigns.create.currency')}
                </label>
                <select
                  value={formData.currency}
                  onChange={(e) => updateFormData('currency', e.target.value)}
                  className="w-full px-4 py-2.5 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                >
                  <option value="USD">USD - US Dollar</option>
                  <option value="EUR">EUR - Euro</option>
                  <option value="GBP">GBP - British Pound</option>
                  <option value="SAR">SAR - Saudi Riyal</option>
                  <option value="AED">AED - UAE Dirham</option>
                </select>
              </div>

              {/* Daily Budget */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('campaigns.create.dailyBudget')}
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground">
                    {formData.currency === 'USD'
                      ? '$'
                      : formData.currency === 'EUR'
                        ? '€'
                        : formData.currency}
                  </span>
                  <input
                    type="number"
                    value={formData.daily_budget}
                    onChange={(e) => updateFormData('daily_budget', e.target.value)}
                    placeholder="0.00"
                    min="0"
                    step="0.01"
                    className={cn(
                      'w-full pl-12 pr-4 py-2.5 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary',
                      errors.daily_budget && 'border-red-500'
                    )}
                  />
                </div>
                {errors.daily_budget && (
                  <p className="mt-1 text-sm text-red-500">{errors.daily_budget}</p>
                )}
              </div>

              {/* Lifetime Budget */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('campaigns.create.lifetimeBudget')}
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground">
                    {formData.currency === 'USD'
                      ? '$'
                      : formData.currency === 'EUR'
                        ? '€'
                        : formData.currency}
                  </span>
                  <input
                    type="number"
                    value={formData.lifetime_budget}
                    onChange={(e) => updateFormData('lifetime_budget', e.target.value)}
                    placeholder="0.00"
                    min="0"
                    step="0.01"
                    className="w-full pl-12 pr-4 py-2.5 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                </div>
              </div>

              {/* Schedule */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    {t('campaigns.create.startDate')}
                  </label>
                  <input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) => updateFormData('start_date', e.target.value)}
                    className="w-full px-4 py-2.5 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    {t('campaigns.create.endDate')}
                  </label>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => updateFormData('end_date', e.target.value)}
                    min={formData.start_date}
                    className={cn(
                      'w-full px-4 py-2.5 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary',
                      errors.end_date && 'border-red-500'
                    )}
                  />
                  {errors.end_date && (
                    <p className="mt-1 text-sm text-red-500">{errors.end_date}</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Targeting Step */}
          {currentStep === 'targeting' && (
            <div className="space-y-5">
              <div className="flex items-center gap-3 p-4 rounded-lg bg-purple-500/10 border border-purple-500/20">
                <Users className="w-5 h-5 text-purple-500" />
                <p className="text-sm text-purple-600 dark:text-purple-400">
                  {t('campaigns.create.targetingInfo')}
                </p>
              </div>

              {/* Audiences Section */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-3">
                  {t('campaigns.create.audiences', 'Audiences')}{' '}
                  <span className="text-muted-foreground font-normal">(Optional)</span>
                </label>

                {platformAudiences ? (
                  <>
                    {/* Audience Tabs */}
                    <div className="flex gap-2 mb-3">
                      <button
                        onClick={() => setAudienceTab('custom')}
                        className={cn(
                          'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                          audienceTab === 'custom'
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted hover:bg-muted/80'
                        )}
                      >
                        <UserPlus className="w-4 h-4" />
                        Custom ({platformAudiences.custom.length})
                      </button>
                      <button
                        onClick={() => setAudienceTab('lookalike')}
                        className={cn(
                          'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                          audienceTab === 'lookalike'
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted hover:bg-muted/80'
                        )}
                      >
                        <UsersRound className="w-4 h-4" />
                        Lookalike ({platformAudiences.lookalike.length})
                      </button>
                      <button
                        onClick={() => setAudienceTab('saved')}
                        className={cn(
                          'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                          audienceTab === 'saved'
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted hover:bg-muted/80'
                        )}
                      >
                        <Bookmark className="w-4 h-4" />
                        Saved ({platformAudiences.saved.length})
                      </button>
                    </div>

                    {/* Custom Audiences */}
                    {audienceTab === 'custom' && (
                      <div className="space-y-2 max-h-40 overflow-y-auto">
                        {platformAudiences.custom.map((audience) => (
                          <label
                            key={audience.id}
                            className={cn(
                              'flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all',
                              formData.custom_audiences.includes(audience.id)
                                ? 'border-primary bg-primary/5'
                                : 'border-transparent bg-muted/50 hover:bg-muted'
                            )}
                          >
                            <div className="flex items-center gap-3">
                              <input
                                type="checkbox"
                                checked={formData.custom_audiences.includes(audience.id)}
                                onChange={() => toggleAudience('custom_audiences', audience.id)}
                                className="rounded border-muted-foreground"
                              />
                              <span className="font-medium text-sm">{audience.name}</span>
                            </div>
                            <span className="text-xs text-muted-foreground">
                              {formatAudienceSize(audience.size)} users
                            </span>
                          </label>
                        ))}
                      </div>
                    )}

                    {/* Lookalike Audiences */}
                    {audienceTab === 'lookalike' && (
                      <div className="space-y-2 max-h-40 overflow-y-auto">
                        {platformAudiences.lookalike.map((audience) => (
                          <label
                            key={audience.id}
                            className={cn(
                              'flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all',
                              formData.lookalike_audiences.includes(audience.id)
                                ? 'border-primary bg-primary/5'
                                : 'border-transparent bg-muted/50 hover:bg-muted'
                            )}
                          >
                            <div className="flex items-center gap-3">
                              <input
                                type="checkbox"
                                checked={formData.lookalike_audiences.includes(audience.id)}
                                onChange={() => toggleAudience('lookalike_audiences', audience.id)}
                                className="rounded border-muted-foreground"
                              />
                              <div>
                                <span className="font-medium text-sm block">{audience.name}</span>
                                <span className="text-xs text-muted-foreground">
                                  Source: {audience.source}
                                </span>
                              </div>
                            </div>
                            <span className="text-xs text-muted-foreground">
                              {formatAudienceSize(audience.size)}
                            </span>
                          </label>
                        ))}
                      </div>
                    )}

                    {/* Saved Audiences */}
                    {audienceTab === 'saved' && (
                      <div className="space-y-2 max-h-40 overflow-y-auto">
                        {platformAudiences.saved.map((audience) => (
                          <label
                            key={audience.id}
                            className={cn(
                              'flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all',
                              formData.saved_audiences.includes(audience.id)
                                ? 'border-primary bg-primary/5'
                                : 'border-transparent bg-muted/50 hover:bg-muted'
                            )}
                          >
                            <div className="flex items-center gap-3">
                              <input
                                type="checkbox"
                                checked={formData.saved_audiences.includes(audience.id)}
                                onChange={() => toggleAudience('saved_audiences', audience.id)}
                                className="rounded border-muted-foreground"
                              />
                              <div>
                                <span className="font-medium text-sm block">{audience.name}</span>
                                <span className="text-xs text-muted-foreground">
                                  {audience.description}
                                </span>
                              </div>
                            </div>
                          </label>
                        ))}
                      </div>
                    )}

                    {/* Selected audiences count */}
                    {(formData.custom_audiences.length > 0 ||
                      formData.lookalike_audiences.length > 0 ||
                      formData.saved_audiences.length > 0) && (
                      <p className="text-xs text-primary mt-2">
                        {formData.custom_audiences.length +
                          formData.lookalike_audiences.length +
                          formData.saved_audiences.length}{' '}
                        audience(s) selected
                      </p>
                    )}
                  </>
                ) : (
                  <div className="flex items-center justify-between p-4 rounded-lg border border-dashed bg-muted/30">
                    <div className="flex items-center gap-3">
                      <Users className="w-5 h-5 text-muted-foreground" />
                      <div>
                        <p className="text-sm font-medium text-foreground">No audiences synced</p>
                        <p className="text-xs text-muted-foreground">
                          Audiences can be synced after connecting your platform. Use demographic
                          targeting below instead.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Age Range */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('campaigns.create.ageRange')}
                </label>
                <div className="flex items-center gap-4">
                  <input
                    type="number"
                    value={formData.targeting_age_min}
                    onChange={(e) => updateFormData('targeting_age_min', e.target.value)}
                    min="13"
                    max="100"
                    className={cn(
                      'w-24 px-4 py-2.5 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary text-center',
                      errors.targeting_age_min && 'border-red-500'
                    )}
                  />
                  <span className="text-muted-foreground">to</span>
                  <input
                    type="number"
                    value={formData.targeting_age_max}
                    onChange={(e) => updateFormData('targeting_age_max', e.target.value)}
                    min="13"
                    max="100"
                    className={cn(
                      'w-24 px-4 py-2.5 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary text-center',
                      errors.targeting_age_max && 'border-red-500'
                    )}
                  />
                  <span className="text-sm text-muted-foreground">
                    {t('campaigns.create.yearsOld')}
                  </span>
                </div>
                {(errors.targeting_age_min || errors.targeting_age_max) && (
                  <p className="mt-1 text-sm text-red-500">
                    {errors.targeting_age_min || errors.targeting_age_max}
                  </p>
                )}
              </div>

              {/* Gender */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('campaigns.create.gender')}
                </label>
                <div className="flex gap-3">
                  {['all', 'male', 'female'].map((gender) => (
                    <button
                      key={gender}
                      onClick={() => {
                        if (gender === 'all') {
                          updateFormData('targeting_genders', []);
                        } else {
                          const current = formData.targeting_genders;
                          if (current.includes(gender)) {
                            updateFormData(
                              'targeting_genders',
                              current.filter((g) => g !== gender)
                            );
                          } else {
                            updateFormData('targeting_genders', [...current, gender]);
                          }
                        }
                      }}
                      className={cn(
                        'px-4 py-2 rounded-lg text-sm font-medium border transition-all',
                        (gender === 'all' && formData.targeting_genders.length === 0) ||
                          formData.targeting_genders.includes(gender)
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-transparent bg-muted hover:bg-muted/80 text-foreground'
                      )}
                    >
                      {t(`campaigns.create.genders.${gender}`)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Locations */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('campaigns.create.locations')}
                </label>
                <input
                  type="text"
                  value={formData.targeting_locations}
                  onChange={(e) => updateFormData('targeting_locations', e.target.value)}
                  placeholder={t('campaigns.create.locationsPlaceholder')}
                  className="w-full px-4 py-2.5 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
                <p className="mt-1 text-xs text-muted-foreground">
                  {t('campaigns.create.locationsHelp')}
                </p>
              </div>

              {/* Interests */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('campaigns.create.interests')}
                </label>
                <input
                  type="text"
                  value={formData.targeting_interests}
                  onChange={(e) => updateFormData('targeting_interests', e.target.value)}
                  placeholder={t('campaigns.create.interestsPlaceholder')}
                  className="w-full px-4 py-2.5 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
                <p className="mt-1 text-xs text-muted-foreground">
                  {t('campaigns.create.interestsHelp')}
                </p>
              </div>
            </div>
          )}

          {/* Submit Error */}
          {submitError && (
            <div className="mt-4 flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-600">
              <AlertCircle className="w-5 h-5" />
              <span>{submitError}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t bg-muted/30">
          <button
            onClick={currentStepIndex === 0 ? handleClose : handleBack}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            {currentStepIndex === 0 ? t('common.cancel') : t('common.back')}
          </button>

          {currentStepIndex < STEPS.length - 1 ? (
            <button
              onClick={handleNext}
              className="flex items-center gap-2 px-6 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              {t('common.next')}
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="flex items-center gap-2 px-6 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t('campaigns.create.creating')}
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  {t('campaigns.create.createCampaign')}
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default CampaignCreateModal;
