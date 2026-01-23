/**
 * Stratum AI - CMS (Content Management System) API Client
 *
 * API client with TypeScript types and React Query hooks for CMS endpoints.
 * Handles blog posts, pages, categories, tags, authors, and contact submissions.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// =============================================================================
// TypeScript Types
// =============================================================================

// Status Types (2026 Workflow Standard)
export type PostStatus =
  | 'draft'
  | 'in_review'
  | 'changes_requested'
  | 'approved'
  | 'scheduled'
  | 'published'
  | 'unpublished'
  | 'archived'
  | 'rejected'

export type ContentType = 'blog_post' | 'case_study' | 'guide' | 'whitepaper' | 'announcement' | 'newsletter' | 'press_release'
export type PageStatus = 'draft' | 'in_review' | 'approved' | 'published' | 'archived'

// 2026 CMS Roles
export type CMSRole =
  | 'super_admin'
  | 'admin'
  | 'editor_in_chief'
  | 'editor'
  | 'author'
  | 'contributor'
  | 'reviewer'
  | 'viewer'

// 2026 Workflow Actions
export type WorkflowAction =
  | 'created'
  | 'updated'
  | 'submitted_for_review'
  | 'approved'
  | 'rejected'
  | 'changes_requested'
  | 'scheduled'
  | 'published'
  | 'unpublished'
  | 'archived'
  | 'restored'
  | 'deleted'

// Category Types
export interface CMSCategory {
  id: string
  name: string
  slug: string
  description?: string
  color?: string
  icon?: string
  display_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CategoryCreate {
  name: string
  slug?: string
  description?: string
  color?: string
  icon?: string
  display_order?: number
  is_active?: boolean
}

export interface CategoryUpdate {
  name?: string
  slug?: string
  description?: string
  color?: string
  icon?: string
  display_order?: number
  is_active?: boolean
}

export interface CategoryListResponse {
  categories: CMSCategory[]
  total: number
}

// Tag Types
export interface CMSTag {
  id: string
  name: string
  slug: string
  description?: string
  color?: string
  usage_count: number
  created_at: string
  updated_at: string
}

export interface TagCreate {
  name: string
  slug?: string
  description?: string
  color?: string
}

export interface TagUpdate {
  name?: string
  slug?: string
  description?: string
  color?: string
}

export interface TagListResponse {
  tags: CMSTag[]
  total: number
}

// Author Types
export interface CMSAuthor {
  id: string
  user_id?: number
  name: string
  slug: string
  email?: string
  bio?: string
  avatar_url?: string
  job_title?: string
  company?: string
  twitter_handle?: string
  linkedin_url?: string
  github_handle?: string
  website_url?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AuthorCreate {
  name: string
  slug?: string
  email?: string
  bio?: string
  avatar_url?: string
  job_title?: string
  company?: string
  twitter_handle?: string
  linkedin_url?: string
  github_handle?: string
  website_url?: string
  user_id?: number
  is_active?: boolean
}

export interface AuthorUpdate {
  name?: string
  slug?: string
  email?: string
  bio?: string
  avatar_url?: string
  job_title?: string
  company?: string
  twitter_handle?: string
  linkedin_url?: string
  github_handle?: string
  website_url?: string
  user_id?: number
  is_active?: boolean
}

export interface AuthorListResponse {
  authors: CMSAuthor[]
  total: number
}

// Post Types
export interface CMSPost {
  id: string
  title: string
  slug: string
  excerpt?: string
  content?: string
  content_json?: Record<string, unknown>
  status: PostStatus
  content_type: ContentType
  published_at?: string
  scheduled_at?: string
  meta_title?: string
  meta_description?: string
  canonical_url?: string
  og_image_url?: string
  featured_image_url?: string
  featured_image_alt?: string
  reading_time_minutes?: number
  word_count?: number
  view_count: number
  is_featured: boolean
  allow_comments: boolean
  category?: CMSCategory
  author?: CMSAuthor
  tags: CMSTag[]
  created_at: string
  updated_at: string
}

export interface PostPublic {
  id: string
  title: string
  slug: string
  excerpt?: string
  content?: string
  published_at?: string
  meta_title?: string
  meta_description?: string
  og_image_url?: string
  featured_image_url?: string
  featured_image_alt?: string
  reading_time_minutes?: number
  view_count: number
  is_featured: boolean
  content_type: ContentType
  category?: CMSCategory
  author?: CMSAuthor
  tags: CMSTag[]
}

export interface PostCreate {
  title: string
  slug?: string
  excerpt?: string
  content?: string
  content_json?: Record<string, unknown>
  status?: PostStatus
  content_type?: ContentType
  category_id?: string
  author_id?: string
  tag_ids?: string[]
  published_at?: string
  scheduled_at?: string
  meta_title?: string
  meta_description?: string
  canonical_url?: string
  og_image_url?: string
  featured_image_url?: string
  featured_image_alt?: string
  reading_time_minutes?: number
  is_featured?: boolean
  allow_comments?: boolean
}

export interface PostUpdate {
  title?: string
  slug?: string
  excerpt?: string
  content?: string
  content_json?: Record<string, unknown>
  status?: PostStatus
  content_type?: ContentType
  category_id?: string
  author_id?: string
  tag_ids?: string[]
  published_at?: string
  scheduled_at?: string
  meta_title?: string
  meta_description?: string
  canonical_url?: string
  og_image_url?: string
  featured_image_url?: string
  featured_image_alt?: string
  reading_time_minutes?: number
  is_featured?: boolean
  allow_comments?: boolean
}

export interface PostListResponse {
  posts: CMSPost[]
  total: number
  page: number
  page_size: number
}

export interface PostPublicListResponse {
  posts: PostPublic[]
  total: number
  page: number
  page_size: number
}

// Page Types
export interface CMSPage {
  id: string
  title: string
  slug: string
  content?: string
  content_json?: Record<string, unknown>
  status: PageStatus
  published_at?: string
  meta_title?: string
  meta_description?: string
  show_in_navigation: boolean
  navigation_label?: string
  navigation_order: number
  template: string
  created_at: string
  updated_at: string
}

export interface PageCreate {
  title: string
  slug?: string
  content?: string
  content_json?: Record<string, unknown>
  status?: PageStatus
  meta_title?: string
  meta_description?: string
  show_in_navigation?: boolean
  navigation_label?: string
  navigation_order?: number
  template?: string
}

export interface PageUpdate {
  title?: string
  slug?: string
  content?: string
  content_json?: Record<string, unknown>
  status?: PageStatus
  meta_title?: string
  meta_description?: string
  show_in_navigation?: boolean
  navigation_label?: string
  navigation_order?: number
  template?: string
}

export interface PageListResponse {
  pages: CMSPage[]
  total: number
}

// Contact Types
export interface CMSContact {
  id: string
  name: string
  email: string
  company?: string
  phone?: string
  subject?: string
  message: string
  source_page?: string
  is_read: boolean
  read_at?: string
  is_responded: boolean
  responded_at?: string
  response_notes?: string
  is_spam: boolean
  created_at: string
}

export interface ContactSubmit {
  name: string
  email: string
  company?: string
  phone?: string
  subject?: string
  message: string
  source_page?: string
}

export interface ContactListResponse {
  contacts: CMSContact[]
  total: number
  page: number
  page_size: number
}

// Filter Types
export interface PostFilters {
  page?: number
  page_size?: number
  category_slug?: string
  tag_slug?: string
  content_type?: ContentType
  search?: string
  featured_only?: boolean
}

export interface AdminPostFilters extends PostFilters {
  status_filter?: PostStatus
}

export interface ContactFilters {
  page?: number
  page_size?: number
  unread_only?: boolean
  exclude_spam?: boolean
}

// =============================================================================
// 2026 Workflow Types
// =============================================================================

export interface WorkflowHistoryEntry {
  id: string
  action: WorkflowAction
  from_status?: string
  to_status?: string
  performed_by_id?: number
  comment?: string
  version_number?: number
  extra_data?: Record<string, unknown>
  created_at?: string
}

export interface WorkflowHistoryResponse {
  post_id: string
  history: WorkflowHistoryEntry[]
  total: number
  page: number
  page_size: number
}

export interface PostVersion {
  id: string
  version: number
  title: string
  slug: string
  excerpt?: string
  change_summary?: string
  change_type?: string
  word_count?: number
  reading_time_minutes?: number
  created_by_id?: number
  created_at?: string
}

export interface VersionHistoryResponse {
  post_id: string
  current_version: number
  versions: PostVersion[]
  total: number
  page: number
  page_size: number
}

export interface WorkflowActionResponse {
  post_id: string
  status: PostStatus
  submitted_at?: string
  approved_at?: string
  rejected_at?: string
  scheduled_at?: string
  published_at?: string
  assigned_reviewer_id?: number
  rejection_reason?: string
  review_notes?: string
}

export interface RestoreVersionResponse {
  post_id: string
  restored_from_version: number
  new_version: number
}

// =============================================================================
// Query Keys
// =============================================================================

export const cmsKeys = {
  all: ['cms'] as const,
  // Posts
  posts: () => [...cmsKeys.all, 'posts'] as const,
  postsList: (filters: PostFilters) => [...cmsKeys.posts(), 'list', filters] as const,
  postsDetail: (slug: string) => [...cmsKeys.posts(), 'detail', slug] as const,
  postsAdmin: (filters: AdminPostFilters) => [...cmsKeys.posts(), 'admin', filters] as const,
  postsAdminDetail: (id: string) => [...cmsKeys.posts(), 'admin', 'detail', id] as const,
  // Categories
  categories: () => [...cmsKeys.all, 'categories'] as const,
  categoriesList: (activeOnly?: boolean) => [...cmsKeys.categories(), { activeOnly }] as const,
  // Tags
  tags: () => [...cmsKeys.all, 'tags'] as const,
  tagsList: () => [...cmsKeys.tags(), 'list'] as const,
  // Authors
  authors: () => [...cmsKeys.all, 'authors'] as const,
  authorsList: () => [...cmsKeys.authors(), 'list'] as const,
  // Pages
  pages: () => [...cmsKeys.all, 'pages'] as const,
  pagesList: () => [...cmsKeys.pages(), 'list'] as const,
  // Contacts
  contacts: () => [...cmsKeys.all, 'contacts'] as const,
  contactsList: (filters: ContactFilters) => [...cmsKeys.contacts(), 'list', filters] as const,
  // 2026 Workflow
  workflow: () => [...cmsKeys.all, 'workflow'] as const,
  workflowHistory: (postId: string) => [...cmsKeys.workflow(), 'history', postId] as const,
  versions: () => [...cmsKeys.all, 'versions'] as const,
  versionHistory: (postId: string) => [...cmsKeys.versions(), postId] as const,
}

// =============================================================================
// Public API Functions
// =============================================================================

// Posts (Public)
export const fetchPublishedPosts = async (filters: PostFilters = {}): Promise<PostPublicListResponse> => {
  const params = new URLSearchParams()
  if (filters.page) params.append('page', String(filters.page))
  if (filters.page_size) params.append('page_size', String(filters.page_size))
  if (filters.category_slug) params.append('category_slug', filters.category_slug)
  if (filters.tag_slug) params.append('tag_slug', filters.tag_slug)
  if (filters.content_type) params.append('content_type', filters.content_type)
  if (filters.search) params.append('search', filters.search)
  if (filters.featured_only) params.append('featured_only', 'true')

  const response = await apiClient.get<ApiResponse<PostPublicListResponse>>(
    `/cms/posts?${params.toString()}`
  )
  return response.data.data
}

export const fetchPostBySlug = async (slug: string): Promise<PostPublic> => {
  const response = await apiClient.get<ApiResponse<PostPublic>>(`/cms/posts/${slug}`)
  return response.data.data
}

// Categories (Public)
export const fetchCategories = async (activeOnly = true): Promise<CategoryListResponse> => {
  const response = await apiClient.get<ApiResponse<CategoryListResponse>>(
    `/cms/categories?active_only=${activeOnly}`
  )
  return response.data.data
}

// Tags (Public)
export const fetchTags = async (): Promise<TagListResponse> => {
  const response = await apiClient.get<ApiResponse<TagListResponse>>('/cms/tags')
  return response.data.data
}

// Contact Form (Public)
export const submitContactForm = async (data: ContactSubmit): Promise<{ submitted: boolean }> => {
  const response = await apiClient.post<ApiResponse<{ submitted: boolean }>>('/cms/contact', data)
  return response.data.data
}

// =============================================================================
// Admin API Functions
// =============================================================================

// Admin Posts
export const fetchAdminPosts = async (filters: AdminPostFilters = {}): Promise<PostListResponse> => {
  const params = new URLSearchParams()
  if (filters.page) params.append('page', String(filters.page))
  if (filters.page_size) params.append('page_size', String(filters.page_size))
  if (filters.status_filter) params.append('status_filter', filters.status_filter)
  if (filters.content_type) params.append('content_type', filters.content_type)
  if (filters.search) params.append('search', filters.search)

  const response = await apiClient.get<ApiResponse<PostListResponse>>(
    `/cms/admin/posts?${params.toString()}`
  )
  return response.data.data
}

export const fetchAdminPost = async (id: string): Promise<CMSPost> => {
  const response = await apiClient.get<ApiResponse<CMSPost>>(`/cms/admin/posts/${id}`)
  return response.data.data
}

export const createPost = async (data: PostCreate): Promise<CMSPost> => {
  const response = await apiClient.post<ApiResponse<CMSPost>>('/cms/admin/posts', data)
  return response.data.data
}

export const updatePost = async (id: string, data: PostUpdate): Promise<CMSPost> => {
  const response = await apiClient.patch<ApiResponse<CMSPost>>(`/cms/admin/posts/${id}`, data)
  return response.data.data
}

export const deletePost = async (id: string): Promise<void> => {
  await apiClient.delete(`/cms/admin/posts/${id}`)
}

// Admin Categories
export const fetchAdminCategories = async (): Promise<CategoryListResponse> => {
  const response = await apiClient.get<ApiResponse<CategoryListResponse>>('/cms/admin/categories')
  return response.data.data
}

export const createCategory = async (data: CategoryCreate): Promise<CMSCategory> => {
  const response = await apiClient.post<ApiResponse<CMSCategory>>('/cms/admin/categories', data)
  return response.data.data
}

export const updateCategory = async (id: string, data: CategoryUpdate): Promise<CMSCategory> => {
  const response = await apiClient.patch<ApiResponse<CMSCategory>>(`/cms/admin/categories/${id}`, data)
  return response.data.data
}

export const deleteCategory = async (id: string): Promise<void> => {
  await apiClient.delete(`/cms/admin/categories/${id}`)
}

// Admin Tags
export const fetchAdminTags = async (): Promise<TagListResponse> => {
  const response = await apiClient.get<ApiResponse<TagListResponse>>('/cms/admin/tags')
  return response.data.data
}

export const createTag = async (data: TagCreate): Promise<CMSTag> => {
  const response = await apiClient.post<ApiResponse<CMSTag>>('/cms/admin/tags', data)
  return response.data.data
}

export const updateTag = async (id: string, data: TagUpdate): Promise<CMSTag> => {
  const response = await apiClient.patch<ApiResponse<CMSTag>>(`/cms/admin/tags/${id}`, data)
  return response.data.data
}

export const deleteTag = async (id: string): Promise<void> => {
  await apiClient.delete(`/cms/admin/tags/${id}`)
}

// Admin Authors
export const fetchAdminAuthors = async (): Promise<AuthorListResponse> => {
  const response = await apiClient.get<ApiResponse<AuthorListResponse>>('/cms/admin/authors')
  return response.data.data
}

export const createAuthor = async (data: AuthorCreate): Promise<CMSAuthor> => {
  const response = await apiClient.post<ApiResponse<CMSAuthor>>('/cms/admin/authors', data)
  return response.data.data
}

export const updateAuthor = async (id: string, data: AuthorUpdate): Promise<CMSAuthor> => {
  const response = await apiClient.patch<ApiResponse<CMSAuthor>>(`/cms/admin/authors/${id}`, data)
  return response.data.data
}

export const deleteAuthor = async (id: string): Promise<void> => {
  await apiClient.delete(`/cms/admin/authors/${id}`)
}

// Admin Pages
export const fetchAdminPages = async (): Promise<PageListResponse> => {
  const response = await apiClient.get<ApiResponse<PageListResponse>>('/cms/admin/pages')
  return response.data.data
}

export const createPage = async (data: PageCreate): Promise<CMSPage> => {
  const response = await apiClient.post<ApiResponse<CMSPage>>('/cms/admin/pages', data)
  return response.data.data
}

export const updatePage = async (id: string, data: PageUpdate): Promise<CMSPage> => {
  const response = await apiClient.patch<ApiResponse<CMSPage>>(`/cms/admin/pages/${id}`, data)
  return response.data.data
}

export const deletePage = async (id: string): Promise<void> => {
  await apiClient.delete(`/cms/admin/pages/${id}`)
}

// Admin Contacts
export const fetchAdminContacts = async (filters: ContactFilters = {}): Promise<ContactListResponse> => {
  const params = new URLSearchParams()
  if (filters.page) params.append('page', String(filters.page))
  if (filters.page_size) params.append('page_size', String(filters.page_size))
  if (filters.unread_only) params.append('unread_only', 'true')
  if (filters.exclude_spam !== undefined) params.append('exclude_spam', String(filters.exclude_spam))

  const response = await apiClient.get<ApiResponse<ContactListResponse>>(
    `/cms/admin/contacts?${params.toString()}`
  )
  return response.data.data
}

export const markContactRead = async (id: string, isRead: boolean): Promise<CMSContact> => {
  const response = await apiClient.patch<ApiResponse<CMSContact>>(
    `/cms/admin/contacts/${id}/read`,
    { is_read: isRead }
  )
  return response.data.data
}

export const markContactResponded = async (
  id: string,
  isResponded: boolean,
  responseNotes?: string
): Promise<CMSContact> => {
  const response = await apiClient.patch<ApiResponse<CMSContact>>(
    `/cms/admin/contacts/${id}/responded`,
    { is_responded: isResponded, response_notes: responseNotes }
  )
  return response.data.data
}

export const markContactSpam = async (id: string, isSpam: boolean): Promise<CMSContact> => {
  const response = await apiClient.patch<ApiResponse<CMSContact>>(
    `/cms/admin/contacts/${id}/spam`,
    { is_spam: isSpam }
  )
  return response.data.data
}

// =============================================================================
// React Query Hooks - Public
// =============================================================================

export const usePosts = (filters: PostFilters = {}) => {
  return useQuery({
    queryKey: cmsKeys.postsList(filters),
    queryFn: () => fetchPublishedPosts(filters),
  })
}

export const usePost = (slug: string) => {
  return useQuery({
    queryKey: cmsKeys.postsDetail(slug),
    queryFn: () => fetchPostBySlug(slug),
    enabled: !!slug,
  })
}

export const useCategories = (activeOnly = true) => {
  return useQuery({
    queryKey: cmsKeys.categoriesList(activeOnly),
    queryFn: () => fetchCategories(activeOnly),
  })
}

export const useTags = () => {
  return useQuery({
    queryKey: cmsKeys.tagsList(),
    queryFn: fetchTags,
  })
}

export const useSubmitContact = () => {
  return useMutation({
    mutationFn: submitContactForm,
  })
}

// =============================================================================
// React Query Hooks - Admin Posts
// =============================================================================

export const useAdminPosts = (filters: AdminPostFilters = {}) => {
  return useQuery({
    queryKey: cmsKeys.postsAdmin(filters),
    queryFn: () => fetchAdminPosts(filters),
  })
}

export const useAdminPost = (id: string) => {
  return useQuery({
    queryKey: cmsKeys.postsAdminDetail(id),
    queryFn: () => fetchAdminPost(id),
    enabled: !!id,
  })
}

export const useCreatePost = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createPost,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
    },
  })
}

export const useUpdatePost = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PostUpdate }) => updatePost(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
    },
  })
}

export const useDeletePost = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deletePost,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
    },
  })
}

// =============================================================================
// React Query Hooks - Admin Categories
// =============================================================================

export const useAdminCategories = () => {
  return useQuery({
    queryKey: cmsKeys.categories(),
    queryFn: fetchAdminCategories,
  })
}

export const useCreateCategory = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.categories() })
    },
  })
}

export const useUpdateCategory = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CategoryUpdate }) => updateCategory(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.categories() })
    },
  })
}

export const useDeleteCategory = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.categories() })
    },
  })
}

// =============================================================================
// React Query Hooks - Admin Tags
// =============================================================================

export const useAdminTags = () => {
  return useQuery({
    queryKey: cmsKeys.tags(),
    queryFn: fetchAdminTags,
  })
}

export const useCreateTag = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createTag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.tags() })
    },
  })
}

export const useUpdateTag = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TagUpdate }) => updateTag(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.tags() })
    },
  })
}

export const useDeleteTag = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteTag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.tags() })
    },
  })
}

// =============================================================================
// React Query Hooks - Admin Authors
// =============================================================================

export const useAdminAuthors = () => {
  return useQuery({
    queryKey: cmsKeys.authors(),
    queryFn: fetchAdminAuthors,
  })
}

export const useCreateAuthor = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAuthor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.authors() })
    },
  })
}

export const useUpdateAuthor = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AuthorUpdate }) => updateAuthor(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.authors() })
    },
  })
}

export const useDeleteAuthor = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteAuthor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.authors() })
    },
  })
}

// =============================================================================
// React Query Hooks - Admin Pages
// =============================================================================

export const useAdminPages = () => {
  return useQuery({
    queryKey: cmsKeys.pagesList(),
    queryFn: fetchAdminPages,
  })
}

export const useCreatePage = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createPage,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.pages() })
    },
  })
}

export const useUpdatePage = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PageUpdate }) => updatePage(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.pages() })
    },
  })
}

export const useDeletePage = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deletePage,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.pages() })
    },
  })
}

// =============================================================================
// React Query Hooks - Admin Contacts
// =============================================================================

export const useAdminContacts = (filters: ContactFilters = {}) => {
  return useQuery({
    queryKey: cmsKeys.contactsList(filters),
    queryFn: () => fetchAdminContacts(filters),
  })
}

export const useMarkContactRead = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, isRead }: { id: string; isRead: boolean }) => markContactRead(id, isRead),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.contacts() })
    },
  })
}

export const useMarkContactResponded = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, isResponded, responseNotes }: { id: string; isResponded: boolean; responseNotes?: string }) =>
      markContactResponded(id, isResponded, responseNotes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.contacts() })
    },
  })
}

export const useMarkContactSpam = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, isSpam }: { id: string; isSpam: boolean }) => markContactSpam(id, isSpam),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.contacts() })
    },
  })
}

// =============================================================================
// 2026 Workflow API Functions
// =============================================================================

export const submitPostForReview = async (
  postId: string,
  reviewerId?: number
): Promise<WorkflowActionResponse> => {
  const params = reviewerId ? `?reviewer_id=${reviewerId}` : ''
  const response = await apiClient.post<ApiResponse<WorkflowActionResponse>>(
    `/cms/admin/posts/${postId}/submit-for-review${params}`
  )
  return response.data.data
}

export const approvePost = async (
  postId: string,
  notes?: string
): Promise<WorkflowActionResponse> => {
  const params = notes ? `?notes=${encodeURIComponent(notes)}` : ''
  const response = await apiClient.post<ApiResponse<WorkflowActionResponse>>(
    `/cms/admin/posts/${postId}/approve${params}`
  )
  return response.data.data
}

export const rejectPost = async (
  postId: string,
  reason: string
): Promise<WorkflowActionResponse> => {
  const response = await apiClient.post<ApiResponse<WorkflowActionResponse>>(
    `/cms/admin/posts/${postId}/reject?reason=${encodeURIComponent(reason)}`
  )
  return response.data.data
}

export const requestPostChanges = async (
  postId: string,
  notes: string
): Promise<WorkflowActionResponse> => {
  const response = await apiClient.post<ApiResponse<WorkflowActionResponse>>(
    `/cms/admin/posts/${postId}/request-changes?notes=${encodeURIComponent(notes)}`
  )
  return response.data.data
}

export const schedulePost = async (
  postId: string,
  scheduledAt: string
): Promise<WorkflowActionResponse> => {
  const response = await apiClient.post<ApiResponse<WorkflowActionResponse>>(
    `/cms/admin/posts/${postId}/schedule?scheduled_at=${encodeURIComponent(scheduledAt)}`
  )
  return response.data.data
}

export const publishPostImmediately = async (
  postId: string
): Promise<WorkflowActionResponse> => {
  const response = await apiClient.post<ApiResponse<WorkflowActionResponse>>(
    `/cms/admin/posts/${postId}/publish`
  )
  return response.data.data
}

export const unpublishPost = async (
  postId: string
): Promise<WorkflowActionResponse> => {
  const response = await apiClient.post<ApiResponse<WorkflowActionResponse>>(
    `/cms/admin/posts/${postId}/unpublish`
  )
  return response.data.data
}

export const archivePost = async (
  postId: string
): Promise<WorkflowActionResponse> => {
  const response = await apiClient.post<ApiResponse<WorkflowActionResponse>>(
    `/cms/admin/posts/${postId}/archive`
  )
  return response.data.data
}

export const fetchWorkflowHistory = async (
  postId: string,
  page = 1,
  pageSize = 20
): Promise<WorkflowHistoryResponse> => {
  const response = await apiClient.get<ApiResponse<WorkflowHistoryResponse>>(
    `/cms/admin/posts/${postId}/workflow-history?page=${page}&page_size=${pageSize}`
  )
  return response.data.data
}

export const fetchVersionHistory = async (
  postId: string,
  page = 1,
  pageSize = 20
): Promise<VersionHistoryResponse> => {
  const response = await apiClient.get<ApiResponse<VersionHistoryResponse>>(
    `/cms/admin/posts/${postId}/versions?page=${page}&page_size=${pageSize}`
  )
  return response.data.data
}

export const restorePostVersion = async (
  postId: string,
  version: number
): Promise<RestoreVersionResponse> => {
  const response = await apiClient.post<ApiResponse<RestoreVersionResponse>>(
    `/cms/admin/posts/${postId}/restore-version/${version}`
  )
  return response.data.data
}

// =============================================================================
// 2026 Workflow React Query Hooks
// =============================================================================

export const useSubmitForReview = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ postId, reviewerId }: { postId: string; reviewerId?: number }) =>
      submitPostForReview(postId, reviewerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
    },
  })
}

export const useApprovePost = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ postId, notes }: { postId: string; notes?: string }) =>
      approvePost(postId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
    },
  })
}

export const useRejectPost = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ postId, reason }: { postId: string; reason: string }) =>
      rejectPost(postId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
    },
  })
}

export const useRequestChanges = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ postId, notes }: { postId: string; notes: string }) =>
      requestPostChanges(postId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
    },
  })
}

export const useSchedulePost = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ postId, scheduledAt }: { postId: string; scheduledAt: string }) =>
      schedulePost(postId, scheduledAt),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
    },
  })
}

export const usePublishPost = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (postId: string) => publishPostImmediately(postId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
    },
  })
}

export const useUnpublishPost = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (postId: string) => unpublishPost(postId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
    },
  })
}

export const useArchivePost = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (postId: string) => archivePost(postId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
    },
  })
}

export const useWorkflowHistory = (postId: string, page = 1, pageSize = 20) => {
  return useQuery({
    queryKey: cmsKeys.workflowHistory(postId),
    queryFn: () => fetchWorkflowHistory(postId, page, pageSize),
    enabled: !!postId,
  })
}

export const useVersionHistory = (postId: string, page = 1, pageSize = 20) => {
  return useQuery({
    queryKey: cmsKeys.versionHistory(postId),
    queryFn: () => fetchVersionHistory(postId, page, pageSize),
    enabled: !!postId,
  })
}

export const useRestoreVersion = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ postId, version }: { postId: string; version: number }) =>
      restorePostVersion(postId, version),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
      queryClient.invalidateQueries({ queryKey: cmsKeys.versionHistory(variables.postId) })
      queryClient.invalidateQueries({ queryKey: cmsKeys.workflowHistory(variables.postId) })
    },
  })
}

// =============================================================================
// 2026 Workflow Status Helpers
// =============================================================================

export const WORKFLOW_STATUS_CONFIG: Record<PostStatus, {
  label: string
  color: string
  bgColor: string
  description: string
  allowedActions: string[]
}> = {
  draft: {
    label: 'Draft',
    color: 'text-gray-400',
    bgColor: 'bg-gray-500/20',
    description: 'Work in progress, not yet submitted',
    allowedActions: ['submit_for_review', 'schedule', 'publish'],
  },
  in_review: {
    label: 'In Review',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/20',
    description: 'Waiting for reviewer approval',
    allowedActions: ['approve', 'reject', 'request_changes'],
  },
  changes_requested: {
    label: 'Changes Requested',
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/20',
    description: 'Reviewer requested modifications',
    allowedActions: ['submit_for_review'],
  },
  approved: {
    label: 'Approved',
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    description: 'Ready to publish or schedule',
    allowedActions: ['publish', 'schedule'],
  },
  scheduled: {
    label: 'Scheduled',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    description: 'Will be published automatically',
    allowedActions: ['publish', 'unschedule'],
  },
  published: {
    label: 'Published',
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/20',
    description: 'Live and visible to readers',
    allowedActions: ['unpublish', 'archive'],
  },
  unpublished: {
    label: 'Unpublished',
    color: 'text-gray-400',
    bgColor: 'bg-gray-500/20',
    description: 'Temporarily taken offline',
    allowedActions: ['publish', 'archive'],
  },
  archived: {
    label: 'Archived',
    color: 'text-gray-500',
    bgColor: 'bg-gray-600/20',
    description: 'Permanently archived',
    allowedActions: ['restore'],
  },
  rejected: {
    label: 'Rejected',
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    description: 'Did not pass review',
    allowedActions: ['submit_for_review'],
  },
}

export const getStatusConfig = (status: PostStatus) => {
  return WORKFLOW_STATUS_CONFIG[status] || WORKFLOW_STATUS_CONFIG.draft
}

// =============================================================================
// Landing Page Content Hooks (Features, FAQ, Pricing)
// =============================================================================

/**
 * Content category slugs for landing page content
 */
export const CONTENT_CATEGORIES = {
  FEATURES: 'landing-features',
  FAQ: 'landing-faq',
  PRICING: 'landing-pricing',
  FAQ_PRICING: 'faq-pricing',
  FAQ_FEATURES: 'faq-features',
  FAQ_TRUST_ENGINE: 'faq-trust-engine',
  FAQ_INTEGRATIONS: 'faq-integrations',
  FAQ_DATA: 'faq-data',
  FAQ_SUPPORT: 'faq-support',
} as const

/**
 * Feature layer structure for landing page
 */
export interface FeatureLayer {
  id: string
  name: string
  description: string
  color: string
  bgColor: string
  borderColor: string
  iconName: string
  displayOrder: number
  features: FeatureItem[]
}

export interface FeatureItem {
  id: string
  title: string
  description: string
  iconName: string
  displayOrder: number
}

/**
 * FAQ item structure
 */
export interface FAQItem {
  id: string
  question: string
  answer: string
  category: string
  displayOrder: number
}

/**
 * Pricing tier structure
 */
export interface PricingTier {
  id: string
  name: string
  description: string
  price: string
  period: string
  adSpend: string
  features: string[]
  cta: string
  ctaLink: string
  highlighted: boolean
  badge?: string
  displayOrder: number
}

/**
 * Trust badge structure
 */
export interface TrustBadge {
  id: string
  icon: string
  text: string
  displayOrder: number
}

/**
 * Fetch posts by category slug
 */
async function fetchPostsByCategory(
  categorySlug: string,
  status: PostStatus = 'published'
): Promise<CMSPost[]> {
  try {
    const response = await apiClient.get<{ posts: CMSPost[]; total: number }>(
      `/cms/posts?category=${categorySlug}&status=${status}`
    )
    return response.data.posts || []
  } catch {
    return []
  }
}

/**
 * Parse feature layers from CMS posts
 * Posts should have metadata with layer info
 */
function parseFeatureLayers(posts: CMSPost[]): FeatureLayer[] {
  // Group posts by layer (stored in metadata.layer)
  const layers = new Map<string, FeatureLayer>()

  posts.forEach((post) => {
    const meta = (post.meta || {}) as Record<string, unknown>
    const layerId = (meta.layerId as string) || 'default'

    if (!layers.has(layerId)) {
      layers.set(layerId, {
        id: layerId,
        name: (meta.layerName as string) || 'Features',
        description: (meta.layerDescription as string) || '',
        color: (meta.layerColor as string) || 'from-stratum-500 to-cyan-500',
        bgColor: (meta.layerBgColor as string) || 'bg-stratum-500/10',
        borderColor: (meta.layerBorderColor as string) || 'border-stratum-500/20',
        iconName: (meta.layerIcon as string) || 'SparklesIcon',
        displayOrder: (meta.layerOrder as number) || 0,
        features: [],
      })
    }

    const layer = layers.get(layerId)!
    layer.features.push({
      id: post.id,
      title: post.title,
      description: post.excerpt || '',
      iconName: (meta.featureIcon as string) || 'ChartBarIcon',
      displayOrder: (meta.displayOrder as number) || 0,
    })
  })

  // Sort layers and features
  return Array.from(layers.values())
    .sort((a, b) => a.displayOrder - b.displayOrder)
    .map((layer) => ({
      ...layer,
      features: layer.features.sort((a, b) => a.displayOrder - b.displayOrder),
    }))
}

/**
 * Parse FAQ items from CMS posts
 */
function parseFAQItems(posts: CMSPost[]): FAQItem[] {
  return posts
    .map((post) => {
      const meta = (post.meta || {}) as Record<string, unknown>
      return {
        id: post.id,
        question: post.title,
        answer: post.content || post.excerpt || '',
        category: (meta.faqCategory as string) || 'general',
        displayOrder: (meta.displayOrder as number) || 0,
      }
    })
    .sort((a, b) => a.displayOrder - b.displayOrder)
}

/**
 * Parse pricing tiers from CMS posts
 */
function parsePricingTiers(posts: CMSPost[]): PricingTier[] {
  return posts
    .map((post) => {
      const meta = (post.meta || {}) as Record<string, unknown>
      return {
        id: post.id,
        name: post.title,
        description: post.excerpt || '',
        price: (meta.price as string) || '$0',
        period: (meta.period as string) || '/month',
        adSpend: (meta.adSpend as string) || '',
        features: (meta.features as string[]) || [],
        cta: (meta.cta as string) || 'Get Started',
        ctaLink: (meta.ctaLink as string) || '/signup',
        highlighted: (meta.highlighted as boolean) || false,
        badge: meta.badge as string | undefined,
        displayOrder: (meta.displayOrder as number) || 0,
      }
    })
    .sort((a, b) => a.displayOrder - b.displayOrder)
}

/**
 * Hook: Fetch feature layers for landing page
 */
export const useFeatureLayers = () => {
  return useQuery({
    queryKey: [...cmsKeys.posts(), 'features'],
    queryFn: async () => {
      const posts = await fetchPostsByCategory(CONTENT_CATEGORIES.FEATURES)
      return parseFeatureLayers(posts)
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook: Fetch FAQ items
 */
export const useFAQItems = (category?: string) => {
  return useQuery({
    queryKey: [...cmsKeys.posts(), 'faq', category],
    queryFn: async () => {
      // Fetch all FAQ posts
      const categorySlug = category
        ? `faq-${category}`
        : CONTENT_CATEGORIES.FAQ
      const posts = await fetchPostsByCategory(categorySlug)
      return parseFAQItems(posts)
    },
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Hook: Fetch all FAQ items from all categories
 */
export const useAllFAQItems = () => {
  return useQuery({
    queryKey: [...cmsKeys.posts(), 'faq', 'all'],
    queryFn: async () => {
      // Fetch from main FAQ category
      const posts = await fetchPostsByCategory(CONTENT_CATEGORIES.FAQ)
      return parseFAQItems(posts)
    },
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Hook: Fetch pricing tiers
 */
export const usePricingTiers = () => {
  return useQuery({
    queryKey: [...cmsKeys.posts(), 'pricing'],
    queryFn: async () => {
      const posts = await fetchPostsByCategory(CONTENT_CATEGORIES.PRICING)
      return parsePricingTiers(posts)
    },
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Hook: Fetch trust badges
 */
export const useTrustBadges = () => {
  return useQuery({
    queryKey: [...cmsKeys.posts(), 'trust-badges'],
    queryFn: async () => {
      const posts = await fetchPostsByCategory('landing-trust-badges')
      return posts.map((post) => {
        const meta = (post.meta || {}) as Record<string, unknown>
        return {
          id: post.id,
          icon: (meta.icon as string) || '✓',
          text: post.title,
          displayOrder: (meta.displayOrder as number) || 0,
        }
      }).sort((a, b) => a.displayOrder - b.displayOrder) as TrustBadge[]
    },
    staleTime: 5 * 60 * 1000,
  })
}
