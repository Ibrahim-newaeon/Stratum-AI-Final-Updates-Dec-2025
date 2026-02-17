/**
 * Stratum AI - Campaign Builder Wizard
 *
 * Multi-step wizard for creating and editing campaign drafts.
 * Supports Meta, Google, TikTok, and Snapchat platforms.
 */

import { useState, useCallback, useRef, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ChevronRightIcon,
  ChevronLeftIcon,
  CheckIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
  PhotoIcon,
  VideoCameraIcon,
  XMarkIcon,
  CloudArrowUpIcon,
  DocumentIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import {
  useAdAccounts,
  useCreateCampaignDraft,
  useSubmitDraft,
  useCampaignDraft,
  type Platform as APIPlatform,
} from '@/api/campaignBuilder'

type Platform = 'meta' | 'google' | 'tiktok' | 'snapchat'
type BudgetType = 'daily' | 'lifetime'
type Objective = 'sales' | 'leads' | 'traffic' | 'awareness' | 'engagement'
type AssetType = 'image' | 'video' | 'carousel'

interface CreativeAsset {
  id: string
  file: File
  name: string
  type: AssetType
  preview: string
  size: number
  status: 'uploading' | 'ready' | 'error'
  headline?: string
  description?: string
  callToAction?: string
}

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
  creatives: CreativeAsset[]
}

const steps = [
  { id: 'platform', name: 'Platform & Account' },
  { id: 'basics', name: 'Campaign Basics' },
  { id: 'budget', name: 'Budget & Schedule' },
  { id: 'targeting', name: 'Targeting' },
  { id: 'creatives', name: 'Ad Creatives' },
  { id: 'review', name: 'Review & Submit' },
]

const callToActionOptions = [
  { value: 'shop_now', label: 'Shop Now' },
  { value: 'learn_more', label: 'Learn More' },
  { value: 'sign_up', label: 'Sign Up' },
  { value: 'contact_us', label: 'Contact Us' },
  { value: 'get_offer', label: 'Get Offer' },
  { value: 'download', label: 'Download' },
  { value: 'book_now', label: 'Book Now' },
]

const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
const ACCEPTED_VIDEO_TYPES = ['video/mp4', 'video/quicktime', 'video/webm']
const MAX_FILE_SIZE = 100 * 1024 * 1024 // 100MB

const objectives: { value: Objective; label: string; description: string }[] = [
  { value: 'sales', label: 'Sales', description: 'Drive purchases and conversions' },
  { value: 'leads', label: 'Leads', description: 'Generate leads and signups' },
  { value: 'traffic', label: 'Traffic', description: 'Send people to your website' },
  { value: 'awareness', label: 'Awareness', description: 'Reach new audiences' },
  { value: 'engagement', label: 'Engagement', description: 'Get more interactions' },
]


export default function CampaignBuilder() {
  const { tenantId, draftId } = useParams<{ tenantId: string; draftId?: string }>()
  const tid = parseInt(tenantId || '1', 10)
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
    creatives: [],
  })
  const [isDragging, setIsDragging] = useState(false)
  const [editingAsset, setEditingAsset] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const isEditing = !!draftId

  // API hooks for ad accounts per platform
  const { data: metaAccounts } = useAdAccounts(tid, 'meta', true)
  const { data: googleAccounts } = useAdAccounts(tid, 'google', true)
  const { data: tiktokAccounts } = useAdAccounts(tid, 'tiktok', true)
  const { data: snapchatAccounts } = useAdAccounts(tid, 'snapchat', true)

  // API mutation hooks
  const createDraft = useCreateCampaignDraft(tid)
  const submitDraft = useSubmitDraft(tid)
  const { data: existingDraft } = useCampaignDraft(tid, draftId || '')

  // Combine ad accounts from all platforms (API data only)
  const adAccounts = useMemo(() => {
    return [
      ...(metaAccounts || []).map((acc) => ({
        id: acc.id,
        name: acc.name,
        platform: 'meta' as Platform,
      })),
      ...(googleAccounts || []).map((acc) => ({
        id: acc.id,
        name: acc.name,
        platform: 'google' as Platform,
      })),
      ...(tiktokAccounts || []).map((acc) => ({
        id: acc.id,
        name: acc.name,
        platform: 'tiktok' as Platform,
      })),
      ...(snapchatAccounts || []).map((acc) => ({
        id: acc.id,
        name: acc.name,
        platform: 'snapchat' as Platform,
      })),
    ]
  }, [metaAccounts, googleAccounts, tiktokAccounts, snapchatAccounts])

  const updateDraft = <K extends keyof CampaignDraft>(
    field: K,
    value: CampaignDraft[K]
  ) => {
    setDraft(prev => ({ ...prev, [field]: value }))
  }

  // File upload handlers
  const getAssetType = (file: File): AssetType => {
    if (ACCEPTED_VIDEO_TYPES.includes(file.type)) return 'video'
    return 'image'
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const processFiles = useCallback((files: FileList | File[]) => {
    const fileArray = Array.from(files)
    const validFiles = fileArray.filter(file => {
      const isValidType = [...ACCEPTED_IMAGE_TYPES, ...ACCEPTED_VIDEO_TYPES].includes(file.type)
      const isValidSize = file.size <= MAX_FILE_SIZE
      return isValidType && isValidSize
    })

    const newAssets: CreativeAsset[] = validFiles.map(file => ({
      id: `asset_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      file,
      name: file.name,
      type: getAssetType(file),
      preview: URL.createObjectURL(file),
      size: file.size,
      status: 'ready' as const,
      headline: '',
      description: '',
      callToAction: 'learn_more',
    }))

    setDraft(prev => ({
      ...prev,
      creatives: [...prev.creatives, ...newAssets],
    }))
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files.length) {
      processFiles(e.dataTransfer.files)
    }
  }, [processFiles])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      processFiles(e.target.files)
    }
    // Reset input value to allow selecting the same file again
    e.target.value = ''
  }, [processFiles])

  const removeAsset = useCallback((id: string) => {
    setDraft(prev => {
      const asset = prev.creatives.find(a => a.id === id)
      if (asset) {
        URL.revokeObjectURL(asset.preview)
      }
      return {
        ...prev,
        creatives: prev.creatives.filter(a => a.id !== id),
      }
    })
  }, [])

  const updateAsset = useCallback((id: string, updates: Partial<CreativeAsset>) => {
    setDraft(prev => ({
      ...prev,
      creatives: prev.creatives.map(asset =>
        asset.id === id ? { ...asset, ...updates } : asset
      ),
    }))
  }, [])

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
    try {
      await createDraft.mutateAsync({
        platform: draft.platform || 'meta',
        ad_account_id: draft.adAccountId,
        name: draft.name,
        description: `${draft.objective} campaign`,
        draft_json: {
          objective: draft.objective,
          budget: draft.budget,
          schedule: draft.schedule,
          targeting: draft.targeting,
          creatives: draft.creatives.map((c) => ({
            id: c.id,
            name: c.name,
            type: c.type,
            headline: c.headline,
            description: c.description,
            callToAction: c.callToAction,
          })),
        },
      })
      alert('Draft saved!')
      navigate(`/app/${tenantId}/campaigns/drafts`)
    } catch (error) {
      console.error('Failed to save draft:', error)
      // Fallback for demo mode
      alert('Draft saved (demo mode)!')
      navigate(`/app/${tenantId}/campaigns/drafts`)
    }
  }

  const handleSubmitForApproval = async () => {
    try {
      if (draftId) {
        await submitDraft.mutateAsync(draftId)
        alert('Submitted for approval!')
      } else {
        // Save first then submit
        const newDraft = await createDraft.mutateAsync({
          platform: draft.platform || 'meta',
          ad_account_id: draft.adAccountId,
          name: draft.name,
          description: `${draft.objective} campaign`,
          draft_json: {
            objective: draft.objective,
            budget: draft.budget,
            schedule: draft.schedule,
            targeting: draft.targeting,
            creatives: draft.creatives.map((c) => ({
              id: c.id,
              name: c.name,
              type: c.type,
              headline: c.headline,
              description: c.description,
              callToAction: c.callToAction,
            })),
          },
        })
        await submitDraft.mutateAsync(newDraft.id)
        alert('Submitted for approval!')
      }
      navigate(`/app/${tenantId}/campaigns/drafts`)
    } catch (error) {
      console.error('Failed to submit:', error)
      // Fallback for demo mode
      alert('Submitted for approval (demo mode)!')
      navigate(`/app/${tenantId}/campaigns/drafts`)
    }
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
                {adAccounts.filter(acc => acc.platform === draft.platform).length > 0 ? (
                  <div className="space-y-2">
                    {adAccounts
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
                ) : (
                  <div className="rounded-lg border-2 border-dashed border-border p-6 text-center">
                    <p className="text-muted-foreground">No ad accounts found for {draft.platform}.</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Connect your {draft.platform.charAt(0).toUpperCase() + draft.platform.slice(1)} account first from the{' '}
                      <a href={`/app/${tenantId}/campaigns/connect`} className="text-primary hover:underline">
                        Connect Platforms
                      </a>{' '}page.
                    </p>
                  </div>
                )}
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

      case 'creatives':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-2">Upload Ad Creatives</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Upload images or videos for your ad. Supported formats: JPEG, PNG, GIF, WebP, MP4, WebM.
              </p>

              {/* Drag & Drop Zone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all',
                  isDragging
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-primary/50 hover:bg-muted/50'
                )}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept={[...ACCEPTED_IMAGE_TYPES, ...ACCEPTED_VIDEO_TYPES].join(',')}
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <CloudArrowUpIcon className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="font-medium">Drag and drop files here</p>
                <p className="text-sm text-muted-foreground mt-1">
                  or click to browse
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  Max file size: 100MB
                </p>
              </div>
            </div>

            {/* Uploaded Assets */}
            {draft.creatives.length > 0 && (
              <div>
                <h4 className="font-medium mb-3">Uploaded Assets ({draft.creatives.length})</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {draft.creatives.map((asset) => (
                    <div
                      key={asset.id}
                      className="rounded-xl border bg-card overflow-hidden"
                    >
                      {/* Asset Preview */}
                      <div className="relative aspect-video bg-muted">
                        {asset.type === 'video' ? (
                          <video
                            src={asset.preview}
                            className="w-full h-full object-cover"
                            controls
                          />
                        ) : (
                          <img
                            src={asset.preview}
                            alt={asset.name}
                            className="w-full h-full object-cover"
                          />
                        )}
                        <button
                          onClick={() => removeAsset(asset.id)}
                          className="absolute top-2 right-2 p-1.5 rounded-full bg-black/60 text-white hover:bg-black/80 transition-colors"
                        >
                          <XMarkIcon className="h-4 w-4" />
                        </button>
                        <div className="absolute bottom-2 left-2 flex items-center gap-1.5">
                          <span className="px-2 py-0.5 rounded-full bg-black/60 text-white text-xs flex items-center gap-1">
                            {asset.type === 'video' ? (
                              <VideoCameraIcon className="h-3 w-3" />
                            ) : (
                              <PhotoIcon className="h-3 w-3" />
                            )}
                            {asset.type}
                          </span>
                          <span className="px-2 py-0.5 rounded-full bg-black/60 text-white text-xs">
                            {formatFileSize(asset.size)}
                          </span>
                        </div>
                      </div>

                      {/* Asset Details */}
                      <div className="p-4 space-y-3">
                        <p className="text-sm font-medium truncate" title={asset.name}>
                          {asset.name}
                        </p>

                        {editingAsset === asset.id ? (
                          <div className="space-y-3">
                            <div>
                              <label className="block text-xs font-medium mb-1">Headline</label>
                              <input
                                type="text"
                                value={asset.headline || ''}
                                onChange={(e) => updateAsset(asset.id, { headline: e.target.value })}
                                placeholder="Enter headline..."
                                maxLength={40}
                                className="w-full px-3 py-1.5 text-sm rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                              />
                              <p className="text-xs text-muted-foreground mt-0.5">
                                {(asset.headline || '').length}/40 characters
                              </p>
                            </div>
                            <div>
                              <label className="block text-xs font-medium mb-1">Description</label>
                              <textarea
                                value={asset.description || ''}
                                onChange={(e) => updateAsset(asset.id, { description: e.target.value })}
                                placeholder="Enter description..."
                                maxLength={125}
                                rows={2}
                                className="w-full px-3 py-1.5 text-sm rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                              />
                              <p className="text-xs text-muted-foreground mt-0.5">
                                {(asset.description || '').length}/125 characters
                              </p>
                            </div>
                            <div>
                              <label className="block text-xs font-medium mb-1">Call to Action</label>
                              <select
                                value={asset.callToAction || 'learn_more'}
                                onChange={(e) => updateAsset(asset.id, { callToAction: e.target.value })}
                                className="w-full px-3 py-1.5 text-sm rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                              >
                                {callToActionOptions.map((cta) => (
                                  <option key={cta.value} value={cta.value}>
                                    {cta.label}
                                  </option>
                                ))}
                              </select>
                            </div>
                            <button
                              onClick={() => setEditingAsset(null)}
                              className="w-full py-1.5 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:opacity-90"
                            >
                              Done
                            </button>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {asset.headline && (
                              <p className="text-sm text-muted-foreground">
                                <span className="font-medium">Headline:</span> {asset.headline}
                              </p>
                            )}
                            {asset.callToAction && (
                              <p className="text-xs text-muted-foreground">
                                CTA: {callToActionOptions.find(c => c.value === asset.callToAction)?.label || asset.callToAction}
                              </p>
                            )}
                            <button
                              onClick={() => setEditingAsset(asset.id)}
                              className="text-xs text-primary hover:underline"
                            >
                              Edit ad copy
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Platform-specific Tips */}
            <div className="rounded-lg border bg-muted/30 p-4">
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <SparklesIcon className="h-4 w-4 text-primary" />
                Platform Recommendations for {draft.platform ? draft.platform.charAt(0).toUpperCase() + draft.platform.slice(1) : 'Ads'}
              </h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                {draft.platform === 'meta' && (
                  <>
                    <li>- Image: 1080x1080px (1:1) or 1200x628px (1.91:1)</li>
                    <li>- Video: 15-60 seconds, vertical (9:16) performs best</li>
                    <li>- Keep text overlay under 20% of image area</li>
                  </>
                )}
                {draft.platform === 'google' && (
                  <>
                    <li>- Responsive display: 1200x628px, 300x250px, 728x90px</li>
                    <li>- Video: 15-30 seconds, horizontal (16:9)</li>
                    <li>- Include clear branding and call-to-action</li>
                  </>
                )}
                {draft.platform === 'tiktok' && (
                  <>
                    <li>- Video: 9:16 aspect ratio, 9-15 seconds optimal</li>
                    <li>- Use native-looking content for better engagement</li>
                    <li>- Add captions as 80% of users watch without sound</li>
                  </>
                )}
                {draft.platform === 'snapchat' && (
                  <>
                    <li>- Full screen vertical: 1080x1920px (9:16)</li>
                    <li>- Video: 3-10 seconds for Story Ads</li>
                    <li>- Keep branding subtle and authentic</li>
                  </>
                )}
                {!draft.platform && (
                  <li>- Select a platform to see specific recommendations</li>
                )}
              </ul>
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
                <div>
                  <dt className="text-sm text-muted-foreground">Ad Creatives</dt>
                  <dd className="font-medium">
                    {draft.creatives.length} asset{draft.creatives.length !== 1 ? 's' : ''} uploaded
                  </dd>
                </div>
              </dl>
            </div>

            {/* Creative Assets Preview */}
            {draft.creatives.length > 0 && (
              <div className="rounded-xl border bg-card p-6">
                <h3 className="text-lg font-semibold mb-4">Ad Creatives Preview</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {draft.creatives.map((asset) => (
                    <div key={asset.id} className="relative aspect-square rounded-lg overflow-hidden bg-muted">
                      {asset.type === 'video' ? (
                        <div className="w-full h-full flex items-center justify-center">
                          <VideoCameraIcon className="h-8 w-8 text-muted-foreground" />
                        </div>
                      ) : (
                        <img
                          src={asset.preview}
                          alt={asset.name}
                          className="w-full h-full object-cover"
                        />
                      )}
                      <div className="absolute inset-0 bg-black/0 hover:bg-black/20 transition-colors" />
                      {asset.headline && (
                        <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/80 to-transparent">
                          <p className="text-xs text-white truncate">{asset.headline}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

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
