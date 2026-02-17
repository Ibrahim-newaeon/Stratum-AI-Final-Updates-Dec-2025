/**
 * Stratum AI - Campaign Drafts List
 *
 * View and manage campaign drafts with approval workflow.
 */

import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  DocumentTextIcon,
  PencilSquareIcon,
  TrashIcon,
  PaperAirplaneIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import { useToast } from '@/components/ui/use-toast'
import {
  useSubmitDraft,
  usePublishDraft,
  useDeleteCampaignDraft,
} from '@/api/campaignBuilder'

type DraftStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'publishing' | 'published' | 'failed'

interface CampaignDraft {
  id: string
  name: string
  platform: string
  status: DraftStatus
  budget: number
  currency: string
  objective: string
  createdAt: string
  updatedAt: string
  createdBy: string
  approvedBy?: string
}

const mockDrafts: CampaignDraft[] = [
  {
    id: '1',
    name: 'KSA Prospecting - Q1',
    platform: 'meta',
    status: 'draft',
    budget: 500,
    currency: 'SAR',
    objective: 'sales',
    createdAt: '2024-01-18T10:00:00Z',
    updatedAt: '2024-01-20T14:30:00Z',
    createdBy: 'Ahmed Al-Saud',
  },
  {
    id: '2',
    name: 'UAE Retargeting',
    platform: 'google',
    status: 'submitted',
    budget: 1200,
    currency: 'AED',
    objective: 'conversions',
    createdAt: '2024-01-15T09:00:00Z',
    updatedAt: '2024-01-19T11:00:00Z',
    createdBy: 'Sara Mohammed',
  },
  {
    id: '3',
    name: 'Brand Awareness - Ramadan',
    platform: 'meta',
    status: 'approved',
    budget: 2500,
    currency: 'SAR',
    objective: 'awareness',
    createdAt: '2024-01-10T08:00:00Z',
    updatedAt: '2024-01-18T16:00:00Z',
    createdBy: 'Omar Hassan',
    approvedBy: 'Admin User',
  },
  {
    id: '4',
    name: 'Product Launch - Winter',
    platform: 'tiktok',
    status: 'rejected',
    budget: 800,
    currency: 'SAR',
    objective: 'traffic',
    createdAt: '2024-01-12T12:00:00Z',
    updatedAt: '2024-01-17T10:00:00Z',
    createdBy: 'Fatima Al-Ali',
  },
]

const statusConfig: Record<DraftStatus, { icon: any; label: string; color: string }> = {
  draft: { icon: DocumentTextIcon, label: 'Draft', color: 'text-gray-600 bg-gray-100 dark:bg-gray-800' },
  submitted: { icon: ClockIcon, label: 'Pending Approval', color: 'text-amber-600 bg-amber-100 dark:bg-amber-900/30' },
  approved: { icon: CheckCircleIcon, label: 'Approved', color: 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30' },
  rejected: { icon: XCircleIcon, label: 'Rejected', color: 'text-red-600 bg-red-100 dark:bg-red-900/30' },
  publishing: { icon: ClockIcon, label: 'Publishing...', color: 'text-blue-600 bg-blue-100 dark:bg-blue-900/30' },
  published: { icon: CheckCircleIcon, label: 'Published', color: 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30' },
  failed: { icon: XCircleIcon, label: 'Failed', color: 'text-red-600 bg-red-100 dark:bg-red-900/30' },
}

export default function CampaignDrafts() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const [drafts, setDrafts] = useState(mockDrafts)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const { toast } = useToast()

  // API hooks
  const tenantIdNum = tenantId ? parseInt(tenantId, 10) : 0
  const submitDraft = useSubmitDraft(tenantIdNum)
  const publishDraft = usePublishDraft(tenantIdNum)
  const deleteDraft = useDeleteCampaignDraft(tenantIdNum)

  const handleDelete = async (draftId: string) => {
    if (confirm('Are you sure you want to delete this draft?')) {
      try {
        await deleteDraft.mutateAsync(draftId)
        // Update local state optimistically
        setDrafts(drafts.filter(d => d.id !== draftId))
        toast({
          title: 'Draft deleted',
          description: 'The campaign draft has been deleted successfully.',
        })
      } catch (error) {
        toast({
          title: 'Delete failed',
          description: error instanceof Error ? error.message : 'Failed to delete draft. Please try again.',
          variant: 'destructive',
        })
      }
    }
  }

  const handleSubmit = async (draftId: string) => {
    try {
      await submitDraft.mutateAsync(draftId)
      // Update local state optimistically
      setDrafts(drafts.map(d =>
        d.id === draftId ? { ...d, status: 'submitted' as DraftStatus } : d
      ))
      toast({
        title: 'Draft submitted',
        description: 'The campaign draft has been submitted for approval.',
      })
    } catch (error) {
      toast({
        title: 'Submit failed',
        description: error instanceof Error ? error.message : 'Failed to submit draft. Please try again.',
        variant: 'destructive',
      })
    }
  }

  const handlePublish = async (draftId: string) => {
    // Set publishing status optimistically
    setDrafts(drafts.map(d =>
      d.id === draftId ? { ...d, status: 'publishing' as DraftStatus } : d
    ))
    try {
      await publishDraft.mutateAsync(draftId)
      // Update local state on success
      setDrafts(drafts.map(d =>
        d.id === draftId ? { ...d, status: 'published' as DraftStatus } : d
      ))
      toast({
        title: 'Campaign published',
        description: 'The campaign has been published successfully.',
      })
    } catch (error) {
      // Revert to approved status on failure
      setDrafts(drafts.map(d =>
        d.id === draftId ? { ...d, status: 'failed' as DraftStatus } : d
      ))
      toast({
        title: 'Publish failed',
        description: error instanceof Error ? error.message : 'Failed to publish campaign. Please try again.',
        variant: 'destructive',
      })
    }
  }

  const filteredDrafts = drafts.filter(d =>
    statusFilter === 'all' || d.status === statusFilter
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Campaign Drafts</h1>
          <p className="text-muted-foreground">
            {drafts.length} draft{drafts.length !== 1 ? 's' : ''} total
          </p>
        </div>
        <Link
          to={`/app/${tenantId}/campaigns/new`}
          className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
        >
          Create New Draft
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'draft', 'submitted', 'approved', 'rejected', 'published'].map((status) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            className={cn(
              'px-3 py-1.5 text-sm rounded-lg transition-colors',
              statusFilter === status
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted hover:bg-muted/80'
            )}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </button>
        ))}
      </div>

      {/* Drafts List */}
      <div className="space-y-4">
        {filteredDrafts.map((draft) => {
          const status = statusConfig[draft.status]
          const StatusIcon = status.icon

          return (
            <div
              key={draft.id}
              className="rounded-xl border bg-card p-6 shadow-card hover:shadow-lg transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-lg bg-muted">
                    <DocumentTextIcon className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg">{draft.name}</h3>
                    <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                      <span className="capitalize">{draft.platform}</span>
                      <span>-</span>
                      <span className="capitalize">{draft.objective}</span>
                      <span>-</span>
                      <span>{draft.currency} {draft.budget}/day</span>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full', status.color)}>
                        <StatusIcon className="h-3 w-3" />
                        {status.label}
                      </span>
                      {draft.approvedBy && (
                        <span className="text-xs text-muted-foreground">
                          Approved by {draft.approvedBy}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* Actions based on status */}
                  {draft.status === 'draft' && (
                    <>
                      <Link
                        to={`/app/${tenantId}/campaigns/drafts/${draft.id}`}
                        className="p-2 rounded-lg hover:bg-accent transition-colors"
                        title="Edit"
                      >
                        <PencilSquareIcon className="h-5 w-5" />
                      </Link>
                      <button
                        onClick={() => handleSubmit(draft.id)}
                        className="p-2 rounded-lg hover:bg-accent transition-colors"
                        title="Submit for Approval"
                      >
                        <PaperAirplaneIcon className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => handleDelete(draft.id)}
                        className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/30 text-red-600 transition-colors"
                        title="Delete"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </>
                  )}

                  {draft.status === 'approved' && (
                    <button
                      onClick={() => handlePublish(draft.id)}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
                    >
                      <PaperAirplaneIcon className="h-4 w-4" />
                      Publish
                    </button>
                  )}

                  {draft.status === 'rejected' && (
                    <Link
                      to={`/app/${tenantId}/campaigns/drafts/${draft.id}`}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg border hover:bg-accent transition-colors"
                    >
                      <PencilSquareIcon className="h-4 w-4" />
                      Edit & Resubmit
                    </Link>
                  )}
                </div>
              </div>

              {/* Metadata */}
              <div className="mt-4 pt-4 border-t flex items-center justify-between text-sm text-muted-foreground">
                <span>Created by {draft.createdBy}</span>
                <span>Updated {new Date(draft.updatedAt).toLocaleDateString()}</span>
              </div>
            </div>
          )
        })}
      </div>

      {filteredDrafts.length === 0 && (
        <div className="rounded-xl border bg-muted/30 p-12 text-center">
          <DocumentTextIcon className="h-12 w-12 mx-auto text-muted-foreground" />
          <h3 className="mt-4 font-semibold">No Drafts Found</h3>
          <p className="text-muted-foreground mt-2">
            {statusFilter === 'all'
              ? 'Create your first campaign draft to get started'
              : `No drafts with status "${statusFilter}"`}
          </p>
          <Link
            to={`/app/${tenantId}/campaigns/new`}
            className="inline-block mt-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
          >
            Create Draft
          </Link>
        </div>
      )}
    </div>
  )
}
