/**
 * Stratum AI - Superadmin CMS Dashboard
 *
 * Content Management System for managing blog posts, pages, categories,
 * tags, authors, and contact form submissions.
 */

import { useState } from 'react'
import { cn } from '@/lib/utils'
import {
  FileText,
  FolderOpen,
  Tags,
  Users,
  MessageSquare,
  Plus,
  Search,
  Edit2,
  Trash2,
  Eye,
  MoreVertical,
  Filter,
  RefreshCw,
  Mail,
  MailOpen,
  AlertTriangle,
  CheckCircle,
  Clock,
  Send,
  ThumbsUp,
  ThumbsDown,
  MessageCircle,
  Calendar,
  Rocket,
  Archive,
  RotateCcw,
  History,
  GitBranch,
  XCircle,
} from 'lucide-react'
import {
  useAdminPosts,
  useAdminCategories,
  useAdminTags,
  useAdminAuthors,
  useAdminPages,
  useAdminContacts,
  useCreatePost,
  useUpdatePost,
  useDeletePost,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
  useCreateTag,
  useDeleteTag,
  useCreateAuthor,
  useUpdateAuthor,
  useDeleteAuthor,
  useCreatePage,
  useUpdatePage,
  useDeletePage,
  useMarkContactRead,
  useMarkContactSpam,
  // 2026 Workflow hooks
  useSubmitForReview,
  useApprovePost,
  useRejectPost,
  useRequestChanges,
  useSchedulePost,
  usePublishPost,
  useUnpublishPost,
  useArchivePost,
  useWorkflowHistory,
  useVersionHistory,
  useRestoreVersion,
  WORKFLOW_STATUS_CONFIG,
  getStatusConfig,
  CMSPost,
  CMSCategory,
  CMSTag,
  CMSAuthor,
  CMSPage,
  CMSContact,
  PostStatus,
} from '@/api/cms'
import { PostEditor } from '@/components/cms/PostEditor'

type TabType = 'posts' | 'pages' | 'categories' | 'tags' | 'authors' | 'contacts'

const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
  { id: 'posts', label: 'Posts', icon: <FileText className="w-4 h-4" /> },
  { id: 'pages', label: 'Pages', icon: <FolderOpen className="w-4 h-4" /> },
  { id: 'categories', label: 'Categories', icon: <FolderOpen className="w-4 h-4" /> },
  { id: 'tags', label: 'Tags', icon: <Tags className="w-4 h-4" /> },
  { id: 'authors', label: 'Authors', icon: <Users className="w-4 h-4" /> },
  { id: 'contacts', label: 'Contact Inbox', icon: <MessageSquare className="w-4 h-4" /> },
]

// 2026 Workflow Status Colors
const statusColors: Record<PostStatus, string> = {
  draft: 'bg-neutral-600 text-neutral-200',
  in_review: 'bg-yellow-600 text-yellow-200',
  changes_requested: 'bg-orange-600 text-orange-200',
  approved: 'bg-emerald-600 text-emerald-200',
  scheduled: 'bg-blue-600 text-blue-200',
  published: 'bg-green-600 text-green-200',
  unpublished: 'bg-neutral-500 text-neutral-200',
  archived: 'bg-neutral-700 text-neutral-300',
  rejected: 'bg-red-600 text-red-200',
}

// Status icons for visual clarity
const statusIcons: Record<PostStatus, React.ReactNode> = {
  draft: <Edit2 className="w-3 h-3" />,
  in_review: <Clock className="w-3 h-3" />,
  changes_requested: <MessageCircle className="w-3 h-3" />,
  approved: <ThumbsUp className="w-3 h-3" />,
  scheduled: <Calendar className="w-3 h-3" />,
  published: <Rocket className="w-3 h-3" />,
  unpublished: <XCircle className="w-3 h-3" />,
  archived: <Archive className="w-3 h-3" />,
  rejected: <ThumbsDown className="w-3 h-3" />,
}

export default function CMS() {
  const [activeTab, setActiveTab] = useState<TabType>('posts')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<PostStatus | ''>('')
  const [showPostEditor, setShowPostEditor] = useState(false)
  const [editingPost, setEditingPost] = useState<CMSPost | undefined>()
  const [page, setPage] = useState(1)

  // 2026 Workflow state
  const [selectedPostForWorkflow, setSelectedPostForWorkflow] = useState<CMSPost | null>(null)
  const [showWorkflowHistory, setShowWorkflowHistory] = useState(false)
  const [showVersionHistory, setShowVersionHistory] = useState(false)
  const [showScheduleModal, setShowScheduleModal] = useState(false)
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [showChangesModal, setShowChangesModal] = useState(false)
  const [scheduleDate, setScheduleDate] = useState('')
  const [rejectReason, setRejectReason] = useState('')
  const [changesNotes, setChangesNotes] = useState('')

  // Data hooks
  const { data: postsData, isLoading: postsLoading, refetch: refetchPosts } = useAdminPosts({
    page,
    page_size: 20,
    search: search || undefined,
    status_filter: statusFilter || undefined,
  })
  const { data: categoriesData, isLoading: categoriesLoading, refetch: refetchCategories } = useAdminCategories()
  const { data: tagsData, isLoading: tagsLoading, refetch: refetchTags } = useAdminTags()
  const { data: authorsData, isLoading: authorsLoading, refetch: refetchAuthors } = useAdminAuthors()
  const { data: pagesData, isLoading: pagesLoading, refetch: refetchPages } = useAdminPages()
  const { data: contactsData, isLoading: contactsLoading, refetch: refetchContacts } = useAdminContacts({
    page,
    page_size: 20,
  })

  // Mutation hooks
  const createPost = useCreatePost()
  const updatePost = useUpdatePost()
  const deletePost = useDeletePost()
  const createCategory = useCreateCategory()
  const updateCategory = useUpdateCategory()
  const deleteCategory = useDeleteCategory()
  const createTag = useCreateTag()
  const deleteTag = useDeleteTag()
  const createAuthor = useCreateAuthor()
  const updateAuthor = useUpdateAuthor()
  const deleteAuthor = useDeleteAuthor()
  const createPage = useCreatePage()
  const updatePage = useUpdatePage()
  const deletePage = useDeletePage()
  const markContactRead = useMarkContactRead()
  const markContactSpam = useMarkContactSpam()

  // 2026 Workflow mutation hooks
  const submitForReview = useSubmitForReview()
  const approvePost = useApprovePost()
  const rejectPost = useRejectPost()
  const requestChanges = useRequestChanges()
  const schedulePost = useSchedulePost()
  const publishPost = usePublishPost()
  const unpublishPost = useUnpublishPost()
  const archivePost = useArchivePost()
  const restoreVersion = useRestoreVersion()

  // Workflow history hooks (conditional)
  const { data: workflowHistoryData } = useWorkflowHistory(
    selectedPostForWorkflow?.id || '',
    1,
    50
  )
  const { data: versionHistoryData } = useVersionHistory(
    selectedPostForWorkflow?.id || '',
    1,
    50
  )

  // Handlers
  const handleCreatePost = () => {
    setEditingPost(undefined)
    setShowPostEditor(true)
  }

  const handleEditPost = (post: CMSPost) => {
    setEditingPost(post)
    setShowPostEditor(true)
  }

  const handleSavePost = async (data: any) => {
    try {
      if (editingPost) {
        await updatePost.mutateAsync({ id: editingPost.id, data })
      } else {
        await createPost.mutateAsync(data)
      }
      setShowPostEditor(false)
      setEditingPost(undefined)
    } catch (error) {
      console.error('Failed to save post:', error)
    }
  }

  const handleDeletePost = async (id: string) => {
    if (confirm('Are you sure you want to delete this post?')) {
      await deletePost.mutateAsync(id)
    }
  }

  const handleCreateCategory = async () => {
    const name = prompt('Enter category name:')
    if (name) {
      await createCategory.mutateAsync({ name })
    }
  }

  const handleDeleteCategory = async (id: string) => {
    if (confirm('Are you sure you want to delete this category?')) {
      await deleteCategory.mutateAsync(id)
    }
  }

  const handleCreateTag = async () => {
    const name = prompt('Enter tag name:')
    if (name) {
      await createTag.mutateAsync({ name })
    }
  }

  const handleDeleteTag = async (id: string) => {
    if (confirm('Are you sure you want to delete this tag?')) {
      await deleteTag.mutateAsync(id)
    }
  }

  const handleCreateAuthor = async () => {
    const name = prompt('Enter author name:')
    if (name) {
      await createAuthor.mutateAsync({ name })
    }
  }

  const handleDeleteAuthor = async (id: string) => {
    if (confirm('Are you sure you want to delete this author?')) {
      await deleteAuthor.mutateAsync(id)
    }
  }

  const handleMarkRead = async (id: string, isRead: boolean) => {
    await markContactRead.mutateAsync({ id, isRead })
  }

  const handleMarkSpam = async (id: string, isSpam: boolean) => {
    await markContactSpam.mutateAsync({ id, isSpam })
  }

  // 2026 Workflow handlers
  const handleSubmitForReview = async (post: CMSPost) => {
    try {
      await submitForReview.mutateAsync({ postId: post.id })
    } catch (error) {
      console.error('Failed to submit for review:', error)
    }
  }

  const handleApprove = async (post: CMSPost) => {
    try {
      await approvePost.mutateAsync({ postId: post.id })
    } catch (error) {
      console.error('Failed to approve:', error)
    }
  }

  const handleReject = async () => {
    if (!selectedPostForWorkflow || rejectReason.length < 10) return
    try {
      await rejectPost.mutateAsync({
        postId: selectedPostForWorkflow.id,
        reason: rejectReason,
      })
      setShowRejectModal(false)
      setRejectReason('')
      setSelectedPostForWorkflow(null)
    } catch (error) {
      console.error('Failed to reject:', error)
    }
  }

  const handleRequestChanges = async () => {
    if (!selectedPostForWorkflow || changesNotes.length < 10) return
    try {
      await requestChanges.mutateAsync({
        postId: selectedPostForWorkflow.id,
        notes: changesNotes,
      })
      setShowChangesModal(false)
      setChangesNotes('')
      setSelectedPostForWorkflow(null)
    } catch (error) {
      console.error('Failed to request changes:', error)
    }
  }

  const handleSchedule = async () => {
    if (!selectedPostForWorkflow || !scheduleDate) return
    try {
      await schedulePost.mutateAsync({
        postId: selectedPostForWorkflow.id,
        scheduledAt: new Date(scheduleDate).toISOString(),
      })
      setShowScheduleModal(false)
      setScheduleDate('')
      setSelectedPostForWorkflow(null)
    } catch (error) {
      console.error('Failed to schedule:', error)
    }
  }

  const handlePublish = async (post: CMSPost) => {
    try {
      await publishPost.mutateAsync(post.id)
    } catch (error) {
      console.error('Failed to publish:', error)
    }
  }

  const handleUnpublish = async (post: CMSPost) => {
    try {
      await unpublishPost.mutateAsync(post.id)
    } catch (error) {
      console.error('Failed to unpublish:', error)
    }
  }

  const handleArchive = async (post: CMSPost) => {
    if (confirm('Are you sure you want to archive this post?')) {
      try {
        await archivePost.mutateAsync(post.id)
      } catch (error) {
        console.error('Failed to archive:', error)
      }
    }
  }

  const openWorkflowHistory = (post: CMSPost) => {
    setSelectedPostForWorkflow(post)
    setShowWorkflowHistory(true)
  }

  const openVersionHistory = (post: CMSPost) => {
    setSelectedPostForWorkflow(post)
    setShowVersionHistory(true)
  }

  // Get available workflow actions for a post based on its status
  const getWorkflowActions = (post: CMSPost) => {
    const actions: { label: string; icon: React.ReactNode; action: () => void; variant?: string }[] = []

    switch (post.status) {
      case 'draft':
      case 'changes_requested':
      case 'rejected':
        actions.push({
          label: 'Submit for Review',
          icon: <Send className="w-4 h-4" />,
          action: () => handleSubmitForReview(post),
        })
        actions.push({
          label: 'Schedule',
          icon: <Calendar className="w-4 h-4" />,
          action: () => { setSelectedPostForWorkflow(post); setShowScheduleModal(true) },
        })
        actions.push({
          label: 'Publish Now',
          icon: <Rocket className="w-4 h-4" />,
          action: () => handlePublish(post),
          variant: 'success',
        })
        break

      case 'in_review':
        actions.push({
          label: 'Approve',
          icon: <ThumbsUp className="w-4 h-4" />,
          action: () => handleApprove(post),
          variant: 'success',
        })
        actions.push({
          label: 'Request Changes',
          icon: <MessageCircle className="w-4 h-4" />,
          action: () => { setSelectedPostForWorkflow(post); setShowChangesModal(true) },
          variant: 'warning',
        })
        actions.push({
          label: 'Reject',
          icon: <ThumbsDown className="w-4 h-4" />,
          action: () => { setSelectedPostForWorkflow(post); setShowRejectModal(true) },
          variant: 'danger',
        })
        break

      case 'approved':
        actions.push({
          label: 'Schedule',
          icon: <Calendar className="w-4 h-4" />,
          action: () => { setSelectedPostForWorkflow(post); setShowScheduleModal(true) },
        })
        actions.push({
          label: 'Publish Now',
          icon: <Rocket className="w-4 h-4" />,
          action: () => handlePublish(post),
          variant: 'success',
        })
        break

      case 'scheduled':
        actions.push({
          label: 'Publish Now',
          icon: <Rocket className="w-4 h-4" />,
          action: () => handlePublish(post),
          variant: 'success',
        })
        break

      case 'published':
        actions.push({
          label: 'Unpublish',
          icon: <XCircle className="w-4 h-4" />,
          action: () => handleUnpublish(post),
          variant: 'warning',
        })
        actions.push({
          label: 'Archive',
          icon: <Archive className="w-4 h-4" />,
          action: () => handleArchive(post),
        })
        break

      case 'unpublished':
        actions.push({
          label: 'Publish',
          icon: <Rocket className="w-4 h-4" />,
          action: () => handlePublish(post),
          variant: 'success',
        })
        actions.push({
          label: 'Archive',
          icon: <Archive className="w-4 h-4" />,
          action: () => handleArchive(post),
        })
        break
    }

    // Always add history actions
    actions.push({
      label: 'Workflow History',
      icon: <History className="w-4 h-4" />,
      action: () => openWorkflowHistory(post),
    })
    actions.push({
      label: 'Version History',
      icon: <GitBranch className="w-4 h-4" />,
      action: () => openVersionHistory(post),
    })

    return actions
  }

  const renderContent = () => {
    switch (activeTab) {
      case 'posts':
        return (
          <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" />
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search posts..."
                    className="pl-10 pr-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500 w-64"
                  />
                </div>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as PostStatus | '')}
                  className="px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="">All Status</option>
                  <option value="draft">Draft</option>
                  <option value="in_review">In Review</option>
                  <option value="changes_requested">Changes Requested</option>
                  <option value="approved">Approved</option>
                  <option value="scheduled">Scheduled</option>
                  <option value="published">Published</option>
                  <option value="unpublished">Unpublished</option>
                  <option value="rejected">Rejected</option>
                  <option value="archived">Archived</option>
                </select>
              </div>
              <button
                onClick={handleCreatePost}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                New Post
              </button>
            </div>

            {/* Posts Table */}
            {postsLoading ? (
              <div className="text-center py-8 text-neutral-400">Loading posts...</div>
            ) : (
              <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
                <table className="w-full">
                  <thead className="bg-neutral-800/50">
                    <tr>
                      <th className="text-left px-4 py-3 text-sm font-medium text-neutral-400">Title</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-neutral-400">Status</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-neutral-400">Author</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-neutral-400">Views</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-neutral-400">Date</th>
                      <th className="text-right px-4 py-3 text-sm font-medium text-neutral-400">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {postsData?.posts.map((post) => {
                      const workflowActions = getWorkflowActions(post)
                      return (
                        <tr key={post.id} className="border-t border-neutral-800 hover:bg-neutral-800/30">
                          <td className="px-4 py-3">
                            <div className="font-medium text-white">{post.title}</div>
                            <div className="text-sm text-neutral-500">/blog/{post.slug}</div>
                          </td>
                          <td className="px-4 py-3">
                            <span className={cn('px-2 py-1 text-xs rounded-full inline-flex items-center gap-1', statusColors[post.status])}>
                              {statusIcons[post.status]}
                              {post.status.replace('_', ' ')}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-neutral-400">{post.author?.name || '-'}</td>
                          <td className="px-4 py-3 text-neutral-400">{post.view_count}</td>
                          <td className="px-4 py-3 text-neutral-400 text-sm">
                            {new Date(post.created_at).toLocaleDateString()}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center justify-end gap-1">
                              {/* Quick workflow actions based on status */}
                              {workflowActions.slice(0, 2).map((action, idx) => (
                                <button
                                  key={idx}
                                  onClick={action.action}
                                  className={cn(
                                    'p-1.5 rounded text-xs transition-colors',
                                    action.variant === 'success' && 'text-green-400 hover:bg-green-500/20',
                                    action.variant === 'warning' && 'text-yellow-400 hover:bg-yellow-500/20',
                                    action.variant === 'danger' && 'text-red-400 hover:bg-red-500/20',
                                    !action.variant && 'text-neutral-400 hover:text-white hover:bg-neutral-700'
                                  )}
                                  title={action.label}
                                >
                                  {action.icon}
                                </button>
                              ))}
                              <button
                                onClick={() => handleEditPost(post)}
                                className="p-1.5 text-neutral-400 hover:text-white transition-colors"
                                title="Edit"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>
                              <div className="relative group">
                                <button
                                  className="p-1.5 text-neutral-400 hover:text-white transition-colors"
                                  title="More actions"
                                >
                                  <MoreVertical className="w-4 h-4" />
                                </button>
                                <div className="absolute right-0 top-full mt-1 w-48 bg-neutral-800 border border-neutral-700 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
                                  {workflowActions.map((action, idx) => (
                                    <button
                                      key={idx}
                                      onClick={action.action}
                                      className={cn(
                                        'w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors',
                                        action.variant === 'success' && 'text-green-400 hover:bg-green-500/20',
                                        action.variant === 'warning' && 'text-yellow-400 hover:bg-yellow-500/20',
                                        action.variant === 'danger' && 'text-red-400 hover:bg-red-500/20',
                                        !action.variant && 'text-neutral-300 hover:bg-neutral-700'
                                      )}
                                    >
                                      {action.icon}
                                      {action.label}
                                    </button>
                                  ))}
                                  <hr className="border-neutral-700 my-1" />
                                  <button
                                    onClick={() => handleDeletePost(post.id)}
                                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-red-400 hover:bg-red-500/20 transition-colors"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                    Delete
                                  </button>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
                {postsData?.total === 0 && (
                  <div className="text-center py-8 text-neutral-400">No posts found</div>
                )}
              </div>
            )}

            {/* Pagination */}
            {postsData && postsData.total > 20 && (
              <div className="flex items-center justify-between">
                <div className="text-sm text-neutral-400">
                  Showing {((page - 1) * 20) + 1} - {Math.min(page * 20, postsData.total)} of {postsData.total}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 bg-neutral-800 text-white rounded disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page * 20 >= postsData.total}
                    className="px-3 py-1 bg-neutral-800 text-white rounded disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )

      case 'categories':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-white">Categories</h3>
              <button
                onClick={handleCreateCategory}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                New Category
              </button>
            </div>

            {categoriesLoading ? (
              <div className="text-center py-8 text-neutral-400">Loading categories...</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {categoriesData?.categories.map((category) => (
                  <div
                    key={category.id}
                    className="p-4 bg-neutral-900 border border-neutral-800 rounded-xl"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {category.color && (
                          <div
                            className="w-4 h-4 rounded-full"
                            style={{ backgroundColor: category.color }}
                          />
                        )}
                        <div>
                          <div className="font-medium text-white">{category.name}</div>
                          <div className="text-sm text-neutral-500">/{category.slug}</div>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteCategory(category.id)}
                        className="p-2 text-neutral-400 hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    {category.description && (
                      <p className="mt-2 text-sm text-neutral-400">{category.description}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )

      case 'tags':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-white">Tags</h3>
              <button
                onClick={handleCreateTag}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                New Tag
              </button>
            </div>

            {tagsLoading ? (
              <div className="text-center py-8 text-neutral-400">Loading tags...</div>
            ) : (
              <div className="flex flex-wrap gap-3">
                {tagsData?.tags.map((tag) => (
                  <div
                    key={tag.id}
                    className="flex items-center gap-2 px-4 py-2 bg-neutral-900 border border-neutral-800 rounded-full group"
                  >
                    {tag.color && (
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: tag.color }}
                      />
                    )}
                    <span className="text-white">{tag.name}</span>
                    <span className="text-neutral-500 text-sm">({tag.usage_count})</span>
                    <button
                      onClick={() => handleDeleteTag(tag.id)}
                      className="p-1 text-neutral-400 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )

      case 'authors':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-white">Authors</h3>
              <button
                onClick={handleCreateAuthor}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                New Author
              </button>
            </div>

            {authorsLoading ? (
              <div className="text-center py-8 text-neutral-400">Loading authors...</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {authorsData?.authors.map((author) => (
                  <div
                    key={author.id}
                    className="p-4 bg-neutral-900 border border-neutral-800 rounded-xl"
                  >
                    <div className="flex items-center gap-4">
                      {author.avatar_url ? (
                        <img
                          src={author.avatar_url}
                          alt={author.name}
                          className="w-12 h-12 rounded-full object-cover"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded-full bg-neutral-800 flex items-center justify-center">
                          <Users className="w-6 h-6 text-neutral-500" />
                        </div>
                      )}
                      <div className="flex-1">
                        <div className="font-medium text-white">{author.name}</div>
                        {author.job_title && (
                          <div className="text-sm text-neutral-500">{author.job_title}</div>
                        )}
                      </div>
                      <button
                        onClick={() => handleDeleteAuthor(author.id)}
                        className="p-2 text-neutral-400 hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    {author.bio && (
                      <p className="mt-3 text-sm text-neutral-400 line-clamp-2">{author.bio}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )

      case 'pages':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-white">Static Pages</h3>
              <button
                onClick={() => {/* TODO: Page editor */}}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                New Page
              </button>
            </div>

            {pagesLoading ? (
              <div className="text-center py-8 text-neutral-400">Loading pages...</div>
            ) : (
              <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
                <table className="w-full">
                  <thead className="bg-neutral-800/50">
                    <tr>
                      <th className="text-left px-4 py-3 text-sm font-medium text-neutral-400">Title</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-neutral-400">Status</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-neutral-400">In Nav</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-neutral-400">Template</th>
                      <th className="text-right px-4 py-3 text-sm font-medium text-neutral-400">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pagesData?.pages.map((page) => (
                      <tr key={page.id} className="border-t border-neutral-800 hover:bg-neutral-800/30">
                        <td className="px-4 py-3">
                          <div className="font-medium text-white">{page.title}</div>
                          <div className="text-sm text-neutral-500">/{page.slug}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn(
                            'px-2 py-1 text-xs rounded-full',
                            page.status === 'published' ? 'bg-green-600 text-green-200' : 'bg-neutral-600 text-neutral-200'
                          )}>
                            {page.status}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {page.show_in_navigation ? (
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          ) : (
                            <span className="text-neutral-500">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-neutral-400">{page.template}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              className="p-2 text-neutral-400 hover:text-white transition-colors"
                              title="Edit"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => deletePage.mutate(page.id)}
                              className="p-2 text-neutral-400 hover:text-red-400 transition-colors"
                              title="Delete"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {pagesData?.total === 0 && (
                  <div className="text-center py-8 text-neutral-400">No pages found</div>
                )}
              </div>
            )}
          </div>
        )

      case 'contacts':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-white">Contact Inbox</h3>
              <button
                onClick={() => refetchContacts()}
                className="flex items-center gap-2 px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-white rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
            </div>

            {contactsLoading ? (
              <div className="text-center py-8 text-neutral-400">Loading contacts...</div>
            ) : (
              <div className="space-y-3">
                {contactsData?.contacts.map((contact) => (
                  <div
                    key={contact.id}
                    className={cn(
                      'p-4 bg-neutral-900 border rounded-xl transition-colors',
                      contact.is_read ? 'border-neutral-800' : 'border-blue-600/50 bg-blue-600/5'
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        {contact.is_read ? (
                          <MailOpen className="w-5 h-5 text-neutral-500 mt-0.5" />
                        ) : (
                          <Mail className="w-5 h-5 text-blue-500 mt-0.5" />
                        )}
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-white">{contact.name}</span>
                            <span className="text-neutral-500">&lt;{contact.email}&gt;</span>
                            {contact.is_spam && (
                              <span className="px-2 py-0.5 text-xs bg-red-600/20 text-red-400 rounded-full">
                                Spam
                              </span>
                            )}
                          </div>
                          {contact.subject && (
                            <div className="text-sm text-neutral-400 mt-1">{contact.subject}</div>
                          )}
                          <p className="text-sm text-neutral-300 mt-2 line-clamp-2">{contact.message}</p>
                          <div className="flex items-center gap-4 mt-2 text-xs text-neutral-500">
                            <span>{new Date(contact.created_at).toLocaleString()}</span>
                            {contact.company && <span>Company: {contact.company}</span>}
                            {contact.phone && <span>Phone: {contact.phone}</span>}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleMarkRead(contact.id, !contact.is_read)}
                          className="p-2 text-neutral-400 hover:text-white transition-colors"
                          title={contact.is_read ? 'Mark unread' : 'Mark read'}
                        >
                          {contact.is_read ? <Mail className="w-4 h-4" /> : <MailOpen className="w-4 h-4" />}
                        </button>
                        <button
                          onClick={() => handleMarkSpam(contact.id, !contact.is_spam)}
                          className={cn(
                            'p-2 transition-colors',
                            contact.is_spam ? 'text-red-400' : 'text-neutral-400 hover:text-red-400'
                          )}
                          title={contact.is_spam ? 'Not spam' : 'Mark as spam'}
                        >
                          <AlertTriangle className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
                {contactsData?.total === 0 && (
                  <div className="text-center py-8 text-neutral-400">No messages yet</div>
                )}
              </div>
            )}
          </div>
        )
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Content Management</h1>
          <p className="text-neutral-400">Manage blog posts, pages, and site content</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 p-1 bg-neutral-900 border border-neutral-800 rounded-xl w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              activeTab === tab.id
                ? 'bg-blue-600 text-white'
                : 'text-neutral-400 hover:text-white hover:bg-neutral-800'
            )}
          >
            {tab.icon}
            {tab.label}
            {tab.id === 'contacts' && contactsData?.contacts.filter((c) => !c.is_read).length > 0 && (
              <span className="px-1.5 py-0.5 text-xs bg-blue-500 text-white rounded-full">
                {contactsData?.contacts.filter((c) => !c.is_read).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      {renderContent()}

      {/* Post Editor Modal */}
      {showPostEditor && (
        <PostEditor
          post={editingPost}
          categories={categoriesData?.categories || []}
          authors={authorsData?.authors || []}
          tags={tagsData?.tags || []}
          onSave={handleSavePost}
          onCancel={() => {
            setShowPostEditor(false)
            setEditingPost(undefined)
          }}
          isLoading={createPost.isPending || updatePost.isPending}
        />
      )}

      {/* Schedule Modal */}
      {showScheduleModal && selectedPostForWorkflow && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-white mb-4">Schedule Post</h3>
            <p className="text-neutral-400 text-sm mb-4">
              Schedule "{selectedPostForWorkflow.title}" for future publishing.
            </p>
            <input
              type="datetime-local"
              value={scheduleDate}
              onChange={(e) => setScheduleDate(e.target.value)}
              className="w-full px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white mb-4"
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setShowScheduleModal(false); setScheduleDate(''); setSelectedPostForWorkflow(null) }}
                className="px-4 py-2 text-neutral-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSchedule}
                disabled={!scheduleDate || schedulePost.isPending}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 transition-colors"
              >
                {schedulePost.isPending ? 'Scheduling...' : 'Schedule'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && selectedPostForWorkflow && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-white mb-4">Reject Post</h3>
            <p className="text-neutral-400 text-sm mb-4">
              Reject "{selectedPostForWorkflow.title}". Please provide a reason (min 10 characters).
            </p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Reason for rejection..."
              rows={4}
              className="w-full px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white mb-4 resize-none"
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setShowRejectModal(false); setRejectReason(''); setSelectedPostForWorkflow(null) }}
                className="px-4 py-2 text-neutral-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={rejectReason.length < 10 || rejectPost.isPending}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg disabled:opacity-50 transition-colors"
              >
                {rejectPost.isPending ? 'Rejecting...' : 'Reject'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Request Changes Modal */}
      {showChangesModal && selectedPostForWorkflow && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-white mb-4">Request Changes</h3>
            <p className="text-neutral-400 text-sm mb-4">
              Request changes on "{selectedPostForWorkflow.title}". Describe what needs to be changed (min 10 characters).
            </p>
            <textarea
              value={changesNotes}
              onChange={(e) => setChangesNotes(e.target.value)}
              placeholder="Describe required changes..."
              rows={4}
              className="w-full px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white mb-4 resize-none"
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setShowChangesModal(false); setChangesNotes(''); setSelectedPostForWorkflow(null) }}
                className="px-4 py-2 text-neutral-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleRequestChanges}
                disabled={changesNotes.length < 10 || requestChanges.isPending}
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg disabled:opacity-50 transition-colors"
              >
                {requestChanges.isPending ? 'Submitting...' : 'Request Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Workflow History Modal */}
      {showWorkflowHistory && selectedPostForWorkflow && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Workflow History</h3>
              <button
                onClick={() => { setShowWorkflowHistory(false); setSelectedPostForWorkflow(null) }}
                className="p-2 text-neutral-400 hover:text-white transition-colors"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            <p className="text-neutral-400 text-sm mb-4">
              Audit trail for "{selectedPostForWorkflow.title}"
            </p>
            <div className="flex-1 overflow-y-auto space-y-3">
              {workflowHistoryData?.history.map((entry) => (
                <div key={entry.id} className="p-3 bg-neutral-800/50 border border-neutral-700 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className={cn(
                      'px-2 py-0.5 text-xs rounded-full',
                      entry.to_status && statusColors[entry.to_status as PostStatus]
                    )}>
                      {entry.action.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-neutral-500">
                      {entry.created_at && new Date(entry.created_at).toLocaleString()}
                    </span>
                  </div>
                  {entry.from_status && entry.to_status && (
                    <div className="text-sm text-neutral-400">
                      {entry.from_status.replace('_', ' ')} → {entry.to_status.replace('_', ' ')}
                    </div>
                  )}
                  {entry.comment && (
                    <p className="text-sm text-neutral-300 mt-2">{entry.comment}</p>
                  )}
                </div>
              ))}
              {workflowHistoryData?.history.length === 0 && (
                <div className="text-center py-8 text-neutral-500">No workflow history yet</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Version History Modal */}
      {showVersionHistory && selectedPostForWorkflow && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Version History</h3>
              <button
                onClick={() => { setShowVersionHistory(false); setSelectedPostForWorkflow(null) }}
                className="p-2 text-neutral-400 hover:text-white transition-colors"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            <p className="text-neutral-400 text-sm mb-4">
              Content versions for "{selectedPostForWorkflow.title}" (Current: v{versionHistoryData?.current_version || 1})
            </p>
            <div className="flex-1 overflow-y-auto space-y-3">
              {versionHistoryData?.versions.map((version) => (
                <div key={version.id} className="p-3 bg-neutral-800/50 border border-neutral-700 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="px-2 py-0.5 text-xs bg-blue-600/20 text-blue-400 rounded-full">
                      Version {version.version}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-neutral-500">
                        {version.created_at && new Date(version.created_at).toLocaleString()}
                      </span>
                      {version.version !== versionHistoryData?.current_version && (
                        <button
                          onClick={() => {
                            if (confirm(`Restore to version ${version.version}?`)) {
                              restoreVersion.mutate({ postId: selectedPostForWorkflow.id, version: version.version })
                            }
                          }}
                          className="p-1 text-neutral-400 hover:text-white transition-colors"
                          title="Restore this version"
                        >
                          <RotateCcw className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="text-sm font-medium text-white">{version.title}</div>
                  {version.change_summary && (
                    <p className="text-sm text-neutral-400 mt-1">{version.change_summary}</p>
                  )}
                  <div className="flex items-center gap-4 mt-2 text-xs text-neutral-500">
                    {version.word_count && <span>{version.word_count} words</span>}
                    {version.reading_time_minutes && <span>{version.reading_time_minutes} min read</span>}
                  </div>
                </div>
              ))}
              {versionHistoryData?.versions.length === 0 && (
                <div className="text-center py-8 text-neutral-500">No version history yet</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
