/**
 * Stratum AI - Campaign Builder Wizard
 *
 * Multi-step wizard for creating and editing campaign drafts.
 * Supports Meta, Google, TikTok, and Snapchat platforms.
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ChevronRightIcon,
  ChevronLeftIcon,
  CheckIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

type Platform = 'meta' | 'google' | 'tiktok' | 'snapchat'
type BudgetType = 'daily' | 'lifetime'
type Objective = 'sales' | 'leads' | 'traffic' | 'awareness' | 'engagement'

interface CampaignDraft {
  platform: Platform | null
  adAccountId: string
  name: string
  objective: Objective | null
  budget: {
    type: BudgetType
    amount: number
    currency: string
  }
  schedule: {
    start: string
    end: string | null
  }
  targeting: {
    locations: string[]
    ageMin: number
    ageMax: number
    genders: string[]
  }
}

const steps = [
  { id: 'platform', name: 'Platform & Account' },
  { id: 'basics', name: 'Campaign Basics' },
  { id: 'budget', name: 'Budget & Schedule' },
  { id: 'targeting', name: 'Targeting' },
  { id: 'review', name: 'Review & Submit' },
]

const objectives: { value: Objective; label: string; description: string }[] = [
  { value: 'sales', label: 'Sales', description: 'Drive purchases and conversions' },
  { value: 'leads', label: 'Leads', description: 'Generate leads and signups' },
  { value: 'traffic', label: 'Traffic', description: 'Send people to your website' },
  { value: 'awareness', label: 'Awareness', description: 'Reach new audiences' },
  { value: 'engagement', label: 'Engagement', description: 'Get more interactions' },
]

const mockAdAccounts = [
  { id: 'act_123', name: 'Main Business Account', platform: 'meta' as Platform },
  { id: 'act_456', name: 'E-commerce Store', platform: 'meta' as Platform },
  { id: 'gads_789', name: 'Company Google Ads', platform: 'google' as Platform },
]

export default function CampaignBuilder() {
  const { tenantId, draftId } = useParams<{ tenantId: string; draftId?: string }>()
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)
  const [draft, setDraft] = useState<CampaignDraft>({
    platform: null,
    adAccountId: '',
    name: '',
    objective: null,
    budget: {
      type: 'daily',
      amount: 100,
      currency: 'SAR',
    },
    schedule: {
      start: new Date().toISOString().split('T')[0],
      end: null,
    },
    targeting: {
      locations: [],
      ageMin: 18,
      ageMax: 65,
      genders: ['all'],
    },
  })

  const isEditing = !!draftId

  const updateDraft = <K extends keyof CampaignDraft>(
    field: K,
    value: CampaignDraft[K]
  ) => {
    setDraft(prev => ({ ...prev, [field]: value }))
  }

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSaveDraft = async () => {
    // In production: await api.post(`/tenant/${tenantId}/campaign-drafts`, draft)
    alert('Draft saved!')
    navigate(`/app/${tenantId}/campaigns/drafts`)
  }

  const handleSubmitForApproval = async () => {
    // In production: await api.post(`/tenant/${tenantId}/campaign-drafts/${draftId}/submit`)
    alert('Submitted for approval!')
    navigate(`/app/${tenantId}/campaigns/drafts`)
  }

  const renderStepContent = () => {
    switch (steps[currentStep].id) {
      case 'platform':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-4">Select Platform</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {(['meta', 'google', 'tiktok', 'snapchat'] as Platform[]).map((p) => (
                  <button
                    key={p}
                    onClick={() => updateDraft('platform', p)}
                    className={cn(
                      'p-4 rounded-xl border-2 transition-all text-center',
                      draft.platform === p
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                    )}
                  >
                    <div className="h-12 w-12 mx-auto rounded-lg bg-muted flex items-center justify-center mb-2">
                      <span className="text-xl font-bold">{p.charAt(0).toUpperCase()}</span>
                    </div>
                    <span className="font-medium capitalize">{p}</span>
                  </button>
                ))}
              </div>
            </div>

            {draft.platform && (
              <div>
                <h3 className="text-lg font-semibold mb-4">Select Ad Account</h3>
                <div className="space-y-2">
                  {mockAdAccounts
                    .filter(acc => acc.platform === draft.platform)
                    .map((acc) => (
                      <button
                        key={acc.id}
                        onClick={() => updateDraft('adAccountId', acc.id)}
                        className={cn(
                          'w-full p-4 rounded-lg border-2 text-left transition-all',
                          draft.adAccountId === acc.id
                            ? 'border-primary bg-primary/5'
                            : 'border-border hover:border-primary/50'
                        )}
                      >
                        <p className="font-medium">{acc.name}</p>
                        <p className="text-sm text-muted-foreground">{acc.id}</p>
                      </button>
                    ))}
                </div>
              </div>
            )}
          </div>
        )

      case 'basics':
        return (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2">Campaign Name</label>
              <input
                type="text"
                value={draft.name}
                onChange={(e) => updateDraft('name', e.target.value)}
                placeholder="Enter campaign name..."
                className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-4">Campaign Objective</label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {objectives.map((obj) => (
                  <button
                    key={obj.value}
                    onClick={() => updateDraft('objective', obj.value)}
                    className={cn(
                      'p-4 rounded-lg border-2 text-left transition-all',
                      draft.objective === obj.value
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                    )}
                  >
                    <p className="font-medium">{obj.label}</p>
                    <p className="text-sm text-muted-foreground">{obj.description}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )

      case 'budget':
        return (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-4">Budget Type</label>
              <div className="flex gap-4">
                {(['daily', 'lifetime'] as BudgetType[]).map((type) => (
                  <button
                    key={type}
                    onClick={() => updateDraft('budget', { ...draft.budget, type })}
                    className={cn(
                      'flex-1 p-4 rounded-lg border-2 transition-all',
                      draft.budget.type === type
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                    )}
                  >
                    <p className="font-medium capitalize">{type} Budget</p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                {draft.budget.type === 'daily' ? 'Daily Budget' : 'Total Budget'} ({draft.budget.currency})
              </label>
              <input
                type="number"
                value={draft.budget.amount}
                onChange={(e) => updateDraft('budget', { ...draft.budget, amount: Number(e.target.value) })}
                min={1}
                className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Start Date</label>
                <input
                  type="date"
                  value={draft.schedule.start}
                  onChange={(e) => updateDraft('schedule', { ...draft.schedule, start: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">End Date (Optional)</label>
                <input
                  type="date"
                  value={draft.schedule.end || ''}
                  onChange={(e) => updateDraft('schedule', { ...draft.schedule, end: e.target.value || null })}
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
            </div>

            {/* Budget guardrail warning */}
            {draft.budget.amount > 1000 && (
              <div className="flex items-start gap-3 p-4 rounded-lg bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800">
                <ExclamationTriangleIcon className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-amber-800 dark:text-amber-200">Budget Guardrail</p>
                  <p className="text-sm text-amber-700 dark:text-amber-300">
                    This campaign requires approval for budgets over SAR 1,000/day
                  </p>
                </div>
              </div>
            )}
          </div>
        )

      case 'targeting':
        return (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2">Target Locations</label>
              <input
                type="text"
                placeholder="e.g., Saudi Arabia, UAE, Egypt..."
                className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Separate multiple locations with commas
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Minimum Age</label>
                <input
                  type="number"
                  value={draft.targeting.ageMin}
                  onChange={(e) => updateDraft('targeting', { ...draft.targeting, ageMin: Number(e.target.value) })}
                  min={13}
                  max={65}
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Maximum Age</label>
                <input
                  type="number"
                  value={draft.targeting.ageMax}
                  onChange={(e) => updateDraft('targeting', { ...draft.targeting, ageMax: Number(e.target.value) })}
                  min={13}
                  max={65}
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-4">Gender Targeting</label>
              <div className="flex gap-4">
                {[
                  { value: 'all', label: 'All' },
                  { value: 'male', label: 'Male' },
                  { value: 'female', label: 'Female' },
                ].map((gender) => (
                  <button
                    key={gender.value}
                    onClick={() => updateDraft('targeting', { ...draft.targeting, genders: [gender.value] })}
                    className={cn(
                      'px-4 py-2 rounded-lg border-2 transition-all',
                      draft.targeting.genders.includes(gender.value)
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                    )}
                  >
                    {gender.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )

      case 'review':
        return (
          <div className="space-y-6">
            <div className="rounded-xl border bg-card p-6">
              <h3 className="text-lg font-semibold mb-4">Campaign Summary</h3>
              <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <dt className="text-sm text-muted-foreground">Platform</dt>
                  <dd className="font-medium capitalize">{draft.platform || 'Not selected'}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Ad Account</dt>
                  <dd className="font-medium">{draft.adAccountId || 'Not selected'}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Campaign Name</dt>
                  <dd className="font-medium">{draft.name || 'Not set'}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Objective</dt>
                  <dd className="font-medium capitalize">{draft.objective || 'Not selected'}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Budget</dt>
                  <dd className="font-medium">
                    {draft.budget.currency} {draft.budget.amount} / {draft.budget.type}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Schedule</dt>
                  <dd className="font-medium">
                    {draft.schedule.start} - {draft.schedule.end || 'Ongoing'}
                  </dd>
                </div>
              </dl>
            </div>

            {/* AI Insights */}
            <div className="rounded-xl border bg-gradient-to-br from-purple-50 to-indigo-50 dark:from-purple-950/20 dark:to-indigo-950/20 p-6">
              <div className="flex items-center gap-2 mb-4">
                <SparklesIcon className="h-5 w-5 text-purple-600" />
                <h3 className="font-semibold text-purple-900 dark:text-purple-100">AI Insights</h3>
              </div>
              <ul className="space-y-2 text-sm text-purple-800 dark:text-purple-200">
                <li>- Budget is within normal range for {draft.objective} campaigns</li>
                <li>- Consider adding lookalike audiences for better reach</li>
                <li>- Estimated ROAS based on similar campaigns: 3.5x - 4.2x</li>
              </ul>
            </div>
          </div>
        )
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">
          {isEditing ? 'Edit Campaign Draft' : 'Create New Campaign'}
        </h1>
        <p className="text-muted-foreground">
          Step {currentStep + 1} of {steps.length}: {steps[currentStep].name}
        </p>
      </div>

      {/* Progress Steps */}
      <nav className="flex items-center justify-between">
        {steps.map((step, index) => (
          <div
            key={step.id}
            className={cn(
              'flex items-center',
              index < steps.length - 1 && 'flex-1'
            )}
          >
            <div
              className={cn(
                'flex items-center justify-center h-10 w-10 rounded-full border-2 transition-colors',
                index < currentStep && 'bg-primary border-primary text-primary-foreground',
                index === currentStep && 'border-primary text-primary',
                index > currentStep && 'border-muted-foreground text-muted-foreground'
              )}
            >
              {index < currentStep ? (
                <CheckIcon className="h-5 w-5" />
              ) : (
                <span className="text-sm font-medium">{index + 1}</span>
              )}
            </div>
            {index < steps.length - 1 && (
              <div
                className={cn(
                  'flex-1 h-0.5 mx-2',
                  index < currentStep ? 'bg-primary' : 'bg-muted'
                )}
              />
            )}
          </div>
        ))}
      </nav>

      {/* Step Content */}
      <div className="rounded-xl border bg-card p-6 shadow-card min-h-[400px]">
        {renderStepContent()}
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between">
        <button
          onClick={handleBack}
          disabled={currentStep === 0}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-accent transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronLeftIcon className="h-5 w-5" />
          Back
        </button>

        <div className="flex gap-3">
          <button
            onClick={handleSaveDraft}
            className="px-4 py-2 rounded-lg border hover:bg-accent transition-colors"
          >
            Save Draft
          </button>

          {currentStep === steps.length - 1 ? (
            <button
              onClick={handleSubmitForApproval}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
            >
              Submit for Approval
            </button>
          ) : (
            <button
              onClick={handleNext}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
            >
              Next
              <ChevronRightIcon className="h-5 w-5" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
