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

const statusColors: Record<PostStatus, string> = {
  draft: 'bg-neutral-600 text-neutral-200',
  scheduled: 'bg-blue-600 text-blue-200',
  published: 'bg-green-600 text-green-200',
  archived: 'bg-orange-600 text-orange-200',
}

export default function CMS() {
  const [activeTab, setActiveTab] = useState<TabType>('posts')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<PostStatus | ''>('')
  const [showPostEditor, setShowPostEditor] = useState(false)
  const [editingPost, setEditingPost] = useState<CMSPost | undefined>()
  const [page, setPage] = useState(1)

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
                  <option value="scheduled">Scheduled</option>
                  <option value="published">Published</option>
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
                    {postsData?.posts.map((post) => (
                      <tr key={post.id} className="border-t border-neutral-800 hover:bg-neutral-800/30">
                        <td className="px-4 py-3">
                          <div className="font-medium text-white">{post.title}</div>
                          <div className="text-sm text-neutral-500">/blog/{post.slug}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn('px-2 py-1 text-xs rounded-full', statusColors[post.status])}>
                            {post.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-neutral-400">{post.author?.name || '-'}</td>
                        <td className="px-4 py-3 text-neutral-400">{post.view_count}</td>
                        <td className="px-4 py-3 text-neutral-400 text-sm">
                          {new Date(post.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleEditPost(post)}
                              className="p-2 text-neutral-400 hover:text-white transition-colors"
                              title="Edit"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDeletePost(post.id)}
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
    </div>
  )
}
